"""Independent local-only tests. No UEFN compiler, visual semantics or host LLM."""
from __future__ import annotations
import json
import sys
import zipfile
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verseforge_core.quality_engine import review_sources,load_contract
from verseforge_core.visual_reverse import inspect_image,plan_from_observations,load_visual_spec
from verseforge_core.delivery_pipeline import deliver
from verseforge_core.chat_package import verify_package

@pytest.fixture
def stage(tmp_path):
    root=tmp_path/'stage'
    (root/'Verse').mkdir(parents=True)
    (root/'Verse'/'Button.verse').write_text('using { /Verse.org/Simulation }\nbutton_device_manager := class(creative_device):\n    OnBegin<override>()<suspends>:void =\n        Print("hello")\n',encoding='utf-8')
    return root

@pytest.fixture
def contract():
    return {'schema':'verseforge-acceptance-v1','requirements':[
        {'id':'feature source exists','validation':'static-evidence','contains':'button_device_manager'},
        {'id':'behavior checked in Fortnite','validation':'manual-uefn'},
        {'id':'two player isolation','validation':'multiplayer-uefn'},
    ]}


def test_quality_sources(stage,contract):
    r=review_sources(stage,contract)
    assert r['source_count']==1
    assert r['uefn_compilation']=='NOT TESTED'
    assert r['acceptance_checks'][0]['static_match']
    assert not r['acceptance_checks'][1]['static_match']
    assert r['local_check']=='PASS'


def test_quality_missing_static_check(stage,contract):
    contract['requirements'][0]['contains']='totally_not_in_sources'
    r=review_sources(stage,contract)
    assert r['local_check']=='REVIEW REQUIRED'
    assert r['acceptance_checks'][0]['status']=='MISSING TEXT'


def test_quality_reject_fake_compile_anchor(stage,contract):
    contract['requirements'][1]['contains']='OnBegin'
    with pytest.raises(ValueError,match='Behavioral'):review_sources(stage,contract)


def test_quality_reject_unverified_marker(stage):
    with (stage/'Verse'/'Button.verse').open('a') as f:f.write('\n# TODO(API VERIFY)\n')
    r=review_sources(stage)
    assert r['local_check']=='REVIEW REQUIRED'
    assert any('Unverified' in issue for issue in r['warnings'])


def test_quality_reject_zero_width(stage):
    with (stage/'Verse'/'Button.verse').open('a') as f:f.write('\n#\u200b hidden\n')
    assert any('Unicode' in x for x in review_sources(stage)['warnings'])


def test_quality_reject_file_symlink(stage,tmp_path):
    link=stage/'Verse'/'alias.verse'
    try: link.symlink_to(stage/'Verse'/'Button.verse')
    except (OSError,NotImplementedError):pytest.skip('No symlinks')
    with pytest.raises(ValueError,match='Symlink'):review_sources(stage)


def test_quality_reject_bad_declarations(stage):
    (stage/'Verse'/'Button.verse').write_text('not real source\n')
    assert review_sources(stage)['local_check']=='REVIEW REQUIRED'

@pytest.mark.parametrize('invalid',[{}, {'schema':'other','requirements':[{'id':'x','validation':'static-evidence'}]},
                                       {'schema':'verseforge-acceptance-v1','requirements':[]}])
def test_quality_bad_contract(stage,invalid):
    with pytest.raises(ValueError):review_sources(stage,invalid)


def test_delivery_end_to_end(stage,contract,tmp_path):
    output=tmp_path/'out.zip'
    result=deliver(stage,output,contract)
    assert result['result']=='PASS'
    assert result['zip_integrity']=='PASS'
    assert verify_package(output)['result']=='PASS'
    with zipfile.ZipFile(output) as z:
        assert 'Verse/Button.verse' in z.namelist()
        report=z.read('VALIDATION.md').decode()
        assert 'NOT TESTED' in report
        assert 'two player isolation' in report


