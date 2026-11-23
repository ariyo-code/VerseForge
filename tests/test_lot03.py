"""LOT 03: transport tests use a local MOCK SERVER, never a UEFN compiler."""
from __future__ import annotations
import hashlib
import json
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.mcp_runtime import MCPRuntime,MCPError,_parse_response,connect_report
from verseforge_core.environment import diagnose,_config_extract
from verseforge_core.compilation import classify_result,parse_diagnostics,compile_project,unavailability_record,scrub
from verseforge_core.repair_session import run_repair_session
from verseforge_core.workspace import edit_project

@contextmanager
def server(*,kind='success',sse=False,deny=False):
    calls=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            length=int(self.headers.get('Content-Length','0'))
            body=json.loads(self.rfile.read(length))
            calls.append({'method':body.get('method'),'params':body.get('params'),'session':self.headers.get('Mcp-Session-Id')})
            if deny:
                self.send_response(403);self.end_headers();return
            meth=body['method']
            if meth=='notifications/initialized':
                self.send_response(202);self.end_headers();return
            if meth=='initialize':result={'protocolVersion':'2025-06-18','serverInfo':{'name':'TEST-MOCK','version':'mock'}}
            elif meth=='tools/list':result={'tools':[{'name':'compile_verse','inputSchema':{'type':'object','properties':{'target':{'type':'string'}},'required':['target'],'additionalProperties':False}},
                    {'name':'read_info','inputSchema':{'type':'object','properties':{},'additionalProperties':False}}]}
            elif meth=='tools/call':
                if kind=='error':result={'isError':True,'content':[{'type':'text','text':'Demo.verse(12,5): error V123: missing symbol'}]}
                elif kind=='unknown':result={'content':[{'type':'text','text':'I did something'}]}
                elif kind=='contradict':result={'isError':False,'structuredContent':{'success':True},'content':[{'type':'text','text':'Demo.verse(2,1): error: boom'}]}
                else:result={'isError':False,'structuredContent':{'status':'SUCCESS','success':True},'content':[{'type':'text','text':'0 errors'}]}
            else: result={}
            payload=json.dumps({'jsonrpc':'2.0','id':body['id'],'result':result}).encode()
            if sse and meth=='tools/list':
                payload=b'event: ping\ndata: {"jsonrpc":"2.0","id":999,"result":{}}\n\n'+b'data: '+payload+b'\n\n'
            self.send_response(200)
            self.send_header('Content-Type','text/event-stream' if (sse and meth=='tools/list') else 'application/json')
            self.send_header('Mcp-Session-Id','mock-session')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers();self.wfile.write(payload)
    svr=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=svr.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{svr.server_port}/mcp',calls
    finally:svr.shutdown();svr.server_close();thread.join(timeout=2)

@pytest.mark.parametrize('kind,status',[('success','SUCCESS'),('error','FAILED'),('unknown','UNKNOWN'),('contradict','FAILED')])
def test_real_http_mock_tool_call(kind,status):
    with server(kind=kind) as (endpoint,calls):
        cli=MCPRuntime(endpoint).connect()
        assert cli.server_info['name']=='TEST-MOCK'
        assert sorted(cli.tools)==['compile_verse','read_info']
        response=cli.call('compile_verse',{'target':'test'},confirmed=True,allow_mutation=True)
        assert classify_result(response['result'])[0]==status
        assert any(c['session']=='mock-session' for c in calls if c['method']=='tools/call')

@pytest.mark.parametrize('bad', ['http://example.com/mcp','http://127.0.0.1:8000/private','https://127.0.0.1:8000/mcp','http://127.0.0.1:8000/mcp?token=abc'])
def test_mcp_rejects_unsafe_endpoints(bad):
    with pytest.raises(ValueError):MCPRuntime(bad)

def test_sse_correlation():
    with server(sse=True) as (endpoint,_):assert MCPRuntime(endpoint).connect().tools

def test_mcp_explicit_authorization():
    with server() as (endpoint,_):
        cli=MCPRuntime(endpoint).connect()
        with pytest.raises(PermissionError):cli.call('compile_verse',{'target':'x'})
        with pytest.raises(PermissionError):cli.call('compile_verse',{'target':'x'},confirmed=True)
        with pytest.raises(MCPError):cli.call('invented',{},confirmed=True)

def test_mcp_schema_and_valid_read_only_call():
    with server() as (endpoint,_):
        cli=MCPRuntime(endpoint).connect()
        assert cli.call('read_info',{},confirmed=True)['transport']=='real-rpc'
        with pytest.raises(Exception):cli.call('compile_verse',{'not_allowed':1},confirmed=True,allow_mutation=True)

def test_mcp_permission_denied():
    with server(deny=True) as (endpoint,_):
        assert connect_report(endpoint)['connection']=='MCP_PERMISSION_DENIED'

