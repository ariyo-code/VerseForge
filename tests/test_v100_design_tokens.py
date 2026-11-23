from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.ui_engine import render_ui


def observation():
 return {'schema':'verseforge-visual-observations-v1', 'screens':[{'id':'home','elements':[]}], 'requested_behavior':'Basic original screen'}


def test_theme_tokens_roundtrip(tmp_path):
 tokens={'palette':{'background':'#010203','surface':'#121314','text':'#EEF0F2','primary':'#AABBCC'}}
 result=render_ui(observation(),tmp_path/'preview',design_tokens=tokens)
 assert result['result']=='PREVIEW AND HANDOFF CREATED'
 assert '--accent:#AABBCC' in (tmp_path/'preview/preview.html').read_text()
 assert json.loads((tmp_path/'preview/DESIGN_TOKENS.json').read_text())['palette']['background']=='#010203'
 assert json.loads((tmp_path/'preview/UMG_HANDOFF.json').read_text())['palette']['primary']=='#AABBCC'


@pytest.mark.parametrize('bad',[{'palette':{'background':'red'}}, {'palette':{'primary':'#123456;url(//x)'}},
                                   {'palette':{'injection':'#123456'}}, {'palette':None}, [], None])
def test_invalid_design_tokens_rejected(tmp_path,bad):
 if bad is None:return
 with pytest.raises(ValueError):render_ui(observation(),tmp_path/'bad',design_tokens=bad)
