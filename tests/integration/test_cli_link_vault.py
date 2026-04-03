"""Integration tests for link-vault command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


@pytest.fixture
def source_vault(fixture_copy: callable) -> Path:
    return fixture_copy("vault/source_vault")


@pytest.fixture
def alt_vault(fixture_copy: callable) -> Path:
    return fixture_copy("vault/alt_vault")


class TestLinkVaultCommand:
    def test_creates_symlink_and_updates_config(
        self,
        tmp_path: Path,
        source_vault: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(tmp_path, ["link-vault", str(source_vault)], monkeypatch)

        assert result.exit_code == 0
        link = tmp_path / "docs"
        assert link.is_symlink()
        assert link.resolve() == source_vault.resolve()

        config = (tmp_path / "bullish-ssg.toml").read_text(encoding="utf-8")
        assert "[vault]" in config
        assert 'mode = "symlink"' in config
        assert f'source_path = "{source_vault.resolve()}"' in config
        assert 'link_path = "docs"' in config

    def test_second_run_is_idempotent(
        self,
        tmp_path: Path,
        source_vault: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = run_in_workspace(tmp_path, ["link-vault", str(source_vault)], monkeypatch)
        second = run_in_workspace(tmp_path, ["link-vault", str(source_vault)], monkeypatch)

        assert first.exit_code == 0
        assert second.exit_code == 0
        assert "already points" in second.output.lower() or "already linked" in second.output.lower()

    def test_changed_target_updates_symlink_in_repair_mode(
        self,
        tmp_path: Path,
        source_vault: Path,
        alt_vault: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        first = run_in_workspace(tmp_path, ["link-vault", str(source_vault)], monkeypatch)
        second = run_in_workspace(tmp_path, ["link-vault", str(alt_vault), "--repair"], monkeypatch)

        assert first.exit_code == 0
        assert second.exit_code == 0
        assert (tmp_path / "docs").resolve() == alt_vault.resolve()

    def test_conflict_with_existing_non_symlink_path_fails_safely(
        self,
        tmp_path: Path,
        source_vault: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "index.md").write_text("# Existing docs\n", encoding="utf-8")

        result = run_in_workspace(tmp_path, ["link-vault", str(source_vault)], monkeypatch)

        assert result.exit_code == 1
        assert "already exists" in result.output.lower()
        assert docs.is_dir()
        assert not docs.is_symlink()

    def test_force_replaces_existing_non_symlink_path(
        self,
        tmp_path: Path,
        source_vault: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        docs = tmp_path / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "index.md").write_text("# Existing docs\n", encoding="utf-8")

        result = run_in_workspace(tmp_path, ["link-vault", str(source_vault), "--force"], monkeypatch)

        assert result.exit_code == 0
        assert docs.is_symlink()
        assert docs.resolve() == source_vault.resolve()
