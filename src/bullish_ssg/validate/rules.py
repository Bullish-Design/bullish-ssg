"""Validation rules for content and configuration."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

from bullish_ssg.config.schema import VaultConfig
from bullish_ssg.content.discovery import ContentDiscovery
from bullish_ssg.content.frontmatter import FrontmatterParseError, FrontmatterParser


@dataclass
class ValidationDiagnostic:
    """Represents a validation diagnostic."""

    source_file: Optional[Path]
    line_number: Optional[int]
    message: str
    severity: str = "error"  # "error", "warning", or "info"
    rule: str = ""

    def __str__(self) -> str:
        location = self.source_file or "config"
        if self.line_number:
            location = f"{location}:{self.line_number}"
        return f"{location}: [{self.severity}] {self.message}"


@dataclass
class ValidationResult:
    """Result of a validation run."""

    passed: bool
    diagnostics: list[ValidationDiagnostic] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "info")

    def print_summary(self) -> None:
        """Print human-readable summary."""
        if self.passed and not self.diagnostics:
            print("Validation passed with no issues.")
            if self.stats:
                for key, value in self.stats.items():
                    print(f"  {key}: {value}")
        else:
            for diag in self.diagnostics:
                print(str(diag))
            print(f"\nSummary: {self.error_count} errors, {self.warning_count} warnings, {self.info_count} info")
            if self.stats:
                for key, value in self.stats.items():
                    print(f"  {key}: {value}")


class FrontmatterValidator:
    """Validates frontmatter in content files."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.parser = FrontmatterParser(vault_path)

    def validate_file(self, file_path: Path) -> Iterator[ValidationDiagnostic]:
        """Validate frontmatter in a single file."""
        try:
            parsed = self.parser.parse(file_path)
            # Check for common issues
            if parsed.metadata.get("title") is None:
                yield ValidationDiagnostic(
                    source_file=file_path,
                    line_number=None,
                    message="Missing 'title' in frontmatter",
                    severity="warning",
                    rule="frontmatter.title",
                )
        except FrontmatterParseError as e:
            yield ValidationDiagnostic(
                source_file=file_path,
                line_number=None,
                message=str(e),
                severity="error",
                rule="frontmatter.parse",
            )

    def validate_files(self, file_paths: list[Path]) -> list[ValidationDiagnostic]:
        """Validate frontmatter in multiple files."""
        diagnostics = []
        for path in file_paths:
            diagnostics.extend(self.validate_file(path))
        return diagnostics


class SymlinkValidator:
    """Validates symlink health in symlink mode."""

    def __init__(self, vault_config: VaultConfig) -> None:
        self.vault_config = vault_config

    def validate(self) -> list[ValidationDiagnostic]:
        """Validate symlink if in symlink mode."""
        diagnostics = []

        if self.vault_config.mode != "symlink":
            return diagnostics

        link_path = self.vault_config.link_path

        # Check if path exists at all (symlinks can be broken)
        try:
            # Use lstat to check symlink itself without following
            link_path.lstat()
        except (OSError, FileNotFoundError):
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message=f"Symlink path does not exist: {link_path}",
                    severity="error",
                    rule="symlink.exists",
                )
            )
            return diagnostics

        if not link_path.is_symlink():
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message=f"Path exists but is not a symlink: {link_path}",
                    severity="error",
                    rule="symlink.type",
                )
            )
            return diagnostics

        # Try to resolve the symlink target
        try:
            # Read the symlink target without resolving
            target = link_path.readlink()
            # Check if target exists
            resolved = link_path.resolve()
            if not resolved.exists():
                diagnostics.append(
                    ValidationDiagnostic(
                        source_file=None,
                        line_number=None,
                        message=f"Broken symlink: {link_path} -> {target}",
                        severity="error",
                        rule="symlink.target",
                    )
                )
        except (OSError, RuntimeError) as e:
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message=f"Cannot resolve symlink {link_path}: {e}",
                    severity="error",
                    rule="symlink.resolve",
                )
            )

        return diagnostics


