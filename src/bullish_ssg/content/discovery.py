"""Content discovery for indexing vault files."""

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterator, Sequence


@dataclass
class ContentFile:
    """Represents a discovered content file."""

    path: Path
    relative_path: Path
    extension: str


class ContentDiscovery:
    """Discovers content files in a vault directory."""

    DEFAULT_MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
    DEFAULT_ASSET_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".pdf",
        ".mp4",
        ".webm",
    }

    def __init__(
        self,
        vault_path: Path,
        ignore_patterns: Sequence[str] = (),
        include_markdown: bool = True,
        include_assets: bool = True,
    ) -> None:
        """Initialize discovery with vault path and options.

        Args:
            vault_path: Root directory to scan
            ignore_patterns: Glob patterns to exclude (e.g., ".obsidian/**")
            include_markdown: Whether to include markdown files
            include_assets: Whether to include asset files
        """
        self.vault_path = vault_path.resolve()
        self.ignore_patterns = list(ignore_patterns)
        self.include_markdown = include_markdown
        self.include_assets = include_assets

        # Build set of extensions to include
        self.extensions: set[str] = set()
        if include_markdown:
            self.extensions.update(self.DEFAULT_MARKDOWN_EXTENSIONS)
        if include_assets:
            self.extensions.update(self.DEFAULT_ASSET_EXTENSIONS)

    def discover(self) -> Iterator[ContentFile]:
        """Discover all content files matching criteria.

        Yields:
            ContentFile for each discovered file
        """
        if not self.vault_path.exists():
            return

        if not self.vault_path.is_dir():
            return

        for path in self.vault_path.rglob("*"):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            if not self._has_matching_extension(path):
                continue

            relative = path.relative_to(self.vault_path)
            yield ContentFile(
                path=path,
                relative_path=relative,
                extension=path.suffix.lower(),
            )

    def discover_markdown(self) -> Iterator[ContentFile]:
        """Discover only markdown files.

        Yields:
            ContentFile for each markdown file
        """
        if not self.vault_path.exists():
            return

        if not self.vault_path.is_dir():
            return

        for path in self.vault_path.rglob("*"):
            if not path.is_file():
                continue

            if self._should_ignore(path):
                continue

            if path.suffix.lower() not in self.DEFAULT_MARKDOWN_EXTENSIONS:
                continue

            relative = path.relative_to(self.vault_path)
            yield ContentFile(
                path=path,
                relative_path=relative,
                extension=path.suffix.lower(),
            )

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored based on patterns."""
        relative = path.relative_to(self.vault_path)
        relative_str = str(relative)

        for pattern in self.ignore_patterns:
            if fnmatch(relative_str, pattern):
                return True
            # Also check parent directories
            if "/" in pattern:
                parts = pattern.split("/")
                if len(parts) == 2 and parts[1] == "**":
                    # Pattern like ".obsidian/**" - check if any parent matches
                    if fnmatch(relative_str.split("/")[0], parts[0]):
                        return True

        return False

    def _has_matching_extension(self, path: Path) -> bool:
        """Check if file has a matching extension."""
        if not self.extensions:
            return True
        return path.suffix.lower() in self.extensions

    def count(self) -> int:
        """Return total count of discovered files."""
        return sum(1 for _ in self.discover())

    def count_markdown(self) -> int:
        """Return count of markdown files only."""
        return sum(1 for _ in self.discover_markdown())
