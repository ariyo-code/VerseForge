"""Transactional, opt-in Verse file edits with hash preconditions and rollbacks."""
from __future__ import annotations
import hashlib
import json
import os
import re
import tempfile
import unicodedata
import uuid
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from .xray import project_xray,analyze_source

PROTECTED={'Content','Plugins','Intermediate','Saved','.git','node_modules','Binaries'}
MAX_SIZE=500_000


def hash_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()


def safe_target(root:Path,relative:str)->Path:
    if not isinstance(relative,str) or '\\' in relative or not relative.endswith('.verse'):
        raise ValueError('Only relative POSIX .verse paths are allowed')
    pp=PurePosixPath(relative)
    if pp.is_absolute() or not pp.parts or any(v in ('.','..') for v in pp.parts):
        raise ValueError('Unsafe relative path')
    if pp.parts[0]=='.verseforge' or any(x in PROTECTED for x in pp.parts):
        raise ValueError('Protected project path')
    resolved=root.resolve(strict=True)
    current=resolved
    for part in pp.parts:
        current=current/part
        if current.is_symlink():raise ValueError('Symlink inside target path')
    if not current.resolve(strict=False).is_relative_to(resolved):
        raise ValueError('Escapes project root')
    return current


def _validate_plan(plan:dict,root:Path)->list[tuple[Path,bytes|None,bytes]]:
    if set(plan)!={'schema','changes','purpose'} or plan['schema']!='verseforge-edits-v1':
        raise ValueError('Unsupported edit plan')
    if not plan['purpose'] or not isinstance(plan['changes'],list) or not plan['changes']:
        raise ValueError('Missing changes or purpose')
    if len(plan['changes'])>60:raise ValueError('Too many files in one batch')
    writes=[];used=set()
    for change in plan['changes']:
        if set(change)!={'path','old_sha256','new_content'}:raise ValueError('Invalid change entry')
        target=safe_target(root,change['path'])
        if target in used:raise ValueError('Duplicate edit path')
        used.add(target)
        new=change['new_content']
        if not isinstance(new,str) or not new.strip() or '\x00' in new or len(new.encode())>MAX_SIZE:
            raise ValueError('New Verse content invalid or exceeds size limit')
        if any(unicodedata.category(c)=='Cf' for c in new):
            raise ValueError('Invisible formatting/bidi Unicode control forbidden in Verse')
        if not re.search(r'(?m)^\s*(?:\w+\s*:=\s*(?:class|module)\b|var\s+\w+\s*:|\w+\s*\([^\n]*\)\s*(?:<[^>]+>)*\s*:[^\n=]+\s*=)',new):
            raise ValueError('Verse file has no recognizable declaration; review edit')
        old=target.read_bytes() if target.exists() else None
        expected=change['old_sha256']
        if old is None and expected is not None:raise ValueError('Target missing but update requested')
        if old is not None and (not isinstance(expected,str) or hash_bytes(old)!=expected):
            raise ValueError('Precondition failed: stale SHA-256 or file exists')
        writes.append((target,old,new.encode('utf-8')))
    return writes


def edit_project(project:Path,plan:dict,apply:bool=False)->dict:
    project=project.expanduser().resolve(strict=True)
    if not project.is_dir():raise ValueError('Not a project directory')
    writes=_validate_plan(plan,project)
    # Avoid conflict with an existing state owner/class declared in other files.
    existing=project_xray(project)
    external_classes={c for c,paths in existing['classes'].items() if any(project/p != t for p in paths for t,_,_ in writes)}
    new_classes={}
    for target,_,content in writes:
        added=analyze_source(target.name,content.decode())
        if external_classes.intersection(added['classes']):
            raise ValueError(f'Existing class would be duplicated: {sorted(external_classes.intersection(added["classes"]))}')
        for cls in added['classes']:
            if cls in new_classes:
                raise ValueError(f'Duplicate class across proposed changes: {cls}')
            new_classes[cls]=target
    summary=[{'path':str(t.relative_to(project)),'operation':'create' if old is None else 'update',
              'old_sha256':hash_bytes(old) if old is not None else None,'new_sha256':hash_bytes(new)} for t,old,new in writes]
    if not apply:
        return {'result':'PREVIEW','changes':summary,'written':False,'compiler':'NOT TESTED'}
    # Prepare backup; rollback even if a later replacement fails. The backup is local-only.
    return _commit(project,writes,summary)


def _commit(project:Path,writes:list,summary:list)->dict:
    batch=uuid.uuid4().hex
    backup=project/'.verseforge'/'backups'/batch
    if (project/'.verseforge').is_symlink() or (project/'.verseforge'/'backups').is_symlink():
        raise ValueError('Unsafe symlinked backup location')
    backup.mkdir(parents=True,exist_ok=False)
    replaced=[]
    try:
        for i,(target,old,new) in enumerate(writes):
            if old is not None:
                (backup/f'{i}.original').write_bytes(old)
            target.parent.mkdir(parents=True,exist_ok=True)
            # Recheck just before write to guard against concurrent modifications.
            now=target.read_bytes() if target.exists() else None
            if now!=old:raise ValueError(f'Concurrent modification detected at {target.name}')
            fd,temp=tempfile.mkstemp(prefix='.vf-',suffix='.tmp',dir=target.parent)
            try:
                with os.fdopen(fd,'wb') as f:
                    f.write(new);f.flush();os.fsync(f.fileno())
                os.replace(temp,target)
            finally:
                if os.path.exists(temp):os.unlink(temp)
            replaced.append((target,old))
        manifest={'schema':'verseforge-backup-v1','batch':batch,'changes':summary}
        (backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    except Exception:
        for t,old in reversed(replaced):
            if old is None:t.unlink(missing_ok=True)
            else:t.write_bytes(old)
        raise
    return {'result':'APPLIED','changes':summary,'written':True,'backup_batch':batch,'compiler':'NOT TESTED'}


def rollback(project:Path,batch:str)->dict:
    project=project.resolve(strict=True)
    if not re.fullmatch(r'[0-9a-f]{32}',batch):raise ValueError('Invalid backup ID')
    backup=project/'.verseforge'/'backups'/batch
    if (project/'.verseforge').is_symlink() or (project/'.verseforge'/'backups').is_symlink() or backup.is_symlink():
        raise ValueError('Unsafe symlinked rollback location')
    if (backup/'rolled_back').exists():raise ValueError('Backup already rolled back')
    manifest=json.loads((backup/'manifest.json').read_text())
    targets=[]
    for i,entry in enumerate(manifest['changes']):
        target=safe_target(project,entry['path'])
        if not target.exists() or hash_bytes(target.read_bytes())!=entry['new_sha256']:
            raise ValueError('Rollback conflict: file changed after apply')
        original=(backup/f'{i}.original').read_bytes() if entry['old_sha256'] is not None else None
        if original is not None and hash_bytes(original)!=entry['old_sha256']:
            raise ValueError('Backup integrity mismatch')
        targets.append((target,original))
    for t,orig in targets:
        if orig is None:t.unlink()
        else:t.write_bytes(orig)
    (backup/'rolled_back').write_text(datetime.now(timezone.utc).isoformat())
    return {'result':'ROLLED_BACK','batch':batch,'restored':len(targets)}
