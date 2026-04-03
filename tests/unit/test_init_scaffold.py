"""Tests for init scaffolding and patchers."""

from pathlib import Path

from bullish_ssg.init.patchers import ensure_precommit
from bullish_ssg.init.scaffold import ProjectScaffolder


class TestProjectScaffolder:
    def test_init_on_empty_repo_creates_expected_files(self, tmp_path: Path) -> None:
        result = ProjectScaffolder(tmp_path).run(dry_run=False)

        assert result.changed_files
        assert (tmp_path / "bullish-ssg.toml").exists()
        assert (tmp_path / ".gitignore").exists()
        assert (tmp_path / ".pre-commit-config.yaml").exists()
        assert (tmp_path / "devenv.nix").exists()
        assert (tmp_path / "docs" / "index.md").exists()

        config_text = (tmp_path / "bullish-ssg.toml").read_text(encoding="utf-8")
        assert "[site]" in config_text
        assert "url = \"http://localhost:8000/\"" in config_text

    def test_init_merges_existing_repo_without_duplication(self, tmp_path: Path) -> None:
        (tmp_path / "bullish-ssg.toml").write_text(
            "[site]\nname='Example'\nurl='https://example.com/'\n",
            encoding="utf-8",
        )
        (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
        (tmp_path / "devenv.nix").write_text("{ pkgs, ... }: {\n}\n", encoding="utf-8")

        first = ProjectScaffolder(tmp_path).run(dry_run=False)
        second = ProjectScaffolder(tmp_path).run(dry_run=False)

        assert first.changed_files
        assert not second.changed_files

        gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert gitignore.count("site/") == 1

        precommit = (tmp_path / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        assert precommit.count("bullish-ssg-validate") == 1

        devenv = (tmp_path / "devenv.nix").read_text(encoding="utf-8")
        assert devenv.count("bullish-ssg:validate") == 1

    def test_init_dry_run_reports_changes_without_writing(self, tmp_path: Path) -> None:
        result = ProjectScaffolder(tmp_path).run(dry_run=True)

        assert result.changed_files
        assert not (tmp_path / "bullish-ssg.toml").exists()
        assert not (tmp_path / ".gitignore").exists()
        assert not (tmp_path / ".pre-commit-config.yaml").exists()
        assert not (tmp_path / "devenv.nix").exists()
        assert not (tmp_path / "docs").exists()

    def test_precommit_patcher_handles_file_without_repos_key(self, tmp_path: Path) -> None:
        precommit = tmp_path / ".pre-commit-config.yaml"
        precommit.write_text("default_stages: [pre-commit]\n", encoding="utf-8")

        changes = ensure_precommit(tmp_path, dry_run=False)

        assert changes
        contents = precommit.read_text(encoding="utf-8")
        assert "repos:" in contents
        assert "bullish-ssg-validate" in contents
