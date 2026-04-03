"""Tests for vault link manager."""

from pathlib import Path

import pytest

from bullish_ssg.vault_link.manager import SymlinkError, VaultLinkManager


class TestVaultLinkManagerCreate:
    """Tests for creating symlinks."""

    def test_create_symlink(self, tmp_path: Path) -> None:
        """Test creating a new symlink."""
        source = tmp_path / "vault"
        source.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.create()

        assert result is True
        link = tmp_path / "docs"
        assert link.is_symlink()
        assert link.resolve() == source.resolve()

    def test_create_idempotent(self, tmp_path: Path) -> None:
        """Test that create is idempotent."""
        source = tmp_path / "external_vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.create()

        assert result is False  # No change needed

    def test_create_fails_when_source_missing(self, tmp_path: Path) -> None:
        """Test that create fails when source doesn't exist."""
        source = tmp_path / "nonexistent"

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError) as exc_info:
            manager.create()
        assert "does not exist" in str(exc_info.value).lower()

    def test_create_fails_when_source_is_file(self, tmp_path: Path) -> None:
        """Test that create fails when source is a file."""
        source = tmp_path / "external_vault"
        source.write_text("not a dir")

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError) as exc_info:
            manager.create()
        assert "not a directory" in str(exc_info.value).lower()

    def test_create_fails_when_dir_exists(self, tmp_path: Path) -> None:
        """Test that create fails when directory exists at link path."""
        source = tmp_path / "vault"
        source.mkdir()
        existing = tmp_path / "docs"
        existing.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError) as exc_info:
            manager.create()
        assert "already exists" in str(exc_info.value).lower()

    def test_create_with_force_replaces_directory(self, tmp_path: Path) -> None:
        """Test that force mode replaces existing directory."""
        source = tmp_path / "vault"
        source.mkdir()
        existing = tmp_path / "docs"
        existing.mkdir()
        (existing / "file.txt").write_text("content")

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.create(force=True)

        assert result is True
        link = tmp_path / "docs"
        assert link.is_symlink()
        assert link.resolve() == source.resolve()

    def test_create_updates_changed_target(self, tmp_path: Path) -> None:
        """Test that create updates symlink when target changes."""
        source1 = tmp_path / "vault1"
        source1.mkdir()
        source2 = tmp_path / "vault2"
        source2.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source1)

        manager = VaultLinkManager(source2, Path("docs"), tmp_path)
        result = manager.create()

        assert result is True
        assert link.resolve() == source2.resolve()


class TestVaultLinkManagerRepair:
    """Tests for repairing symlinks."""

    def test_repair_broken_symlink(self, tmp_path: Path) -> None:
        """Test repairing broken symlink."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        # Break the symlink
        source.rmdir()
        new_source = tmp_path / "new_vault"
        new_source.mkdir()

        # Create manager with new source
        manager = VaultLinkManager(new_source, Path("docs"), tmp_path)
        result = manager.repair()

        assert result is True
        assert link.is_symlink()
        assert link.resolve() == new_source.resolve()

    def test_repair_idempotent(self, tmp_path: Path) -> None:
        """Test repair is idempotent for valid symlink."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.repair()

        assert result is False  # No repair needed

    def test_repair_creates_missing_symlink(self, tmp_path: Path) -> None:
        """Test repair creates symlink when missing."""
        source = tmp_path / "vault"
        source.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.repair()

        assert result is True
        link = tmp_path / "docs"
        assert link.is_symlink()

    def test_repair_fails_on_directory(self, tmp_path: Path) -> None:
        """Test repair fails when path is directory."""
        source = tmp_path / "vault"
        source.mkdir()
        existing = tmp_path / "docs"
        existing.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError) as exc_info:
            manager.repair()
        assert "not a symlink" in str(exc_info.value).lower()


class TestVaultLinkManagerRemove:
    """Tests for removing symlinks."""

    def test_remove_symlink(self, tmp_path: Path) -> None:
        """Test removing a symlink."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.remove()

        assert result is True
        assert not link.exists()

    def test_remove_missing_returns_false(self, tmp_path: Path) -> None:
        """Test removing non-existent symlink returns False."""
        source = tmp_path / "vault"
        source.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        result = manager.remove()

        assert result is False

    def test_remove_fails_on_directory(self, tmp_path: Path) -> None:
        """Test remove fails on directory."""
        source = tmp_path / "vault"
        source.mkdir()
        existing = tmp_path / "docs"
        existing.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        with pytest.raises(SymlinkError) as exc_info:
            manager.remove()
        assert "not a symlink" in str(exc_info.value).lower()


class TestVaultLinkManagerStatus:
    """Tests for status reporting."""

    def test_status_no_symlink(self, tmp_path: Path) -> None:
        """Test status when no symlink exists."""
        source = tmp_path / "vault"
        source.mkdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is False
        assert status["is_symlink"] is False
        assert status["is_valid"] is False

    def test_status_valid_symlink(self, tmp_path: Path) -> None:
        """Test status with valid symlink."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is True
        assert status["is_symlink"] is True
        assert status["target_exists"] is True
        assert status["is_valid"] is True

    def test_status_broken_symlink(self, tmp_path: Path) -> None:
        """Test status with broken symlink."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)
        source.rmdir()

        manager = VaultLinkManager(source, Path("docs"), tmp_path)
        status = manager.status()

        assert status["exists"] is True
        assert status["is_symlink"] is True
        assert status["target_exists"] is False
        assert status["is_valid"] is False
