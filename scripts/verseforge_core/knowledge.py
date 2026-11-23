"""Safe allowlisted CLI bridge to installed Verse-AI-Knowledge. Never edits upstream."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path

ALLOWED={
    'version', 'doctor', 'search', 'context', 'api', 'claim', 'explain',
    'evidence','coverage','status','lint','api-queue'
}


def run_knowledge(args: list[str], repo: str | None = None, timeout: int = 20) -> dict:
    if not args or args[0] not in ALLOWED:
        raise ValueError('Only specific read-only verse-ai operations are allowed')
    if any(x.startswith('@') for x in args):
        raise ValueError('Response-file arguments are not accepted')
    # Only non-mutating CLI arguments. These are defensive against future upstream flags.
    banned={'--fix','--write','--update','--refresh','--apply','--delete',
            '--output','--out','--export','--save','--force','--inplace'}
    if any(x.split('=',1)[0].lower() in banned for x in args):
        raise ValueError('Potentially mutating CLI options are forbidden')
    exe=shutil.which('verse-ai')
    if not exe:
        return {'available':False,'status':'NOT TESTED','reason':'verse-ai not installed'}
    cwd=Path(repo).expanduser().resolve(strict=True) if repo else None
    if cwd and (not (cwd/'AI_BOOTSTRAP.md').is_file() or not cwd.is_dir()):
        raise ValueError('Knowledge path does not appear to be Verse-AI-Knowledge')
    # Even read-only commands are invoked with no shell and a hard timeout.
    try:
        completed=subprocess.run([exe,*args],cwd=cwd,stdin=subprocess.DEVNULL,
          capture_output=True,text=True,timeout=timeout,check=False)
    except subprocess.TimeoutExpired:
        return {'available':True,'status':'ERROR','reason':'command timed out'}
    return {'available':True,'status':'PASS' if completed.returncode==0 else 'ERROR',
            'exit_code':completed.returncode,'stdout':completed.stdout[-12000:],
            'stderr':completed.stderr[-3000:]}
