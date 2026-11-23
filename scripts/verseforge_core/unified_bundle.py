"""Single offline workflow: verified local assets + UI handoff + Verse project ZIP.

The host coding agent still authors nontrivial Verse behavior. This process never
claims to create native UMG .uasset files, call UEFN or infer image semantics.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .asset_engine import import_assets
from .compose_engine import compose_project
from .engineering_engine import architecture
from .ui_engine import render_ui
from .chat_package import verify_package


def build_bundle(
    engineering_spec: dict[str, Any], authored_source: Path, output_dir: Path,
    *, uefn_version: str, ui_observations: dict[str, Any] | None = None,
    asset_spec: dict[str, Any] | None = None,
    local_asset_sources: Path | None = None,
    api_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a new complete delivery directory, or leave no output on failure.

    A blocked composition (missing source or API declarations) is returned
    without publishing a partial folder. The UI is a browser preview only.
    """
    plan = architecture(engineering_spec)
    source = Path(authored_source).expanduser()
    output = Path(output_dir).expanduser()
    if source.is_symlink() or not source.is_dir():
        raise ValueError('An existing non-symlinked authored-source folder is required')
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise ValueError('Cannot overwrite bundle output or follow symlinked parent')
    if output.resolve(strict=False).is_relative_to(source.resolve()):
        raise ValueError('Bundle output must be outside the authored source tree')
    if (asset_spec is None) != (local_asset_sources is None):
        raise ValueError('Licensed asset spec and source directory must be supplied together')
    # Validate required assets/UI configuration before copying any source data.
    if ui_observations is not None and not isinstance(ui_observations, dict):
        raise ValueError('UI observations must be a JSON object')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.verseforge-unified-', dir=output.parent) as temporary:
        work = Path(temporary)
        stage = work / 'stage'
        # The composer below checks every file in the staged tree, disallowing
        # hidden/symlinked/private files. We also avoid following symlinks here.
        from .compose_engine import _source_entries
        entries = _source_entries(source)
        stage.mkdir()
        for src, rel in entries:
            dst = stage / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        assets_report = None
        assets_dir = None
        if asset_spec is not None:
            assets_dir = work / 'licensed_assets'
            assets_report = import_assets(asset_spec, local_asset_sources, assets_dir)
            for asset in assets_dir.rglob('*'):
                if asset.is_file():
                    relative = asset.relative_to(assets_dir)
                    # Only supported source documents and asset files are copied to
                    # the game ZIP. ASSET_ATTRIBUTIONS.md is a handoff document.
                    if relative.as_posix() not in {'ASSET_MANIFEST.json', 'ASSET_ATTRIBUTIONS.md'} and relative.parts[0] not in {'UI','Assets'}:
                        raise ValueError('Unexpected asset output')
                    to = stage / relative
                    if to.exists() or to.is_symlink():
                        raise ValueError(f'Conflicting source/asset file: {relative}')
                    to.parent.mkdir(parents=True, exist_ok=True)
                    to.write_bytes(asset.read_bytes())
        zip_path = work / 'gameplay.zip'
        result = compose_project(engineering_spec, stage, zip_path,
                                 uefn_version=uefn_version, api_evidence=api_evidence)
        if result['result'] != 'PASS':
            return {'result':'BLOCKED', 'reason':result, 'output_created':False,
                    'uefn_compile':'NOT TESTED'}
        preview = None
        if ui_observations is not None:
            preview = render_ui(ui_observations, work / 'ui_preview',
                                assets_dir=assets_dir, emit_verse=False)
        verification = verify_package(zip_path)
        if verification['result'] != 'PASS':
            raise ValueError('Game ZIP failed independent verification')
        deliverable = work / 'complete'
        deliverable.mkdir()
        shutil.copyfile(zip_path, deliverable / 'GAMEPLAY.zip')
        if ui_observations is not None:
            shutil.copytree(work / 'ui_preview', deliverable / 'UI_PREVIEW')
        brief = {
            'schema':'verseforge-unified-bundle-v1', 'project':plan['project'],
            'modules':result['modules'], 'uefn_version':uefn_version,
            'gameplay_zip_sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            'zip_integrity':verification['result'],
            'assets':{'count':assets_report['files'], 'legal_review':assets_report['legal_review']} if assets_report else None,
            'ui':{'screens':preview['screens'], 'mode':'BROWSER MOCK AND UMG HANDOFF'} if preview else None,
            'gameplay_source':'HOST-AUTHORED',
            'api_evidence':result['api'],
            'umg_asset':'NOT GENERATED', 'uefn_compile':'NOT TESTED',
            'runtime':'NOT TESTED', 'multiplayer':'NOT TESTED',
        }
        (deliverable / 'BUNDLE_REPORT.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
        (deliverable / 'INSTALL.md').write_text(
            '# VerseForge project bundle\n\n'
            '1. Unzip GAMEPLAY.zip; review the architecture and required devices.\n'
            '2. Copy the Verse sources to a disposable UEFN island and import reviewed artwork.\n'
            '3. If UI_PREVIEW exists, recreate its handoff in a UMG Widget Blueprint; '
            'HTML is not an installable Fortnite widget.\n'
            '4. Compile with real UEFN and fix exact compiler errors, then test multiple players.\n\n'
            '**This offline bundle has not been compiled or playtested.**\n', encoding='utf-8')
        os.replace(deliverable, output)
        return {'result':'BUNDLE CREATED','output':str(output), 'zip_integrity':verification['result'],
                'modules':result['modules'],'ui_preview':bool(preview),
                'reviewed_asset_pack':bool(assets_report),'uefn_compile':'NOT TESTED',
                'runtime':'NOT TESTED', 'multiplayer':'NOT TESTED'}
