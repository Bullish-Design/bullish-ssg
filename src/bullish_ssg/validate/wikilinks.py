"""Wikilink parsing and resolution for Obsidian-style links."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class WikilinkDiagnostic:
    """Represents a wikilink diagnostic (error or warning)."""

    source_file: Path
    line_number: int
    raw_link: str
    reason: str
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        return f"{self.source_file}:{self.line_number}: [{self.severity}] {self.reason}"


@dataclass
class ParsedWikilink:
    """Represents a parsed wikilink."""

    raw: str
    page: str
    alias: Optional[str]
    heading: Optional[str]
    block_id: Optional[str]
    line_number: int

    @property
    def target(self) -> str:
        """Get the full target (page + heading/block)."""
        if self.heading:
            return f"{self.page}#{self.heading}"
        if self.block_id:
            return f"{self.page}#^{self.block_id}"
        return self.page


class WikilinkParser:
    """Parser for Obsidian-style wikilinks."""

    # Pattern: [[page]], [[page|alias]], [[page#heading]], [[page#^block-id]]
    # Groups: 1=page, 2=|display, 3=display, 4=#heading, 5=heading, 6=^block, 7=block-id
    WIKILINK_PATTERN = re.compile(
        r"\[\["
        r"([^\]|#]+)"  # Group 1: Page name
        r"(?:\|([^\]]+))?"  # Group 2-3: Optional alias after |
        r"(?:#(?!\^)([^\]]+))?"  # Group 4-5: Optional heading anchor
        r"(?:#\^([^\]]+))?"  # Group 6-7: Optional block reference
        r"\]\]"
    )

    def parse(self, content: str) -> Iterator[ParsedWikilink]:
        """Parse all wikilinks from content with line numbers."""
        lines = content.split("\n")

        for line_number, line in enumerate(lines, start=1):
            for match in self.WIKILINK_PATTERN.finditer(line):
                raw = match.group(0)
                page = match.group(1).strip()
                alias = match.group(2)
                heading = match.group(3)
                block_id = match.group(4)

                # Strip whitespace from components
                if alias:
                    alias = alias.strip()
                if heading:
                    heading = heading.strip()
                if block_id:
                    block_id = block_id.strip()

                yield ParsedWikilink(
                    raw=raw,
                    page=page,
                    alias=alias,
                    heading=heading,
                    block_id=block_id,
                    line_number=line_number,
                )

    def parse_file(self, file_path: Path) -> Iterator[ParsedWikilink]:
        """Parse wikilinks from a file."""
        content = file_path.read_text(encoding="utf-8")
        yield from self.parse(content)


class PageIndex:
    """Index of pages for wikilink resolution."""

    def __init__(self, vault_path: Path) -> None:
        """Initialize index with vault path.

        Args:
            vault_path: Root directory of the vault
        """
        self.vault_path = vault_path.resolve()
        self._slug_to_path: dict[str, Path] = {}
        self._path_to_slugs: dict[Path, list[str]] = {}

    def add_page(self, relative_path: Path, slugs: list[str]) -> None:
        """Add a page to the index.

        Args:
            relative_path: Relative path from vault root
            slugs: List of slugs that can resolve to this page
        """
        full_path = self.vault_path / relative_path
        self._path_to_slugs[relative_path] = slugs

        for slug in slugs:
            self._slug_to_path[slug] = relative_path

    def resolve_page(self, page_ref: str) -> Optional[Path]:
        """Resolve a page reference to a relative path.

        Args:
            page_ref: Page name or slug from wikilink

        Returns:
            Relative path if found, None otherwise
        """
        # Normalize the page ref
        normalized = self._normalize_page_ref(page_ref)

        # Direct match
        if normalized in self._slug_to_path:
            return self._slug_to_path[normalized]

        # Try matching just the filename stem
        stem = Path(normalized).stem if "/" in normalized else normalized
        if stem in self._slug_to_path:
            return self._slug_to_path[stem]

        return None

    def _normalize_page_ref(self, ref: str) -> str:
        """Normalize a page reference for matching."""
        # Remove extension if present
        if "." in ref:
            ref = ref.rsplit(".", 1)[0]
        # Convert spaces and underscores to hyphens, lowercase
        ref = ref.lower().replace(" ", "-").replace("_", "-")
        return ref

    def get_page_path(self, relative_path: Path) -> Path:
        """Get full path for a relative path."""
        return self.vault_path / relative_path


class HeadingExtractor:
    """Extracts headings from markdown content."""

    HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)(?:\s+#*)?$", re.MULTILINE)

    def extract(self, content: str) -> list[str]:
        """Extract all headings from markdown content."""
        headings = []
        for match in self.HEADING_PATTERN.finditer(content):
            heading = match.group(1).strip()
            headings.append(heading)
        return headings

    def extract_file(self, file_path: Path) -> list[str]:
        """Extract headings from a file."""
        content = file_path.read_text(encoding="utf-8")
        return self.extract(content)

    def normalize_heading(self, heading: str) -> str:
        """Normalize a heading for anchor matching.

        Converts to lowercase, removes special chars, replaces spaces with hyphens.
        """
        # Convert to lowercase
        normalized = heading.lower()
        # Remove special characters except alphanumeric and hyphens
        normalized = re.sub(r"[^a-z0-9\s-]", "", normalized)
        # Replace spaces and multiple hyphens with single hyphen
        normalized = re.sub(r"\s+", "-", normalized)
        normalized = re.sub(r"-+", "-", normalized)
        # Strip leading/trailing hyphens
        return normalized.strip("-")

    def has_heading(self, content: str, target_heading: str) -> bool:
        """Check if content contains a heading matching the target.

        Args:
            content: Markdown content to search
            target_heading: Target heading (normalized)

        Returns:
            True if matching heading found
        """
        headings = self.extract(content)
        normalized_target = self.normalize_heading(target_heading)

        for heading in headings:
            if self.normalize_heading(heading) == normalized_target:
                return True
        return False


class WikilinkResolver:
    """Resolves wikilinks and validates heading anchors."""

    def __init__(
        self,
        page_index: PageIndex,
        cache_content: bool = True,
    ) -> None:
        """Initialize resolver with page index.

        Args:
            page_index: Indexed pages for resolution
            cache_content: Whether to cache file contents for heading lookup
        """
        self.page_index = page_index
        self._cache_content = cache_content
        self._content_cache: dict[Path, str] = {}
        self._heading_extractor = HeadingExtractor()

    def _get_content(self, file_path: Path) -> str:
        """Get file content, with caching if enabled."""
        if self._cache_content:
            if file_path not in self._content_cache:
                self._content_cache[file_path] = file_path.read_text(encoding="utf-8")
            return self._content_cache[file_path]
        return file_path.read_text(encoding="utf-8")

    def resolve(
        self,
        wikilink: ParsedWikilink,
        source_file: Path,
    ) -> Optional[WikilinkDiagnostic]:
        """Resolve a single wikilink and return diagnostic if broken.

        Args:
            wikilink: The parsed wikilink
            source_file: File containing the link

        Returns:
            Diagnostic if link is broken, None if valid
        """
        # Try to resolve the page
        target_path = self.page_index.resolve_page(wikilink.page)

        if target_path is None:
            return WikilinkDiagnostic(
                source_file=source_file,
                line_number=wikilink.line_number,
                raw_link=wikilink.raw,
                reason=f"Page not found: '{wikilink.page}'",
                severity="error",
            )

        # Check heading anchor if present
        if wikilink.heading:
            full_path = self.page_index.get_page_path(target_path)
            try:
                content = self._get_content(full_path)
                if not self._heading_extractor.has_heading(content, wikilink.heading):
                    return WikilinkDiagnostic(
                        source_file=source_file,
                        line_number=wikilink.line_number,
                        raw_link=wikilink.raw,
                        reason=(f"Heading not found: '{wikilink.heading}' in page '{wikilink.page}'"),
                        severity="error",
                    )
            except (OSError, IOError):
                return WikilinkDiagnostic(
                    source_file=source_file,
                    line_number=wikilink.line_number,
                    raw_link=wikilink.raw,
                    reason=f"Could not read page: '{wikilink.page}'",
                    severity="error",
                )

        # Block references are warnings in v1
        if wikilink.block_id:
            return WikilinkDiagnostic(
                source_file=source_file,
                line_number=wikilink.line_number,
                raw_link=wikilink.raw,
                reason=(f"Block reference validation not implemented: '^{wikilink.block_id}'"),
                severity="warning",
            )

        return None

    def validate_file(self, file_path: Path) -> list[WikilinkDiagnostic]:
        """Validate all wikilinks in a file.

        Args:
            file_path: Path to the file to validate

        Returns:
            List of diagnostics for broken/warning links
        """
        diagnostics: list[WikilinkDiagnostic] = []
        parser = WikilinkParser()

        for wikilink in parser.parse_file(file_path):
            diagnostic = self.resolve(wikilink, file_path)
            if diagnostic:
                diagnostics.append(diagnostic)

        return diagnostics

    def validate_files(self, file_paths: list[Path]) -> list[WikilinkDiagnostic]:
        """Validate wikilinks in multiple files.

        Args:
            file_paths: List of paths to validate

        Returns:
            List of all diagnostics
        """
        all_diagnostics: list[WikilinkDiagnostic] = []

        for file_path in file_paths:
            diagnostics = self.validate_file(file_path)
            all_diagnostics.extend(diagnostics)

        return all_diagnostics


def build_page_index(
    vault_path: Path,
    content_files: list[Path],
    slug_extractor: callable = None,
) -> PageIndex:
    """Build a page index from discovered content files.

    Args:
        vault_path: Root of the vault
        content_files: List of relative paths to content files
        slug_extractor: Optional function to extract slugs from file path

    Returns:
        Populated PageIndex
    """
    index = PageIndex(vault_path)

    for relative_path in content_files:
        # Default slugs: filename stem, and full path stem
        slugs = [relative_path.stem]

        # Also add the relative path without extension
        path_str = str(relative_path.with_suffix(""))
        if path_str != relative_path.stem:
            slugs.append(path_str.replace("/", "-"))
            slugs.append(path_str)

        index.add_page(relative_path, slugs)

    return index
