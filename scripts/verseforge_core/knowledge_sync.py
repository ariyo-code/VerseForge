"""Read-only knowledge repository freshness and reproducible version pinning.

No network updates or unsupported claims. Upstream API snapshots are not
validated merely because the repo version is high.
"""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

_API = re.compile(r"(?i)(?:api\s+(?:snapshot|version)|snapshot\s+api)\s*[:=]?\s*(?:v)?(\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)")
_VERSION = re.compile(r"^\d{1,3}\.\d{1,3}(?:\.\d{1,3})?$|^unknown$")


def knowledge_audit(repo: Path, target_uefn: str, expected_commit: str | None = None) -> dict[str, Any]:
    """No git fetch or mutation; reports only current local knowledge state."""
    repo = Path(repo).expanduser().resolve(strict=True)
    if not repo.is_dir() or not (repo/'AI_BOOTSTRAP.md').is_file():
        raise ValueError('Path is not a recognized Verse-AI-Knowledge checkout')
    if not isinstance(target_uefn,str) or not _VERSION.fullmatch(target_uefn) or target_uefn=='unknown':
        raise ValueError('Target UEFN version is required (e.g. 43.10)')
    if expected_commit and not re.fullmatch(r'[a-f0-9]{40}',expected_commit):
        raise ValueError('Expected SHA must be a full lowercase Git commit hash')
    paths = ('VERSION.md','README.md','AI_BOOTSTRAP.md','knowledge/ROUTING.md')
    samples = []
    found = []
    for path in paths:
        file = repo/path
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 1_000_000:
            continue
        content = file.read_text(encoding='utf-8',errors='replace')
        sha = hashlib.sha256(content.encode()).hexdigest()
        samples.append({'path':path,'sha256':sha})
        matches = _API.findall(content)
        for match in matches:
            found.append({'path':path,'version':match})
    try:
        run = subprocess.run(['git','-C',str(repo),'rev-parse','--verify','HEAD'],
                             capture_output=True,text=True,timeout=5,check=False)
        commit = run.stdout.strip() if run.returncode==0 and re.fullmatch(r'[a-f0-9]{40}',run.stdout.strip()) else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        commit = None
    values = sorted({x['version'] for x in found})
    snap = values[0] if len(values)==1 else None
    if expected_commit and commit != expected_commit:
        status='COMMIT_MISMATCH'
    elif len(values)>1:
        status='CONFLICTING_SNAPSHOTS'
    elif not values:
        status='SNAPSHOT_NOT_DECLARED'
    elif snap != target_uefn:
        status='API_SNAPSHOT_MISMATCH'
    else:
        status='SNAPSHOT_MATCH_DECLARATION_ONLY'
    return {'schema':'verseforge-knowledge-audit-v1','status':status,'checkout':str(repo),
            'target_uefn':target_uefn,'declared_snapshots':found,'commit':commit,
            'expected_commit':expected_commit,'sampled_files':samples,
            'api_verified':'NOT VERIFIED','compile':'NOT TESTED',
            'note':'Snapshot declaration and Git commit pinning do not prove that the API implementation works. Use exact field claims and editor evidence.'}


def make_lock(report: dict[str,Any], output: Path) -> dict[str,Any]:
    if report.get('schema')!='verseforge-knowledge-audit-v1':
        raise ValueError('Expected knowledge audit report')
    output = Path(output)
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise ValueError('Refusing to overwrite knowledge lock file')
    lock = {k:report[k] for k in ('schema','target_uefn','commit','declared_snapshots','sampled_files','status')}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(lock,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return {'result':'LOCK WRITTEN','file':str(output),'status':report['status'],'api_verified':'NOT VERIFIED'}