def test_mcp_unknown_tcp_connection():
    # Bound ephemeral port freed before probe; failure expected, no UEFN implied.
    with server() as (endpoint,_):pass
    assert connect_report(endpoint,timeout=.2)['connection']=='MCP_UNREACHABLE'

@pytest.mark.parametrize('payload',[
    b'{"jsonrpc":"2.0","id":9,"result":{}}',b'not json',
    b'{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"no"}}'])
def test_mcp_invalid_protocol_rejected(payload):
    with pytest.raises((MCPError,ValueError)):_parse_response(payload,'application/json',1)

def test_mcp_sse_matching_identifier():
    payload=b'data: {"jsonrpc":"2.0","id":2,"result":{"right":true}}\n\n'
    assert _parse_response(payload,'text/event-stream',2)=={'right':True}
    with pytest.raises(MCPError):_parse_response(payload,'text/event-stream',3)

@pytest.mark.parametrize('status',[('SUCCESS',True),('FAILED',False),('UNKNOWN',None)])
def test_compiler_structured_result(status):
    s,good=status
    obj={'structuredContent':{'status':s}}
    assert classify_result(obj)[0]==s

def test_compiler_diagnostics_positions_and_secrets():
    log='Z.verse(10,4): error V200: bad\nA.verse:11:3: warning: caution\nBearer abc123'
    d=parse_diagnostics(log)
    assert len(d)==2 and d[0]['line']==10 and d[1]['column']==3
    assert 'abc123' not in scrub(log)

def test_compiler_unavailable_record():
    rec=unavailability_record('/tmp/nonreal','UEFN unreachable')
    assert rec['status']=='UNAVAILABLE' and rec['evidence'] is None

def test_compile_missing_project_descriptor(tmp_path):
    (tmp_path/'a.verse').write_text('a := class(creative_device):\n')
    with pytest.raises(ValueError,match='descriptor'):
        compile_project('http://127.0.0.1:8000/mcp','compile_verse',{'target':'x'},project=tmp_path,files=['a.verse'],evidence_dir=tmp_path/'ev',confirmed=True)

def test_compile_mock_evidence_cannot_promote(tmp_path):
    (tmp_path/'Test.uefnproject').write_text('{}')
    (tmp_path/'a.verse').write_text('a := class(creative_device):\n')
    with server() as (endpoint,_):
        result=compile_project(endpoint,'compile_verse',{'target':'x'},project=tmp_path,files=['a.verse'],evidence_dir=tmp_path/'ev',confirmed=True)
    assert result['status']=='SUCCESS'
    assert result['editor_identity_verified'] is False
    assert result['uefn_version_observed'] is None
    assert hashlib.sha256(Path(result['evidence']['path']).read_bytes()).hexdigest()==result['evidence']['sanitized_raw_sha256']
    from verseforge_core.gates import promote
    with pytest.raises(ValueError):promote('static-checked','compiled',{'uefn_compile_log':{'success':True,'source':'mock','timestamp':'2026-11-22','source_type':'mock','raw_log_sha256':'a'*64}})

def test_environment_no_uefn_and_no_probe(tmp_path):
    obj=diagnose(project=tmp_path)
    assert obj['uefn_mcp']['connection']=='MCP_NOT_CONFIGURED'
    assert obj['compiler_state']=='UNAVAILABLE'
    assert obj['project']['state']=='PROJECT_NOT_OPEN'

def test_environment_detects_file_but_not_open(tmp_path):
    (tmp_path/'Demo.uefnproject').write_text('{}')
    (tmp_path/'x.verse').write_text('x := class(creative_device):\n')
    result=diagnose(project=tmp_path)
    assert result['project']['state']=='PROJECT_NOT_OPEN'
    assert result['project']['disk_state']=='FILES_READY'
    assert result['project']['verse_files']==1
    assert 'not proof' in result['project']['note']

def test_environment_config_json_and_toml(tmp_path):
    js=tmp_path/'mcp.json'; js.write_text('{"mcpServers":{"editor":{"url":"http://127.0.0.1:8000/mcp"}}}')
    toml=tmp_path/'config.toml';toml.write_text('[mcp_servers.knowledge]\nurl="http://127.0.0.1:8002/mcp"')
    assert len(_config_extract([js,toml]))==2

def candidate(path,body,old=None):
    return {'schema':'verseforge-edits-v1','purpose':'compiler error repair',
            'changes':[{'path':path,'old_sha256':old,'new_content':body}]}

def baseline():return {'status':'FAILED','error_count':1,'diagnostics':[{'severity':'error','file':'x.verse','line':1,'message':'bad'}]}

def test_repair_success_with_mock_compiler(tmp_path):
    proposal=candidate('x.verse','x := class(creative_device):\n')
    compiled=lambda:{'status':'SUCCESS','error_count':0,'diagnostics':[],'run_id':'mock123'}
    out=run_repair_session(tmp_path,baseline(),[proposal],compiled)
    assert out['result']=='COMPILED_RESPONSE_REPORTED'
    assert (tmp_path/'x.verse').exists()
    assert out['last_compile']['run_id']=='mock123'

