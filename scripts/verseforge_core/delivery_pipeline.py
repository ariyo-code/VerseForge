"""One offline pipeline: review staged *existing* Verse, generate honest status, ZIP and verify.

The host coding model writes the Verse sources. This utility never claims that it
can synthesize Verse or run the Epic compiler.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import stat
import tempfile
from pathlib import Path
from .chat_package import package, verify_package, allowed, MAX_FILES, MAX_FILE, MAX_TOTAL
from .quality_engine import review_sources


def _stage_copy(source: Path, destination: Path) -> None:
    files = 0
    total = 0
    for item in sorted(source.rglob('*')):
        relative = item.relative_to(source)
        mode = item.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError('Symlink forbidden in delivery source')
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode) or not allowed(relative):
            raise ValueError(f'Unsupported delivery input: {relative}')
        size = item.stat().st_size
        files += 1
        total += size
        if files > MAX_FILES or size > MAX_FILE or total > MAX_TOTAL:
            raise ValueError('Delivery source exceeds safe resource limits')
        if relative.as_posix() == 'VALIDATION.md':
            # Never trust a host-authored claim of compilation in a local delivery.
            continue
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, output)


def deliver(source: Path, output: Path, contract: dict | None = None, *, strict: bool = False) -> dict:
    source = Path(source).expanduser().resolve(strict=True)
    output = Path(output).expanduser()
    if output.is_symlink() or output.exists():
        raise ValueError('Refusing to overwrite existing output')
    if output.resolve(strict=False).is_relative_to(source):
        raise ValueError('Output must be outside delivery source')
    report = review_sources(source, contract)
    if strict and report['local_check'] != 'PASS':
        return {'result': 'BLOCKED', 'reason': 'Static evidence requires review', 'review': report}
    with tempfile.TemporaryDirectory(prefix='verseforge-deliver-') as work:
        stage = Path(work) / 'source'
        stage.mkdir()
        _stage_copy(source, stage)
        lines = [
            '# VerseForge / Evidence and limitations', '',
            f'- Verse files: {report["source_count"]}',
            f'- Local heuristic review: **{report["local_check"]}**',
            '- UEFN compilation: **NOT TESTED**',
            '- Gameplay: **NOT TESTED**',
            '- Multiplayer: **NOT TESTED**',
            '- Cryptographic signature: **NOT PRESENT**', '',
            'The code is authored by the host agent; local checks are not the Epic Verse compiler.',
            'Copy Verse sources to an isolated UEFN project, configure required editable devices,',
            'compile with the real editor and perform in-game tests before deployment.', '',
            '## Local warnings',
        ]
        lines += [f'- {warning}' for warning in report['warnings']] or ['- None detected by local checks']
        lines += ['', '## Acceptance requirements', '']
        lines += [f'- **{row["id"]}**: {row["status"]}' for row in report['acceptance_checks']] or ['- No acceptance contract supplied']
        (stage / 'VALIDATION.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        result = package(stage, output)
    verification = verify_package(output)
    if verification['result'] != 'PASS':
        output.unlink(missing_ok=True)
        raise ValueError('Post-package integrity verification failed')
    return {'result': 'PASS', 'archive': str(output.resolve()), 'sha256': result['sha256'],
            'source_count': report['source_count'], 'local_check': report['local_check'],
            'review': report, 'zip_integrity': verification['result'],
            'uefn_compile': 'NOT TESTED', 'gameplay': 'NOT TESTED', 'multiplayer': 'NOT TESTED',
            'signature': 'NOT PRESENT'}
