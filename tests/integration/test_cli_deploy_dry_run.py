"""Integration tests for deploy CLI command using sample fixtures."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


@pytest.fixture
def gh_pages_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("deploy/gh_pages_dry_run")


@pytest.fixture
def branch_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("deploy/branch_dry_run")


@pytest.fixture
def preflight_fail_workspace(fixture_copy: callable) -> Path:
    workspace = fixture_copy("deploy/preflight_fail")
    docs_dir = workspace / "docs"
    if docs_dir.exists():
        docs_dir.rmdir()
    return workspace


class TestDeployCommand:
    def test_deploy_no_config_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["deploy", "--dry-run"], monkeypatch)

        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_deploy_gh_pages_dry_run_uses_gh_adapter(
        self,
        gh_pages_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(gh_pages_workspace, ["deploy", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "Preflight passed" in result.output
        assert "gh pages deploy" in result.output

    def test_deploy_branch_dry_run_uses_branch_adapter(
        self,
        branch_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(branch_workspace, ["deploy", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "Preflight passed" in result.output
        assert "git branch --list" in result.output

    def test_deploy_preflight_failure_blocks_deploy(
        self,
        preflight_fail_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(preflight_fail_workspace, ["deploy", "--dry-run"], monkeypatch)

        assert result.exit_code == 1
        assert "Preflight checks failed" in result.output
        assert "gh pages deploy" not in result.output

    def test_deploy_dry_run_does_not_require_kiln_binary(
        self,
        gh_pages_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(gh_pages_workspace, ["deploy", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "Command not found: kiln" not in result.output