class OrphanValidator:
    """Checks for orphaned pages (no incoming links)."""

    def __init__(self, vault_path: Path, required_slugs: Optional[set[str]] = None) -> None:
        self.vault_path = vault_path
        self.required_slugs = required_slugs or {"index"}

    def validate(
        self,
        all_pages: list[Path],
        linked_pages: set[str],
    ) -> list[ValidationDiagnostic]:
        """Check for orphaned pages.

        Args:
            all_pages: List of all page paths
            linked_pages: Set of page slugs that are linked

        Returns:
            List of diagnostics for orphaned pages
        """
        diagnostics = []
        all_slugs = {p.stem for p in all_pages}

        # Required pages are exempt from orphan check
        check_slugs = all_slugs - self.required_slugs

        for slug in check_slugs:
            if slug not in linked_pages:
                # Find the file for this slug
                page = next((p for p in all_pages if p.stem == slug), None)
                if page:
                    diagnostics.append(
                        ValidationDiagnostic(
                            source_file=page,
                            line_number=None,
                            message=f"Page has no incoming links (orphaned)",
                            severity="info",
                            rule="orphan.page",
                        )
                    )

        return diagnostics


class ValidationRunner:
    """Runs all validation rules."""

    def __init__(
        self,
        vault_path: Path,
        vault_config: Optional[VaultConfig] = None,
        ignore_patterns: Optional[list[str]] = None,
    ) -> None:
        self.vault_path = vault_path
        self.vault_config = vault_config
        self.ignore_patterns = ignore_patterns or []

    def run_full_validation(
        self,
        include_orphan_check: bool = False,
    ) -> ValidationResult:
        """Run full validation suite.

        Args:
            include_orphan_check: Whether to check for orphaned pages

        Returns:
            ValidationResult with all diagnostics
        """
        diagnostics: list[ValidationDiagnostic] = []
        stats: dict[str, Any] = {}

        # Discover content
        discovery = ContentDiscovery(
            self.vault_path,
            ignore_patterns=self.ignore_patterns,
        )
        content_files = list(discovery.discover_markdown())
        stats["files_discovered"] = len(content_files)

        if not content_files:
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message=f"No markdown files found in vault: {self.vault_path}",
                    severity="warning",
                    rule="discovery.empty",
                )
            )

        # Validate frontmatter
        frontmatter_validator = FrontmatterValidator(self.vault_path)
        file_paths = [cf.path for cf in content_files]
        fm_diagnostics = frontmatter_validator.validate_files(file_paths)
        diagnostics.extend(fm_diagnostics)
        stats["files_checked"] = len(file_paths)

        # Validate symlink if in symlink mode
        if self.vault_config and self.vault_config.mode == "symlink":
            symlink_validator = SymlinkValidator(self.vault_config)
            symlink_diagnostics = symlink_validator.validate()
            diagnostics.extend(symlink_diagnostics)

        # Orphan check
        if include_orphan_check and content_files:
            orphan_diagnostics = self._run_orphan_check(content_files)
            diagnostics.extend(orphan_diagnostics)
            stats["orphans_detected"] = sum(1 for d in orphan_diagnostics if d.rule == "orphan.page")

        errors = [d for d in diagnostics if d.severity == "error"]

        return ValidationResult(
            passed=len(errors) == 0,
            diagnostics=diagnostics,
            stats=stats,
        )

    def _run_orphan_check(self, content_files: list[Any]) -> list[ValidationDiagnostic]:
        """Run orphan detection among publishable pages."""
        file_paths = [cf.path for cf in content_files]
        relative_paths = [cf.relative_path for cf in content_files]
        page_index = build_page_index(self.vault_path, relative_paths)
        parser = WikilinkParser()
        frontmatter_parser = FrontmatterParser(self.vault_path)

        publishable_pages: set[Path] = set()
        for file_path in file_paths:
            parsed = frontmatter_parser.parse_safe(file_path, default_metadata={})
            relative = file_path.relative_to(self.vault_path)
            if _is_publishable(parsed.metadata):
                publishable_pages.add(relative)

        linked_pages: set[str] = set()
        for file_path in file_paths:
            source_rel = file_path.relative_to(self.vault_path)
            if source_rel not in publishable_pages:
                continue
            for wikilink in parser.parse_file(file_path):
                resolved = page_index.resolve_page(wikilink.page)
                if resolved is None or resolved not in publishable_pages:
                    continue
                linked_pages.add(resolved.stem)

        orphan_validator = OrphanValidator(self.vault_path)
        return orphan_validator.validate(sorted(publishable_pages), linked_pages)

    def run_symlink_check(self) -> ValidationResult:
        """Run symlink health check only.

        Returns:
            ValidationResult with symlink diagnostics
        """
        diagnostics: list[ValidationDiagnostic] = []

        if not self.vault_config:
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message="No vault configuration available",
                    severity="error",
                    rule="config.missing",
                )
            )
            return ValidationResult(passed=False, diagnostics=diagnostics)

        if self.vault_config.mode != "symlink":
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message="Symlink check only applicable in symlink mode",
                    severity="info",
                    rule="symlink.mode",
                )
            )
            return ValidationResult(passed=True, diagnostics=diagnostics)

        symlink_validator = SymlinkValidator(self.vault_config)
        diagnostics = symlink_validator.validate()
        errors = [d for d in diagnostics if d.severity == "error"]

        return ValidationResult(
            passed=len(errors) == 0,
            diagnostics=diagnostics,
        )


