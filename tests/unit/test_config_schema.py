"""Tests for configuration schema validation."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from bullish_ssg.config.schema import (
    BullishConfig,
    ContentConfig,
    DeployConfig,
    HookConfig,
    SiteConfig,
    ValidationConfig,
    VaultConfig,
    VaultMode,
)


class TestSiteConfig:
    """Tests for SiteConfig validation."""

    def test_valid_site_config_with_name(self) -> None:
        config = SiteConfig(url="https://example.com/", name="Test Site")
        assert config.url == "https://example.com/"
        assert config.name == "Test Site"
        assert config.title == "Test Site"

    def test_title_alias_supported(self) -> None:
        config = SiteConfig.model_validate({"url": "https://example.com/", "title": "Alias Title"})
        assert config.name == "Alias Title"
        assert config.title == "Alias Title"

    def test_missing_scheme_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SiteConfig(url="example.com/", name="Test")
        assert "absolute" in str(exc_info.value).lower()

    def test_missing_trailing_slash_fails(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SiteConfig(url="https://example.com", name="Test")
        assert "trailing slash" in str(exc_info.value).lower()


class TestVaultConfig:
    """Tests for VaultConfig validation."""

    def test_direct_mode_default(self) -> None:
        config = VaultConfig()
        assert config.mode == VaultMode.DIRECT

    def test_symlink_mode_requires_source_path(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            VaultConfig(mode=VaultMode.SYMLINK)
        assert "source_path" in str(exc_info.value).lower()

    def test_symlink_mode_with_source_path(self) -> None:
        config = VaultConfig(mode=VaultMode.SYMLINK, source_path=Path("/path/to/vault"))
        assert config.mode == VaultMode.SYMLINK
        assert config.source_path == Path("/path/to/vault")


class TestContentConfig:
    """Tests for ContentConfig defaults and aliases."""

    def test_default_values(self) -> None:
        config = ContentConfig()
        assert config.source_dir == Path("docs")
        assert config.output_dir == Path("site")
        assert ".obsidian/**" in config.ignore_patterns
        assert "blog" in config.blog_dirs
        assert config.default_type == "doc"

    def test_aliases_supported(self) -> None:
        config = ContentConfig.model_validate({"vault_dir": "vault", "site_dir": "public"})
        assert config.source_dir == Path("vault")
        assert config.output_dir == Path("public")


class TestValidationConfig:
    def test_default_values(self) -> None:
        config = ValidationConfig()
        assert config.require_date_for_posts is True
        assert config.fail_on_broken_links is True
        assert config.check_heading_anchors is True


class TestDeployConfig:
    def test_default_values(self) -> None:
        config = DeployConfig()
        assert config.method == "gh-pages"
        assert config.site_dir == Path("site")
        assert config.branch == "main"
        assert config.pages_branch == "gh-pages"


class TestHookConfig:
    def test_default_values(self) -> None:
        config = HookConfig()
        assert config.pre_build is None
        assert config.post_build is None
        assert config.pre_deploy is None
        assert config.post_deploy is None


class TestBullishConfig:
    def test_minimal_config(self) -> None:
        config = BullishConfig(site=SiteConfig(url="https://example.com/", name="Test"))
        assert config.site.url == "https://example.com/"
        assert isinstance(config.content, ContentConfig)
        assert isinstance(config.vault, VaultConfig)

    def test_missing_site_fails(self) -> None:
        with pytest.raises(ValidationError):
            BullishConfig()  # type: ignore[call-arg]
