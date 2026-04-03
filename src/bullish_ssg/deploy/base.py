"""Shared deployer protocol definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from bullish_ssg.render.kiln import CommandResult


class Deployer(Protocol):
    """Protocol for deployment adapters."""

    def deploy(self, site_dir: Path, dry_run: bool = False) -> CommandResult:
        """Deploy built site content."""

    def get_deploy_url(self) -> str:
        """Return the effective deploy URL or a user-facing fallback."""
