from __future__ import annotations
import argparse
import json
from pathlib import Path
from .knowledge import run_knowledge
from .project import inspect_project,build_plan
from .provenance import verify
from .validation import validate
from .ui import ui_plan
from .xray import project_xray
from .workspace import rollback
from .build import prepare,verify_proposal
from .reliability import check_claims
from .mcp_probe import probe,inspect_config
from .mcp_client import invoke_tool
from .repair import classify,next_attempt
from .gates import promote,static_review
from .environment import diagnose
from .mcp_runtime import connect_report
from .compilation import compile_project,unavailability_record
from .repair_session import run_repair_session
from .mcp_sync import mcp_guarded_edit
from .chat_mode import route as chat_route, menu as chat_menu, guide as chat_guide
from .chat_package import package as chat_package, verify_package as verify_chat_package
from .quality_engine import review_sources, load_contract
from .delivery_pipeline import deliver
from .visual_reverse import inspect_image, load_visual_spec, plan_from_observations
from .engineering_engine import architecture, load_engineering_spec, scaffold
from .ui_engine import render_ui
from .asset_engine import import_assets
from .asset_catalog import discover_sources
from .distribution import release, verify_release, install_release, restore_backup
from .knowledge_sync import knowledge_audit, make_lock
from .release_signature import sign_release, verify_release_signature
from .compose_engine import compose_project
from .recipe_generator import generate_button_hud
from .unified_bundle import build_bundle

ROOT=Path(__file__).resolve().parents[2]

