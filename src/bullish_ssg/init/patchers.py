"""Patch helpers for repository scaffolding."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import toml

from bullish_ssg.init.templates import render_default_config, render_devenv_snippet, render_precommit_hook

DEFAULT_CONFIG: dict[str, Any] = toml.loads(render_default_config())

DEFAULT_DOCS_INDEX = "# Welcome\n\nThis site is managed by bullish-ssg.\n"

REQUIRED_GITIGNORE_LINES = [
    "site/",
]

DEFAULT_DEVENV = """\
{ pkgs, ... }:
{
  packages = [
    pkgs.git
    pkgs.uv
  ];
}
"""


@dataclass(frozen=True)
class PatchChange:
    """A single patch change description."""

    path: Path
    action: str
    detail: str


def ensure_config_file(repo_root: Path, dry_run: bool) -> list[PatchChange]:
    """Create or merge bullish config."""
    path = repo_root / "bullish-ssg.toml"
    if not path.exists():
        if not dry_run:
            path.write_text(toml.dumps(DEFAULT_CONFIG), encoding="utf-8")
        return [PatchChange(path=path, action="create", detail="Created default bullish-ssg.toml")]

    existing = toml.load(path)
    merged = _deep_merge(existing, DEFAULT_CONFIG)
    if merged == existing:
        return []

    if not dry_run:
        path.write_text(toml.dumps(merged), encoding="utf-8")
    return [PatchChange(path=path, action="update", detail="Merged missing default config keys")]


def ensure_gitignore(repo_root: Path, dry_run: bool) -> list[PatchChange]:
    """Ensure required ignore lines exist."""
    path = repo_root / ".gitignore"
    if not path.exists():
        body = "\n".join(REQUIRED_GITIGNORE_LINES) + "\n"
        if not dry_run:
            path.write_text(body, encoding="utf-8")
        return [PatchChange(path=path, action="create", detail="Created .gitignore entries for build output")]

    text = path.read_text(encoding="utf-8")
    missing = [line for line in REQUIRED_GITIGNORE_LINES if line not in text.splitlines()]
    if not missing:
        return []

    updated = text
    if not updated.endswith("\n"):
        updated += "\n"
    updated += "\n".join(missing) + "\n"
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return [PatchChange(path=path, action="update", detail=f"Added .gitignore entries: {', '.join(missing)}")]


def ensure_precommit(repo_root: Path, dry_run: bool) -> list[PatchChange]:
    """Ensure pre-commit local validation hook exists."""
    path = repo_root / ".pre-commit-config.yaml"
    hook_block = render_precommit_hook()
    if not path.exists():
        content = "repos:\n" + hook_block
        if not dry_run:
            path.write_text(content, encoding="utf-8")
        return [PatchChange(path=path, action="create", detail="Created pre-commit config with bullish-ssg hook")]

    text = path.read_text(encoding="utf-8")
    if "bullish-ssg-validate" in text:
        return []

    if "repos:" not in text:
        updated = "repos:\n" + PRECOMMIT_BLOCK
    else:
        updated = text
        if not updated.endswith("\n"):
            updated += "\n"
        updated += hook_block
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return [PatchChange(path=path, action="update", detail="Added bullish-ssg pre-commit hook")]


def ensure_devenv(repo_root: Path, dry_run: bool) -> list[PatchChange]:
    """Ensure devenv.nix has bullish-ssg helper task/script."""
    path = repo_root / "devenv.nix"
    if not path.exists():
        body = DEFAULT_DEVENV.rstrip() + "\n"
        body = _insert_devenv_block(body)
        if not dry_run:
            path.write_text(body, encoding="utf-8")
        return [PatchChange(path=path, action="create", detail="Created devenv.nix with bullish-ssg validation task")]

    text = path.read_text(encoding="utf-8")
    if "bullish-ssg:validate" in text:
        return []

    updated = _insert_devenv_block(text)
    if not dry_run:
        path.write_text(updated, encoding="utf-8")
    return [PatchChange(path=path, action="update", detail="Added bullish-ssg validation task to devenv.nix")]


def ensure_docs_index(repo_root: Path, dry_run: bool) -> list[PatchChange]:
    """Ensure starter docs/index.md exists."""
    path = repo_root / "docs" / "index.md"
    if path.exists():
        return []
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(DEFAULT_DOCS_INDEX, encoding="utf-8")
    return [PatchChange(path=path, action="create", detail="Created starter docs/index.md")]


def _insert_devenv_block(text: str) -> str:
    """Insert devenv snippet before final root brace."""
    devenv_block = render_devenv_snippet()
    marker = "# >>> bullish-ssg >>>"
    if marker in text:
        return text

    idx = text.rfind("}")
    if idx == -1:
        if text and not text.endswith("\n"):
            text += "\n"
        return text + devenv_block

    prefix = text[:idx]
    suffix = text[idx:]
    if not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + devenv_block + suffix


def _deep_merge(base: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Merge defaults into base without overriding existing values."""
    out = dict(base)
    for key, value in defaults.items():
        if key not in out:
            out[key] = value
            continue
        if isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
    return out
