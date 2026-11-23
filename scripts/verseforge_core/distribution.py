"""Reproducible public skill releases with bounded verification and atomic installation.

SHA-256 here is an integrity comparison only, NOT cryptographic authorship.
Do not include private-service, credentials, signed capabilities, or customer data.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "verseforge-public-release-v1"
_MAX_FILES = 300
_MAX_FILE = 8 * 1024 * 1024
_MAX_TOTAL = 48 * 1024 * 1024
_EXTENSION = {".md", ".json", ".yaml", ".yml", ".py", ".txt", ".verse", ".ps1", ".toml", ".png", ".svg"}
_PARTS = {"SKILL.md", "README.md", "LICENSE.md", "requirements-optional.txt", "agents", "assets", "ci", "evals", "examples", "integrations", "references", "scripts", "templates", "tests", "workflows"}
_BAD = re.compile(r"(?:^|/)(?:\.env(?:\.[^/]*)?|(?:secret|credential|token|private[-_]?key|license[-_]?db)(?:[._-][^/]*)?)(?:/|$)|\.(?:pem|p12|key)(?:$|/)", re.I)
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-(?:rc|beta)[0-9]+)?$")


def _source_files(root: Path) -> list[tuple[str, bytes]]:
    if root.is_symlink() or not root.is_dir() or not (root / "SKILL.md").is_file():
        raise ValueError("Expected a non-symlinked VerseForge root with SKILL.md")
    items = []
    total = 0
    used = set()
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        # skip caches and local test reports; never silently skip symlinked files.
        if p.is_symlink():
            raise ValueError("Symlink in skill root is forbidden")
        if any(x.startswith(".") or x == "__pycache__" for x in rel.parts) or p.suffix in {".pyc", ".pyo"}:
            continue
        if p.is_dir():
            continue
        if not p.is_file():
            raise ValueError("Special files cannot enter a release")
        if rel.parts[0] not in _PARTS or p.suffix.lower() not in _EXTENSION or _BAD.search(rel.as_posix()):
            raise ValueError(f"Unauthorized public file: {rel}")
        name = rel.as_posix()
        if name.casefold() in used:
            raise ValueError("Case-colliding public paths")
        used.add(name.casefold())
        size = p.stat().st_size
        total += size
        if len(items) >= _MAX_FILES or size > _MAX_FILE or total > _MAX_TOTAL:
            raise ValueError("Release exceeds resource limit")
        data = p.read_bytes()
        # Match an actual multiline PEM block, not a literal detection string in source code.
        if re.search(rb"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{40,}", data):
            raise ValueError("Private signing key found in candidate public release")
        items.append((name, data))
    return items


def _write_zip(dst: Path, files: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(dst, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for name, data in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=8)


def release(root: Path, output: Path, version: str) -> dict[str, Any]:
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError("Version must be SemVer (e.g. 1.0.0-rc2)")
    raw_root = Path(root).expanduser()
    if raw_root.is_symlink():
        raise ValueError("Symlinked release source root refused")
    root = raw_root.resolve(strict=True)
    output = Path(output).expanduser()
    if output.exists() or output.is_symlink() or output.suffix.lower() != ".zip" or output.parent.is_symlink():
        raise ValueError("Refusing invalid or existing release ZIP")
    if output.resolve(strict=False).is_relative_to(root):
        raise ValueError("Release ZIP output must be outside skill source root")
    files = _source_files(root)
    records = [{"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for name, data in files]
    manifest = {"schema": SCHEMA, "version": version, "files": records, "edition": "public",
                "cryptographic_signature": "NOT PRESENT", "uefn_compile": "NOT TESTED"}
    contents = files + [("RELEASE_MANIFEST.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())]
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_zip(output, contents)
        result = verify_release(output)
        if result["result"] != "PASS":
            raise ValueError("Post-build verification failed")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return {**result, "path": str(output), "version": version}


def verify_release(archive: Path) -> dict[str, Any]:
    archive = Path(archive).expanduser()
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("Expected regular release ZIP")
    if archive.stat().st_size > _MAX_TOTAL:
        raise ValueError("Release file exceeds maximum size")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not 2 <= len(members) <= _MAX_FILES + 1:
            raise ValueError("Unbounded release member count")
        names = [m.filename for m in members]
        if len({x.casefold() for x in names}) != len(names) or "RELEASE_MANIFEST.json" not in names:
            raise ValueError("Duplicate paths or missing manifest")
        total = 0
        for info in members:
            name = info.filename
            pure = PurePosixPath(name)
            if (not name or name != pure.as_posix() or pure.is_absolute() or ".." in pure.parts
                    or "\\" in name or not all(x and not x.startswith(".") for x in pure.parts)):
                raise ValueError("Unsafe public release path")
            if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or not stat.S_ISREG(info.external_attr >> 16):
                raise ValueError("Unsupported release member type")
            if name != "RELEASE_MANIFEST.json" and (pure.parts[0] not in _PARTS or pure.suffix.lower() not in _EXTENSION or _BAD.search(name)):
                raise ValueError("Unauthorized release member")
            if info.file_size < 0 or info.file_size > _MAX_FILE:
                raise ValueError("Member too large")
            total += info.file_size
            if total > _MAX_TOTAL:
                raise ValueError("Release expands too large")
        man = json.loads(z.read("RELEASE_MANIFEST.json"))
        if (not isinstance(man, dict) or man.get("schema") != SCHEMA
                or not isinstance(man.get("version"), str) or not _VERSION.fullmatch(man["version"])
                or man.get("edition") != "public" or man.get("cryptographic_signature") != "NOT PRESENT"):
            raise ValueError("Invalid release manifest")
        expected = man.get("files")
        if not isinstance(expected, list) or len(expected) != len(members) - 1:
            raise ValueError("Manifest member count mismatch")
        real = set(names) - {"RELEASE_MANIFEST.json"}
        entries = {}
        for item in expected:
            if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
                raise ValueError("Malformed release item")
            path = item["path"]
            if not isinstance(path, str) or path in entries or path not in real:
                raise ValueError("Duplicate/unknown release item")
            value = z.read(path)
            if len(value) != item["bytes"] or hashlib.sha256(value).hexdigest() != item["sha256"]:
                raise ValueError(f"Release content hash mismatch: {path}")
            entries[path] = len(value)
        if set(entries) != real or "SKILL.md" not in entries:
            raise ValueError("Missing public release files")
        return {"result": "PASS", "version": man["version"], "files": len(entries),
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "cryptographic_signature": "NOT PRESENT", "uefn_compile": "NOT TESTED"}



def verify_installation(directory: Path) -> dict[str, Any]:
    """Validate installed release against its manifest before upgrade or rollback.

    This proves local content integrity only; it does not authenticate its publisher.
    """
    directory = Path(directory).expanduser()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Expected a regular installed release directory")
    manifest_path = directory / "RELEASE_MANIFEST.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 1024 * 1024:
        raise ValueError("Missing or oversized installed release manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA
            or not isinstance(manifest.get("version"), str) or not _VERSION.fullmatch(manifest["version"])
            or manifest.get("edition") != "public"
            or manifest.get("cryptographic_signature") != "NOT PRESENT"
            or not isinstance(manifest.get("files"), list)):
        raise ValueError("Invalid installed release manifest")
    expected = {}
    declared_size = 0
    for rec in manifest["files"]:
        if not isinstance(rec, dict) or set(rec) != {"path", "bytes", "sha256"}:
            raise ValueError("Invalid installed manifest record")
        relative = rec["path"]
        if not isinstance(relative, str):
            raise ValueError("Invalid installed file path")
        pp = PurePosixPath(relative)
        if (relative != pp.as_posix() or pp.is_absolute() or ".." in pp.parts
                or "\\" in relative or not pp.parts or any(x.startswith(".") for x in pp.parts)
                or pp.parts[0] not in _PARTS or pp.suffix.lower() not in _EXTENSION
                or _BAD.search(relative) or relative.casefold() in expected):
            raise ValueError("Unsafe installed file path")
        size = rec["bytes"]
        digest = rec["sha256"]
        if (type(size) is not int or size < 0 or size > _MAX_FILE
                or not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest)):
            raise ValueError("Invalid installed file size or SHA-256")
        declared_size += size
        if declared_size > _MAX_TOTAL or len(expected) >= _MAX_FILES:
            raise ValueError("Installed release exceeds file limits")
        expected[relative.casefold()] = (relative, size, digest)
    seen = set()
    for file in directory.rglob("*"):
        if file.is_symlink():
            raise ValueError("Symlink in installed release")
        if file.is_dir():
            continue
        if not file.is_file():
            raise ValueError("Special file in installed release")
        rel = file.relative_to(directory).as_posix()
        if rel == "RELEASE_MANIFEST.json":
            continue
        entry = expected.get(rel.casefold())
        if entry is None or entry[0] != rel:
            raise ValueError(f"Undeclared file in installed release: {rel}")
        if file.stat().st_size != entry[1]:
            raise ValueError(f"Modified installed release: {rel}")
        if hashlib.sha256(file.read_bytes()).hexdigest() != entry[2]:
            raise ValueError(f"Installed release hash mismatch: {rel}")
        seen.add(rel.casefold())
    if seen != set(expected) or "skill.md" not in seen:
        raise ValueError("Installed release is incomplete")
    return {"result": "PASS", "version": manifest["version"], "files": len(expected),
            "publisher_authentication": "NOT ESTABLISHED", "uefn_compile": "NOT TESTED"}


def install_release(archive: Path, destination: Path, *, upgrade: bool = False, allow_downgrade: bool = False) -> dict[str, Any]:
    """Atomic installation with versioned backup; never delete an unrecognized directory."""
    report = verify_release(archive)
    destination = Path(destination).expanduser()
    if destination.is_symlink() or destination.parent.is_symlink():
        raise ValueError("Symlinked installation path refused")
    if destination.exists() and not upgrade:
        raise ValueError("Use explicit upgrade to replace an existing installation")
    if destination.exists() and not (destination / "RELEASE_MANIFEST.json").is_file():
        raise ValueError("Existing directory does not look like a VerseForge installation")
    if destination.exists():
        verify_installation(destination)
        installed = json.loads((destination / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
        current_version = installed.get("version")
        if installed.get("schema") != SCHEMA or not isinstance(current_version, str) or not _VERSION.fullmatch(current_version):
            raise ValueError("Invalid existing installation manifest")
        def version_key(value: str):
            base, _, suffix = value.partition('-')
            numbers = tuple(map(int, base.split('.')))
            numbers = (numbers + (0, 0, 0))[:3]
            return (*numbers, 0 if suffix else 1, int(suffix[2:]) if suffix.startswith('rc') and suffix[2:].isdigit() else -1)
        if version_key(report['version']) < version_key(current_version) and not allow_downgrade:
            raise ValueError("Refusing version downgrade; use explicit allow_downgrade or release-rollback")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".vf-stage-", dir=destination.parent))
    backup = None
    try:
        with zipfile.ZipFile(archive) as z:
            for file in z.infolist():
                target = temp / file.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as f:
                    f.write(z.read(file.filename))
        if destination.exists():
            old = json.loads((destination / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
            oldver = old.get("version", "unknown").replace("/", "_")
            backup = destination.with_name(f"{destination.name}.backup-{oldver}")
            if backup.exists() or backup.is_symlink():
                raise ValueError("Backup already exists; rollback or archive it first")
            os.replace(destination, backup)
        try:
            os.replace(temp, destination)
        except Exception:
            if backup is not None:
                os.replace(backup, destination)
            raise
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return {"result": "INSTALLED", "version": report["version"], "target": str(destination),
            "backup": str(backup) if backup else None, "uefn_compile": "NOT TESTED"}


def restore_backup(destination: Path, backup: Path) -> dict[str, Any]:
    destination, backup = Path(destination), Path(backup)
    if (not destination.is_dir() or not backup.is_dir() or destination.is_symlink() or backup.is_symlink()
            or destination.parent.resolve() != backup.parent.resolve()
            or not backup.name.startswith(destination.name + ".backup-")):
        raise ValueError("Invalid installation and backup pair")
    if not (destination / "RELEASE_MANIFEST.json").is_file() or not (backup / "RELEASE_MANIFEST.json").is_file():
        raise ValueError("Missing installation manifest")
    verify_installation(destination)
    verify_installation(backup)
    renamed = destination.with_name(destination.name + ".rollback-candidate")
    if renamed.exists() or renamed.is_symlink():
        raise ValueError("Rollback temporary path already exists")
    os.replace(destination, renamed)
    try:
        os.replace(backup, destination)
    except Exception:
        os.replace(renamed, destination)
        raise
    return {"result": "RESTORED", "target": str(destination), "replaced_installation": str(renamed)}
