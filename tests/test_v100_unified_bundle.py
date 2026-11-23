"""Integration: source-owned gameplay, licensing and UI preview in one offline bundle."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.unified_bundle import build_bundle
from verseforge_core.chat_package import verify_package


def spec():
    return {'schema':'verseforge-engineering-spec-v1', 'project':'city_rp', 'description':'City RP financial engine',
            'modules':[{'id':'bank','kind':'economy','state_scope':'player-persistent',
                        'owns':['wallet'],'requirements':['Prevent double spending']} ]}


def source(tmp_path):
    p=tmp_path/'staging';(p/'Verse').mkdir(parents=True)
    (p/'Verse/bank_device.verse').write_text('''using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }
bank_device := class(creative_device):
    OnBegin<override>()<suspends>:void =
        Print("UI ready")
''')
    return p


def ui():
    return {'schema':'verseforge-visual-observations-v1','screens':[
        {'id':'home','elements':[{'id':'header','kind':'text','text':'CITY RP',
            'bounds':{'x':.1,'y':.1,'w':.5,'h':.2},'action':'display','evidence':'user-specified'}]}]}


def test_bundle_with_preview(tmp_path):
    result=build_bundle(spec(),source(tmp_path),tmp_path/'delivered',uefn_version='43.10',ui_observations=ui())
    assert result['result']=='BUNDLE CREATED' and result['ui_preview']
    dest=tmp_path/'delivered'
    assert verify_package(dest/'GAMEPLAY.zip')['result']=='PASS'
    assert (dest/'UI_PREVIEW/preview.html').is_file()
    report=json.loads((dest/'BUNDLE_REPORT.json').read_text())
    assert report['umg_asset']=='NOT GENERATED' and report['uefn_compile']=='NOT TESTED'


def test_bundle_missing_module_does_not_publish(tmp_path):
    src=source(tmp_path)
    (src/'Verse/bank_device.verse').unlink()
    dst=tmp_path/'delivered'
    result=build_bundle(spec(),src,dst,uefn_version='43.10')
    assert result['result']=='BLOCKED' and not dst.exists()


def test_bundle_rejects_output_inside_source(tmp_path):
    src=source(tmp_path)
    with pytest.raises(ValueError,match='outside'):
        build_bundle(spec(),src,src/'out',uefn_version='43.10')


def test_bundle_rejects_partial_asset_configuration(tmp_path):
    src=source(tmp_path)
    with pytest.raises(ValueError,match='together'):
        build_bundle(spec(),src,tmp_path/'out',uefn_version='43.10',asset_spec={'assets':[]})


def test_bundle_rejects_symlinked_sources(tmp_path):
    src=source(tmp_path)
    (src/'evil').symlink_to(tmp_path/'missing')
    with pytest.raises(ValueError,match='Symlink'):
        build_bundle(spec(),src,tmp_path/'out',uefn_version='43.10')


def test_bundle_with_reviewed_assets(tmp_path):
    from PIL import Image
    src=source(tmp_path)
    asset_root=tmp_path/'images';asset_root.mkdir()
    Image.new('RGB',(32,32),'black').save(asset_root/'icon.png')
    asset_spec={'schema':'verseforge-asset-import-v1','assets':[{
        'source':'icon.png','target':'UI/icon.png','origin':'original',
        'license':'OWNER-CREATED','creator':'owner','rights_reviewed':True}]}
    result=build_bundle(spec(),src,tmp_path/'out',uefn_version='43.10',ui_observations=ui(),
                        asset_spec=asset_spec,local_asset_sources=asset_root)
    assert result['result']=='BUNDLE CREATED'
    assert result['reviewed_asset_pack'] is True
    assert verify_package(tmp_path/'out/GAMEPLAY.zip')['result']=='PASS'
