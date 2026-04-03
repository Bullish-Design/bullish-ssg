"""Tests for validation rules and commands."""

from pathlib import Path

import pytest

from bullish_ssg.validate.rules import (
    FrontmatterValidator,
    OrphanValidator,
    SymlinkValidator,
    ValidationDiagnostic,
    ValidationResult,
    ValidationRunner,
    WikilinkValidator,
)


class TestValidationDiagnostic:
    """Tests for ValidationDiagnostic."""

    def test_diagnostic_string_with_line(self) -> None:
        diag = ValidationDiagnostic(
            source_file=Path("/vault/page.md"),
            line_number=10,
            message="Broken link",
            severity="error",
            rule="test",
        )
        result = str(diag)
        assert "/vault/page.md:10:" in result
        assert "[error]" in result
        assert "Broken link" in result

    def test_diagnostic_string_without_line(self) -> None:
        diag = ValidationDiagnostic(
            source_file=Path("/vault/page.md"),
            line_number=None,
            message="Missing title",
            severity="warning",
            rule="test",
        )
        result = str(diag)
        assert "/vault/page.md:" in result
        assert "[warning]" in result
        assert "Missing title" in result

    def test_diagnostic_string_config_level(self) -> None:
        diag = ValidationDiagnostic(
            source_file=None,
            line_number=None,
            message="Config error",
            severity="error",
            rule="config",
        )
        result = str(diag)
        assert "config:" in result


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_empty_result(self) -> None:
        result = ValidationResult(passed=True)
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.info_count == 0

    def test_counts_mixed_severities(self) -> None:
        result = ValidationResult(
            passed=False,
            diagnostics=[
                ValidationDiagnostic(None, None, "Error 1", "error"),
                ValidationDiagnostic(None, None, "Error 2", "error"),
                ValidationDiagnostic(None, None, "Warning", "warning"),
                ValidationDiagnostic(None, None, "Info", "info"),
            ],
        )
        assert result.error_count == 2
        assert result.warning_count == 1
        assert result.info_count == 1


class TestFrontmatterValidator:
    """Tests for FrontmatterValidator."""

    def test_valid_frontmatter_passes(self, fixture_file: callable) -> None:
        vault_path = fixture_file("frontmatter")
        validator = FrontmatterValidator(vault_path)
        file_path = fixture_file("frontmatter/valid.md")

        diagnostics = list(validator.validate_file(file_path))

        assert len(diagnostics) == 0

    def test_no_frontmatter_warns_about_title(self, fixture_file: callable) -> None:
        vault_path = fixture_file("frontmatter")
        validator = FrontmatterValidator(vault_path)
        file_path = fixture_file("frontmatter/no_frontmatter.md")

        diagnostics = list(validator.validate_file(file_path))

        # Should warn about missing title
        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "warning"
        assert "title" in diagnostics[0].message.lower()

    def test_invalid_frontmatter_reports_error(self, fixture_file: callable) -> None:
        vault_path = fixture_file("frontmatter")
        validator = FrontmatterValidator(vault_path)
        file_path = fixture_file("frontmatter/invalid_yaml.md")

        diagnostics = list(validator.validate_file(file_path))

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "error"


class TestSymlinkValidator:
    """Tests for SymlinkValidator."""

    def test_non_symlink_mode_returns_empty(self, tmp_path: Path) -> None:
        from bullish_ssg.config.schema import VaultConfig

        config = VaultConfig(mode="direct")
        validator = SymlinkValidator(config)

        diagnostics = validator.validate()

        assert len(diagnostics) == 0

    def test_missing_symlink_path(self, tmp_path: Path) -> None:
        from bullish_ssg.config.schema import VaultConfig

        link_path = tmp_path / "missing_link"
        config = VaultConfig(mode="symlink", source_path=tmp_path / "source")
        config.link_path = link_path

        validator = SymlinkValidator(config)
        diagnostics = validator.validate()

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "error"
        assert "does not exist" in diagnostics[0].message

    def test_path_exists_but_not_symlink(self, tmp_path: Path) -> None:
        from bullish_ssg.config.schema import VaultConfig

        link_path = tmp_path / "docs"
        link_path.mkdir()
        config = VaultConfig(mode="symlink", source_path=tmp_path / "source")
        config.link_path = link_path

        validator = SymlinkValidator(config)
        diagnostics = validator.validate()

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "error"
        assert "not a symlink" in diagnostics[0].message.lower()

    def test_broken_symlink_detected(self, tmp_path: Path) -> None:
        from bullish_ssg.config.schema import VaultConfig

        link_path = tmp_path / "docs"
        target_path = tmp_path / "nonexistent_target"
        link_path.symlink_to(target_path)

        config = VaultConfig(mode="symlink", source_path=target_path)
        config.link_path = link_path

        validator = SymlinkValidator(config)
        diagnostics = validator.validate()

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "error"
        assert "broken symlink" in diagnostics[0].message.lower()


