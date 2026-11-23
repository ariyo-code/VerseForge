"""Machine-checkable asset traceability for ZIP exports.

A manifest describes ownership/licensing claims; it does not independently
establish legal rights. Production use still needs actual per-asset review.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Callable

SCHEMA = 'verseforge-asset-manifest-v1'
LICENSES = {'OWNER-CREATED', 'MIT', 'ISC', 'CC0-1.0', 'CC-BY-4.0', 'CC-BY-SA-4.0', 'LICENSED'}
ATTRIBUTION = {'MIT', 'ISC', 'CC-BY-4.0', 'CC-BY-SA-4.0'}
EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.ogg', '.wav'}


def is_resource(path: str) -> bool:
    pure = PurePosixPath(path)
    return len(pure.parts) >= 2 and pure.parts[0] in {'UI', 'Assets'} and pure.suffix.lower() in EXTENSIONS


def check_asset_manifest(data: bytes | None, files: dict[str, bytes]) -> dict:
    resources = {p for p in files if is_resource(p)}
    if not resources:
        if data is not None:
            raise ValueError('No UI/Assets resources to declare')
        return {'result': 'PASS', 'declared': 0, 'legal_review': 'NOT PERFORMED'}
    if data is None or len(data) > 128 * 1024:
        raise ValueError('A bounded ASSET_MANIFEST.json is required for UI/Assets resources')
    try:
        manifest = json.loads(data)
    except (UnicodeError, ValueError) as exc:
        raise ValueError('Invalid asset manifest JSON') from exc
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA or not isinstance(manifest.get('assets'), list):
        raise ValueError('Invalid asset manifest schema')
    if len(manifest['assets']) != len(resources) or len(resources) > 150:
        raise ValueError('Asset manifest item count mismatch')
    seen = set()
    for rec in manifest['assets']:
        if not isinstance(rec, dict):
            raise ValueError('Bad asset record')
        path = rec.get('path')
        if not isinstance(path, str) or path not in resources or path in seen:
            raise ValueError('Unknown or duplicate asset path')
        seen.add(path)
        if rec.get('license') not in LICENSES:
            raise ValueError('Unknown asset license; manual review required')
        if rec.get('sha256') != hashlib.sha256(files[path]).hexdigest():
            raise ValueError('Asset hash mismatch')
        if rec['license'] == 'OWNER-CREATED':
            if rec.get('origin') != 'original' or not isinstance(rec.get('creator'), str) or not rec['creator'].strip():
                raise ValueError('Original asset needs a declared creator')
        else:
            if rec.get('origin') != 'third-party':
                raise ValueError('Third-party licensing requires declared origin')
            if not isinstance(rec.get('source_url'), str) or not rec['source_url'].startswith('https://'):
                raise ValueError('Third-party asset needs an HTTPS source URL')
            if not isinstance(rec.get('license_url'), str) or not rec['license_url'].startswith('https://'):
                raise ValueError('Third-party asset needs a license evidence URL')
        if rec['license'] in ATTRIBUTION and not (isinstance(rec.get('attribution'), str) and rec['attribution'].strip()):
            raise ValueError('Attribution text required for this asset license')
    if seen != resources:
        raise ValueError('Assets missing from manifest')
    return {'result': 'PASS', 'declared': len(seen), 'legal_review': 'NOT PERFORMED',
            'note': 'Provenance and claimed license fields are consistent; actual rights must be verified separately.'}