# Import here to avoid circular imports
from bullish_ssg.validate.wikilinks import (
    WikilinkParser,
    WikilinkResolver,
    build_page_index,
    normalize_page_ref,
)


class WikilinkValidator:
    """Validates wikilinks across the vault."""

    def __init__(
        self,
        vault_path: Path,
        fail_on_broken: bool = True,
        ignore_patterns: Optional[list[str]] = None,
    ) -> None:
        self.vault_path = vault_path
        self.fail_on_broken = fail_on_broken
        self.ignore_patterns = ignore_patterns or []

    def validate(self) -> ValidationResult:
        """Run wikilink validation across all markdown files.

        Returns:
            ValidationResult with all link diagnostics
        """
        diagnostics: list[ValidationDiagnostic] = []
        stats: dict[str, Any] = {}

        # Discover content
        discovery = ContentDiscovery(
            self.vault_path,
            ignore_patterns=self.ignore_patterns,
        )
        content_files = sorted(discovery.discover_markdown(), key=lambda cf: str(cf.relative_path))
        stats["files_checked"] = len(content_files)

        if not content_files:
            diagnostics.append(
                ValidationDiagnostic(
                    source_file=None,
                    line_number=None,
                    message=f"No markdown files found in vault: {self.vault_path}",
                    severity="error",
                    rule="discovery.empty",
                )
            )
            return ValidationResult(passed=False, diagnostics=diagnostics)

        # Build page index
        relative_paths = [cf.relative_path for cf in content_files]
        page_index = build_page_index(self.vault_path, relative_paths)
        unpublished_refs = self._collect_unpublished_refs(content_files)

        # Validate links
        resolver = WikilinkResolver(
            page_index,
            unpublished_refs=unpublished_refs,
            unpublished_policy="warning",
        )
        parser = WikilinkParser()
        total_links = 0
        broken_links = 0

        for content_file in content_files:
            parsed_links = list(parser.parse_file(content_file.path))
            total_links += len(parsed_links)
            for link in parsed_links:
                diag = resolver.resolve(link, content_file.path)
                if diag is None:
                    continue
                if diag.severity == "error":
                    broken_links += 1
                diagnostics.append(
                    ValidationDiagnostic(
                        source_file=diag.source_file,
                        line_number=diag.line_number,
                        message=f"{diag.raw_link}: {diag.reason}",
                        severity=diag.severity,
                        rule="wikilink.resolve",
                    )
                )

        stats["total_links"] = total_links
        stats["broken_links"] = broken_links
        stats["files_with_issues"] = len({d.source_file for d in diagnostics if d.source_file is not None})

        errors = [d for d in diagnostics if d.severity == "error"]
        passed = len(errors) == 0 or not self.fail_on_broken

        return ValidationResult(
            passed=passed,
            diagnostics=diagnostics,
            stats=stats,
        )

    def _collect_unpublished_refs(self, included_files: list[Any]) -> set[str]:
        """Collect normalized refs for excluded or unpublished markdown pages."""
        included_relative = {cf.relative_path for cf in included_files}
        all_discovery = ContentDiscovery(self.vault_path, ignore_patterns=[])
        all_files = sorted(all_discovery.discover_markdown(), key=lambda cf: str(cf.relative_path))
        frontmatter_parser = FrontmatterParser(self.vault_path)

        unpublished_refs: set[str] = set()
        for content_file in all_files:
            parsed = frontmatter_parser.parse_safe(content_file.path, default_metadata={})
            is_excluded = content_file.relative_path not in included_relative
            if not is_excluded and _is_publishable(parsed.metadata):
                continue

            relative_no_suffix = content_file.relative_path.with_suffix("")
            candidates = [
                content_file.relative_path.stem,
                str(relative_no_suffix),
                str(relative_no_suffix).replace("/", "-"),
            ]
            for candidate in candidates:
                unpublished_refs.add(normalize_page_ref(candidate))

        return unpublished_refs


def _is_publishable(metadata: dict[str, Any]) -> bool:
    """Return True when metadata marks a page as publishable."""
    if bool(metadata.get("draft", False)):
        return False
    if metadata.get("published") is False:
        return False
    return True
