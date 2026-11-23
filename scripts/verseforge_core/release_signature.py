"""Detached Ed25519 public-skill archive signatures (publisher authenticity).

Trust in the publisher's public key must be established *out of band*.
This signature proves archive bytes, not code quality, UEFN compilation or
customer entitlement. Private key never enters the release artifact.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .distribution import verify_release

DOMAIN = b"VERSEFORGE-PUBLIC-RELEASE-V1\0"
SCHEMA = "verseforge-release-signature-v1"


def _canonical(payload: dict[str,Any]) -> bytes:
    return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def sign_release(archive: Path, key_path: Path, output: Path) -> dict[str,Any]:
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError as exc:
        raise ValueError('Optional cryptography dependency is required for release signing') from exc
    archive=Path(archive)
    key_path=Path(key_path)
    output=Path(output)
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise ValueError('Signature output must not exist')
    if key_path.is_symlink() or not key_path.is_file():
        raise ValueError('Expected a local non-symlinked private signing key')
    result=verify_release(archive)
    key=load_pem_private_key(key_path.read_bytes(),password=None)
    if not isinstance(key,Ed25519PrivateKey):
        raise ValueError('Ed25519 private key required')
    pub = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    pubid = hashlib.sha256(pub).hexdigest()[:24]
    payload={"schema":SCHEMA,"algorithm":"Ed25519-SHA256","version":result['version'],
             "release_sha256":result['sha256'],"publisher_key_id":pubid}
    signed={"payload":payload,"signature":base64.b64encode(key.sign(DOMAIN+_canonical(payload))).decode('ascii')}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:
        json.dump(signed,f,indent=2,ensure_ascii=False)
        f.write('\n')
    return {"result":"SIGNED","file":str(output),"version":result['version'],"publisher_key_id":pubid,
            "uefn_compile":"NOT TESTED"}


def verify_release_signature(archive: Path, signature_file: Path, public_key: Path) -> dict[str,Any]:
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key, Encoding, PublicFormat
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError as exc:
        raise ValueError('Optional cryptography dependency is required for release signature verification') from exc
    for p in (signature_file,public_key):
        p=Path(p)
        if not p.is_file() or p.is_symlink() or p.stat().st_size>80_000:
            raise ValueError('Signature and public key must be regular bounded files')
    result=verify_release(archive)
    record=json.loads(Path(signature_file).read_text(encoding='utf-8'))
    if not isinstance(record,dict) or set(record)!={'payload','signature'}:
        raise ValueError('Malformed release signature')
    payload=record['payload']
    if (not isinstance(payload,dict) or set(payload)!={'schema','algorithm','version','release_sha256','publisher_key_id'}
         or payload['schema']!=SCHEMA or payload['algorithm']!='Ed25519-SHA256'
         or payload['version']!=result['version'] or payload['release_sha256']!=result['sha256']):
        raise ValueError('Release signature payload does not match the artifact')
    key=load_pem_public_key(Path(public_key).read_bytes())
    if not isinstance(key,Ed25519PublicKey):
        raise ValueError('Ed25519 public key required')
    fingerprint=hashlib.sha256(key.public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)).hexdigest()[:24]
    if payload['publisher_key_id']!=fingerprint:
        raise ValueError('Unexpected publisher key fingerprint')
    try:
        key.verify(base64.b64decode(record['signature'],validate=True),DOMAIN+_canonical(payload))
    except (ValueError, InvalidSignature) as exc:
        raise ValueError('Invalid publisher release signature') from exc
    return {"result":"VERIFIED","version":result['version'],"release_sha256":result['sha256'],
            "publisher_key_id":fingerprint,"notice":"Trusted public key must be established out of band; UEFN compile NOT TESTED"}