def test_delivery_discards_user_fake_validation(stage,tmp_path):
    (stage/'VALIDATION.md').write_text('UEFN COMPILED PASSED\n')
    output=tmp_path/'zip.zip'
    deliver(stage,output)
    with zipfile.ZipFile(output) as z:
        assert 'UEFN COMPILED PASSED' not in z.read('VALIDATION.md').decode()


def test_delivery_strict_blocks_unknown(stage,tmp_path):
    (stage/'Verse'/'Button.verse').write_text('garbage')
    r=deliver(stage,tmp_path/'out.zip',strict=True)
    assert r['result']=='BLOCKED'
    assert not (tmp_path/'out.zip').exists()


def test_delivery_reject_private_input(stage,tmp_path):
    (stage/'secret.key').write_bytes(b'superprivate')
    with pytest.raises(ValueError,match='Unsupported'):deliver(stage,tmp_path/'out.zip')


def test_delivery_reject_output_within_source(stage):
    with pytest.raises(ValueError,match='outside'):deliver(stage,stage/'out.zip')


def test_delivery_reject_output_existing(stage,tmp_path):
    p=tmp_path/'out.zip';p.write_bytes(b'already')
    with pytest.raises(ValueError,match='overwrite'):deliver(stage,p)


def test_visual_image_details(tmp_path):
    from PIL import Image
    path=tmp_path/'test.png';Image.new('RGB',(180,80),(255,20,30)).save(path)
    result=inspect_image(path)
    assert result['dimensions']=={'width':180,'height':80}
    assert result['format']=='PNG'
    assert result['detected_widgets']=='NOT PERFORMED'
    assert result['image_sent_remotely'] is False


def test_visual_image_fake_content(tmp_path):
    path=tmp_path/'fake.png';path.write_bytes(b'not a png')
    with pytest.raises(ValueError,match='Invalid'):inspect_image(path)


def test_visual_image_symlink(tmp_path):
    from PIL import Image
    real=tmp_path/'real.png';Image.new('RGB',(10,10)).save(real)
    link=tmp_path/'alias.png'
    try:link.symlink_to(real)
    except (OSError,NotImplementedError):pytest.skip('No symlinks')
    with pytest.raises(ValueError,match='symlinks'):inspect_image(link)

@pytest.fixture
def visual_spec():
    return {'schema':'verseforge-visual-observations-v1','screens':[{ 'id':'home','elements':[
        {'id':'open_button','kind':'button','text':'Ouvrir','evidence':'observed','bounds':{'x':.1,'y':.1,'w':.5,'h':.15},'action':'navigate'},
        {'id':'balance','kind':'text','text':'100','evidence':'inferred','bounds':{'x':.2,'y':.4,'w':.3,'h':.1},'action':'display'}
    ]}], 'requested_behavior':'Open menu'}


def test_visual_plan(visual_spec):
    p=plan_from_observations(visual_spec)
    assert p['uefn_compile']=='NOT TESTED'
    assert p['verse_source']=='NOT GENERATED'
    assert p['interaction_checks'][0]['action']=='navigate'
    assert p['uncertainties']

@pytest.mark.parametrize('mutation',[
    lambda d:d['screens'].append(dict(d['screens'][0])),
    lambda d:d['screens'][0]['elements'][0]['bounds'].update(x=.9),
    lambda d:d['screens'][0]['elements'][0].update(evidence='certain'),
    lambda d:d['screens'][0]['elements'][0].update(action='execute_shell'),
    lambda d:d['screens'][0]['elements'][0].update(id='../escape'),
    lambda d:d['screens'][0]['elements'].append(dict(d['screens'][0]['elements'][0])),
    lambda d:d.update(schema='different'),
])
def test_visual_schema_rejections(visual_spec,mutation):
    mutation(visual_spec)
    with pytest.raises(ValueError):plan_from_observations(visual_spec)


def test_visual_spec_file_size(tmp_path):
    p=tmp_path/'large.json';p.write_bytes(b'a'*270_000)
    with pytest.raises(ValueError,match='too large'):load_visual_spec(p)
