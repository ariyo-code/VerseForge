"""VerseForge new engines: deterministic functionality and adversarial input tests.

No tests here are Verse compilation or real Fortnite gameplay tests.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verseforge_core.engineering_engine import architecture, scaffold
from verseforge_core.ui_engine import render_ui
from verseforge_core.verse_ui_generator import generate_verse_ui
from verseforge_core.asset_engine import import_assets
from verseforge_core.distribution import release, verify_release, install_release, restore_backup


def spec():
    return {"schema":"verseforge-engineering-spec-v1", "project":"city_rp", "description":"Modular City RP systems",
            "modules":[
                {"id":"economy", "kind":"economy", "state_scope":"player-persistent", "owns":["player_wallet"],
                 "permissions":["economy_modify"], "requirements":["No double crediting"]},
                {"id":"vehicles", "kind":"vehicle", "state_scope":"session", "owns":["vehicle_keys"], "depends_on":["economy"],
                 "requirements":["Owner and key handling"], "api_claims":["vehicle_spawner_device"]},
                {"id":"inventory", "kind":"inventory", "state_scope":"player-persistent", "owns":["player_items"],
                 "depends_on":["economy"], "requirements":["No item duplication"]},
                {"id":"admin_ui", "kind":"ui", "depends_on":["vehicles", "inventory"], "requirements":["Owner permissions"]},
            ]}


def vision():
    return {"schema":"verseforge-visual-observations-v1", "screens":[
       {"id":"home","elements":[
           {"id":"heading", "kind":"text", "text":"City RP <script>alert(1)</script>", "bounds":{"x":.1,"y":.1,"w":.7,"h":.1}, "action":"display", "evidence":"observed"},
           {"id":"to_bank","kind":"button","text":"Bank","bounds":{"x":.2,"y":.4,"w":.2,"h":.1},"action":"navigate","target":"bank","evidence":"user-specified"}]},
       {"id":"bank","elements":[{"id":"close","kind":"button","text":"Close","bounds":{"x":.8,"y":.1,"w":.1,"h":.1},"action":"close","evidence":"observed"}]}]}


def test_engineering_order_and_ownership():
    out=architecture(spec())
    assert out['module_order'].index('economy') < out['module_order'].index('vehicles')
    assert out['module_order'][-1]=='admin_ui'
    assert out['state_owners']['player_wallet']=='economy'
    assert out['uefn_compile']=='NOT TESTED'


def test_engineering_deterministic():
    assert architecture(spec())==architecture(spec())


def test_scaffold_files_and_owner(tmp_path):
    p=architecture(spec()); result=scaffold(p,tmp_path/'generated')
    assert result['files']==7
    assert (tmp_path/'generated/Verse/admin_ui_device.verse').is_file()
    assert 'NOT TESTED' in (tmp_path/'generated/README.md').read_text()
    with pytest.raises(ValueError):scaffold(p,tmp_path/'generated')


@pytest.mark.parametrize('change',[
    lambda s:s['modules'].append(s['modules'][0].copy()),
    lambda s:s['modules'][1].update(depends_on=['unknown']),
    lambda s:s['modules'][0].update(depends_on=['admin_ui']),
    lambda s:s['modules'][1].update(owns=['player_wallet']),
    lambda s:s['modules'][0].update(state_scope='global-persistent'),
    lambda s:s['modules'][2].update(state_scope='none'),
    lambda s:s['modules'][0].update(id='../../files'),
    lambda s:s.update(schema='other'),
])
def test_engineering_fail_closed(change):
    obj=spec();change(obj)
    with pytest.raises(ValueError):architecture(obj)


def test_ui_preview_handoff_and_scaffold(tmp_path):
    report=render_ui(vision(),tmp_path/'preview',emit_verse=True)
    assert report['screens']==2 and report['widgets']==3
    page=(tmp_path/'preview/preview.html').read_text()
    assert '<script>alert(1)</script>' not in page
    assert '&lt;script&gt;' in page
    assert 'screen_home' in page and 'screen_bank' in page
    assert 'data-target="bank"' in page
    assert 'screen_bank' in page
    assert 'Verse UI' in (tmp_path/'preview/IMPLEMENTATION.md').read_text() or 'UMG' in (tmp_path/'preview/IMPLEMENTATION.md').read_text()
    source=(tmp_path/'preview/Verse/vf_generated_ui_device.verse').read_text()
    assert 'OnBegin<override>()' in source and 'Go_s0_to_bank' in source
    assert 'NOT TESTED' in source


def test_ui_source_is_not_a_compiler_claim():
    out=generate_verse_ui(vision())
    assert out['source_status']=='GENERATED — COMPILATION NOT TESTED'
    assert out['umg_asset']=='NOT GENERATED'
    assert out['unimplemented_actions']==[]


def test_ui_extra_actions_unimplemented():
    obs=vision();obs['screens'][0]['elements'][1]['action']='submit';obs['screens'][0]['elements'][1].pop('target')
    out=generate_verse_ui(obs)
    assert out['unimplemented_actions'][0]['status'].startswith('NOT IMPLEMENTED')


@pytest.mark.parametrize('bad',[
    lambda o:o['screens'][0]['elements'][1].update(target='../../evil'),
    lambda o:o['screens'][0]['elements'][1].update(target='absent'),
    lambda o:o['screens'][0]['elements'][0].update(target='bank'),
    lambda o:o['screens'][0]['elements'][0].update(bounds={"x":.9,"y":.9,"w":.3,"h":.3}),
])
def test_ui_reject_bad_observations(bad):
    obj=vision();bad(obj)
    with pytest.raises(ValueError):generate_verse_ui(obj)


def test_ui_output_never_overwritten(tmp_path):
    folder=tmp_path/'out';folder.mkdir()
    with pytest.raises(ValueError):render_ui(vision(),folder)


def _image(path:Path):
    from PIL import Image
    im=Image.new('RGB',(48,48),(20,30,40));im.save(path)


def _asset_spec():
    return {"schema":"verseforge-asset-import-v1", "assets":[
        {"source":"icon.png","target":"UI/icon.png","license":"OWNER-CREATED","origin":"original",
         "creator":"Project owner", "rights_reviewed":True}]}


def test_asset_import_hash_and_manifest(tmp_path):
    inp=tmp_path/'in';inp.mkdir();_image(inp/'icon.png')
    report=import_assets(_asset_spec(), inp, tmp_path/'out')
    assert report['files']==1
    assert report['manifest']['result']=='PASS'
    assert (tmp_path/'out/UI/icon.png').is_file()
    assert 'rights' in report['legal_review'].lower() or 'verified' in report['legal_review'].lower()


def test_asset_image_resize(tmp_path):
    inp=tmp_path/'in';inp.mkdir();_image(inp/'icon.png')
    obj=_asset_spec();obj['assets'][0]['max_dimension']=128
    result=import_assets(obj,inp,tmp_path/'out');assert result['files']==1


@pytest.mark.parametrize('mutate',[
    lambda s:s['assets'][0].update(rights_reviewed=False),
    lambda s:s['assets'][0].update(target='../../secret.png'),
    lambda s:s['assets'][0].update(target='README.md'),
    lambda s:s['assets'][0].update(license='unknown'),
    lambda s:s['assets'][0].update(origin='third-party'),
    lambda s:s['assets'][0].update(max_dimension=99999),
    lambda s:s['assets'].append(s['assets'][0].copy()),
])
def test_asset_import_fail_closed(mutate,tmp_path):
    inp=tmp_path/'in';inp.mkdir();_image(inp/'icon.png')
    obj=_asset_spec();mutate(obj)
    with pytest.raises(ValueError):import_assets(obj,inp,tmp_path/'out')


def test_asset_symlink_not_allowed(tmp_path):
    inp=tmp_path/'in';inp.mkdir();_image(tmp_path/'original.png')
    (inp/'icon.png').symlink_to(tmp_path/'original.png')
    with pytest.raises(ValueError):import_assets(_asset_spec(),inp,tmp_path/'out')


def test_asset_rejects_fake_png(tmp_path):
    inp=tmp_path/'in';inp.mkdir();(inp/'icon.png').write_text('not a png')
    with pytest.raises(ValueError):import_assets(_asset_spec(),inp,tmp_path/'out')


def _skill(tmp_path:Path):
    source=tmp_path/'skill';source.mkdir()
    (source/'SKILL.md').write_text('---\nname: verseforge\n---\nReal skill')
    (source/'README.md').write_text('Manual')
    (source/'scripts').mkdir();(source/'scripts/tool.py').write_text('print(1)')
    return source


def test_release_build_verify_deterministic(tmp_path):
    source=_skill(tmp_path)
    first=release(source,tmp_path/'one.zip','1.0.0-rc2')
    second=release(source,tmp_path/'two.zip','1.0.0-rc2')
    assert first['sha256']==second['sha256']
    assert verify_release(tmp_path/'one.zip')['files']==3


def test_release_install_upgrade_restore(tmp_path):
    source=_skill(tmp_path)
    release(source,tmp_path/'one.zip','1.0.0-rc2')
    installed=install_release(tmp_path/'one.zip',tmp_path/'install')
    assert installed['result']=='INSTALLED'
    (source/'README.md').write_text('Updated')
    release(source,tmp_path/'two.zip','1.0.0')
    result=install_release(tmp_path/'two.zip',tmp_path/'install',upgrade=True)
    assert result['backup']
    assert (tmp_path/'install/README.md').read_text()=='Updated'
    restored=restore_backup(tmp_path/'install',Path(result['backup']))
    assert restored['result']=='RESTORED'
    assert (tmp_path/'install/README.md').read_text()=='Manual'


def test_release_existing_unknown_dir_rejected(tmp_path):
    source=_skill(tmp_path);release(source,tmp_path/'one.zip','1.0.0')
    unknown=tmp_path/'target';unknown.mkdir()
    with pytest.raises(ValueError):install_release(tmp_path/'one.zip',unknown,upgrade=True)


def test_release_rejects_symlink(tmp_path):
    source=_skill(tmp_path)
    (source/'scripts/bad.py').symlink_to(source/'README.md')
    with pytest.raises(ValueError):release(source,tmp_path/'one.zip','1.0.0')


def test_release_tampered_content_fails(tmp_path):
    source=_skill(tmp_path);release(source,tmp_path/'one.zip','1.0.0')
    with zipfile.ZipFile(tmp_path/'one.zip') as z:
        files={k:z.read(k) for k in z.namelist()}
    files['README.md']=b'Hacked'
    with zipfile.ZipFile(tmp_path/'evil.zip','w') as z:
        for k,v in files.items():z.writestr(k,v)
    with pytest.raises(ValueError):verify_release(tmp_path/'evil.zip')


def test_release_zip_slip_rejected(tmp_path):
    source=_skill(tmp_path);release(source,tmp_path/'one.zip','1.0.0')
    with zipfile.ZipFile(tmp_path/'one.zip') as z:files={k:z.read(k) for k in z.namelist()}
    with zipfile.ZipFile(tmp_path/'evil.zip','w') as z:
        for k,v in files.items():z.writestr(k,v)
        z.writestr('../hacked.txt','oops')
    with pytest.raises(ValueError):verify_release(tmp_path/'evil.zip')


def test_release_prevents_private_key(tmp_path):
    source=_skill(tmp_path)
    (source/'README.md').write_text('-----BEGIN PRIVATE KEY-----\n'+'A'*90+'\n-----END PRIVATE KEY-----\n')
    with pytest.raises(ValueError):release(source,tmp_path/'one.zip','1.0.0')
