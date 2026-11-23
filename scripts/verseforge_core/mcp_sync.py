"""Single-writer MCP file edit preconditions and postconditions for editor writes.

A server-side editor buffer may differ from disk. When that happens, explicitly
report UNVERIFIED instead of doing a second local write or automatic rollback.
"""
from __future__ import annotations
import hashlib
import json
import uuid
from pathlib import Path
from .workspace import safe_target
from .mcp_runtime import MCPRuntime


def _sha(data:bytes|None)->str|None:
    return hashlib.sha256(data).hexdigest() if data is not None else None


def mcp_guarded_edit(project:Path,relative_path:str,old_sha256:str|None,
                     new_content:str,endpoint:str,tool:str,arguments:dict,*,confirmed:bool,
                     client_factory=MCPRuntime)->dict:
    if not confirmed:raise PermissionError('Explicit confirmation required before MCP editor writes')
    root=project.expanduser().resolve(strict=True)
    target=safe_target(root,relative_path)
    if not isinstance(new_content,str) or not new_content.strip():raise ValueError('New content required')
    expected_new=_sha(new_content.encode('utf-8'))
    observed=target.read_bytes() if target.exists() else None
    if _sha(observed)!=old_sha256:raise ValueError('Stale source fingerprint: concurrent change or unexpected file')
    backup=root/'.verseforge'/'remote-backups'/uuid.uuid4().hex
    if any(p.is_symlink() for p in (root/'.verseforge',root/'.verseforge'/'remote-backups')):
        raise ValueError('Symlinked backup location forbidden')
    backup.mkdir(parents=True,exist_ok=False)
    if observed is not None:(backup/'original.verse').write_bytes(observed)
    (backup/'precondition.json').write_text(json.dumps({'relative_path':relative_path,'old_sha256':old_sha256,
                            'expected_new_sha256':expected_new},indent=2))
    # Recheck immediately before the editor call; never apply a local edit here.
    present=target.read_bytes() if target.exists() else None
    if _sha(present)!=old_sha256:raise ValueError('Concurrent source modification before MCP call')
    client=client_factory(endpoint).connect()
    response=client.call(tool,arguments,confirmed=True,allow_mutation=True)
    after=target.read_bytes() if target.exists() else None
    after_sha=_sha(after)
    status='DISK_VERIFIED' if after_sha==expected_new else 'UNVERIFIED'
    output={'result':status,'relative_path':relative_path,'before_sha256':old_sha256,
             'after_sha256':after_sha,'expected_new_sha256':expected_new,
             'mcp_tool':tool,'server_claimed_identity':client.server_info,
             'backup_path':str(backup),'mcp_reported_error':response['result'].get('isError'),
             'uefn_compilation':'NOT TESTED','playtest':'NOT TESTED',
             'note':'UNVERIFIED means editor in-memory changes or disk conflicts; do not blindly overwrite/rollback.'}
    (backup/'result.json').write_text(json.dumps(output,indent=2)+'\n')
    return output
