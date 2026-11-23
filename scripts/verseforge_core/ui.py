"""Deterministic UI specification generator, not an editor importer."""
from __future__ import annotations
import json
from pathlib import Path


def ui_plan(skill_root:Path,style_name:str,screen_name:str='garage')->dict:
    styles=json.loads((skill_root/'assets/design-styles.json').read_text())
    exact=[x for x in styles if x['name'].lower()==style_name.strip().lower() or x['id']==style_name.strip().lower()]
    if len(exact)!=1:raise ValueError('Unknown UI style; choose a name from assets/design-styles.json')
    if not screen_name.replace('-','').isalnum():raise ValueError('Unsupported screen template')
    path=skill_root/'templates/ui-screens'/f'{screen_name}.json'
    if not path.is_file():raise ValueError('Unsupported screen template')
    screen=json.loads(path.read_text())
    screen['style']=exact[0]['name']
    screen['art_direction']=exact[0]['guidance']
    dna=json.loads((skill_root/'assets/design-dna.example.json').read_text())
    return {'kind':'ui-implementation-spec','design_dna':dna,'screen':screen,'next_steps':['Verify UMG/Verse UI field API claims in installed editor','Check licenses for specific selected graphics','Import widget/assets with discovered editor tooling','Run gamepad/touch/session interaction tests'],'editor_import':'NOT TESTED','verse_compile':'NOT TESTED'}
