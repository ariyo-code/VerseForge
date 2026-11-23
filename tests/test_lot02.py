"""LOT 02 local behavioral tests. Explicitly not UEFN/LLM/editor tests."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import pytest

SKILL=Path(__file__).resolve().parents[1]
BENCH=SKILL/'examples/benchmarks'
sys.path.insert(0,str(SKILL/'scripts'))
from verseforge_core.xray import project_xray
from verseforge_core.workspace import safe_target,edit_project,rollback
from verseforge_core.reliability import check_claims
from verseforge_core.gates import promote,static_review
from verseforge_core.repair import classify,next_attempt
from verseforge_core.build import prepare,verify_proposal
from verseforge_core.mcp_probe import _loopback,inspect_config,probe


def plan(path,body,old=None):
    return {'schema':'verseforge-edits-v1','purpose':'local test','changes':[{'path':path,'old_sha256':old,'new_content':body}]}


def test_xray_real_verse(tmp_path):
    (tmp_path/'Bank.verse').write_text('using { /Fortnite.com/Devices }\nvar Saved:weak_map(player, profile) = map{}\nbank_manager := class(creative_device):\n    @editable\n    OpenButton:button_device = button_device{}\n    OnBegin<override>()<suspends>:void =\n        OpenButton.InteractedWithEvent.Subscribe(OnTap)\n')
    result=project_xray(tmp_path)
    assert result['potential_economy_owners']==['Bank.verse']
    assert result['persistent_map_count']==1
    assert result['files'][0]['editable']==[{'name':'OpenButton','type':'button_device'}]
    assert result['files'][0]['subscriptions'][0]['event']=='InteractedWithEvent'
    assert result['compiler']=='NOT TESTED'


def test_xray_duplicate_owner(tmp_path):
    for name in ('a','b'):(tmp_path/f'{name}.verse').write_text('the_same := class(creative_device):\n')
    r=project_xray(tmp_path)
    assert any('Duplicate class' in x for x in r['warnings'])


def test_xray_symlink_not_followed(tmp_path):
    (tmp_path/'safe.verse').write_text('safe_dev := class(creative_device):\n')
    (tmp_path/'link.verse').symlink_to(tmp_path/'safe.verse')
    assert project_xray(tmp_path)['file_count']==1


def test_preview_then_apply_then_rollback(tmp_path):
    body='my_device := class(creative_device):\n    Value:int = 3\n'
    p=plan('new/my_device.verse',body)
    assert edit_project(tmp_path,p)['result']=='PREVIEW'
    assert not (tmp_path/'new/my_device.verse').exists()
    result=edit_project(tmp_path,p,apply=True)
    assert (tmp_path/'new/my_device.verse').read_text()==body
    assert rollback(tmp_path,result['backup_batch'])['restored']==1
    assert not (tmp_path/'new/my_device.verse').exists()


def test_update_sha_precondition_and_restore(tmp_path):
    f=tmp_path/'foo.verse';original='foo := class(creative_device):\n';f.write_text(original)
    revised='foo := class(creative_device):\n    Enabled:logic = true\n'
    p=plan('foo.verse',revised,hashlib.sha256(original.encode()).hexdigest())
    out=edit_project(tmp_path,p,apply=True)
    assert f.read_text()==revised
    assert rollback(tmp_path,out['backup_batch'])['restored']==1
    assert f.read_text()==original


def test_reject_stale_and_overwrite(tmp_path):
    f=tmp_path/'test.verse';f.write_text('orig := class(creative_device):\n')
    with pytest.raises(ValueError,match='Precondition'):
        edit_project(tmp_path,plan('test.verse','orig := class(creative_device):\n'))
    with pytest.raises(ValueError,match='Precondition'):
        edit_project(tmp_path,plan('test.verse','orig := class(creative_device):\n','0'*64))


@pytest.mark.parametrize('bad', ['../oops.verse','/etc/demo.verse','../outside/test.verse','Content/A.verse','Saved/B.verse','C:\\tmp\\bad.verse','.verseforge/a.verse'])
def test_block_dangerous_paths(tmp_path,bad):
    with pytest.raises(ValueError):safe_target(tmp_path,bad)


def test_reject_symlinked_dir(tmp_path):
    (tmp_path/'target').mkdir()
    (tmp_path/'link').symlink_to(tmp_path/'target',target_is_directory=True)
    with pytest.raises(ValueError,match='Symlink'):safe_target(tmp_path,'link/hello.verse')


def test_detect_duplicate_class_in_existing_project(tmp_path):
    (tmp_path/'old.verse').write_text('money_service := class(creative_device):\n')
    with pytest.raises(ValueError,match='duplicated'):
        edit_project(tmp_path,plan('new.verse','money_service := class(creative_device):\n'),apply=True)


def test_detect_duplicate_classes_across_proposed_files(tmp_path):
    p={'schema':'verseforge-edits-v1','purpose':'test','changes':[
        {'path':'a.verse','old_sha256':None,'new_content':'same := class(creative_device):\n'},
        {'path':'b.verse','old_sha256':None,'new_content':'same := class(creative_device):\n'}]}
    with pytest.raises(ValueError,match='Duplicate class'):edit_project(tmp_path,p,apply=True)


def test_rollback_refuses_modified_file(tmp_path):
    result=edit_project(tmp_path,plan('new.verse','something := class(creative_device):\n'),apply=True)
    (tmp_path/'new.verse').write_text('human_change := class(creative_device):\n')
    with pytest.raises(ValueError,match='conflict'):rollback(tmp_path,result['backup_batch'])
    assert 'human_change' in (tmp_path/'new.verse').read_text()


def test_build_context_identifies_existing_economy(tmp_path):
    (tmp_path/'economy.verse').write_text('wallet_manager := class(creative_device):\n')
    out=prepare('Ajoute un garage persistant a mon économie',tmp_path)
    assert out['project_xray']['potential_economy_owners']==['economy.verse']
    assert out['compiler']=='NOT TESTED'


def test_verify_proposal_checks_before_write(tmp_path):
    p=plan('feature.verse','a_class := class(creative_device):\n')
    assert verify_proposal(tmp_path,p)['result']=='PREVIEW'
    assert not (tmp_path/'feature.verse').exists()
    assert verify_proposal(tmp_path,p,apply=True)['result']=='APPLIED'
    assert (tmp_path/'feature.verse').exists()


def test_claims_allow_with_provenance_and_deny_unverified():
    def fake_runner(args,repo):
        return {'available':True,'status':'PASS','stdout':json.dumps({'decision':'ALLOW','supported':True,'evidence_ids':['real-claim-123']})}
    out=check_claims(['button_device'],runner=fake_runner,fields=('signature','parameters'))
    assert out['result']=='PASS'
    assert out['symbols'][0]['claims']['signature']['evidence_ids']==['real-claim-123']
    def deny(args,repo):return {'available':True,'status':'ERROR','reason':'No proof'}
    out=check_claims(['UnknownApi'],runner=deny,fields=('signature',))
    assert out['result']=='NEEDS_API_VERIFICATION'
    assert out['symbols'][0]['claims']['signature']['decision']=='TODO(API VERIFY)'


def test_claims_reject_shelllike_symbol():
    with pytest.raises(ValueError):check_claims(['button_device;rm -rf /'])


def test_static_gate_does_not_pretend_compilation():
    out=static_review('test.verse','hello := class(creative_device):\n')
    assert out['syntax_heuristics']=='PASS' and out['uefn_compile']=='NOT TESTED'
    assert static_review('a.verse','not a class')['syntax_heuristics']=='FAIL'


def test_promotion_requires_real_evidence():
    with pytest.raises(ValueError):promote('draft','compiled',{})
    assert promote('draft','static-checked',{'static_report':{'success':True,'source':'local-tool','timestamp':'2026-11-22'}})['status']=='static-checked'
    with pytest.raises(ValueError):promote('static-checked','compiled',{'uefn_compile_log':{'success':True,'source':'mock','timestamp':'2026-11-22'}})
    with pytest.raises(ValueError):promote('verified','multiplayer-verified',{'multiplayer_test_record':{'success':True,'source':'session','source_type':'multi-client-session','timestamp':'2026-11-22','client_count':1,'raw_log_sha256':'a'*64}})


def test_compiler_error_parser_and_repair_attempts():
    out=classify('Foo.verse(12,4): error V101: unknown identifier\nOther.verse:22:5: warning W20')
    assert len(out['diagnostics'])==2
    assert out['diagnostics'][0]['line']==12
    sha='a'*64
    assert next_attempt([],sha)['result']=='PROPOSE'
    assert next_attempt([{'candidate_sha256':sha}],sha)['result']=='STOP'
    assert next_attempt([{}, {}, {}],'b'*64,max_attempts=3)['result']=='STOP'


def test_mcp_url_restriction_and_missing_config(tmp_path):
    for addr in ('https://example.com/mcp','http://192.168.1.1:8000/mcp','file:///etc/passwd','http://127.0.0.1/admin'):
        with pytest.raises(ValueError):_loopback(addr)
    assert inspect_config(tmp_path/'missing.json')['state']=='not-configured'
    p=tmp_path/'mcp.json';p.write_text(json.dumps({'mcpServers':{'unreal-mcp':{'type':'http','url':'http://127.0.0.1:8000/mcp'}}}))
    assert inspect_config(p)['servers'][0]['name']=='unreal-mcp'


def test_benchmark_real_sources_and_boundaries():
    rows={r.name:sorted(r.glob('*.verse')) for r in BENCH.iterdir() if r.is_dir()}
    assert len(rows)==3
    assert sorted(len(x) for x in rows.values()) == [1,1,2]
    for files in rows.values():
        for file in files:
            code=file.read_text()
            assert 'NOT TESTED' in code or 'not' in code
            assert static_review(file.name,code)['syntax_heuristics']=='PASS'
    assert 'RespawnVehicle()' in (BENCH/'C-rp-garage/vf_starter_garage_device.verse').read_text()
    assert 'AddWidget(' in (BENCH/'B-verse-ui/vf_two_view_ui_device.verse').read_text()
    assert '.Show(Who,' in (BENCH/'A-interactive-device/vf_interactive_notice_device.verse').read_text()


def test_cli_end_to_end(tmp_path):
    new='xray_device := class(creative_device):\n'
    p=tmp_path/'proposal.json';p.write_text(json.dumps(plan('feature.verse',new)))
    cli=SKILL/'scripts/vf.py'
    r=subprocess.run([sys.executable,str(cli),'proposal','--project',str(tmp_path),'--plan',str(p),'--apply'],capture_output=True,text=True)
    assert r.returncode==0,r.stderr+r.stdout
    batch=json.loads(r.stdout)['changes']['backup_batch']
    r2=subprocess.run([sys.executable,str(cli),'xray','--project',str(tmp_path)],capture_output=True,text=True)
    assert json.loads(r2.stdout)['classes']['xray_device']==['feature.verse']
    r3=subprocess.run([sys.executable,str(cli),'rollback','--project',str(tmp_path),'--batch',batch],capture_output=True,text=True)
    assert json.loads(r3.stdout)['result']=='ROLLED_BACK'


def test_rejects_invisible_unicode_markers(tmp_path):
    p=plan('bad.verse','foo := class(creative_device):\n    # hidden \u202e marker\n')
    with pytest.raises(ValueError,match='Invisible'):edit_project(tmp_path,p,apply=True)


def test_real_protocol_mcp_handshake_against_local_mock():
    """Proves client handshake implementation with a mock, NOT a real UEFN session."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            content=int(self.headers.get('Content-Length','0'))
            body=json.loads(self.rfile.read(content))
            method=body.get('method')
            if method=='notifications/initialized':
                self.send_response(202);self.end_headers();return
            if method=='initialize':
                response={'jsonrpc':'2.0','id':body['id'],'result':{
                    'protocolVersion':'2025-06-18','serverInfo':{'name':'test-mock','version':'1'},
                    'capabilities':{'tools':{}}}}
            else:
                response={'jsonrpc':'2.0','id':body['id'],'result':{'tools':[
                    {'name':'read_only_mock','inputSchema':{'type':'object','properties':{'path':{'type':'string'}}}}]}}
            payload=json.dumps(response).encode()
            self.send_response(200);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    try:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        result=probe(f'http://127.0.0.1:{server.server_port}/mcp')
        assert result['connection']=='connected',result
        assert result['tool_names']==['read_only_mock']
        assert result['discovered_tools'][0]['inputSchema']['type']=='object'
        assert result['uefn_editor']=='NOT TESTED'
    finally:
        server.shutdown();server.server_close()


