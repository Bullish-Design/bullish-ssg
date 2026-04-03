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

    def test_valid_site_config(self) -> None:
        """Test that valid site config parses correctly."""
        config = SiteConfig(
            url="https://example.com/",
            title="Test Site",
        )
        assert config.url == "https://example.com/"
        assert config.title == "Test Site"

    def test_missing_scheme_fails(self) -> None:
        """Test that URL without scheme fails."""
        with pytest.raises(ValidationError) as exc_info:
            SiteConfig(url="example.com/", title="Test")
        assert "absolute" in str(exc_info.value).lower()

    def test_missing_trailing_slash_fails(self) -> None:
        """Test that URL without trailing slash fails."""
        with pytest.raises(ValidationError) as exc_info:
            SiteConfig(url="https://example.com", title="Test")
        assert "trailing slash" in str(exc_info.value).lower()

    def test_optional_fields(self) -> None:
        """Test that optional fields work."""
        config = SiteConfig(
            url="https://example.com/",
            title="Test",
            description="A test site",
            author="Test Author",
        )
        assert config.description == "A test site"
        assert config.author == "Test Author"


class TestVaultConfig:
    """Tests for VaultConfig validation."""

    def test_direct_mode_default(self) -> None:
        """Test that direct mode is default."""
        config = VaultConfig()
        assert config.mode == VaultMode.DIRECT

    def test_symlink_mode_requires_source_path(self) -> None:
        """Test that symlink mode requires source_path."""
        with pytest.raises(ValidationError) as exc_info:
            VaultConfig(mode=VaultMode.SYMLINK)
        assert "source_path" in str(exc_info.value).lower()

    def test_symlink_mode_with_source_path(self) -> None:
        """Test that symlink mode with source_path works."""
        config = VaultConfig(
            mode=VaultMode.SYMLINK,
            source_path=Path("/path/to/vault"),
        )
        assert config.mode == VaultMode.SYMLINK
        assert config.source_path == Path("/path/to/vault")

    def test_invalid_mode_fails(self) -> None:
        """Test that invalid mode fails."""
        with pytest.raises(ValidationError):
            VaultConfig(mode="invalid_mode")  # type: ignore[arg-type]


class TestContentConfig:
    """Tests for ContentConfig defaults."""

    def test_default_values(self) -> None:
        """Test that defaults are applied."""
        config = ContentConfig()
        assert config.source_dir == Path("docs")
        assert config.output_dir == Path("site")
        assert ".obsidian/**" in config.ignore_patterns
        assert "blog" in config.blog_dirs
        assert config.default_type == "page"


class TestValidationConfig:
    """Tests for ValidationConfig defaults."""

    def test_default_values(self) -> None:
        """Test that defaults are applied."""
        config = ValidationConfig()
        assert config.require_date_for_posts is True
        assert config.fail_on_broken_links is True
        assert config.check_heading_anchors is True


class TestDeployConfig:
    """Tests for DeployConfig defaults."""

    def test_default_values(self) -> None:
        """Test that defaults are applied."""
        config = DeployConfig()
        assert config.method == "gh-pages"
        assert config.site_dir == Path("site")
        assert config.branch == "gh-pages"


class TestHookConfig:
    """Tests for HookConfig defaults."""

    def test_default_values(self) -> None:
        """Test that all hooks default to None."""
        config = HookConfig()
        assert config.pre_build is None
        assert config.post_build is None
        assert config.pre_deploy is None
        assert config.post_deploy is None


class TestBullishConfig:
    """Tests for complete BullishConfig validation."""

    def test_minimal_config(self) -> None:
        """Test that minimal config (site only) works."""
        config = BullishConfig(site=SiteConfig(url="https://example.com/", title="Test"))
        assert config.site.url == "https://example.com/"
        assert isinstance(config.content, ContentConfig)
        assert isinstance(config.vault, VaultConfig)

    def test_full_config(self) -> None:
        """Test that full config parses correctly."""
        config = BullishConfig(
            site=SiteConfig(
                url="https://example.com/",
                title="Test Site",
                description="A test",
            ),
            content=ContentConfig(
                source_dir=Path("content"),
                output_dir=Path("public"),
            ),
            vault=VaultConfig(
                mode=VaultMode.SYMLINK,
                source_path=Path("/external/vault"),
            ),
            validation=ValidationConfig(
                fail_on_broken_links=False,
            ),
        )
        assert config.site.title == "Test Site"
        assert config.content.source_dir == Path("content")
        assert config.vault.mode == VaultMode.SYMLINK
        assert config.validation.fail_on_broken_links is False

    def test_missing_site_fails(self) -> None:
        """Test that missing site section fails."""
        with pytest.raises(ValidationError):
            BullishConfig()  # type: ignore[call-arg]
