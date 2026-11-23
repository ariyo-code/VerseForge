"""Offline licensed-resource importer with optional image normalization.

Never scrapes a site, asserts redistribution rights or creates .uasset files.
Only local, explicitly approved regular files are importable.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from .asset_license import LICENSES, EXTENSIONS, check_asset_manifest

SCHEMA = "verseforge-asset-import-v1"
MAX_FILES = 100
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 30 * 1024 * 1024
_IMAGE = {".png", ".jpg", ".jpeg", ".webp"}
_AUDIO = {".wav", ".ogg"}
_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_./-]{0,190}$")


def _relative(s: Any, *, allow_nested: bool = True) -> Path:
    if not isinstance(s, str) or not _NAME.fullmatch(s) or "\\" in s:
        raise ValueError("Unsafe relative asset name")
    p = PurePosixPath(s)
    if p.is_absolute() or ".." in p.parts or any(x.startswith(".") for x in p.parts):
        raise ValueError("Asset traversal or hidden path forbidden")
    if not allow_nested and len(p.parts) != 1:
        raise ValueError("Nested name forbidden")
    return Path(*p.parts)


def _regular_nosymlink(base: Path, relative: Path) -> Path:
    cur = base
    if cur.is_symlink():
        raise ValueError("Symlinked asset root is not supported")
    for name in relative.parts:
        cur = cur / name
        mode = cur.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise ValueError("Symlinked asset path forbidden")
    if not stat.S_ISREG(cur.lstat().st_mode) or cur.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Asset must be a bounded regular file")
    return cur


def _check_magic(ext: str, data: bytes) -> None:
    image_magic = {
        ".png": lambda d: d.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda d: d.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda d: d.startswith(b"\xff\xd8\xff"),
        ".webp": lambda d: d.startswith(b"RIFF") and d[8:12] == b"WEBP",
        ".ogg": lambda d: d.startswith(b"OggS"),
        ".wav": lambda d: d.startswith(b"RIFF") and d[8:12] == b"WAVE",
    }
    if not image_magic[ext](data):
        raise ValueError("File extension and file signature disagree")


def import_assets(spec: dict[str, Any], source_root: Path, target: Path) -> dict[str, Any]:
    if not isinstance(spec, dict) or spec.get("schema") != SCHEMA:
        raise ValueError("Unknown asset import schema")
    assets = spec.get("assets")
    if not isinstance(assets, list) or not 1 <= len(assets) <= MAX_FILES:
        raise ValueError("Require 1–100 asset entries")
    raw_root = Path(source_root).expanduser()
    if raw_root.is_symlink():
        raise ValueError("Symlinked asset root refused")
    source_root = raw_root.resolve(strict=True)
    if not source_root.is_dir():
        raise ValueError("Source root must be a directory")
    target = Path(target).expanduser()
    if target.exists() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError("Refusing to overwrite asset output")
    files: dict[str, bytes] = {}
    manifest: list[dict[str, Any]] = []
    seen = set()
    total = 0
    for record in assets:
        if not isinstance(record, dict):
            raise ValueError("Asset entry must be an object")
        source = _relative(record.get("source"))
        dest = _relative(record.get("target"))
        rel = dest.as_posix()
        if len(dest.parts) < 2 or dest.parts[0] not in ("UI", "Assets") or dest.suffix.lower() not in EXTENSIONS:
            raise ValueError("Asset target must be UI/ or Assets/ with an allowed extension")
        if rel.casefold() in seen:
            raise ValueError("Duplicate or case-colliding asset target")
        seen.add(rel.casefold())
        origin_file = _regular_nosymlink(source_root, source)
        src_ext = source.suffix.lower()
        dst_ext = dest.suffix.lower()
        if src_ext not in EXTENSIONS:
            raise ValueError("Unsupported local asset source type")
        if record.get("license") not in LICENSES:
            raise ValueError("Asset license is missing or unrecognized")
        if record.get("rights_reviewed") is not True:
            raise ValueError("Explicit human rights_reviewed=true required; this is not independent verification")
        data = origin_file.read_bytes()
        _check_magic(src_ext, data)
        resize = record.get("max_dimension")
        if resize is not None:
            if src_ext not in _IMAGE or dst_ext != ".png" or type(resize) is not int or not 64 <= resize <= 2048:
                raise ValueError("Resizing requires an image -> .png and a 64–2048 dimension")
            try:
                from PIL import Image, ImageOps
                from io import BytesIO
            except ImportError as exc:
                raise ValueError("Pillow is required for image transforms") from exc
            with Image.open(origin_file) as original:
                if original.width * original.height > 16_000_000 or getattr(original, "n_frames", 1) != 1:
                    raise ValueError("Input image exceeds safe limits")
                converted = ImageOps.exif_transpose(original).convert("RGBA")
                converted.thumbnail((resize, resize))
                buff = BytesIO()
                converted.save(buff, format="PNG", optimize=True)
                data = buff.getvalue()
        elif src_ext != dst_ext:
            raise ValueError("Extension conversion requires a supported image transformation")
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Transformed asset too large")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Asset pack exceeds limit")
        entry = {"path": rel, "sha256": hashlib.sha256(data).hexdigest(),
                 "license": record["license"], "origin": record.get("origin")}
        for key in ("creator", "source_url", "license_url", "attribution"):
            if key in record:
                entry[key] = record[key]
        files[rel] = data
        manifest.append(entry)
    output_manifest = {"schema": "verseforge-asset-manifest-v1", "assets": manifest}
    manbytes = (json.dumps(output_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    review = check_asset_manifest(manbytes, files)
    credits = ["# Asset attributions", "", "Claims supplied by the importer, not independently verified.", ""]
    for item in manifest:
        credits.append(f"- `{item['path']}` — {item['license']}; {item.get('attribution') or item.get('creator') or item.get('source_url', 'source not listed')}")
    target.mkdir(parents=True, exist_ok=False)
    try:
        for path, data in files.items():
            dest = target / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        (target / "ASSET_MANIFEST.json").write_bytes(manbytes)
        (target / "ASSET_ATTRIBUTIONS.md").write_text("\n".join(credits) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(target)
        raise
    return {"result": "IMPORTED", "files": len(files), "bytes": total, "target": str(target),
            "manifest": review, "legal_review": "DECLARED BY USER — NOT INDEPENDENTLY VERIFIED", "uefn_import": "NOT TESTED"}
