from __future__ import annotations
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.knowledge_sync import knowledge_audit,make_lock


def _repo(tmp_path, version='43.10'):
    p=tmp_path/'repo';p.mkdir()
    (p/'AI_BOOTSTRAP.md').write_text('Never invent API signatures.')
    (p/'VERSION.md').write_text(f'API snapshot: {version}')
    return p


def test_knowledge_audit_declared_snapshot(tmp_path):
    p=_repo(tmp_path)
    out=knowledge_audit(p,'43.10')
    assert out['status']=='SNAPSHOT_MATCH_DECLARATION_ONLY'
    assert out['api_verified']=='NOT VERIFIED'


def test_knowledge_audit_version_drift(tmp_path):
    p=_repo(tmp_path,'42.20')
    out=knowledge_audit(p,'43.10')
    assert out['status']=='API_SNAPSHOT_MISMATCH'


def test_knowledge_lock(tmp_path):
    p=_repo(tmp_path)
    state=knowledge_audit(p,'43.10')
    report=make_lock(state,tmp_path/'lock.json')
    assert report['result']=='LOCK WRITTEN'
    lock=json.loads((tmp_path/'lock.json').read_text())
    assert lock['target_uefn']=='43.10'
    with pytest.raises(ValueError):make_lock(state,tmp_path/'lock.json')


@pytest.mark.parametrize('bad',['alpha','43.x','', '../secret'])
def test_knowledge_rejects_bad_target(tmp_path,bad):
    p=_repo(tmp_path)
    with pytest.raises(ValueError):knowledge_audit(p,bad)


def test_knowledge_wrong_commit(tmp_path):
    p=_repo(tmp_path)
    state=knowledge_audit(p,'43.10',expected_commit='a'*40)
    assert state['status']=='COMMIT_MISMATCH'


def test_knowledge_rejects_invalid_root(tmp_path):
    with pytest.raises(ValueError):knowledge_audit(tmp_path,'43.10')
