"""LOT 05 local contract tests. None establish true chatbot or UEFN connectivity."""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verseforge_core.chat_mode import classify, guide, menu, resolve_choice, route
from verseforge_core.chat_package import package, verify_package


@pytest.mark.parametrize('invocation', ['', 'verseforge', '/verseforge', '$verseforge', '@verseforge', '  /VerseForge  '])
def test_invocation_shows_menu(invocation):
    assert classify(invocation)['show_menu'] is True


def test_menu_7_distinct_simple_choices():
    result = menu()
    assert result['view'] == 'control-center'
    assert len(result['choices']) == 7
    assert len({c['id'] for c in result['choices']}) == 7
    assert 'Choisis un numéro' in result['display']
    assert result['interactive_native_panel'] == 'NOT GUARANTEED'


@pytest.mark.parametrize('choice,expected', [('1', 'create'), (2, 'fix'), ('3', 'ui'),
                                                ('4', 'optimize'), ('5', 'audit'), ('6', 'api'),
                                                ('7', 'settings'), ('Choix 1', 'create'),
                                                ('Créer une interface', 'ui'), ('DEBUG', 'fix')])
def test_choice_mapping(choice, expected):
    assert resolve_choice(choice) == expected


@pytest.mark.parametrize('choice', ['0', '8', 'foo', '1 ou 2', True, None])
def test_invalid_choice_is_not_guessed(choice):
    with pytest.raises(ValueError):
        resolve_choice(choice)


@pytest.mark.parametrize('choice', range(1, 8))
def test_menu_selection_one_question(choice):
    state = guide(choice)
    assert state['view'] == 'question'
    assert state['needs_user_input'] is True
    assert state['question'].endswith('?')
    assert state['mode']


def test_guide_without_choice_shows_menu():
    assert guide()['view'] == 'control-center'


def test_guide_not_a_code_generator():
    result = guide(1, 'Garage RP avec véhicules persistants, ZIP', can_create_files=True)
    assert result['view'] == 'ready'
    assert result['intent'] == 'create'
    assert result['selected_output'] == 'zip'
    assert result['not_a_code_generator'] is True
    assert result['uefn_compile'] == 'NOT TESTED'
    assert result['workflow'] == 'workflows/build.md'


def test_correct_ui_mode_selected_even_if_noun_looks_like_system():
    result = guide('3', 'Interface HUD du garage')
    assert result['mode'] == 'UI'
    assert result['user_task'] == 'Interface HUD du garage'


def test_no_loop_back_to_menu_after_details():
    assert guide(1, 'Système de notification Verse')['view'] == 'ready'


def test_guide_fix_requests_evidence_when_not_provided():
    result = guide(2, 'Mon code marche pas')
    assert result['view'] == 'question'
    assert result['needs_user_input'] is True
    assert 'erreur' in result['question']


def test_fix_with_error_context_routes_debug():
    result = guide(2, 'Erreur 3509\nusing { /Verse.org/Simulation }')
    assert result['view'] == 'ready'
    assert result['mode'] == 'DEBUG'


def test_direct_task_bypasses_menu():
    assert classify('$verseforge Crée un garage RP avec interface')['mode'] == 'BUILD'
    assert classify('Crée une interface HUD pour garage')['mode'] == 'UI'
    assert classify('Corrige une erreur dans mon interface')['mode'] == 'DEBUG'
    assert classify('Optimise mon Verse')['mode'] == 'OPTIMIZE'
    assert classify('@verseforge')['show_menu']


def test_explicit_code_preference_wins_zip_tools():
    assert route('Donne juste le code du garage', can_create_files=True)['selected_output'] == 'code'


def test_zip_fallback_without_file_tools():
    result = guide(1, 'Garage Verse en ZIP', can_create_files=False)
    assert result['selected_output'] == 'code'
    assert result['caveats']


def test_project_fallback_without_project_write():
    result = guide(1, 'Garage dans mon projet', can_create_files=True, can_edit_project=False)
    assert result['selected_output'] == 'zip'
    assert result['uefn_compile'] == 'NOT TESTED'


def test_no_claim_of_uefn_compilation_with_connected_flag():
    result = guide(1, 'Garage dans mon projet', can_edit_project=True, uefn_connected=True)
    assert result['selected_output'] == 'project'
    assert result['uefn_compile'] == 'NOT TESTED'


def test_guide_large_user_data_rejected():
    with pytest.raises(ValueError, match='too large'):
        guide(1, 'x' * 32_001)


def _source_stage(tmp_path):
    staging = tmp_path / 'staging'
    (staging / 'Verse').mkdir(parents=True)
    (staging / 'Verse' / 'Feature.verse').write_text('# Verse source\n', encoding='utf-8')
    return staging


