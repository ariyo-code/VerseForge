"""Real MCP invocation adapter + strictly observational UEFN compile result contract.

Does not fabricate compiler output or turn source code heuristics into compilation.
User must explicitly select an advertised compiler tool and supply its actual schema arguments.
"""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from datetime import datetime,timezone
from pathlib import Path
from .mcp_runtime import MCPRuntime,MCPError

RESULTS=('SUCCESS','FAILED','CANCELLED','TIMEOUT','UNAVAILABLE','UNKNOWN')
TOKEN_RE=re.compile(r'(?i)(bearer\s+)[A-Za-z0-9._~+/-]+|((?:access_token|refresh_token|api_key|password|secret)\s*[=:]\s*)\S+')
DIAG=re.compile(r'(?P<file>[^\s():]+\.verse)(?:\((?P<line1>\d+),(?P<col1>\d+)\)|:(?P<line2>\d+)(?::(?P<col2>\d+))?)',re.I)

def scrub(text:str)->str:
    return TOKEN_RE.sub(lambda m: (m.group(1) or m.group(2) or '')+'[REDACTED]',text)


def tool_text(result:dict)->str:
    lines=[]
    for content in result.get('content',[]):
        if isinstance(content,dict) and content.get('type')=='text' and isinstance(content.get('text'),str):
            lines.append(content['text'])
    if isinstance(result.get('structuredContent'),dict):
        lines.append(json.dumps(result['structuredContent'],ensure_ascii=False))
    return '\n'.join(lines)


def parse_diagnostics(log:str)->list[dict]:
    out=[]
    for line in log.splitlines():
        if not re.search(r'\b(error|warning|erreur|warn)\b',line,re.I):continue
        match=DIAG.search(line)
        sev='error' if re.search(r'\b(error|erreur)\b',line,re.I) else 'warning'
        out.append({'severity':sev,'message':scrub(line)[:2000],
                    'file':match.group('file') if match else None,
                    'line':int(match.group('line1') or match.group('line2')) if match else None,
                    'column':int(match.group('col1') or match.group('col2')) if match and (match.group('col1') or match.group('col2')) else None})
    return out


def classify_result(result:dict)->tuple[str,str,list[dict]]:
    if result.get('isError') is True:return 'FAILED','MCP tool returned isError=true',parse_diagnostics(tool_text(result))
    body=tool_text(result)
    diagnostics=parse_diagnostics(body)
    if any(d['severity']=='error' for d in diagnostics):
        return 'FAILED','Compiler error diagnostic returned',diagnostics
    structured=result.get('structuredContent')
    if isinstance(structured,dict):
        # Only explicit compile status in the tool payload can establish a result.
        status=structured.get('status') or structured.get('result')
        if isinstance(status,str):
            s=status.strip().upper()
            if s in RESULTS:return s,'Explicit status in MCP structuredContent',diagnostics
            if s in ('SUCCEEDED','COMPILED','BUILD_SUCCEEDED'):
                return 'SUCCESS','Explicit compile success in MCP structuredContent',diagnostics
            if s in ('ERROR','BUILD_FAILED','COMPILE_FAILED'):
                return 'FAILED','Explicit compile failure in MCP structuredContent',diagnostics
        if structured.get('success') is True and not diagnostics:
            return 'SUCCESS','Explicit success=true in MCP structuredContent',diagnostics
        if structured.get('success') is False:
            return 'FAILED','Explicit success=false in MCP structuredContent',diagnostics
    if any(d['severity']=='error' for d in diagnostics):return 'FAILED','Compiler error diagnostic returned',diagnostics
    # A textual success may be an unrelated tool message: deliberately UNKNOWN.
    return 'UNKNOWN','No unambiguous structured compiler result; review raw tool evidence',diagnostics


def _utc():return datetime.now(timezone.utc).isoformat()


