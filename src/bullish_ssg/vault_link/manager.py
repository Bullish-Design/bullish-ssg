"""Vault symlink manager for creating and repairing symlinks."""

import os
from pathlib import Path
from typing import Optional


class SymlinkError(Exception):
    """Raised when symlink operation fails."""

    pass


class VaultLinkManager:
    """Manages vault symlinks on Linux."""

    def __init__(
        self,
        source_path: Path,
        link_path: Path,
        repo_root: Optional[Path] = None,
    ) -> None:
        """Initialize manager with paths.

        Args:
            source_path: Path to external vault (absolute or relative)
            link_path: Path where symlink should be created (relative to repo_root)
            repo_root: Repository root (defaults to cwd)
        """
        self.source_path = Path(source_path).expanduser().resolve()
        self.link_path = Path(link_path)
        self.repo_root = repo_root or Path.cwd()
        # Use absolute() not resolve() to preserve symlink path
        self.full_link_path = (self.repo_root / self.link_path).absolute()

    def create(self, force: bool = False) -> bool:
        """Create symlink from link_path to source_path.

        Args:
            force: If True, remove existing non-symlink at link_path

        Returns:
            True if created/modified, False if already correct

        Raises:
            SymlinkError: If operation fails or conflicts with existing content
        """
        # Validate source exists
        if not self.source_path.exists():
            raise SymlinkError(
                f"Source path does not exist: {self.source_path}\n  Provide a valid path to your Obsidian vault"
            )

        if not self.source_path.is_dir():
            raise SymlinkError(
                f"Source path is not a directory: {self.source_path}\n  Expected a directory containing markdown files"
            )

        # Check existing at link_path
        if self.full_link_path.exists() or self.full_link_path.is_symlink():
            return self._handle_existing(force)

        # Create parent directories if needed
        self._ensure_parent_exists()

        # Create the symlink (Linux uses relative symlinks for portability)
        try:
            relative_source = os.path.relpath(self.source_path, self.full_link_path.parent)
            os.symlink(relative_source, self.full_link_path)
            return True
        except OSError as e:
            raise SymlinkError(
                f"Failed to create symlink: {e}\n  Source: {self.source_path}\n  Link: {self.full_link_path}"
            ) from e

    def _handle_existing(self, force: bool) -> bool:
        """Handle existing path at link location.

        Args:
            force: Whether to force overwrite

        Returns:
            True if modified, False if already correct
        """
        if self.full_link_path.is_symlink():
            # Compare resolved targets (both normalized to absolute paths)
            current_target = self.full_link_path.resolve()
            expected_target = self.source_path.resolve()

            if current_target == expected_target:
                # Symlink already correct
                return False

            # Symlink exists but points elsewhere - update it
            self._remove_symlink()
            relative_source = os.path.relpath(self.source_path, self.full_link_path.parent)
            os.symlink(relative_source, self.full_link_path)
            return True

        # Not a symlink - check if force is enabled
        if not force:
            what = "directory" if self.full_link_path.is_dir() else "file"
            raise SymlinkError(
                f"Cannot create symlink: {self.full_link_path} already exists as {what}\n"
                f"  Remove it manually or use --force to overwrite"
            )

        # Force mode: remove and recreate
        self._remove_path(self.full_link_path)
        relative_source = os.path.relpath(self.source_path, self.full_link_path.parent)
        os.symlink(relative_source, self.full_link_path)
        return True

    def repair(self) -> bool:
        """Repair broken symlink or update incorrect target.

        Returns:
            True if repaired/updated, False if already correct

        Raises:
            SymlinkError: If source doesn't exist or link_path is not a symlink
        """
        # Validate source exists
        if not self.source_path.exists():
            raise SymlinkError(f"Cannot repair: source path does not exist: {self.source_path}")

        if not self.source_path.is_dir():
            raise SymlinkError(f"Cannot repair: source path is not a directory: {self.source_path}")

        if not self.full_link_path.is_symlink():
            if self.full_link_path.exists():
                raise SymlinkError(
                    f"Cannot repair: {self.full_link_path} is not a symlink\n  Use create() with --force to replace it"
                )
            # Link doesn't exist at all - create it
            return self.create()

        # Check if target is correct (compare resolved paths)
        current_target = self.full_link_path.resolve()
        expected_target = self.source_path.resolve()

        if current_target == expected_target:
            # Check if target exists
            if current_target.exists():
                return False  # Already correct and valid
            # Target missing - need to recreate

        # Update the symlink
        self._remove_symlink()
        relative_source = os.path.relpath(self.source_path, self.full_link_path.parent)
        os.symlink(relative_source, self.full_link_path)
        return True

    def remove(self) -> bool:
        """Remove the symlink.

        Returns:
            True if removed, False if didn't exist

        Raises:
            SymlinkError: If path exists but is not a symlink
        """
        if not self.full_link_path.exists() and not self.full_link_path.is_symlink():
            return False

        if not self.full_link_path.is_symlink():
            raise SymlinkError(
                f"Cannot remove: {self.full_link_path} is not a symlink\n"
                f"  Use your system's file management tools to remove it"
            )

        self._remove_symlink()
        return True

    def status(self) -> dict:
        """Get current status of the symlink.

        Returns:
            Dict with keys: exists, is_symlink, target, target_exists, is_valid
        """
        exists = self.full_link_path.exists() or self.full_link_path.is_symlink()
        is_symlink = self.full_link_path.is_symlink()

        result = {
            "exists": exists,
            "is_symlink": is_symlink,
            "link_path": self.full_link_path,
            "source_path": self.source_path,
            "target": None,
            "target_exists": False,
            "is_valid": False,
        }

        if is_symlink:
            try:
                result["target"] = self.full_link_path.readlink()
                resolved = self.full_link_path.resolve()
                result["target_exists"] = resolved.exists()
                result["is_valid"] = result["target_exists"] and resolved.is_dir()
            except (OSError, RuntimeError):
                pass

        return result

    def _ensure_parent_exists(self) -> None:
        """Ensure parent directory of link_path exists."""
        parent = self.full_link_path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    def _remove_symlink(self) -> None:
        """Remove symlink safely."""
        try:
            os.unlink(self.full_link_path)
        except OSError as e:
            raise SymlinkError(f"Failed to remove symlink: {e}") from e

    def _remove_path(self, path: Path) -> None:
        """Remove a file or directory (dangerous - use with care)."""
        if path.is_dir() and not path.is_symlink():
            import shutil

            shutil.rmtree(path)
        else:
            path.unlink()


def create_vault_link(
    source_path: Path,
    link_path: Path = Path("docs"),
    repo_root: Optional[Path] = None,
    force: bool = False,
) -> bool:
    """Convenience function to create vault symlink.

    Args:
        source_path: Path to external vault
        link_path: Where to create symlink (relative to repo_root)
        repo_root: Repository root
        force: Whether to overwrite existing content

    Returns:
        True if created/modified, False if already correct
    """
    manager = VaultLinkManager(source_path, link_path, repo_root)
    return manager.create(force=force)
