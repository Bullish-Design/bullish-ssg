"""Integration tests for init command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


class TestInitCommand:
    def test_init_creates_scaffold_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["init"], monkeypatch)

        assert result.exit_code == 0
        assert (tmp_path / "bullish-ssg.toml").exists()
        assert (tmp_path / "docs" / "index.md").exists()
        assert "initialized" in result.output.lower()

    def test_init_dry_run_does_not_write(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        result = run_in_workspace(tmp_path, ["init", "--dry-run"], monkeypatch)

        assert result.exit_code == 0
        assert "[DRY RUN]" in result.output
        assert not (tmp_path / "bullish-ssg.toml").exists()

    def test_init_is_idempotent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        first = run_in_workspace(tmp_path, ["init"], monkeypatch)
        second = run_in_workspace(tmp_path, ["init"], monkeypatch)

        assert first.exit_code == 0
        assert second.exit_code == 0
        assert "No changes needed" in second.output
