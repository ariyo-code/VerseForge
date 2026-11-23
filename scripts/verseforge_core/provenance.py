"""Independent verification of VerseForge v1 Ed25519 detached manifests.

No private key is loaded, created or shipped by this public module.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

MARKER_RE=re.compile(rb'\A# verseforge-provenance:v1;artifact=([a-zA-Z0-9-]{8,80})\n')
FIELDS={'schema','algorithm','artifact_id','artifact_path','sha256','issued_at','license_id','signer_key_id'}


def canonical(data: bytes) -> bytes:
    """Normalize only CRLF and CR to LF; preserve all other bytes exactly."""
    return data.replace(b'\r\n',b'\n').replace(b'\r',b'\n')


def sha256(data: bytes) -> str:
    return hashlib.sha256(canonical(data)).hexdigest()


def signing_bytes(payload: dict[str, Any]) -> bytes:
    if set(payload)!=FIELDS:
        raise ValueError('Invalid provenance payload fields')
    return json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def verify(code_file: Path, manifest_file: Path, public_key_file: Path, project_root: Path | None=None) -> dict:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.serialization import load_pem_public_key,Encoding,PublicFormat
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    code_file=code_file.resolve(strict=True)
    manifest=json.loads(manifest_file.read_text(encoding='utf-8'))
    if set(manifest)!={'payload','signature'}:
        raise ValueError('Provenance requires payload and detached signature only')
    payload=manifest['payload']
    if payload['schema']!='verseforge-provenance-v1' or payload['algorithm']!='Ed25519-SHA256':
        raise ValueError('Unsupported provenance format')
    data=canonical(code_file.read_bytes())
    m=MARKER_RE.match(data)
    if not m or m.group(1).decode('ascii')!=payload['artifact_id']:
        raise ValueError('Missing or mismatched visible Verse comment marker')
    root=project_root.resolve(strict=True) if project_root else code_file.parent
    try:
        rel=code_file.relative_to(root).as_posix()
    except ValueError as e:
        raise ValueError('Code file outside project root') from e
    if payload['artifact_path']!=rel:
        raise ValueError('Artifact path mismatch (copied/renamed marker?)')
    if not re.fullmatch(r'[0-9a-f]{64}',payload['sha256']) or payload['sha256']!=hashlib.sha256(data).hexdigest():
        raise ValueError('Code hash mismatch')
    pub=load_pem_public_key(public_key_file.read_bytes())
    if not isinstance(pub,Ed25519PublicKey):
        raise ValueError('Not an Ed25519 public key')
    key_id=hashlib.sha256(pub.public_bytes(Encoding.DER,PublicFormat.SubjectPublicKeyInfo)).hexdigest()[:16]
    if key_id!=payload['signer_key_id']:
        raise ValueError('Signer fingerprint mismatch')
    try:
        signature=base64.b64decode(manifest['signature'],validate=True)
        pub.verify(signature,b'VF-ARTIFACT-V1\0'+signing_bytes(payload))
    except (InvalidSignature,ValueError) as e:
        raise ValueError('Invalid manifest signature') from e
    return {'valid':True,'artifact_id':payload['artifact_id'],'code_sha256':payload['sha256'],
            'signer_key_id':payload['signer_key_id'],'issued_at':payload['issued_at'],
            'compile':'NOT TESTED','runtime':'NOT TESTED','multiplayer':'NOT TESTED'}
