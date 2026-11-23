from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.asset_engine import import_assets
from verseforge_core.ui_engine import render_ui
from PIL import Image


def _spec():
    return {'schema':'verseforge-asset-import-v1','assets':[{'source':'icon.png','target':'UI/icon.png',
       'license':'OWNER-CREATED','origin':'original','creator':'User original icon','rights_reviewed':True}]}


def _ui():
    return {'schema':'verseforge-visual-observations-v1','screens':[{'id':'home','elements':[
        {'id':'logo','kind':'image','text':'Original logo','bounds':{'x':.2,'y':.1,'w':.2,'h':.2},
         'evidence':'user-specified','action':'display','asset':'UI/icon.png'}]}]}


def _pack(tmp_path):
    source=tmp_path/'images';source.mkdir()
    Image.new('RGB',(40,40),(23,34,45)).save(source/'icon.png')
    import_assets(_spec(),source,tmp_path/'licensed')
    return tmp_path/'licensed'


def test_original_asset_appears_in_html_and_manifest(tmp_path):
    pack=_pack(tmp_path)
    result=render_ui(_ui(),tmp_path/'mock',assets_dir=pack,emit_verse=True)
    assert result['attached_assets']==1
    assert (tmp_path/'mock/preview-assets/UI/icon.png').read_bytes() == (pack/'UI/icon.png').read_bytes()
    content=(tmp_path/'mock/preview.html').read_text()
    assert 'src="preview-assets/UI/icon.png"' in content
    manifest=json.loads((tmp_path/'mock/ASSET_MANIFEST.json').read_text())
    assert manifest['assets'][0]['license']=='OWNER-CREATED'
    assert json.loads((tmp_path/'mock/UMG_HANDOFF.json').read_text())['screens'][0]['widgets'][0]['asset']=='UI/icon.png'


def test_asset_preview_without_files_stays_placeholder(tmp_path):
    report=render_ui(_ui(),tmp_path/'mock')
    assert report['attached_assets']==0
    assert 'preview-assets' not in (tmp_path/'mock/preview.html').read_text()


def test_ui_asset_missing_in_approved_pack(tmp_path):
    pack=_pack(tmp_path)
    ui=_ui();ui['screens'][0]['elements'][0]['asset']='UI/absent.png'
    with pytest.raises(ValueError):render_ui(ui,tmp_path/'mock',assets_dir=pack)


def test_ui_asset_path_traversal_rejected(tmp_path):
    ui=_ui();ui['screens'][0]['elements'][0]['asset']='UI/../../secret.png'
    with pytest.raises(ValueError):render_ui(ui,tmp_path/'mock')


def test_ui_wrong_widget_kind_rejected(tmp_path):
    ui=_ui();ui['screens'][0]['elements'][0]['kind']='button'
    with pytest.raises(ValueError):render_ui(ui,tmp_path/'mock')


def test_ui_asset_tamper_rejected(tmp_path):
    pack=_pack(tmp_path)
    with (pack/'UI/icon.png').open('ab') as f:f.write(b'BOGUS')
    with pytest.raises(ValueError):render_ui(_ui(),tmp_path/'mock',assets_dir=pack)


def test_ui_asset_symlink_rejected(tmp_path):
    pack=_pack(tmp_path)
    (pack/'UI/icon.png').unlink()
    (pack/'UI/icon.png').symlink_to(tmp_path/'fake.png')
    with pytest.raises(ValueError):render_ui(_ui(),tmp_path/'mock',assets_dir=pack)
