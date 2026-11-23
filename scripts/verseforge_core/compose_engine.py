"""Integrate *agent-authored* project modules into a verified export.

This does not synthesize complex Verse behavior. Instead, it supplies strict
architecture/ownership/module-existence gates and uses existing truthful
static delivery, ZIP verification and asset provenance validation.
"""
from __future__ import annotations
import json
import re
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

from .engineering_engine import architecture
from .quality_engine import review_sources
from .chat_package import allowed
from .delivery_pipeline import deliver
from .xray import project_xray

SCHEMA='verseforge-api-evidence-v1'
MAX_FILES=160
MAX_TOTAL=32*1024*1024


def _source_entries(root: Path) -> list[tuple[Path,Path]]:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Composer source must be a normal staging directory')
    files=[];total=0;seen=set()
    for p in sorted(root.rglob('*')):
        mode=p.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError('Symlink in composer source')
        if stat.S_ISDIR(mode):continue
        if not stat.S_ISREG(mode):raise ValueError('Unexpected special file')
        rel=p.relative_to(root)
        if not allowed(rel):raise ValueError(f'Unsupported composer input: {rel}')
        if rel.as_posix().casefold() in seen:raise ValueError('Case-colliding input')
        seen.add(rel.as_posix().casefold())
        total+=p.stat().st_size
        if len(files)>=MAX_FILES or total>MAX_TOTAL or p.stat().st_size>8*1024*1024:
            raise ValueError('Composer input exceeds safe limits')
        files.append((p,rel))
    return files


def _api_ledger(plan: dict[str,Any], supplied: dict[str,Any] | None, target: str) -> dict[str,Any]:
    claims=sorted({sym for m in plan['modules'] for sym in m['api_claims']})
    if not claims:
        return {'api_claim_status':'NO API CLAIMS', 'claims':[], 'compiler':'NOT TESTED'}
    if not isinstance(supplied, dict) or supplied.get('schema')!=SCHEMA or not isinstance(supplied.get('claims'),list):
        return {'api_claim_status':'BLOCKED — MISSING DECLARED API EVIDENCE', 'claims':claims, 'compiler':'NOT TESTED'}
    found={}
    for rec in supplied['claims']:
        if not isinstance(rec,dict) or set(rec)!={'symbol','source_url','uefn_version','fields'}:
            raise ValueError('Malformed API evidence record')
        symbol=rec['symbol']
        url=rec['source_url']
        if not isinstance(symbol,str) or not isinstance(url,str) or not url.startswith('https://dev.epicgames.com/'):
            raise ValueError('Only an official Epic API evidence URL is accepted as a declaration')
        if rec['uefn_version']!=target:
            raise ValueError('API evidence version does not match the target editor')
        fields=rec['fields']
        if not isinstance(fields,dict) or not {'signature','parameters','effects'}.issubset(fields):
            raise ValueError('Required exact API fields were not supplied')
        if any(not isinstance(v,str) or not v or len(v)>3000 for v in fields.values()):
            raise ValueError('Invalid API field evidence')
        if symbol in found:
            raise ValueError('Duplicate API evidence record')
        found[symbol]=rec
    missing=[symbol for symbol in claims if symbol not in found]
    return {'api_claim_status':'SELF-DECLARED — NEEDS INDEPENDENT REVIEW' if not missing else 'BLOCKED — MISSING CLAIMS',
            'claims':claims,'missing':missing,'compiler':'NOT TESTED',
            'notice':'Evidence URLs and fields are user/agent declarations; no actual web retrieval or editor proof occurs here.'}


def compose_project(spec: dict[str,Any], source: Path, output: Path,
                    *, uefn_version: str, api_evidence: dict[str,Any] | None = None) -> dict[str,Any]:
    if not re.fullmatch(r'\d{1,3}\.\d{1,3}(?:\.\d{1,3})?', uefn_version):
        raise ValueError('Explicit UEFN target version required')
    plan=architecture(spec)
    source=Path(source).expanduser()
    output=Path(output).expanduser()
    if output.exists() or output.is_symlink() or output.resolve(strict=False).is_relative_to(source.resolve()):
        raise ValueError('Output must be a new ZIP file')
    entries=_source_entries(source)
    existing={r.as_posix() for _,r in entries}
    missing=[f'Verse/{m["id"]}_device.verse' for m in plan['modules'] if f'Verse/{m["id"]}_device.verse' not in existing]
    if missing:
        return {'result':'BLOCKED','reason':'Missing required module sources','missing':missing,'uefn_compile':'NOT TESTED'}
    xray=project_xray(source)
    if xray['warnings']:
        return {'result':'BLOCKED','reason':'Module topology conflicts','issues':xray['warnings'],'uefn_compile':'NOT TESTED'}
    review=review_sources(source)
    if review['local_check']!='PASS':
        return {'result':'BLOCKED','reason':'Static evidence not ready','warnings':review['warnings'],'uefn_compile':'NOT TESTED'}
    ledger=_api_ledger(plan,api_evidence,uefn_version)
    if ledger['api_claim_status'].startswith('BLOCKED'):
        return {'result':'BLOCKED','reason':'Missing API evidence declarations','api':ledger,'uefn_compile':'NOT TESTED'}
    with tempfile.TemporaryDirectory(prefix='vf-compose-') as temp:
        stage=Path(temp)/'input';stage.mkdir()
        for p,r in entries:
            dest=stage/r
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,dest)
        engineering_manifest={'schema':'verseforge-composition-v1','architecture':plan,
                              'api':ledger,'uefn_version':uefn_version,
                              'uefn_compile':'NOT TESTED','gameplay':'NOT TESTED','multiplayer':'NOT TESTED'}
        (stage/'ENGINEERING_MANIFEST.json').write_text(json.dumps(engineering_manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if not (stage/'README.md').exists():
            (stage/'README.md').write_text(f'# {plan["project"]}\n\nAgent-authored RP system. State ownership: {json.dumps(plan["state_owners"])}\n\nUEFN compilation, gameplay and multiplayer are NOT TESTED.\n',encoding='utf-8')
        if not (stage/'INSTALL.md').exists():
            (stage/'INSTALL.md').write_text('# Installation\n\nCopy Verse/*.verse into a UEFN test project. Wire real devices, compile and test each system in the editor. No feature has been compiler-certified by this offline process.\n',encoding='utf-8')
        result=deliver(stage,output,strict=True)
        if result['result']!='PASS':
            return result
    return {'result':'PASS','archive':str(output),'modules':plan['module_order'],
            'integrity':result['zip_integrity'],'api':ledger['api_claim_status'],
            'uefn_compile':'NOT TESTED','runtime':'NOT TESTED','multiplayer':'NOT TESTED'}
