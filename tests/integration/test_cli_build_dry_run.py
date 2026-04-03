"""Integration tests for build and serve CLI commands using sample fixtures."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


@pytest.fixture
def healthy_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("build_cli/healthy")


@pytest.fixture
def missing_vault_workspace(fixture_copy: callable) -> Path:
    workspace = fixture_copy("build_cli/missing_vault")
    docs_dir = workspace / "docs"
    if docs_dir.exists():
        docs_dir.rmdir()
    return workspace


class TestBuildCommand:
    """Tests for build CLI command."""

    def test_build_no_config_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["build"], monkeypatch)

        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_build_dry_run_shows_command(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["build", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "kiln generate" in result.output
        assert "--source" in result.output
        assert "--output" in result.output

    def test_build_reports_failure_on_error(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["build"], monkeypatch)

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "not found" in result.output.lower()


class TestServeCommand:
    """Tests for serve CLI command."""

    def test_serve_no_config_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["serve"], monkeypatch)

        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_serve_dry_run_shows_command(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["serve", "--port", "3000", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert "kiln serve" in result.output
        assert "--port" in result.output
        assert "3000" in result.output

    def test_serve_requires_valid_vault(self, missing_vault_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(missing_vault_workspace, ["serve"], monkeypatch)

        assert result.exit_code == 1
        assert "vault resolution error" in result.output.lower()


class TestBuildCommandDryRun:
    """Tests specifically for build --dry-run behavior."""

    def test_dry_run_does_not_execute(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        output_dir = healthy_workspace / "site"
        assert not output_dir.exists()

        result = run_in_workspace(healthy_workspace, ["build", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert not output_dir.exists()

    def test_dry_run_includes_expected_args(self, healthy_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(healthy_workspace, ["build", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        output = result.output
        assert "kiln generate" in output
        assert "--source" in output
        assert "--output" in output
        assert "docs" in output
        assert "site" in output
