"""Configuration update helpers."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w


def upsert_vault_symlink_settings(config_path: Path, source_path: Path, link_path: Path) -> bool:
    """Update vault settings for symlink mode.

    Returns True when file content changed.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    data: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    vault_data = data.get("vault")
    if not isinstance(vault_data, dict):
        vault_data = {}

    vault_data["mode"] = "symlink"
    vault_data["source_path"] = str(source_path.resolve())
    vault_data["link_path"] = str(link_path)
    data["vault"] = vault_data

    new_text = tomli_w.dumps(data)
    current_text = config_path.read_text(encoding="utf-8")
    if current_text == new_text:
        return False

    config_path.write_text(new_text, encoding="utf-8")
    return True