def main(argv=None):
    p=argparse.ArgumentParser(prog='vf',description='VerseForge offline + opt-in MCP helpers; NOT a Verse compiler')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('validate')
    doctor=sub.add_parser('doctor');doctor.add_argument('--knowledge')
    scan=sub.add_parser('scan');scan.add_argument('--project',required=True)
    xray=sub.add_parser('xray');xray.add_argument('--project',required=True);xray.add_argument('--output')
    plan=sub.add_parser('plan');plan.add_argument('--request',required=True);plan.add_argument('--project');plan.add_argument('--output')
    context=sub.add_parser('build-context');context.add_argument('--request',required=True);context.add_argument('--project',required=True);context.add_argument('--output')
    prop=sub.add_parser('proposal');prop.add_argument('--project',required=True);prop.add_argument('--plan',required=True);prop.add_argument('--apply',action='store_true')
    restore=sub.add_parser('rollback');restore.add_argument('--project',required=True);restore.add_argument('--batch',required=True)
    know=sub.add_parser('knowledge');know.add_argument('--repo');know.add_argument('args',nargs=argparse.REMAINDER)
    api=sub.add_parser('api-check');api.add_argument('--repo');api.add_argument('--fields',default='presence,module,signature,parameters,return_type,effects');api.add_argument('symbols',nargs='+')
    ui=sub.add_parser('ui-plan');ui.add_argument('--style',required=True);ui.add_argument('--screen',default='garage');ui.add_argument('--output')
    pv=sub.add_parser('provenance-verify');pv.add_argument('--file',required=True);pv.add_argument('--manifest',required=True);pv.add_argument('--public-key',required=True);pv.add_argument('--root')
    mcpc=sub.add_parser('mcp-config');mcpc.add_argument('--file',required=True)
    mcpp=sub.add_parser('mcp-probe');mcpp.add_argument('--endpoint',required=True)
    mcpa=sub.add_parser('mcp-call');mcpa.add_argument('--endpoint',required=True);mcpa.add_argument('--tool',required=True);mcpa.add_argument('--arguments',required=True);mcpa.add_argument('--confirmed',action='store_true');mcpa.add_argument('--allow-mutation',action='store_true')
    errors=sub.add_parser('repair-analyze');errors.add_argument('--log',required=True)
    nextp=sub.add_parser('repair-next');nextp.add_argument('--history',required=True);nextp.add_argument('--candidate-sha256',required=True);nextp.add_argument('--max-attempts',type=int,default=3)
    gate=sub.add_parser('promote');gate.add_argument('--current',required=True);gate.add_argument('--target',required=True);gate.add_argument('--evidence',required=True)
    static=sub.add_parser('static-review');static.add_argument('--file',required=True)
    env=sub.add_parser('environment');env.add_argument('--project');env.add_argument('--endpoint');env.add_argument('--knowledge-endpoint');env.add_argument('--probe',action='store_true');env.add_argument('--config',action='append')
    registry=sub.add_parser('mcp-registry');registry.add_argument('--endpoint',required=True)
    comp=sub.add_parser('compile');comp.add_argument('--project',required=True);comp.add_argument('--endpoint',required=True);comp.add_argument('--tool',required=True);comp.add_argument('--arguments',required=True);comp.add_argument('--files',nargs='+',required=True);comp.add_argument('--evidence-dir',required=True);comp.add_argument('--confirm-uefn-compile',action='store_true');comp.add_argument('--uefn-version')
    sync=sub.add_parser('mcp-sync-edit');sync.add_argument('--project',required=True);sync.add_argument('--path',required=True);sync.add_argument('--expected-sha256');sync.add_argument('--new-file',required=True);sync.add_argument('--endpoint',required=True);sync.add_argument('--tool',required=True);sync.add_argument('--arguments',required=True);sync.add_argument('--confirmed',action='store_true')
    session=sub.add_parser('repair-session');session.add_argument('--project',required=True);session.add_argument('--baseline',required=True);session.add_argument('--candidates',required=True);session.add_argument('--endpoint',required=True);session.add_argument('--tool',required=True);session.add_argument('--arguments',required=True);session.add_argument('--files',nargs='+',required=True);session.add_argument('--evidence-dir',required=True);session.add_argument('--confirm-uefn-compile',action='store_true');session.add_argument('--allow-edit',action='store_true');session.add_argument('--max-attempts',type=int,default=3)
    mn=sub.add_parser('menu',help='Show simple VerseForge features; does not activate host-native buttons')
    mn.add_argument('--format',choices=['text','json'],default='text')
    ch=sub.add_parser('chat-route',help='Choose output based on declared capabilities')
    ch.add_argument('--request',default='')
    ch.add_argument('--output',choices=['auto','code','zip','project'],default='auto')
    ch.add_argument('--can-create-files',action='store_true')
    ch.add_argument('--can-edit-project',action='store_true')
    ch.add_argument('--uefn-connected',action='store_true')
    wizard=sub.add_parser('guide',help='Progress one beginner-friendly Control Center choice into a task')
    wizard.add_argument('--choice',help='Choice 1-7, name or id; omitted to show the menu')
    wizard.add_argument('--details',default='',help='User goal or code/error text; passed only to the host LLM')
    wizard.add_argument('--output',choices=['auto','code','zip','project'],default='auto')
    wizard.add_argument('--can-create-files',action='store_true')
    wizard.add_argument('--can-edit-project',action='store_true')
    wizard.add_argument('--uefn-connected',action='store_true')
    pverify=sub.add_parser('package-verify',help='Read and hash-audit an existing VerseForge ZIP without extracting it')
    pverify.add_argument('--file',required=True)
    exp=sub.add_parser('package',help='ZIP only an explicitly staged, allowlisted Verse project output')
    exp.add_argument('--source',required=True)
    exp.add_argument('--output',required=True)
    quality=sub.add_parser('quality-review', help='Heuristic static review and acceptance check; NEVER UEFN compile')
    quality.add_argument('--source', required=True)
    quality.add_argument('--contract')
    visual_img=sub.add_parser('visual-inspect', help='Read non-semantic pixel properties from a local image')
    visual_img.add_argument('--image', required=True)
    visual_plan=sub.add_parser('visual-plan', help='Validate host-vision observation JSON; no Verse or UMG generated')
    visual_plan.add_argument('--spec', required=True)
    visual_plan.add_argument('--image')
    visual_plan.add_argument('--output')
    delivery=sub.add_parser('deliver', help='Review staged agent-authored Verse, create and verify ZIP')
    delivery.add_argument('--source', required=True)
    delivery.add_argument('--output', required=True)
    delivery.add_argument('--contract')
    delivery.add_argument('--strict', action='store_true')
    arch=sub.add_parser('architect', help='Validate module DAG/state owners; optionally create skeletal Verse devices')
    arch.add_argument('--spec', required=True)
    arch.add_argument('--output')
    arch.add_argument('--scaffold-dir')
    uir=sub.add_parser('ui-render', help='Generate browser mock and UMG handoff (no .uasset)')
    uir.add_argument('--spec', required=True)
    uir.add_argument('--output', required=True)
    uir.add_argument('--theme', choices=['dark','light'], default='dark')
    uir.add_argument('--emit-verse', action='store_true', help='Also emit experimental Verse UI scaffold (requires UEFN compile)')
    uir.add_argument('--assets-dir',help='Optional reviewed local asset pack with ASSET_MANIFEST.json')
    uir.add_argument('--design-tokens',help='Optional Design DNA JSON with validated hex palette')
    sources=sub.add_parser('asset-sources', help='Explore curated sources; does not download, authorize, or import third-party assets')
    sources.add_argument('--query',default='')
    sources.add_argument('--category',choices=['icon','aggregator','game-assets','marketplace','official','texture','font','illustration','audio'])
    sources.add_argument('--reviewed-only',action='store_true')
    assets=sub.add_parser('assets-import', help='Import approved local assets with original/third-party license metadata')
    assets.add_argument('--spec', required=True)
    assets.add_argument('--root', required=True)
    assets.add_argument('--output', required=True)
    dist=sub.add_parser('release-build', help='Deterministically build a public skill ZIP, never owner-private service')
    dist.add_argument('--skill-root')
    dist.add_argument('--version', required=True)
    dist.add_argument('--output', required=True)
    dist_check=sub.add_parser('release-verify')
    dist_check.add_argument('--file', required=True)
    dist_install=sub.add_parser('release-install')
    dist_install.add_argument('--file', required=True)
    dist_install.add_argument('--target', required=True)
    dist_install.add_argument('--upgrade', action='store_true')
    dist_install.add_argument('--allow-downgrade', action='store_true')
    dist_install.add_argument('--signature',help='Optional detached release signature')
    dist_install.add_argument('--public-key',help='Trusted publisher public PEM when signature is provided')
    dist_rb=sub.add_parser('release-rollback')
    dist_rb.add_argument('--target', required=True)
    dist_rb.add_argument('--backup', required=True)
    ka=sub.add_parser('knowledge-audit', help='Read-only API snapshot drift and Git commit report')
    ka.add_argument('--repo', required=True)
    ka.add_argument('--uefn-version', required=True)
    ka.add_argument('--expected-commit')
    ka.add_argument('--lock')
    sig=sub.add_parser('release-sign',help='Owner-only detached Ed25519 public release signature')
    sig.add_argument('--file',required=True)
    sig.add_argument('--private-key',required=True)
    sig.add_argument('--output',required=True)
    sigverify=sub.add_parser('release-signature-verify',help='Check release bytes and trusted publisher key')
    sigverify.add_argument('--file',required=True)
    sigverify.add_argument('--signature',required=True)
    sigverify.add_argument('--public-key',required=True)
    bundle=sub.add_parser('bundle-project',help='Package host-authored Verse, optionally licensed assets and UI preview')
    bundle.add_argument('--spec',required=True)
    bundle.add_argument('--source',required=True)
    bundle.add_argument('--output',required=True)
    bundle.add_argument('--uefn-version',required=True)
    bundle.add_argument('--ui-spec')
    bundle.add_argument('--asset-spec')
    bundle.add_argument('--asset-root')
    bundle.add_argument('--api-evidence')
    recipe=sub.add_parser('recipe-button-hud', help='Generate original Button/HUD Verse device; UEFN compile NOT TESTED')
    recipe.add_argument('--spec',required=True)
    recipe.add_argument('--output',required=True)
    composer=sub.add_parser('compose-project',help='Integrate agent-authored modules with state/API/ZIP gates')
    composer.add_argument('--spec',required=True)
    composer.add_argument('--source',required=True)
    composer.add_argument('--output',required=True)
    composer.add_argument('--uefn-version',required=True)
    composer.add_argument('--api-evidence')
    ns=p.parse_args(argv)
    try:
        if ns.cmd=='architect':
            result=architecture(load_engineering_spec(Path(ns.spec)))
            if ns.scaffold_dir:
                result={'plan':result,'scaffold':scaffold(result,Path(ns.scaffold_dir))}
        elif ns.cmd=='ui-render':result=render_ui(load_visual_spec(Path(ns.spec)),Path(ns.output),theme=ns.theme,emit_verse=ns.emit_verse,assets_dir=Path(ns.assets_dir) if ns.assets_dir else None,design_tokens=json.loads(Path(ns.design_tokens).read_text(encoding="utf-8")) if ns.design_tokens else None)
        elif ns.cmd=='asset-sources':result=discover_sources(ROOT/'assets'/'sources.json',query=ns.query,category=ns.category,reviewed_only=ns.reviewed_only)
        elif ns.cmd=='assets-import':
            data=json.loads(Path(ns.spec).read_text(encoding='utf-8'))
            result=import_assets(data,Path(ns.root),Path(ns.output))
        elif ns.cmd=='release-build':result=release(Path(ns.skill_root) if ns.skill_root else ROOT,Path(ns.output),ns.version)
        elif ns.cmd=='release-verify':result=verify_release(Path(ns.file))
        elif ns.cmd=='release-install':
            if bool(ns.signature) != bool(ns.public_key):
                raise ValueError('Both --signature and --public-key are required for authenticated installation')
            authenticated = verify_release_signature(Path(ns.file),Path(ns.signature),Path(ns.public_key)) if ns.signature else None
            result=install_release(Path(ns.file),Path(ns.target),upgrade=ns.upgrade,allow_downgrade=ns.allow_downgrade)
            if authenticated:result['publisher_signature']=authenticated
        elif ns.cmd=='release-rollback':result=restore_backup(Path(ns.target),Path(ns.backup))
        elif ns.cmd=='bundle-project':
            result=build_bundle(load_engineering_spec(Path(ns.spec)),Path(ns.source),Path(ns.output),uefn_version=ns.uefn_version,
                ui_observations=load_visual_spec(Path(ns.ui_spec)) if ns.ui_spec else None,
                asset_spec=json.loads(Path(ns.asset_spec).read_text(encoding='utf-8')) if ns.asset_spec else None,
                local_asset_sources=Path(ns.asset_root) if ns.asset_root else None,
                api_evidence=json.loads(Path(ns.api_evidence).read_text(encoding='utf-8')) if ns.api_evidence else None)
        elif ns.cmd=='recipe-button-hud':
            result=generate_button_hud(json.loads(Path(ns.spec).read_text(encoding='utf-8')),Path(ns.output))
        elif ns.cmd=='compose-project':
            ledger=json.loads(Path(ns.api_evidence).read_text(encoding='utf-8')) if ns.api_evidence else None
            result=compose_project(load_engineering_spec(Path(ns.spec)),Path(ns.source),Path(ns.output),uefn_version=ns.uefn_version,api_evidence=ledger)
        elif ns.cmd=='release-sign':result=sign_release(Path(ns.file),Path(ns.private_key),Path(ns.output))
        elif ns.cmd=='release-signature-verify':result=verify_release_signature(Path(ns.file),Path(ns.signature),Path(ns.public_key))
        elif ns.cmd=='knowledge-audit':
            result=knowledge_audit(Path(ns.repo),ns.uefn_version,ns.expected_commit)
            if ns.lock:
                result['lock']=make_lock(result,Path(ns.lock))
        elif ns.cmd=='validate':result=validate(ROOT)
        elif ns.cmd=='menu':result=chat_menu(ns.format)
        elif ns.cmd=='chat-route':result=chat_route(ns.request,can_create_files=ns.can_create_files,can_edit_project=ns.can_edit_project,uefn_connected=ns.uefn_connected,output=ns.output)
        elif ns.cmd=='guide':result=chat_guide(ns.choice,ns.details,output=ns.output,can_create_files=ns.can_create_files,can_edit_project=ns.can_edit_project,uefn_connected=ns.uefn_connected)
        elif ns.cmd=='quality-review':result=review_sources(Path(ns.source),load_contract(Path(ns.contract)) if ns.contract else None)
        elif ns.cmd=='visual-inspect':result=inspect_image(Path(ns.image))
        elif ns.cmd=='visual-plan':
            result=plan_from_observations(load_visual_spec(Path(ns.spec)),inspect_image(Path(ns.image)) if ns.image else None)
        elif ns.cmd=='deliver':result=deliver(Path(ns.source),Path(ns.output),load_contract(Path(ns.contract)) if ns.contract else None,strict=ns.strict)
        elif ns.cmd=='package-verify':result=verify_chat_package(Path(ns.file))
        elif ns.cmd=='package':result=chat_package(Path(ns.source),Path(ns.output))
        elif ns.cmd=='doctor':
            base=Path(ns.knowledge).expanduser() if ns.knowledge else None
            result={'skill':validate(ROOT),'knowledge_repo_present':bool(base and (base/'AI_BOOTSTRAP.md').is_file()),
                    'knowledge_cli':run_knowledge(['version'],str(base) if base and base.exists() else None),
                    'uefn_editor':'NOT TESTED','verse_compiler':'NOT TESTED'}
        elif ns.cmd=='scan':result=inspect_project(Path(ns.project))
        elif ns.cmd=='xray':result=project_xray(Path(ns.project))
        elif ns.cmd=='plan':result=build_plan(ns.request,inspect_project(Path(ns.project)) if ns.project else None)
        elif ns.cmd=='build-context':result=prepare(ns.request,Path(ns.project))
        elif ns.cmd=='proposal':result=verify_proposal(Path(ns.project),json.loads(Path(ns.plan).read_text(encoding='utf-8')),apply=ns.apply)
        elif ns.cmd=='rollback':result=rollback(Path(ns.project),ns.batch)
        elif ns.cmd=='knowledge':
            args=ns.args[1:] if ns.args and ns.args[0]=='--' else ns.args
            result=run_knowledge(args,ns.repo)
        elif ns.cmd=='api-check':result=check_claims(ns.symbols,ns.repo,fields=tuple(field.strip() for field in ns.fields.split(',') if field.strip()))
        elif ns.cmd=='ui-plan':result=ui_plan(ROOT,ns.style,ns.screen)
        elif ns.cmd=='provenance-verify':result=verify(Path(ns.file),Path(ns.manifest),Path(ns.public_key),Path(ns.root) if ns.root else None)
        elif ns.cmd=='mcp-config':result=inspect_config(Path(ns.file))
        elif ns.cmd=='mcp-probe':result=probe(ns.endpoint)
        elif ns.cmd=='mcp-call':result=invoke_tool(ns.endpoint,ns.tool,json.loads(Path(ns.arguments).read_text(encoding='utf-8')),confirmed=ns.confirmed,allow_mutation=ns.allow_mutation)
        elif ns.cmd=='repair-analyze':result=classify(Path(ns.log).read_text(encoding='utf-8'))
        elif ns.cmd=='repair-next':result=next_attempt(json.loads(Path(ns.history).read_text(encoding='utf-8')),ns.candidate_sha256,ns.max_attempts)
        elif ns.cmd=='environment':result=diagnose(Path(ns.project) if ns.project else None,ns.endpoint,ns.knowledge_endpoint,[Path(c) for c in ns.config] if ns.config else None,probe_remote=ns.probe)
        elif ns.cmd=='mcp-registry':result=connect_report(ns.endpoint)
        elif ns.cmd=='compile':
            if not ns.confirm_uefn_compile:raise ValueError('Explicit --confirm-uefn-compile required')
            args=json.loads(Path(ns.arguments).read_text(encoding='utf-8'))
            result=compile_project(ns.endpoint,ns.tool,args,project=Path(ns.project),files=ns.files,evidence_dir=Path(ns.evidence_dir),confirmed=True,editor_version=ns.uefn_version)
        elif ns.cmd=='mcp-sync-edit':
            if not ns.confirmed:raise ValueError('Explicit --confirmed required')
            arguments=json.loads(Path(ns.arguments).read_text(encoding='utf-8'))
            content=Path(ns.new_file).read_text(encoding='utf-8')
            result=mcp_guarded_edit(Path(ns.project),ns.path,ns.expected_sha256,content,
                                   ns.endpoint,ns.tool,arguments,confirmed=True)
        elif ns.cmd=='repair-session':
            if not(ns.confirm_uefn_compile and ns.allow_edit):raise ValueError('Requires --confirm-uefn-compile and --allow-edit')
            args=json.loads(Path(ns.arguments).read_text(encoding='utf-8'))
            baseline=json.loads(Path(ns.baseline).read_text(encoding='utf-8'))
            candidates=json.loads(Path(ns.candidates).read_text(encoding='utf-8'))
            def runner():return compile_project(ns.endpoint,ns.tool,args,project=Path(ns.project),files=ns.files,evidence_dir=Path(ns.evidence_dir),confirmed=True)
            result=run_repair_session(Path(ns.project),baseline,candidates,runner,max_attempts=ns.max_attempts)
        elif ns.cmd=='promote':result=promote(ns.current,ns.target,json.loads(Path(ns.evidence).read_text(encoding='utf-8')))
        else:
            src=Path(ns.file)
            result=static_review(src.name,src.read_text(encoding='utf-8'))
        if ns.cmd in ('xray','plan','build-context','ui-plan','visual-plan','architect') and getattr(ns,'output',None):
            out=Path(ns.output)
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2,ensure_ascii=False))
        return 1 if result.get('result') in ('FAIL','BLOCKED') or result.get('status')=='ERROR' else 0
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({'result':'FAIL','reason':str(e)}))
        return 2
