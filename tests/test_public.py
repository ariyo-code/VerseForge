from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verseforge_core.validation import validate
from verseforge_core.project import inspect_project,build_plan
from verseforge_core.knowledge import run_knowledge
from verseforge_core.provenance import canonical,sha256,signing_bytes


def test_skill_structure():
    r=validate(ROOT)
    assert r['result']=='PASS',r
    assert r['recipe_count']>=15

def test_skill_route_and_scope():
    s=(ROOT/'SKILL.md').read_text()
    assert 'TODO(API VERIFY)' in s
    assert 'NOT TESTED' in s or 'draft' in s
    assert (ROOT/'workflows/debug.md').exists()

def test_plan_garage_and_ui():
    p=build_plan('Crée un garage RP persistant avec banque et UI multijoueur')
    assert {'garage','economy','persistence','ui','multiplayer'}.issubset(p['required_services'])
    assert p['compiler']=='NOT TESTED'
    assert len(p['risks'])>=3

def test_project_scan_no_execution(tmp_path):
    (tmp_path/'test.verse').write_text('DO NOT EXECUTE')
    (tmp_path/'island.uefnproject').write_text('{}')
    (tmp_path/'external.verse').symlink_to(tmp_path/'test.verse')
    result=inspect_project(tmp_path)
    assert result['verse_files']==['test.verse']
    assert result['uefn_projects']==['island.uefnproject']

def test_knowledge_command_restricts_write():
    with pytest.raises(ValueError):run_knowledge(['validate'])
    with pytest.raises(ValueError):run_knowledge(['--danger'])
    with pytest.raises(ValueError):run_knowledge(['search','@args'])

def test_knowledge_missing_cli_is_not_pass(monkeypatch):
    monkeypatch.setattr('verseforge_core.knowledge.shutil.which',lambda _:None)
    assert run_knowledge(['version'])['status']=='NOT TESTED'

def test_deterministic_canonical():
    assert canonical(b'A\r\nB\rC')==b'A\nB\nC'
    assert sha256(b'A\r\nB')==sha256(b'A\nB')

def test_signing_bytes_strict():
    with pytest.raises(ValueError):signing_bytes({'content':'fake'})

def test_assets_dont_claim_redistribution():
    for x in json.loads((ROOT/'assets/sources.json').read_text()):
        assert x['redistribution']!='permitted'
        assert x['review_status'] in ('source-identified-license-pending','catalog-license-verified-per-asset-check-still-required')

def test_recipe_statuses_are_drafts():
    assert all(x['validation']=='draft' for x in json.loads((ROOT/'templates/recipes.json').read_text()))

def test_eval_scenarios_are_not_faked():
    assert all(c['status']=='NOT TESTED' for c in json.loads((ROOT/'evals/scenarios.json').read_text())['cases'])


def test_ui_plan_is_explicitly_design_only():
    from verseforge_core.ui import ui_plan
    p=ui_plan(ROOT,'FiveM Premium')
    assert p['screen']['commands'][0]['id']=='garage.spawn'
    assert p['verse_compile']=='NOT TESTED'
    assert p['screen']['verification']['import']=='NOT TESTED'

def test_ui_unknown_style():
    from verseforge_core.ui import ui_plan
    with pytest.raises(ValueError):ui_plan(ROOT,"UI Doesn't Exist")


def test_rejects_mutating_knowledge_flags():
    with pytest.raises(ValueError):run_knowledge(['lint','--fix'])
    with pytest.raises(ValueError):run_knowledge(['search','test','--output=/tmp/file'])

def test_skill_frontmatter_is_valid_yaml():
    import yaml
    text=(ROOT/'SKILL.md').read_text()
    front=text.split('---',2)[1]
    data=yaml.safe_load(front)
    assert data['name']=='verseforge'
    assert len(data['description'])<=1024