def test_repair_regression_rollback(tmp_path):
    proposal=candidate('x.verse','x := class(creative_device):\n')
    worse=lambda:{'status':'FAILED','error_count':2,'diagnostics':[{'severity':'error','file':'new.verse','line':4,'message':'new'}]}
    result=run_repair_session(tmp_path,baseline(),[proposal],worse)
    assert result['result']=='STOP' and result['attempts'][0]['rollback']
    assert not (tmp_path/'x.verse').exists()

def test_repair_unavailable_rollback(tmp_path):
    result=run_repair_session(tmp_path,baseline(),[candidate('x.verse','x := class(creative_device):\n')],lambda:{'status':'UNAVAILABLE','diagnostics':[]})
    assert result['result']=='STOP' and result['attempts'][0]['rollback']
    assert not (tmp_path/'x.verse').exists()

def test_repair_requires_failure_baseline(tmp_path):
    obj=run_repair_session(tmp_path,{'status':'UNKNOWN'},[],lambda:None)
    assert obj['result']=='STOP'

def test_repair_invalid_candidate_rejected(tmp_path):
    with pytest.raises(ValueError):run_repair_session(tmp_path,baseline(),[{'invalid':1}],lambda:None)

def test_repair_compiler_exception_restores_project(tmp_path):
    def broken(): raise RuntimeError('Connection broke')
    with pytest.raises(RuntimeError):run_repair_session(tmp_path,baseline(),[candidate('x.verse','x := class(creative_device):\n')],broken)
    assert not (tmp_path/'x.verse').exists()

def test_repair_repetition_stops(tmp_path):
    p=candidate('x.verse','x := class(creative_device):\n')
    # First compile fails without new diagnostics: refuse pointless retries and roll back.
    unchanged=lambda:{'status':'FAILED','error_count':1,'diagnostics':baseline()['diagnostics']}
    out=run_repair_session(tmp_path,baseline(),[p,p],unchanged,max_attempts=2)
    assert out['result']=='STOP' and out['reason']=='No diagnostic improvement'
    assert out['attempts'][0]['rollback'] is True
    assert not (tmp_path/'x.verse').exists()

from verseforge_core.mcp_sync import mcp_guarded_edit

class _FakeEditingClient:
    """Test-only: mimics a disk-changing MCP tool, not an actual UEFN editor."""
    write_path=None
    write_content=None
    def __init__(self,*args,**kwargs):pass
    def connect(self):return self
    server_info={'name':'test-only'}
    def call(self,name,args,*,confirmed,allow_mutation):
        if self.write_path is not None:
            self.write_path.write_text(self.write_content)
        return {'result':{'isError':False}}


def test_guarded_editor_mock_conflict(tmp_path):
    p=tmp_path/'a.verse';p.write_text('origin := class(creative_device):\n')
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    p.write_text('changed := class(creative_device):\n')
    with pytest.raises(ValueError,match='Stale'):
        mcp_guarded_edit(tmp_path,'a.verse',h,'new := class(creative_device):\n',
                         'http://127.0.0.1:8000/mcp','write_source',{},confirmed=True,
                         client_factory=_FakeEditingClient)


def test_guarded_editor_mock_verified_disk(tmp_path):
    p=tmp_path/'b.verse';p.write_text('old := class(creative_device):\n')
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    body='new := class(creative_device):\n'
    _FakeEditingClient.write_path=p;_FakeEditingClient.write_content=body
    try:
        result=mcp_guarded_edit(tmp_path,'b.verse',h,body,'http://127.0.0.1:8000/mcp',
                       'write_source',{},confirmed=True,client_factory=_FakeEditingClient)
        assert result['result']=='DISK_VERIFIED'
        assert Path(result['backup_path'],'original.verse').read_text()=='old := class(creative_device):\n'
        assert result['uefn_compilation']=='NOT TESTED'
    finally:
        _FakeEditingClient.write_path=None


def test_guarded_editor_mock_in_memory_unverified(tmp_path):
    _FakeEditingClient.write_path=None
    result=mcp_guarded_edit(tmp_path,'fresh.verse',None,'fresh := class(creative_device):\n',
                            'http://127.0.0.1:8000/mcp','write_source',{},confirmed=True,
                            client_factory=_FakeEditingClient)
    assert result['result']=='UNVERIFIED'
    assert not (tmp_path/'fresh.verse').exists()


def test_guarded_editor_requires_authorization(tmp_path):
    with pytest.raises(PermissionError):
        mcp_guarded_edit(tmp_path,'a.verse',None,'a := class(creative_device):\n',
                         'http://127.0.0.1:8000/mcp','write_source',{},confirmed=False,
                         client_factory=_FakeEditingClient)
