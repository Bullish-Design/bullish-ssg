"""Tests for vault link resolver."""

from pathlib import Path

import pytest

from bullish_ssg.config.schema import VaultConfig, VaultMode
from bullish_ssg.vault_link.resolver import (
    VaultResolutionError,
    VaultResolver,
    resolve_vault_path,
)


class TestVaultResolverDirectMode:
    """Tests for direct mode resolution."""

    def test_direct_mode_with_existing_dir(self, tmp_path: Path) -> None:
        """Test direct mode with existing directory."""
        vault_dir = tmp_path / "docs"
        vault_dir.mkdir()

        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_dir)
        resolver = VaultResolver(config, tmp_path)

        result = resolver.resolve()
        assert result == vault_dir.resolve()

    def test_direct_mode_missing_dir_fails(self, tmp_path: Path) -> None:
        """Test that missing directory fails in direct mode."""
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=Path("nonexistent"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "does not exist" in str(exc_info.value).lower()

    def test_direct_mode_file_fails(self, tmp_path: Path) -> None:
        """Test that file instead of directory fails."""
        vault_file = tmp_path / "docs"
        vault_file.write_text("not a dir")

        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_file)
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "not a directory" in str(exc_info.value).lower()


class TestVaultResolverSymlinkMode:
    """Tests for symlink mode resolution."""

    def test_symlink_mode_with_valid_link(self, tmp_path: Path) -> None:
        """Test symlink mode with valid symlink."""
        source = tmp_path / "external_vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=source,
            link_path=link.relative_to(tmp_path),
        )
        resolver = VaultResolver(config, tmp_path)

        result = resolver.resolve()
        assert result == source.resolve()

    def test_symlink_mode_missing_symlink_fails(self, tmp_path: Path) -> None:
        """Test that missing symlink fails."""
        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=Path("/some/path"),
            link_path=Path("docs"),
        )
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "does not exist" in str(exc_info.value).lower()

    def test_symlink_mode_directory_instead_fails(self, tmp_path: Path) -> None:
        """Test that directory instead of symlink fails."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=Path("/some/path"),
            link_path=Path("docs"),
        )
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "expected symlink" in str(exc_info.value).lower()

    def test_symlink_mode_broken_link_fails(self, tmp_path: Path) -> None:
        """Test that broken symlink fails."""
        source = tmp_path / "external_vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        # Remove source to break symlink
        source.rmdir()

        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=Path("/some/other/path"),
            link_path=Path("docs"),
        )
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "target does not exist" in str(exc_info.value).lower()


class TestVaultResolverHealthCheck:
    """Tests for health check functionality."""

    def test_healthy_direct_mode(self, tmp_path: Path) -> None:
        """Test health check passes for valid direct mode."""
        vault_dir = tmp_path / "docs"
        vault_dir.mkdir()

        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_dir)
        resolver = VaultResolver(config, tmp_path)

        is_healthy, message = resolver.check_health()
        assert is_healthy is True
        assert message is None

    def test_unhealthy_direct_mode(self, tmp_path: Path) -> None:
        """Test health check fails for invalid direct mode."""
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=Path("missing"))
        resolver = VaultResolver(config, tmp_path)

        is_healthy, message = resolver.check_health()
        assert is_healthy is False
        assert message is not None
        assert "does not exist" in message.lower()


class TestResolveVaultPath:
    """Tests for resolve_vault_path convenience function."""

    def test_resolves_direct_mode(self, tmp_path: Path) -> None:
        """Test convenience function with direct mode."""
        vault_dir = tmp_path / "docs"
        vault_dir.mkdir()

        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_dir)
        result = resolve_vault_path(config, tmp_path)

        assert result == vault_dir.resolve()

    def test_resolves_symlink_mode(self, tmp_path: Path) -> None:
        """Test convenience function with symlink mode."""
        source = tmp_path / "vault"
        source.mkdir()
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=source,
            link_path=Path("docs"),
        )
        result = resolve_vault_path(config, tmp_path)

        assert result == source.resolve()
