"""LOT 04 tests: honest host capability selection and safe ZIP outputs."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verseforge_core.chat_mode import menu,route,classify
from verseforge_core.chat_package import package

@pytest.mark.parametrize('user_text',('','/verseforge','verseforge','$verseforge'))
def test_empty_invocation_menu(user_text):
    assert classify(user_text)['show_menu']

def test_menu_is_simple_and_doesnt_fake_buttons():
    result=menu()
    assert len(result['choices'])==7
    assert result['interactive_native_panel']=='NOT GUARANTEED'
    assert 'Créer un système' in result['display']

def test_bypass_menu_on_user_request():
    assert route('Crée un garage RP')['mode']=='BUILD'
    assert route('Corrige ce bug Verse')['mode']=='DEBUG'
    assert route('Je veux une interface HUD')['mode']=='UI'

def test_code_only_no_files():
    result=route('Crée un garage Verse ZIP')
    assert result['requested_output']=='zip'
    assert result['selected_output']=='code'
    assert result['uefn_compile']=='NOT TESTED'
    assert result['caveats']

def test_zip_if_host_explicitly_allows_files():
    assert route('Crée un garage ZIP',can_create_files=True)['selected_output']=='zip'

def test_project_requires_explicit_capability():
    result=route('Modifie mon projet',output='project',can_create_files=True)
    assert result['selected_output']=='zip'
    assert route('Modifie mon projet',can_edit_project=True,output='project')['selected_output']=='project'

def test_cannot_assume_editor_from_project_writer():
    result=route('Modifie mon projet',can_edit_project=True,output='project')
    assert result['uefn_compile']=='NOT TESTED'
    assert result['caveats']

def test_unknown_mode_rejected():
    with pytest.raises(ValueError):route('some request',output='powerpoint')

def _stage(tmp_path):
    p=tmp_path/'stage';(p/'Verse').mkdir(parents=True)
    (p/'Verse'/'Garage.verse').write_text('using { /Verse.org/Simulation }\n',encoding='utf-8')
    return p

def test_creates_zip_and_manifest(tmp_path):
    src=_stage(tmp_path)
    output=tmp_path/'delivery.zip'
    result=package(src,output)
    assert result['result']=='PASS'
    assert result['uefn_compile']=='NOT TESTED'
    assert output.is_file()
    with ZipFile(output) as z:
        assert sorted(z.namelist())==['INSTALL.md','VERSEFORGE_MANIFEST.json','Verse/Garage.verse']
        m=json.loads(z.read('VERSEFORGE_MANIFEST.json'))
        assert m['validation']['uefn_compile']=='NOT TESTED'
        assert {f['path']:f['sha256'] for f in m['files']}['Verse/Garage.verse']==hashlib.sha256(z.read('Verse/Garage.verse')).hexdigest()
    assert hashlib.sha256(output.read_bytes()).hexdigest()==result['sha256']

def test_zip_reproducible(tmp_path):
    src=_stage(tmp_path)
    a=tmp_path/'a.zip';b=tmp_path/'b.zip'
    package(src,a);package(src,b)
    assert a.read_bytes()==b.read_bytes()

def test_zip_no_overwrite(tmp_path):
    src=_stage(tmp_path)
    dest=tmp_path/'file.zip';package(src,dest)
    with pytest.raises(ValueError,match='overwrite'):package(src,dest)

def test_zip_fails_without_sources(tmp_path):
    src=tmp_path/'empty';src.mkdir()
    with pytest.raises(ValueError,match='At least one'):package(src,tmp_path/'p.zip')

def test_zip_fails_for_private_file(tmp_path):
    src=_stage(tmp_path)
    (src/'.env').write_text('SECRET=abc')
    with pytest.raises(ValueError,match='Unsupported'):package(src,tmp_path/'p.zip')

def test_zip_fails_for_python_script(tmp_path):
    src=_stage(tmp_path)
    (src/'Verse'/'run.py').write_text('print(1)')
    with pytest.raises(ValueError,match='Unsupported'):package(src,tmp_path/'p.zip')

def test_zip_fails_for_private_key(tmp_path):
    src=_stage(tmp_path)
    (src/'Verse'/'Garage.verse').write_bytes(b'-----BEGIN PRIVATE KEY-----\nabc')
    with pytest.raises(ValueError,match='Private key'):package(src,tmp_path/'p.zip')

def test_zip_fails_for_symlink(tmp_path):
    src=_stage(tmp_path)
    dest=src/'Verse'/'outside.verse'
    try: dest.symlink_to(src/'Verse'/'Garage.verse')
    except (OSError,NotImplementedError):pytest.skip('Symlink unavailable')
    with pytest.raises(ValueError,match='Symlink'):package(src,tmp_path/'p.zip')

def test_zip_fails_when_output_inside_staging(tmp_path):
    src=_stage(tmp_path)
    with pytest.raises(ValueError,match='outside'):package(src,src/'out.zip')

def test_zip_fails_if_source_oversize(tmp_path):
    src=_stage(tmp_path)
    with (src/'Verse'/'Garage.verse').open('ab') as f:
        f.truncate(8*1024*1024+1)
    with pytest.raises(ValueError,match='too large'):package(src,tmp_path/'p.zip')

def test_cli_package_does_not_overwrite_archive_with_json(tmp_path):
    src=_stage(tmp_path);out=tmp_path/'real.zip'
    p=subprocess.run([sys.executable,str(ROOT/'scripts/vf.py'),'package','--source',str(src),'--output',str(out)],capture_output=True,text=True,check=False)
    assert p.returncode==0,p.stderr+' '+p.stdout
    assert json.loads(p.stdout)['archive']==str(out)
    with ZipFile(out) as z:
        assert z.testzip() is None

def test_cli_chat_route_no_file_named_auto(tmp_path):
    p=subprocess.run([sys.executable,str(ROOT/'scripts/vf.py'),'chat-route','--request','Créer un garage'],cwd=tmp_path,capture_output=True,text=True)
    assert p.returncode==0,p.stderr+' '+p.stdout
    assert not (tmp_path/'auto').exists()
    assert json.loads(p.stdout)['selected_output']=='code'
