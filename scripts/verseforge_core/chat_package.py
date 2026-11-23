"""Minimal safe output packager for agent-authored Verse files."""
from __future__ import annotations
import hashlib
import json
import os
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath
from .asset_license import check_asset_manifest

# No arbitrary folders, scripts, executables, dotfiles, credentials or private skill content.
ALLOWED = {
    'Verse': {'.verse'},
    'UI': {'.png','.jpg','.jpeg','.webp','.json'},
    'Assets': {'.png','.jpg','.jpeg','.webp','.ogg','.wav'},
    'docs': {'.md','.txt'},
}
ROOT_DOCS={'INSTALL.md','README.md','VALIDATION.md','LICENSE.md','ASSET_MANIFEST.json','ASSET_ATTRIBUTIONS.md','ENGINEERING_MANIFEST.json'}
MAX_FILES=150
MAX_FILE=8*1024*1024
MAX_TOTAL=30*1024*1024
_SUSPICIOUS = re.compile(r'(?i)(?:secret|password|token|credential|private[-_]?key|id_rsa|\.env|oauth|\.pem|\.p12|\.key)')
_PRIVATE_BYTES = (b'-----BEGIN PRIVATE KEY-----',b'-----BEGIN OPENSSH PRIVATE KEY-----',b'-----BEGIN RSA PRIVATE KEY-----')


def allowed(rel: Path)->bool:
    parts=rel.parts
    if any(x.startswith('.') or _SUSPICIOUS.search(x) for x in parts):
        return False
    if len(parts)==1:
        return rel.name in ROOT_DOCS
    if len(parts)<2 or parts[0] not in ALLOWED:
        return False
    if rel.suffix.casefold() not in ALLOWED[parts[0]]:
        return False
    if parts[0]=='docs' and rel.suffix.casefold()=='.md' and rel.name.upper() not in ROOT_DOCS:
        return False
    return True


