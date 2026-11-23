"""CLI workflow tests. These do not activate ChatGPT Skills or UEFN."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
CLI=ROOT/'scripts'/'vf.py'


def run_cli(*args):
    done=subprocess.run([sys.executable,str(CLI),*map(str,args)],capture_output=True,text=True,timeout=30)
    assert done.returncode==0,done.stdout+'\n'+done.stderr
    return json.loads(done.stdout)


def stage(tmp_path):
    src=tmp_path/'stage';(src/'Verse').mkdir(parents=True)
    (src/'Verse'/'Demo.verse').write_text('demo := class(creative_device):\n')
    return src


def test_cli_quality(tmp_path):
    src=stage(tmp_path)
    result=run_cli('quality-review','--source',src)
    assert result['schema']=='verseforge-static-evidence-v1'
    assert result['uefn_compilation']=='NOT TESTED'


def test_cli_deliver_verified(tmp_path):
    src=stage(tmp_path);output=tmp_path/'out.zip'
    result=run_cli('deliver','--source',src,'--output',output)
    assert result['zip_integrity']=='PASS'
    assert run_cli('package-verify','--file',output)['result']=='PASS'


def test_cli_visual_plan_example():
    r=run_cli('visual-plan','--spec',ROOT/'examples'/'visual-observations.example.json')
    assert r['verse_source']=='NOT GENERATED'
    assert len(r['screens'])==1


def test_cli_validate_with_release_candidate():
    r=run_cli('validate')
    assert r['result']=='PASS'


def test_cli_visual_plan_output_file(tmp_path):
    output=tmp_path/'result.json'
    result=run_cli('visual-plan','--spec',ROOT/'examples'/'visual-observations.example.json','--output',output)
    assert json.loads(output.read_text())==result