class TestOrphanValidator:
    """Tests for OrphanValidator."""

    def test_no_orphans_when_all_linked(self, tmp_path: Path) -> None:
        validator = OrphanValidator(tmp_path)
        all_pages = [Path("page1.md"), Path("page2.md")]
        linked_pages = {"page1", "page2"}

        diagnostics = validator.validate(all_pages, linked_pages)

        assert len(diagnostics) == 0

    def test_orphan_detected_when_no_links(self, tmp_path: Path) -> None:
        validator = OrphanValidator(tmp_path)
        all_pages = [Path("page1.md"), Path("orphan.md")]
        linked_pages = {"page1"}

        diagnostics = validator.validate(all_pages, linked_pages)

        assert len(diagnostics) == 1
        assert diagnostics[0].severity == "info"
        assert "orphan" in diagnostics[0].message.lower()

    def test_index_exempt_from_orphan_check(self, tmp_path: Path) -> None:
        validator = OrphanValidator(tmp_path)
        all_pages = [Path("index.md"), Path("page1.md")]
        linked_pages = {"page1"}  # index not linked

        diagnostics = validator.validate(all_pages, linked_pages)

        # index should not be reported as orphan
        assert len(diagnostics) == 0


class TestValidationRunner:
    """Tests for ValidationRunner."""

    def test_empty_vault_warning(self, tmp_path: Path) -> None:
        runner = ValidationRunner(tmp_path)
        result = runner.run_full_validation()

        assert result.passed is True  # Warning is not an error
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].severity == "warning"
        assert "No markdown files" in result.diagnostics[0].message

    def test_full_validation_with_content(self, fixture_file: callable) -> None:
        vault_path = fixture_file("wikilinks")
        runner = ValidationRunner(vault_path)
        result = runner.run_full_validation()

        # Should pass with warnings about missing titles
        assert result.passed is True
        assert result.stats["files_discovered"] > 0
        assert result.stats["files_checked"] > 0

    def test_symlink_check_in_direct_mode(self, fixture_file: callable) -> None:
        from bullish_ssg.config.schema import VaultConfig

        vault_path = fixture_file("wikilinks")
        config = VaultConfig(mode="direct")
        runner = ValidationRunner(vault_path, vault_config=config)
        result = runner.run_symlink_check()

        assert result.passed is True
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].severity == "info"

    def test_full_validation_include_orphans_reports_orphan(self, fixture_file: callable) -> None:
        vault_path = fixture_file("validation/orphan_case/docs")
        runner = ValidationRunner(vault_path)
        result = runner.run_full_validation(include_orphan_check=True)

        orphan_diags = [d for d in result.diagnostics if d.rule == "orphan.page"]
        assert len(orphan_diags) == 1
        assert orphan_diags[0].source_file == Path("orphan.md")
        assert result.stats["orphans_detected"] == 1


class TestWikilinkValidator:
    """Tests for WikilinkValidator."""

    def test_counts_total_links_including_valid_links(self, fixture_file: callable) -> None:
        vault_path = fixture_file("validation/healthy/docs")
        validator = WikilinkValidator(
            vault_path=vault_path,
            fail_on_broken=True,
            ignore_patterns=[".obsidian/**", "templates/**", "_drafts/**"],
        )
        result = validator.validate()

        assert result.passed is True
        assert "files_checked" in result.stats
        assert result.stats["files_checked"] == 3
        assert result.stats["total_links"] == 3
        assert result.stats["broken_links"] == 0

    def test_unpublished_target_link_warns_but_does_not_fail(self, fixture_file: callable) -> None:
        vault_path = fixture_file("validation/unpublished_target")
        validator = WikilinkValidator(
            vault_path=vault_path,
            fail_on_broken=True,
            ignore_patterns=[".obsidian/**", "templates/**", "_drafts/**"],
        )
        result = validator.validate()

        assert result.passed is True
        assert result.stats["total_links"] == 1
        assert result.stats["broken_links"] == 0
        assert any(
            d.severity == "warning" and "unpublished/excluded" in d.message
            for d in result.diagnostics
        )

    def test_empty_vault_fails(self, tmp_path: Path) -> None:
        validator = WikilinkValidator(vault_path=tmp_path)
        result = validator.validate()

        assert result.passed is False
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].severity == "error"
