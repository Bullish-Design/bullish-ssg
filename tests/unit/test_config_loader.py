"""Tests for configuration loader using fixture files."""

from pathlib import Path
from shutil import copy2
from unittest.mock import patch

import pytest

from bullish_ssg.config.loader import find_config_file, load_config
from bullish_ssg.config.schema import BullishConfig, VaultMode


def _copy_fixture_config(fixture_file: callable, filename: str, destination: Path) -> Path:
    source = fixture_file(f"config/{filename}")
    target = destination / source.name
    copy2(source, target)
    return target


class TestFindConfigFile:
    def test_finds_file_in_current_dir(self, tmp_path: Path, fixture_file: callable) -> None:
        config_file = _copy_fixture_config(fixture_file, "valid_minimal.toml", tmp_path)
        config_file.rename(tmp_path / "bullish-ssg.toml")

        with patch("bullish_ssg.config.loader.Path.cwd", return_value=tmp_path):
            result = find_config_file()
            assert result == tmp_path / "bullish-ssg.toml"

    def test_finds_file_walking_up(self, tmp_path: Path, fixture_file: callable) -> None:
        config_file = _copy_fixture_config(fixture_file, "valid_minimal.toml", tmp_path)
        config_file.rename(tmp_path / "bullish-ssg.toml")

        subdir = tmp_path / "sub" / "dir"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == tmp_path / "bullish-ssg.toml"

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        assert find_config_file(tmp_path) is None


class TestLoadConfig:
    def test_loads_valid_config(self, fixture_file: callable) -> None:
        config = load_config(fixture_file("config/valid_full.toml"))
        assert isinstance(config, BullishConfig)
        assert config.site.url == "https://example.com/"
        assert config.site.name == "Full Test Site"
        assert config.content.source_dir == Path("content")
        assert config.vault.mode == VaultMode.DIRECT

    def test_loads_symlink_config(self, fixture_file: callable) -> None:
        config = load_config(fixture_file("config/valid_symlink.toml"))
        assert config.vault.mode == VaultMode.SYMLINK
        assert config.vault.source_path == Path("/path/to/vault")
        assert config.vault.link_path == Path("docs")

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.toml")

    def test_raises_invalid_toml(self, fixture_file: callable) -> None:
        with pytest.raises(ValueError) as exc_info:
            load_config(fixture_file("config/invalid_toml.toml"))
        assert "invalid toml" in str(exc_info.value).lower()

    def test_raises_validation_error(self, fixture_file: callable) -> None:
        with pytest.raises(ValueError) as exc_info:
            load_config(fixture_file("config/invalid_url.toml"))
        assert "validation error" in str(exc_info.value).lower()

    def test_symlink_without_source_path_fails(self, fixture_file: callable) -> None:
        with pytest.raises(ValueError) as exc_info:
            load_config(fixture_file("config/symlink_missing_source.toml"))
        assert "source_path" in str(exc_info.value).lower()

    def test_invalid_mode_fails(self, fixture_file: callable) -> None:
        with pytest.raises(ValueError) as exc_info:
            load_config(fixture_file("config/invalid_mode.toml"))
        assert "validation error" in str(exc_info.value).lower()