def compile_project(endpoint:str,tool_name:str,arguments:dict,*,project:Path,files:list[str],
                    evidence_dir:Path,confirmed:bool,editor_version:str|None=None,
                    timeout:float=40,client_factory=MCPRuntime)->dict:
    root=project.expanduser().resolve(strict=True)
    if not root.is_dir():raise ValueError('Project must be a directory')
    if not list(root.glob('*.uefnproject')):
        raise ValueError('UEFN project descriptor missing in project root')
    # File list and SHA checks are *before* editor call.
    from .workspace import safe_target
    hashes={}
    for rel in files:
        path=safe_target(root,rel)
        if not path.is_file():raise ValueError(f'Missing Verse input {rel}')
        hashes[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
    if not confirmed:raise PermissionError('Real compilation requires explicit confirmation')
    run_id=uuid.uuid4().hex
    start=_utc()
    compiled=None;connection=None;failure=None;raw={}
    try:
        client=client_factory(endpoint,timeout=timeout).connect()
        connection=client.registry()
        if tool_name not in client.tools:raise MCPError('Selected compile tool not advertised')
        response=client.call(tool_name,arguments,confirmed=True,allow_mutation=True)
        raw=response['result']
        compiled,reason,diagnostics=classify_result(raw)
    except (OSError,ValueError,TypeError,PermissionError,MCPError) as exc:
        compiled='UNAVAILABLE' if isinstance(exc,(MCPError,OSError,PermissionError)) else 'UNKNOWN'
        reason=f'{type(exc).__name__}: {str(exc)[:200]}'
        diagnostics=[]
        failure=type(exc).__name__
    end=_utc()
    # No raw secrets, project source or OAuth tokens in exported evidence.
    evidence={'schema':'verseforge-compile-raw-v1','id':run_id,'selected_tool':tool_name,
              'server_claimed_identity':connection.get('server_claimed_identity',{}) if connection else None,
              'result':json.loads(scrub(json.dumps(raw,ensure_ascii=False))),'reason':scrub(reason)}
    payload=(json.dumps(evidence,sort_keys=True,indent=2,ensure_ascii=False)+'\n').encode()
    evidence_dir.mkdir(parents=True,exist_ok=True)
    if evidence_dir.is_symlink():raise ValueError('Symlinked evidence directory forbidden')
    rawpath=evidence_dir/(run_id+'.mcp.json')
    rawpath.write_bytes(payload)
    report={'schema':'verseforge-compiler-result-v1','run_id':run_id,'project':str(root),
            'uefn_version_observed':None, # only fill if independently observed, not operator supplied
            'uefn_version_user_supplied':editor_version,'files':hashes,
            'started_at':start,'finished_at':end,'method':'mcp-tools-call',
            'selected_tool':tool_name,'status':compiled,'classification_reason':reason,
            'error_count':sum(x['severity']=='error' for x in diagnostics),
            'warning_count':sum(x['severity']=='warning' for x in diagnostics),
            'diagnostics':diagnostics,'evidence':{'path':str(rawpath),
                        'sanitized_raw_sha256':hashlib.sha256(payload).hexdigest()},
            'editor_identity_verified':False,
            'gameplay':'NOT TESTED','multiplayer':'NOT TESTED',
            'warning':'Endpoint/tool identity not independently authenticated; this report does not by itself promote to compiled'}
    if failure:report['transport_or_protocol_failure']=failure
    (evidence_dir/(run_id+'.report.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report


def unavailability_record(project:str,reason:str,files:list[str]|None=None)->dict:
    return {'schema':'verseforge-compiler-result-v1','run_id':uuid.uuid4().hex,
            'project':project,'uefn_version_observed':None,'files':files or [],
            'started_at':_utc(),'finished_at':_utc(),'method':'unavailable',
            'status':'UNAVAILABLE','error_count':0,'warning_count':0,'diagnostics':[],
            'reason':reason,'evidence':None,'gameplay':'NOT TESTED','multiplayer':'NOT TESTED'}
