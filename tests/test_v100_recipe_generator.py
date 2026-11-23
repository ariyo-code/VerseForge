"""Tests deterministic offline Verse recipe generation; not actual UEFN tests."""
from pathlib import Path
import json
import sys
import subprocess
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.recipe_generator import generate_button_hud
from verseforge_core.delivery_pipeline import deliver


def spec():
    return {'schema':'verseforge-button-hud-v1','device_name':'city_rp_notice',
            'message':'Bienvenue en ville', 'duration_seconds':3.0}


def test_generates_verse_and_wiring_guide(tmp_path):
    out=tmp_path/'generated'
    info=generate_button_hud(spec(),out)
    assert info['result']=='GENERATED'
    source=(out/'Verse/city_rp_notice_device.verse').read_text()
    assert 'Trigger.InteractedWithEvent.Subscribe' in source
    assert 'Notice.Show(Who, Message, 3.00)' in source
    assert 'OnEnd<override>' in source
    assert 'Compilation: NOT TESTED' in (out/'README.md').read_text()


def test_generation_deterministic(tmp_path):
    a=tmp_path/'a';b=tmp_path/'b'
    x=generate_button_hud(spec(),a)
    y=generate_button_hud(spec(),b)
    assert x['source_sha256']==y['source_sha256']


def test_generation_into_existing_dir_refused(tmp_path):
    out=tmp_path/'exists';out.mkdir()
    with pytest.raises(ValueError):generate_button_hud(spec(),out)


@pytest.mark.parametrize('change',[
    lambda s:s.update(device_name='../leak'),
    lambda s:s.update(message='A"\nOnBegin:...'),
    lambda s:s.update(message='Wrong {Agent}'),
    lambda s:s.update(message=''),
    lambda s:s.update(duration_seconds=-1),
    lambda s:s.update(duration_seconds=True),
    lambda s:s.update(schema='unknown'),
])
def test_generator_rejects_injection_or_bad_inputs(tmp_path,change):
    s=spec();change(s)
    with pytest.raises(ValueError):generate_button_hud(s,tmp_path/'out')


def test_generated_device_can_be_packaged(tmp_path):
    out=tmp_path/'generated'
    generate_button_hud(spec(),out)
    result=deliver(out,tmp_path/'package.zip')
    assert result['result']=='PASS'
    assert result['uefn_compile']=='NOT TESTED'


def test_cli_recipe(tmp_path):
    sp=tmp_path/'spec.json';sp.write_text(json.dumps(spec()))
    script=Path(__file__).resolve().parents[1]/'scripts/vf.py'
    cp=subprocess.run([sys.executable,str(script),'recipe-button-hud','--spec',str(sp),'--output',str(tmp_path/'out')],capture_output=True,text=True,timeout=10)
    assert cp.returncode==0,cp.stderr
    assert (tmp_path/'out/Verse/city_rp_notice_device.verse').is_file()