def _rewrite_zip(original: Path, destination: Path, replacements: dict[str, bytes] | None = None,
                 extra: dict[str, bytes] | None = None, drop: set[str] | None = None):
    replacements = replacements or {}
    extra = extra or {}
    drop = drop or set()
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(destination, 'w') as out:
        for item in src.infolist():
            if item.filename not in drop:
                out.writestr(item.filename, replacements.get(item.filename, src.read(item.filename)))
        for path, payload in extra.items():
            out.writestr(path, payload)


def test_package_verify_real_archive(tmp_path):
    stage = _source_stage(tmp_path)
    z = tmp_path / 'valid.zip'
    package(stage, z)
    result = verify_package(z)
    assert result['result'] == 'PASS'
    assert result['verified_files'] >= 2
    assert result['signature'] == 'NOT PRESENT'
    assert result['uefn_compile'] == 'NOT TESTED'


def test_tampered_verse_content_detected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, {'Verse/Feature.verse': b'# tampered source\n'})
    result = verify_package(bad)
    assert result['result'] == 'FAIL'
    assert any('Hash mismatch' in msg for msg in result['issues'])


def test_added_untracked_file_detected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, extra={'Verse/Hidden.verse': b'# injected\n'})
    assert verify_package(bad)['result'] == 'FAIL'


def test_zip_slip_entry_is_rejected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, extra={'../escape.verse': b'# BAD\n'})
    with pytest.raises(ValueError, match='Unsafe'):
        verify_package(bad)


def test_duplicate_entry_rejected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, extra={'Verse/Feature.verse': b'# duplicated\n'})
    with pytest.raises(ValueError, match='Duplicate'):
        verify_package(bad)


def test_case_collision_rejected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, extra={'Verse/feature.verse': b'# duplicate case\n'})
    with pytest.raises(ValueError, match='case-colliding'):
        verify_package(bad)


def test_missing_manifest_rejected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    _rewrite_zip(good, bad, drop={'VERSEFORGE_MANIFEST.json'})
    with pytest.raises(ValueError, match='Missing'):
        verify_package(bad)


def test_fake_compilation_claim_detected(tmp_path):
    stage = _source_stage(tmp_path)
    good = tmp_path / 'good.zip'; bad = tmp_path / 'bad.zip'
    package(stage, good)
    with zipfile.ZipFile(good) as z:
        manifest = json.loads(z.read('VERSEFORGE_MANIFEST.json'))
    manifest['validation']['uefn_compile'] = 'PASS'
    _rewrite_zip(good, bad, {'VERSEFORGE_MANIFEST.json': json.dumps(manifest).encode('utf-8')})
    assert verify_package(bad)['result'] == 'FAIL'


def test_dangling_destination_symlink_rejected(tmp_path):
    stage = _source_stage(tmp_path)
    target = tmp_path / 'secret.zip'
    alias = tmp_path / 'link.zip'
    try:
        alias.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip('Symlinks not supported by the host')
    with pytest.raises(ValueError, match='overwrite'):
        package(stage, alias)
    assert not target.exists()


def test_control_center_end_to_end_local_cli_to_real_zip(tmp_path):
    """Exercise local menu->choice->existing Verse source->archive, NOT host LLM activation."""
    cli = ROOT / 'scripts/vf.py'
    def invoke(*args):
        p = subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, timeout=15)
        assert p.returncode == 0, p.stdout + p.stderr
        return json.loads(p.stdout)
    first = invoke('menu')
    assert len(first['choices']) == 7
    second = invoke('guide', '--choice', '1')
    assert second['view'] == 'question'
    third = invoke('guide', '--choice', '1', '--details',
                   'Créer bouton déclenchant une notification HUD, en ZIP', '--can-create-files')
    assert third['selected_output'] == 'zip'
    assert third['mode'] == 'BUILD'
    stage = tmp_path / 'staging'
    (stage / 'Verse').mkdir(parents=True)
    # Previously authored benchmark A is the code input; the CLI does NOT generate this file.
    source = ROOT / 'examples/benchmarks/A-interactive-device/vf_interactive_notice_device.verse'
    assert source.exists()
    (stage / 'Verse' / source.name).write_bytes(source.read_bytes())
    archive = tmp_path / 'demo.zip'
    fourth = invoke('package', '--source', str(stage), '--output', str(archive))
    assert fourth['result'] == 'PASS'
    fifth = invoke('package-verify', '--file', str(archive))
    assert fifth['result'] == 'PASS'
    assert fifth['uefn_compile'] == 'NOT TESTED'
    with zipfile.ZipFile(archive) as z:
        assert z.read('Verse/' + source.name) == source.read_bytes()
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == fifth['sha256']


def test_information_options_are_not_verse_source_requests():
    assert guide(6, 'Aide sur les API Verse')['selected_output'] == 'chat'
    assert guide(7, 'Vérifier ma licence')['selected_output'] == 'chat'
    assert guide(5, 'Analyser mon projet en lecture seule')['selected_output'] == 'chat'


def test_simple_help_direct_route():
    r = route('Aide Verse et UEFN')
    assert r['mode'] == 'API_VERIFY'
    assert r['selected_output'] == 'chat'
