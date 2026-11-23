from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.compose_engine import compose_project
from verseforge_core.chat_package import verify_package


def spec(with_api=False):
    entry={'id':'bank','kind':'economy','state_scope':'player-persistent','owns':['wallet'],'requirements':['No double spending']}
    if with_api: entry['api_claims']=['GetFortCharacter']
    return {'schema':'verseforge-engineering-spec-v1','project':'city_rp',
            'description':'Modular city modules', 'modules':[entry]}


def prep(tmp_path, code=None):
    source=tmp_path/'src';(source/'Verse').mkdir(parents=True)
    default=('using { /Fortnite.com/Devices }\nusing { /Verse.org/Simulation }\nusing { /UnrealEngine.com/Temporary/Diagnostics }\n'
             'bank_device := class(creative_device):\n    OnBegin<override>()<suspends>:void =\n        Print("Bank ready")\n')
    (source/'Verse/bank_device.verse').write_text(code or default)
    return source


def test_composer_end_to_end_agent_code_zip(tmp_path):
    source=prep(tmp_path)
    output=tmp_path/'out.zip'
    result=compose_project(spec(),source,output,uefn_version='43.10')
    assert result['result']=='PASS'
    assert result['integrity']=='PASS'
    assert output.is_file()
    assert verify_package(output)['result']=='PASS'
    assert result['uefn_compile']=='NOT TESTED'


def test_composer_missing_module(tmp_path):
    source=prep(tmp_path)
    (source/'Verse/bank_device.verse').unlink()
    result=compose_project(spec(),source,tmp_path/'out.zip',uefn_version='43.10')
    assert result['result']=='BLOCKED' and result['missing']


def test_composer_blocks_placeholder(tmp_path):
    source=prep(tmp_path)
    file=source/'Verse/bank_device.verse'
    file.write_text('# VerseForge engineering scaffold; NOT a functional game system.\n'+file.read_text())
    result=compose_project(spec(),source,tmp_path/'out.zip',uefn_version='43.10')
    assert result['result']=='BLOCKED'
    assert not (tmp_path/'out.zip').exists()


def test_composer_blocks_unverified_api_marker(tmp_path):
    source=prep(tmp_path)
    file=source/'Verse/bank_device.verse'
    file.write_text(file.read_text()+'\n# TODO(API VERIFY)\n')
    result=compose_project(spec(),source,tmp_path/'out.zip',uefn_version='43.10')
    assert result['result']=='BLOCKED'


def test_composer_blocks_no_api_evidence(tmp_path):
    source=prep(tmp_path)
    result=compose_project(spec(True),source,tmp_path/'out.zip',uefn_version='43.10')
    assert result['result']=='BLOCKED'


def test_composer_api_declaration_never_called_verified(tmp_path):
    source=prep(tmp_path)
    ev={'schema':'verseforge-api-evidence-v1', 'claims':[{'symbol':'GetFortCharacter','uefn_version':'43.10',
        'source_url':'https://dev.epicgames.com/documentation/fortnite/example',
        'fields':{'signature':'GetFortCharacter[]', 'parameters':'none','effects':'decides'}}]}
    result=compose_project(spec(True),source,tmp_path/'out.zip',uefn_version='43.10',api_evidence=ev)
    assert result['result']=='PASS' and 'SELF-DECLARED' in result['api']
    assert result['uefn_compile']=='NOT TESTED'


def test_composer_api_wrong_version_rejected(tmp_path):
    source=prep(tmp_path)
    ev={'schema':'verseforge-api-evidence-v1', 'claims':[{'symbol':'GetFortCharacter','uefn_version':'42.20',
        'source_url':'https://dev.epicgames.com/documentation/fortnite/example',
        'fields':{'signature':'x', 'parameters':'none','effects':'none'}}]}
    with pytest.raises(ValueError):compose_project(spec(True),source,tmp_path/'out.zip',uefn_version='43.10',api_evidence=ev)


def test_composer_rejects_source_symlinks(tmp_path):
    source=prep(tmp_path)
    (source/'README.md').symlink_to(source/'Verse/bank_device.verse')
    with pytest.raises(ValueError):compose_project(spec(),source,tmp_path/'out.zip',uefn_version='43.10')


def test_composer_rejects_extra_private_file(tmp_path):
    source=prep(tmp_path)
    (source/'.env').write_text('SECRET=foo')
    with pytest.raises(ValueError):compose_project(spec(),source,tmp_path/'out.zip',uefn_version='43.10')


def test_composer_prevents_output_inside_source(tmp_path):
    source=prep(tmp_path)
    with pytest.raises(ValueError):compose_project(spec(),source,source/'result.zip',uefn_version='43.10')
