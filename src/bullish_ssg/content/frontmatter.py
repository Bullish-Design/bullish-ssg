"""Frontmatter parsing for markdown files."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import frontmatter
import yaml


class FrontmatterParseError(Exception):
    """Raised when frontmatter parsing fails."""

    pass


@dataclass
class ParsedContent:
    """Represents parsed markdown content with frontmatter."""

    path: Path
    relative_path: Path
    metadata: dict[str, Any]
    content: str
    raw_frontmatter: Optional[str] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a metadata value by key."""
        return self.metadata.get(key, default)

    @property
    def title(self) -> Optional[str]:
        """Get title from metadata."""
        return self.metadata.get("title")

    @property
    def slug(self) -> Optional[str]:
        """Get slug from metadata."""
        return self.metadata.get("slug")

    @property
    def date(self) -> Optional[str]:
        """Get date from metadata."""
        return self.metadata.get("date")

    @property
    def content_type(self) -> Optional[str]:
        """Get content type from metadata."""
        return self.metadata.get("type")


class FrontmatterParser:
    """Parses frontmatter from markdown files."""

    def __init__(self, vault_path: Path) -> None:
        """Initialize parser with vault path.

        Args:
            vault_path: Root directory of the vault
        """
        self.vault_path = vault_path.resolve()

    def parse(self, file_path: Path) -> ParsedContent:
        """Parse frontmatter from a file.

        Args:
            file_path: Path to the markdown file

        Returns:
            ParsedContent with metadata and body

        Raises:
            FrontmatterParseError: If parsing fails
        """
        file_path = file_path.resolve()

        if not file_path.exists():
            raise FrontmatterParseError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise FrontmatterParseError(f"Not a file: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                post = frontmatter.load(f)
        except yaml.YAMLError as e:
            raise FrontmatterParseError(f"Invalid YAML in frontmatter of {file_path}: {e}") from e
        except Exception as e:
            raise FrontmatterParseError(f"Failed to parse frontmatter in {file_path}: {e}") from e

        relative = file_path.relative_to(self.vault_path)

        return ParsedContent(
            path=file_path,
            relative_path=relative,
            metadata=dict(post.metadata),
            content=post.content,
            raw_frontmatter=post.metadata.get("_frontmatter"),
        )

    def parse_safe(self, file_path: Path, default_metadata: Optional[dict[str, Any]] = None) -> ParsedContent:
        """Parse frontmatter with safe defaults.

        Args:
            file_path: Path to the markdown file
            default_metadata: Default values for missing metadata

        Returns:
            ParsedContent with metadata (empty dict on failure)
        """
        try:
            return self.parse(file_path)
        except FrontmatterParseError:
            relative = (
                file_path.relative_to(self.vault_path) if self._is_under_vault(file_path) else Path(file_path.name)
            )
            return ParsedContent(
                path=file_path,
                relative_path=relative,
                metadata=default_metadata or {},
                content="",
            )

    def parse_batch(self, file_paths: list[Path]) -> tuple[list[ParsedContent], list[tuple[Path, str]]]:
        """Parse multiple files, collecting successes and failures.

        Args:
            file_paths: List of paths to parse

        Returns:
            Tuple of (successful_parses, failures)
            where failures is list of (path, error_message)
        """
        successes: list[ParsedContent] = []
        failures: list[tuple[Path, str]] = []

        for path in file_paths:
            try:
                parsed = self.parse(path)
                successes.append(parsed)
            except FrontmatterParseError as e:
                failures.append((path, str(e)))

        return successes, failures

    def _is_under_vault(self, path: Path) -> bool:
        """Check if path is under vault path."""
        try:
            path.relative_to(self.vault_path)
            return True
        except ValueError:
            return False


def parse_frontmatter(file_path: Path, vault_path: Optional[Path] = None) -> ParsedContent:
    """Convenience function to parse a single file.

    Args:
        file_path: Path to the markdown file
        vault_path: Optional vault root for relative path calculation

    Returns:
        ParsedContent with metadata and body
    """
    parser = FrontmatterParser(vault_path or file_path.parent)
    return parser.parse(file_path)
