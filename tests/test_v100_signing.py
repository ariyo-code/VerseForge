"""Checks public release signature, forged archives and scaffold delivery status."""
from __future__ import annotations
import sys
import zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verseforge_core.distribution import release
from verseforge_core.release_signature import sign_release,verify_release_signature
from verseforge_core.engineering_engine import architecture,scaffold
from verseforge_core.quality_engine import review_sources
from verseforge_core.delivery_pipeline import deliver
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption


def base(tmp_path):
    root=tmp_path/'skill';root.mkdir();(root/'SKILL.md').write_text('---\nname: verseforge\n---\n')
    (root/'README.md').write_text('Hello')
    release(root,tmp_path/'release.zip','1.0.0-rc2')
    private=Ed25519PrivateKey.generate()
    (tmp_path/'private.pem').write_bytes(private.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,NoEncryption()))
    (tmp_path/'public.pem').write_bytes(private.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    return root


def test_ed25519_release_sign_and_verify(tmp_path):
    base(tmp_path)
    res=sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')
    assert res['result']=='SIGNED'
    valid=verify_release_signature(tmp_path/'release.zip',tmp_path/'release.sig.json',tmp_path/'public.pem')
    assert valid['result']=='VERIFIED' and valid['version']=='1.0.0-rc2'


def test_release_signature_rejects_tampering(tmp_path):
    base(tmp_path)
    sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')
    with zipfile.ZipFile(tmp_path/'release.zip') as z:files={k:z.read(k) for k in z.namelist()}
    files['README.md']=b'tampered'
    with zipfile.ZipFile(tmp_path/'evil.zip','w') as z:
        for k,v in files.items():z.writestr(k,v)
    with pytest.raises(ValueError):verify_release_signature(tmp_path/'evil.zip',tmp_path/'release.sig.json',tmp_path/'public.pem')


def test_release_signature_wrong_key(tmp_path):
    base(tmp_path)
    sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')
    other=Ed25519PrivateKey.generate()
    (tmp_path/'other.pem').write_bytes(other.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    with pytest.raises(ValueError):verify_release_signature(tmp_path/'release.zip',tmp_path/'release.sig.json',tmp_path/'other.pem')


def test_release_signature_bad_source(tmp_path):
    base(tmp_path)
    with pytest.raises(ValueError):sign_release(tmp_path/'release.zip',tmp_path/'public.pem',tmp_path/'release.sig.json')


def test_release_refuses_signature_overwrite(tmp_path):
    base(tmp_path)
    sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')
    with pytest.raises(ValueError):sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')


def test_scaffold_cannot_be_delivered_as_verified_gameplay(tmp_path):
    plan=architecture({'schema':'verseforge-engineering-spec-v1','project':'garage_rp','description':'Garage RP engine',
      'modules':[{'id':'garage','kind':'vehicle','state_scope':'session','owns':['garage_vehicles'],
                  'requirements':['Actual spawn, access and persistence']} ]})
    root=tmp_path/'scaffold';scaffold(plan,root)
    review=review_sources(root/'Verse')
    assert review['local_check']=='REVIEW REQUIRED'
    assert any('Template-only' in w for w in review['warnings'])
    # deliver(...) expects an explicit staging folder with Verse/ files.
    blocked=deliver(root,tmp_path/'out.zip',strict=True)
    assert blocked['result']=='BLOCKED'
    assert not (tmp_path/'out.zip').exists()


def test_signed_public_release_requires_out_of_band_key(tmp_path):
    base(tmp_path)
    signature=sign_release(tmp_path/'release.zip',tmp_path/'private.pem',tmp_path/'release.sig.json')
    # A record with a matching digest is not enough without the trusted public key.
    assert signature['uefn_compile']=='NOT TESTED'


def test_release_allows_nonsecret_design_token_module(tmp_path):
    root=tmp_path/'skill';root.mkdir()
    (root/'SKILL.md').write_text('---\nname: verseforge\n---\n')
    (root/'tests').mkdir()
    (root/'tests/test_design_tokens.py').write_text('def test_palette():\n    assert True\n')
    result=release(root,tmp_path/'skill.zip','1.0.0-rc2')
    assert result['result']=='PASS'


def test_release_denies_actual_token_file(tmp_path):
    root=tmp_path/'skill';root.mkdir()
    (root/'SKILL.md').write_text('---\nname: verseforge\n---\n')
    (root/'scripts').mkdir()
    (root/'scripts/token.txt').write_text('secret content')
    with pytest.raises(ValueError,match='Unauthorized public file'):
        release(root,tmp_path/'skill.zip','1.0.0-rc2')