def package(source: Path, destination: Path)->dict:
    source=source.expanduser().resolve(strict=True)
    if not source.is_dir(): raise ValueError('Staging source must be a directory')
    destination=destination.expanduser()
    if destination.is_symlink(): raise ValueError('Refusing to overwrite existing ZIP')
    destination=destination.resolve(strict=False)
    if destination.suffix.lower()!='.zip': raise ValueError('Output must be a ZIP file')
    if destination.is_relative_to(source): raise ValueError('Output must be outside staging directory')
    if destination.exists() or destination.is_symlink(): raise ValueError('Refusing to overwrite existing ZIP')
    entries=[]; sizes=0
    for entry in sorted(source.rglob('*'),key=lambda p:p.relative_to(source).as_posix()):
        rel=entry.relative_to(source)
        # Explicit lstat so even symlinked files/dirs are rejected.
        mode=entry.lstat().st_mode
        if stat.S_ISLNK(mode): raise ValueError(f'Symlink not allowed: {rel}')
        if stat.S_ISDIR(mode): continue
        if not stat.S_ISREG(mode): raise ValueError(f'Non regular file: {rel}')
        if not allowed(rel): raise ValueError(f'Unsupported or private output path: {rel}')
        sz=entry.stat().st_size
        if sz>MAX_FILE: raise ValueError(f'File too large: {rel}')
        sizes+=sz
        if sizes>MAX_TOTAL or len(entries)>=MAX_FILES: raise ValueError('Package resource limit exceeded')
        data=entry.read_bytes()
        if any(x in data for x in _PRIVATE_BYTES): raise ValueError(f'Private key detected: {rel}')
        entries.append((rel.as_posix(),data))
    as_files = dict(entries)
    check_asset_manifest(as_files.get('ASSET_MANIFEST.json'),as_files)
    if not any(p.endswith('.verse') for p,_ in entries):
        raise ValueError('At least one .verse source is required')
    if not any(p.startswith('Verse/') and p.endswith('.verse') for p,_ in entries):
        raise ValueError('Place Verse sources inside Verse/')
    if not any(p=='INSTALL.md' for p,_ in entries):
        entries.append(('INSTALL.md',b'# VerseForge / Installation\n\nCopy Verse/*.verse into a test UEFN project, configure editable devices, then compile in the actual editor.\n\nUEFN compilation, gameplay and multiplayer are NOT TESTED.\n'))
    manifest={'schema':'verseforge-chat-package-v1','validation':{'static':'NOT TESTED','uefn_compile':'NOT TESTED','gameplay':'NOT TESTED','multiplayer':'NOT TESTED'},
              'files':[{'path':p,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for p,data in sorted(entries)],
              'note':'Manifest records content hashes, not a cryptographic signature or compile evidence.'}
    entries.append(('VERSEFORGE_MANIFEST.json',(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n').encode('utf-8')))
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
            for name,data in sorted(entries):
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16
                z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=7)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {'result':'PASS','archive':str(destination),'source_files':len(manifest['files']),
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'uefn_compile':'NOT TESTED','gameplay':'NOT TESTED','multiplayer':'NOT TESTED',
            'manifest_signed':False}



def verify_package(archive: Path) -> dict:
    """Independent ZIP integrity audit. Hashes detect damage, NOT authorship.

    No extraction is performed. Input is untrusted and bounded before decompression.
    """
    archive = archive.expanduser().resolve(strict=True)
    if not archive.is_file() or archive.suffix.lower() != '.zip':
        raise ValueError('Expected an existing ZIP file')
    errors = []
    try:
        with zipfile.ZipFile(archive, 'r') as z:
            members = z.infolist()
            if len(members) > MAX_FILES + 2:
                raise ValueError('ZIP file count limit exceeded')
            paths = [m.filename for m in members]
            if len(set(paths)) != len(paths) or len({p.casefold() for p in paths}) != len(paths):
                raise ValueError('Duplicate or case-colliding ZIP entries')
            if 'VERSEFORGE_MANIFEST.json' not in paths:
                raise ValueError('Missing VerseForge manifest')
            file_sizes = 0
            for info in members:
                name = info.filename
                rel = PurePosixPath(name)
                if name != rel.as_posix() or rel.is_absolute() or '..' in rel.parts or '\\' in name:
                    raise ValueError(f'Unsafe ZIP member: {name}')
                if name != 'VERSEFORGE_MANIFEST.json' and not allowed(Path(*rel.parts)):
                    raise ValueError(f'Unauthorized ZIP member: {name}')
                if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f'Unsupported ZIP entry type: {name}')
                if info.file_size > MAX_FILE or (info.file_size < 0):
                    raise ValueError(f'Oversized ZIP member: {name}')
                file_sizes += info.file_size
                if file_sizes > MAX_TOTAL + 65536:
                    raise ValueError('ZIP total size limit exceeded')
            manifest = json.loads(z.read('VERSEFORGE_MANIFEST.json'))
            if not isinstance(manifest, dict) or manifest.get('schema') != 'verseforge-chat-package-v1':
                raise ValueError('Unsupported VerseForge manifest schema')
            listed = manifest.get('files')
            if not isinstance(listed, list):
                raise ValueError('Invalid manifest file list')
            actual = {p for p in paths if p != 'VERSEFORGE_MANIFEST.json'}
            expected = set()
            for entry in listed:
                if not isinstance(entry, dict) or not isinstance(entry.get('path'), str):
                    raise ValueError('Malformed manifest file entry')
                path = entry['path']
                expected.add(path)
                if path not in actual:
                    errors.append(f'Missing source: {path}')
                    continue
                content = z.read(path)
                if len(content) != entry.get('bytes'):
                    errors.append(f'Unexpected byte size: {path}')
                if hashlib.sha256(content).hexdigest() != entry.get('sha256'):
                    errors.append(f'Hash mismatch: {path}')
            if len(expected) != len(listed) or expected != actual:
                errors.append('Manifest and ZIP member lists do not match')
            if not any(p.startswith('Verse/') and p.endswith('.verse') for p in actual):
                errors.append('ZIP lacks a Verse source')
            real_files = {name: z.read(name) for name in actual}
            check_asset_manifest(real_files.get('ASSET_MANIFEST.json'),real_files)
            validation = manifest.get('validation')
            if not isinstance(validation, dict) or any(validation.get(k) != 'NOT TESTED' for k in ('static','uefn_compile','gameplay','multiplayer')):
                errors.append('Unverifiable validation claim in ZIP manifest')
            if errors:
                return {'result': 'FAIL', 'issues': errors, 'verified_files': 0,
                        'uefn_compile': 'NOT TESTED', 'signature': 'NOT PRESENT'}
            return {'result': 'PASS', 'verified_files': len(expected),
                    'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                    'uefn_compile': 'NOT TESTED', 'gameplay': 'NOT TESTED',
                    'signature': 'NOT PRESENT',
                    'note': 'SHA-256 matches the manifest; no cryptographic provenance signature or UEFN test.'}
    except (zipfile.BadZipFile, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        raise ValueError(f'Invalid ZIP/manifest: {exc}') from exc
