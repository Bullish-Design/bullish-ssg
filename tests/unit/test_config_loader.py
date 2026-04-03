"""Tests for configuration loader."""

from pathlib import Path
from unittest.mock import patch

import pytest

from bullish_ssg.config.loader import find_config_file, load_config
from bullish_ssg.config.schema import BullishConfig, SiteConfig, VaultMode


class TestFindConfigFile:
    """Tests for find_config_file function."""

    def test_finds_file_in_current_dir(self, tmp_path: Path) -> None:
        """Test finding config in current directory."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text('[site]\nurl = "https://test.com/"\ntitle = "Test"')

        with patch("bullish_ssg.config.loader.Path.cwd", return_value=tmp_path):
            result = find_config_file()
            assert result == config_file

    def test_finds_file_walking_up(self, tmp_path: Path) -> None:
        """Test finding config by walking up directory tree."""
        root = tmp_path
        config_file = root / "bullish-ssg.toml"
        config_file.write_text('[site]\nurl = "https://test.com/"\ntitle = "Test"')

        subdir = root / "sub" / "dir"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == config_file

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Test that None is returned when no config found."""
        result = find_config_file(tmp_path)
        assert result is None

    def test_prefers_bullish_ssg_toml(self, tmp_path: Path) -> None:
        """Test that bullish-ssg.toml is preferred over .config.toml."""
        config1 = tmp_path / "bullish-ssg.toml"
        config2 = tmp_path / "bullish-ssg.config.toml"
        config1.write_text('[site]\nurl = "https://test.com/"\ntitle = "Test"')
        config2.write_text('[site]\nurl = "https://test2.com/"\ntitle = "Test2"')

        with patch("bullish_ssg.config.loader.Path.cwd", return_value=tmp_path):
            result = find_config_file()
            assert result == config1


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid config file."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
url = "https://example.com/"
title = "Test Site"
description = "A test site"

[content]
source_dir = "content"

[vault]
mode = "direct"
""")

        config = load_config(config_file)
        assert isinstance(config, BullishConfig)
        assert config.site.url == "https://example.com/"
        assert config.site.title == "Test Site"
        assert config.content.source_dir == Path("content")
        assert config.vault.mode == VaultMode.DIRECT

    def test_loads_symlink_config(self, tmp_path: Path) -> None:
        """Test loading config with symlink mode."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
url = "https://example.com/"
title = "Test"

[vault]
mode = "symlink"
source_path = "/path/to/vault"
link_path = "docs"
""")

        config = load_config(config_file)
        assert config.vault.mode == VaultMode.SYMLINK
        assert config.vault.source_path == Path("/path/to/vault")
        assert config.vault.link_path == Path("docs")

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        nonexistent = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config(nonexistent)
        assert "not found" in str(exc_info.value).lower()

    def test_raises_invalid_toml(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for invalid TOML."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("[site\nurl = bad")

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)
        assert "Invalid TOML" in str(exc_info.value)

    def test_raises_validation_error(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for invalid config values."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
url = "not-a-url"
title = "Test"
""")

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)
        assert "validation error" in str(exc_info.value).lower()

    def test_symlink_without_source_path_fails(self, tmp_path: Path) -> None:
        """Test that symlink mode without source_path fails."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
url = "https://example.com/"
title = "Test"

[vault]
mode = "symlink"
""")

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)
        assert "source_path" in str(exc_info.value).lower()

    def test_invalid_mode_fails(self, tmp_path: Path) -> None:
        """Test that invalid vault mode fails."""
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
url = "https://example.com/"
title = "Test"

[vault]
mode = "invalid"
""")

        with pytest.raises(ValueError) as exc_info:
            load_config(config_file)
        assert "validation error" in str(exc_info.value).lower()
