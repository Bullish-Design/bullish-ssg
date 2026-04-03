"""Shared test fixtures and helpers."""

from pathlib import Path
import shutil

import pytest


FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"


def fixture_path(relative: str) -> Path:
    """Return absolute path to a fixture file or directory."""
    return FIXTURES_ROOT / relative


def copy_fixture_dir(relative: str, destination: Path) -> Path:
    """Copy a fixture directory to destination and return copied root path."""
    source = fixture_path(relative)
    target = destination / source.name
    shutil.copytree(source, target)
    return target


@pytest.fixture
def fixtures_root() -> Path:
    """Absolute path to fixture root."""
    return FIXTURES_ROOT


@pytest.fixture
def fixture_file() -> callable:
    """Factory fixture to resolve fixture file paths."""

    def _resolver(relative: str) -> Path:
        return fixture_path(relative)

    return _resolver


@pytest.fixture
def fixture_copy(tmp_path: Path) -> callable:
    """Factory fixture to copy fixture directories into temporary workspace."""

    def _copy(relative: str) -> Path:
        return copy_fixture_dir(relative, tmp_path)

    return _copy
