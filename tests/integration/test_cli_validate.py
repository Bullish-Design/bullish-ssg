"""Integration tests for validate/check-links CLI commands using sample fixtures."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    """Run CLI command from a copied fixture workspace."""
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


@pytest.fixture
def healthy_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("validation/healthy")


@pytest.fixture
def malformed_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("validation/malformed_frontmatter")


@pytest.fixture
def broken_links_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("validation/broken_links")


@pytest.fixture
def symlink_broken_workspace(fixture_copy: callable) -> Path:
    workspace = fixture_copy("validation/symlink_mode")
    (workspace / "vault-target").mkdir()
    docs_path = workspace / "docs"
    if docs_path.exists():
        docs_path.rmdir()
    docs_path.symlink_to(workspace / "missing-target")
    return workspace


@pytest.fixture
def orphan_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("validation/orphan_case")


@pytest.fixture
def unpublished_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("validation/unpublished_target")


class TestValidateCommand:
    """Tests for validate CLI command."""

    def test_validate_passes_on_healthy_fixture(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["validate"], monkeypatch)

        assert result.exit_code == 0
        assert "Summary:" in result.output or "Validation passed" in result.output

    def test_validate_fails_on_malformed_frontmatter(
        self,
        malformed_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(malformed_workspace, ["validate"], monkeypatch)

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "yaml" in result.output.lower()

    def test_validate_fails_on_broken_symlink(
        self,
        symlink_broken_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(symlink_broken_workspace, ["validate"], monkeypatch)

        assert result.exit_code == 1
        assert "symlink" in result.output.lower() or "vault resolution" in result.output.lower()

    def test_validate_no_config_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["validate"], monkeypatch)

        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_validate_summary_output(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["validate"], monkeypatch)

        assert result.exit_code == 0
        assert "files_checked" in result.output

    def test_validate_include_orphans_reports_orphans(
        self,
        orphan_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(orphan_workspace, ["validate", "--include-orphans"], monkeypatch)

        assert result.exit_code == 0
        assert "orphaned" in result.output.lower()


class TestCheckLinksCommand:
    """Tests for check-links CLI command."""

    def test_check_links_no_config_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["check-links"], monkeypatch)

        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_check_links_with_broken_links_fails(
        self,
        broken_links_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(broken_links_workspace, ["check-links"], monkeypatch)

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "broken" in result.output.lower()

    def test_check_links_exit_codes(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["check-links"], monkeypatch)

        assert result.exit_code == 0

    def test_check_links_unpublished_target_warns_but_passes(
        self,
        unpublished_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(unpublished_workspace, ["check-links"], monkeypatch)

        assert result.exit_code == 0
        assert "unpublished/excluded" in result.output.lower()


class TestValidationExitCodes:
    """Tests for CLI exit code policy."""

    def test_validate_exit_code_zero_on_success(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["validate"], monkeypatch)
        assert result.exit_code == 0

    def test_validate_exit_code_nonzero_on_failure(
        self,
        malformed_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(malformed_workspace, ["validate"], monkeypatch)
        assert result.exit_code != 0

    def test_check_links_exit_code_zero_when_no_broken(
        self,
        healthy_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(healthy_workspace, ["check-links"], monkeypatch)
        assert result.exit_code == 0
