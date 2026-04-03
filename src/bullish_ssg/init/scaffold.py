"""Project scaffolding orchestration for `bullish-ssg init`."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bullish_ssg.init.patchers import (
    PatchChange,
    ensure_config_file,
    ensure_devenv,
    ensure_docs_index,
    ensure_gitignore,
    ensure_precommit,
)


@dataclass
class ScaffoldResult:
    """Scaffold execution result."""

    changed_files: list[Path] = field(default_factory=list)
    changes: list[PatchChange] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """Return True when any file was changed."""
        return bool(self.changed_files)


class ProjectScaffolder:
    """Apply idempotent project scaffolding patchers."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize scaffolder with repository root."""
        self.repo_root = repo_root

    def run(self, dry_run: bool = False) -> ScaffoldResult:
        """Run all scaffold patchers in stable order."""
        patchers = [
            ensure_config_file,
            ensure_gitignore,
            ensure_precommit,
            ensure_devenv,
            ensure_docs_index,
        ]

        changes: list[PatchChange] = []
        for patcher in patchers:
            changes.extend(patcher(self.repo_root, dry_run=dry_run))

        changed_files = sorted({change.path for change in changes})
        return ScaffoldResult(changed_files=changed_files, changes=changes)
