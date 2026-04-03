"""Tests for vault link manager."""

from pathlib import Path
from shutil import copy2

import pytest

from bullish_ssg.vault_link.manager import SymlinkError, VaultLinkManager


class TestVaultLinkManagerCreate:
    def test_create_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.create()

        assert result is True
        link = tmp_path / "docs"
        assert link.is_symlink()
        assert link.resolve() == source.resolve()

    def test_create_idempotent(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        assert manager.create() is False

    def test_create_fails_when_source_missing(self, tmp_path: Path) -> None:
        manager = VaultLinkManager(tmp_path / "missing", Path("docs"), tmp_path)
        with pytest.raises(SymlinkError):
            manager.create()

    def test_create_fails_when_source_is_file(self, tmp_path: Path, fixture_file: callable) -> None:
        source_file = tmp_path / "source.md"
        copy2(fixture_file("vault/source_vault/index.md"), source_file)

        manager = VaultLinkManager(source_file, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError):
            manager.create()

    def test_create_fails_when_dir_exists(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        (tmp_path / "docs").mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError):
            manager.create()

    def test_create_with_force_replaces_directory(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        existing = tmp_path / "docs"
        existing.mkdir()
        fixture = fixture_copy("vault/alt_vault")
        copy2(fixture / "index.md", existing / "index.md")

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        assert manager.create(force=True) is True
        assert (tmp_path / "docs").resolve() == source.resolve()


class TestVaultLinkManagerRepair:
    def test_repair_broken_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        (source / "index.md").unlink()
        source.rmdir()
        new_source = fixture_copy("vault/alt_vault")

        manager = VaultLinkManager(new_source, Path("docs"), tmp_path)
        assert manager.repair() is True
        assert link.resolve() == new_source.resolve()

    def test_repair_idempotent(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        (tmp_path / "docs").symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        assert manager.repair() is False

    def test_repair_creates_missing_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        assert manager.repair() is True
        assert (tmp_path / "docs").is_symlink()

    def test_repair_non_symlink_path_raises(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        docs = tmp_path / "docs"
        docs.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError):
            manager.repair()


class TestVaultLinkManagerStatus:
    def test_status_valid_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        (tmp_path / "docs").symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is True
        assert status["is_symlink"] is True
        assert status["target_exists"] is True
        assert status["is_valid"] is True

    def test_status_missing_link(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is False
        assert status["is_symlink"] is False
        assert status["is_valid"] is False

    def test_status_broken_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)
        (source / "index.md").unlink()
        source.rmdir()

        replacement = tmp_path / "replacement"
        replacement.mkdir()
        manager = VaultLinkManager(replacement, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is True
        assert status["is_symlink"] is True
        assert status["target_exists"] is False
        assert status["is_valid"] is False


class TestVaultLinkManagerRemove:
    def test_remove_symlink(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)
        manager = VaultLinkManager(source, Path("docs"), tmp_path)

        assert manager.remove() is True
        assert not link.exists()
        assert not link.is_symlink()

    def test_remove_nonexistent_returns_false(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        assert manager.remove() is False

    def test_remove_non_symlink_raises(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        docs = tmp_path / "docs"
        docs.mkdir()
        manager = VaultLinkManager(source, Path("docs"), tmp_path)

        with pytest.raises(SymlinkError):
            manager.remove()
