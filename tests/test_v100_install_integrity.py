"""Installed releases are not trusted merely because their manifest exists."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verseforge_core.distribution import release, install_release, restore_backup, verify_installation


def make_release(tmp_path: Path, version: str) -> Path:
    root = tmp_path / ("source-" + version)
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: verseforge\n---\n", encoding="utf-8")
    (root / "README.md").write_text("Version " + version, encoding="utf-8")
    archive = tmp_path / (version + ".zip")
    release(root, archive, version)
    return archive


def test_installed_release_verified(tmp_path):
    archive = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(archive, dst)
    assert verify_installation(dst)["result"] == "PASS"


def test_install_detection_modified_content(tmp_path):
    first = make_release(tmp_path, "1.0.0-rc2")
    second = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(first, dst)
    (dst / "README.md").write_text("User-modified", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch|Modified"):
        install_release(second, dst, upgrade=True)
    assert (dst / "README.md").read_text() == "User-modified"


def test_install_rejects_undeclared_extras(tmp_path):
    archive = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(archive, dst)
    (dst / "token.txt").write_text("unexpected")
    with pytest.raises(ValueError, match="Undeclared"):
        verify_installation(dst)


def test_install_rejects_symlink(tmp_path):
    archive = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(archive, dst)
    (dst / "README.md").unlink()
    (dst / "README.md").symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError, match="Symlink"):
        verify_installation(dst)


def test_backup_integrity_before_rollback(tmp_path):
    first = make_release(tmp_path, "1.0.0-rc2")
    second = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(first, dst)
    upgrade = install_release(second, dst, upgrade=True)
    backup = Path(upgrade["backup"])
    assert backup.is_dir()
    (backup / "README.md").write_text("tampered")
    with pytest.raises(ValueError, match="hash mismatch|Modified"):
        restore_backup(dst, backup)
    assert verify_installation(dst)["version"] == "1.0.0-rc3"


def test_rollback_unchanged_backup(tmp_path):
    first = make_release(tmp_path, "1.0.0-rc2")
    second = make_release(tmp_path, "1.0.0-rc3")
    dst = tmp_path / "skill"
    install_release(first, dst)
    upgrade = install_release(second, dst, upgrade=True)
    restore_backup(dst, Path(upgrade["backup"]))
    assert verify_installation(dst)["version"] == "1.0.0-rc2"
