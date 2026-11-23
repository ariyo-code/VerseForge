from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verseforge_core.asset_license import check_asset_manifest,SCHEMA
from verseforge_core.chat_package import package,verify_package


def rec(path,data,**kwargs):
    return {'path':path,'sha256':hashlib.sha256(data).hexdigest(),**kwargs}


def stage(tmp_path):
    s=tmp_path/'stage'
    (s/'Verse').mkdir(parents=True)
    (s/'Verse'/'simple.verse').write_text('simple := class():\n')
    (s/'UI').mkdir()
    (s/'UI'/'icon.png').write_bytes(b'\x89PNG\r\n\x1a\nnot actually image')
    return s


def manifest_own(s):
    p=s/'UI'/'icon.png'
    row=rec('UI/icon.png',p.read_bytes(),license='OWNER-CREATED',origin='original',creator='VerseForge user')
    (s/'ASSET_MANIFEST.json').write_text(json.dumps({'schema':SCHEMA,'assets':[row]}))


def test_no_resources_no_manifest():
    assert check_asset_manifest(None,{'Verse/a.verse':b'code'})['result']=='PASS'


def test_resource_requires_manifest(tmp_path):
    s=stage(tmp_path)
    with pytest.raises(ValueError,match='ASSET_MANIFEST'):package(s,tmp_path/'out.zip')


def test_original_asset_packaging(tmp_path):
    s=stage(tmp_path);manifest_own(s)
    out=tmp_path/'out.zip'
    package(s,out)
    assert verify_package(out)['result']=='PASS'


def test_asset_wrong_hash(tmp_path):
    s=stage(tmp_path);manifest_own(s)
    (s/'UI'/'icon.png').write_bytes(b'different')
    with pytest.raises(ValueError,match='hash mismatch'):package(s,tmp_path/'out.zip')


def test_third_party_without_evidence(tmp_path):
    s=stage(tmp_path)
    asset=(s/'UI'/'icon.png').read_bytes()
    row=rec('UI/icon.png',asset,license='MIT',origin='third-party',source_url='https://example.org/icons',
            attribution='Author')
    (s/'ASSET_MANIFEST.json').write_text(json.dumps({'schema':SCHEMA,'assets':[row]}))
    with pytest.raises(ValueError,match='license evidence'):package(s,tmp_path/'out.zip')


def test_third_party_license_record(tmp_path):
    s=stage(tmp_path)
    asset=(s/'UI'/'icon.png').read_bytes()
    row=rec('UI/icon.png',asset,license='MIT',origin='third-party',source_url='https://example.org/icons',
            license_url='https://example.org/LICENSE',attribution='Example contributors')
    (s/'ASSET_MANIFEST.json').write_text(json.dumps({'schema':SCHEMA,'assets':[row]}))
    output=tmp_path/'out.zip'
    package(s,output)
    assert verify_package(output)['result']=='PASS'


def test_third_party_missing_attribution(tmp_path):
    s=stage(tmp_path)
    asset=(s/'UI'/'icon.png').read_bytes()
    row=rec('UI/icon.png',asset,license='MIT',origin='third-party',source_url='https://example.org/icons',
            license_url='https://example.org/LICENSE')
    (s/'ASSET_MANIFEST.json').write_text(json.dumps({'schema':SCHEMA,'assets':[row]}))
    with pytest.raises(ValueError,match='Attribution'):package(s,tmp_path/'out.zip')


def test_manifest_unknown_license(tmp_path):
    s=stage(tmp_path)
    asset=(s/'UI'/'icon.png').read_bytes()
    row=rec('UI/icon.png',asset,license='UNLICENSED',origin='third-party')
    (s/'ASSET_MANIFEST.json').write_text(json.dumps({'schema':SCHEMA,'assets':[row]}))
    with pytest.raises(ValueError,match='Unknown asset license'):package(s,tmp_path/'out.zip')
