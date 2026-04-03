"""Vault path resolver for symlink and direct modes."""

from pathlib import Path
from typing import Optional

from bullish_ssg.config.schema import VaultConfig, VaultMode


class VaultResolutionError(Exception):
    """Raised when vault path cannot be resolved."""

    pass


class VaultResolver:
    """Resolves effective vault path from configuration."""

    def __init__(self, config: VaultConfig, repo_root: Optional[Path] = None) -> None:
        """Initialize resolver with config.

        Args:
            config: Vault configuration
            repo_root: Repository root path (defaults to cwd)
        """
        self.config = config
        self.repo_root = repo_root or Path.cwd()

    def resolve(self) -> Path:
        """Resolve the effective vault path.

        Returns:
            Absolute path to the effective vault directory

        Raises:
            VaultResolutionError: If path cannot be resolved
        """
        if self.config.mode == VaultMode.DIRECT:
            return self._resolve_direct()
        else:
            return self._resolve_symlink()

    def _resolve_direct(self) -> Path:
        """Resolve path in direct mode.

        In direct mode, the link_path is the vault directory itself.
        """
        vault_path = self._resolve_path(self.config.link_path)

        if not vault_path.exists():
            raise VaultResolutionError(
                f"Vault directory does not exist: {vault_path}\n  Create the directory or update config.vault.link_path"
            )

        if not vault_path.is_dir():
            raise VaultResolutionError(
                f"Vault path is not a directory: {vault_path}\n  Expected a directory containing markdown files"
            )

        return vault_path

    def _resolve_symlink(self) -> Path:
        """Resolve path in symlink mode.

        In symlink mode, the link_path should be a symlink pointing to source_path.
        """
        link_path = self._resolve_path(self.config.link_path)
        expected_source = self._resolve_path(self.config.source_path) if self.config.source_path is not None else None

        if expected_source is not None and not expected_source.exists():
            raise VaultResolutionError(
                f"Configured source_path does not exist: {expected_source}\n"
                "  Update config.vault.source_path or run link-vault with a valid target"
            )

        if not link_path.is_symlink():
            if link_path.exists():
                raise VaultResolutionError(
                    f"Expected symlink at {link_path}, but found {self._describe_path(link_path)}\n"
                    f"  Either remove this path or run link-vault with --force"
                )

            raise VaultResolutionError(
                f"Symlink does not exist: {link_path}\n"
                f"  Run: bullish-ssg link-vault {self.config.source_path}"
            )

        # Resolve the symlink target
        try:
            target = link_path.resolve()
        except (OSError, RuntimeError) as e:
            raise VaultResolutionError(f"Failed to resolve symlink target for {link_path}: {e}") from e

        if not target.exists():
            raise VaultResolutionError(
                f"Symlink target does not exist: {target}\n  Source: {link_path}\n  Run link-vault with --repair to fix"
            )

        if not target.is_dir():
            raise VaultResolutionError(
                f"Symlink target is not a directory: {target}\n  Expected a directory containing markdown files"
            )

        if expected_source is not None and target != expected_source.resolve():
            raise VaultResolutionError(
                f"Symlink target mismatch: {link_path}\n"
                f"  Expected: {expected_source.resolve()}\n"
                f"  Actual:   {target}\n"
                "  Run link-vault with --repair to update it"
            )

        return target

    def _resolve_path(self, path: Path) -> Path:
        """Resolve a path relative to repo root or absolute."""
        if path.is_absolute():
            return path
        # Use absolute() not resolve() to preserve symlinks
        return (self.repo_root / path).absolute()

    def _describe_path(self, path: Path) -> str:
        """Return a description of what exists at path."""
        if path.is_dir():
            return "a directory"
        elif path.is_file():
            return "a file"
        else:
            return "something unexpected"

    def check_health(self) -> tuple[bool, Optional[str]]:
        """Check if vault is healthy.

        Returns:
            Tuple of (is_healthy, message_if_not_healthy)
        """
        try:
            self.resolve()
            return True, None
        except VaultResolutionError as e:
            return False, str(e)


def resolve_vault_path(
    config: VaultConfig,
    repo_root: Optional[Path] = None,
) -> Path:
    """Convenience function to resolve vault path.

    Args:
        config: Vault configuration
        repo_root: Repository root path

    Returns:
        Absolute path to effective vault

    Raises:
        VaultResolutionError: If resolution fails
    """
    resolver = VaultResolver(config, repo_root)
    return resolver.resolve()