def test_mcp_call_requires_explicit_consent_and_local_address():
    from verseforge_core.mcp_client import invoke_tool
    with pytest.raises(ValueError,match='confirmed'):
        invoke_tool('http://127.0.0.1:8000/mcp','read_verse_file',{},confirmed=False)
    with pytest.raises(ValueError,match='allow-mutation'):
        invoke_tool('http://127.0.0.1:8000/mcp','compile_verse',{},confirmed=True)
    with pytest.raises(ValueError,match='loopback'):
        invoke_tool('http://outside.com/mcp','read_verse_file',{},confirmed=True)


def test_mcp_call_real_protocol_with_explicit_local_mock_and_schema():
    """HTTP transport is tested against a fake server, NOT an actual UEFN editor."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from verseforge_core.mcp_client import invoke_tool
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            data=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            method=data['method']
            if method=='notifications/initialized':
                self.send_response(202);self.end_headers();return
            if method=='initialize': result={'protocolVersion':'2025-06-18','serverInfo':{'name':'mock-only','version':'1'},'capabilities':{'tools':{}}}
            elif method=='tools/list': result={'tools':[{'name':'read_verse_file','inputSchema':{'type':'object','properties':{'path':{'type':'string'}},'required':['path'],'additionalProperties':False}}]}
            elif method=='tools/call': result={'content':[{'type':'text','text':'MOCK READ OK'}],'isError':False}
            else:raise AssertionError('Unexpected MCP request')
            payload=json.dumps({'jsonrpc':'2.0','id':data['id'],'result':result}).encode()
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    try:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        endpoint=f'http://127.0.0.1:{server.server_port}/mcp'
        res=invoke_tool(endpoint,'read_verse_file',{'path':'safe.verse'},confirmed=True)
        assert res['result']=='MCP_TOOL_RESPONSE' and res['response']['result']['content'][0]['text']=='MOCK READ OK'
        assert res['uefn_compilation']=='NOT VERIFIED BY THIS CLIENT'
        with pytest.raises(ValueError,match="not advertised"):
            invoke_tool(endpoint,'nonexistent',{},confirmed=True)
        with pytest.raises(Exception):
            invoke_tool(endpoint,'read_verse_file',{'path':3},confirmed=True)
    finally:
        server.shutdown();server.server_close()


def test_api_cli_parses_comma_separated_fields(tmp_path):
    cli=SKILL/'scripts/vf.py'
    proc=subprocess.run([sys.executable,str(cli),'api-check','--fields','signature,parameters','button_device'],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr+proc.stdout
    obj=json.loads(proc.stdout)
    assert set(obj['symbols'][0]['claims'])=={'signature','parameters'}
    assert obj['result']=='NEEDS_API_VERIFICATION'  # No local verse-ai CLI installed


def test_real_persistent_class_is_detected_by_xray():
    p=BENCH/'C-rp-garage'
    r=project_xray(p)
    assert 'vf_garage_profile' in r['classes']
    assert r['persistent_map_count']==1


def test_module_only_verse_source_accepted_without_class(tmp_path):
    src='using { /Verse.org/Simulation }\nvar SharedRecord:weak_map(player, int) = map{}\n'
    r=edit_project(tmp_path,plan('profiles.verse',src),apply=True)
    assert r['result']=='APPLIED'
    assert static_review('profiles.verse',src)['syntax_heuristics']=='PASS'


def test_repeated_rollback_refused(tmp_path):
    r=edit_project(tmp_path,plan('x.verse','x := class(creative_device):\n'),apply=True)
    rollback(tmp_path,r['backup_batch'])
    with pytest.raises(ValueError,match='already rolled back'):
        rollback(tmp_path,r['backup_batch'])


def test_symlinked_backup_directory_refused(tmp_path):
    outside=tmp_path.parent/'external_vf_test'
    outside.mkdir(exist_ok=True)
    (tmp_path/'.verseforge').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='symlinked backup'):
        edit_project(tmp_path,plan('x.verse','x := class(creative_device):\n'),apply=True)
