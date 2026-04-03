"""Tests for vault link resolver."""

from pathlib import Path

import pytest

from bullish_ssg.config.schema import VaultConfig, VaultMode
from bullish_ssg.vault_link.resolver import VaultResolutionError, VaultResolver, resolve_vault_path


class TestVaultResolverDirectMode:
    def test_direct_mode_with_existing_dir(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(mode=VaultMode.DIRECT, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        result = resolver.resolve()
        assert result == link

    def test_direct_mode_missing_dir_fails(self, tmp_path: Path) -> None:
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=Path("nonexistent"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "does not exist" in str(exc_info.value).lower()


class TestVaultResolverSymlinkMode:
    def test_symlink_mode_with_valid_link(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=source, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        result = resolver.resolve()
        assert result == source.resolve()

    def test_symlink_mode_missing_symlink_fails(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=source, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "symlink does not exist" in str(exc_info.value).lower()

    def test_symlink_mode_directory_instead_fails(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=source, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "expected symlink" in str(exc_info.value).lower()

    def test_symlink_mode_broken_link_fails(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)
        (source / "index.md").unlink()
        source.rmdir()

        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=source, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        message = str(exc_info.value).lower()
        assert "source_path does not exist" in message or "target does not exist" in message

    def test_symlink_mode_target_mismatch_fails(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        alt_source = fixture_copy("vault/alt_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=alt_source, link_path=Path("docs"))
        resolver = VaultResolver(config, tmp_path)

        with pytest.raises(VaultResolutionError) as exc_info:
            resolver.resolve()
        assert "target mismatch" in str(exc_info.value).lower()


class TestVaultResolverHealthCheck:
    def test_healthy_direct_mode(self, fixture_copy: callable) -> None:
        vault_dir = fixture_copy("vault/source_vault")
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_dir)
        resolver = VaultResolver(config, vault_dir.parent)

        is_healthy, message = resolver.check_health()
        assert is_healthy is True
        assert message is None

    def test_unhealthy_direct_mode(self, tmp_path: Path) -> None:
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=Path("missing"))
        resolver = VaultResolver(config, tmp_path)

        is_healthy, message = resolver.check_health()
        assert is_healthy is False
        assert message is not None


class TestResolveVaultPath:
    def test_resolves_direct_mode(self, fixture_copy: callable) -> None:
        vault_dir = fixture_copy("vault/source_vault")
        config = VaultConfig(mode=VaultMode.DIRECT, link_path=vault_dir)
        result = resolve_vault_path(config, vault_dir.parent)
        assert result == vault_dir.resolve()

    def test_resolves_symlink_mode(self, fixture_copy: callable, tmp_path: Path) -> None:
        source = fixture_copy("vault/source_vault")
        link = tmp_path / "docs"
        link.symlink_to(source)

        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=source, link_path=Path("docs"))
        result = resolve_vault_path(config, tmp_path)
        assert result == source.resolve()
