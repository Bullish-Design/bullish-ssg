"""Snapshot-style tests for init template rendering."""

import pytest

from bullish_ssg.init.templates import (
    render_default_config,
    render_devenv_snippet,
    render_github_pages_workflow,
    render_precommit_hook,
)


def _fixture_text(fixture_file: callable, relative: str) -> str:
    return fixture_file(relative).read_text(encoding="utf-8")


class TestInitTemplates:
    def test_default_config_template_matches_snapshot(self, fixture_file: callable) -> None:
        rendered = render_default_config()
        expected = _fixture_text(fixture_file, "templates/expected_default_config.toml")
        assert rendered == expected

    def test_symlink_config_template_matches_snapshot(self, fixture_file: callable) -> None:
        rendered = render_default_config(vault_mode="symlink", vault_source_path="/vault/path")
        expected = _fixture_text(fixture_file, "templates/expected_symlink_config.toml")
        assert rendered == expected

    def test_precommit_template_matches_snapshot(self, fixture_file: callable) -> None:
        rendered = render_precommit_hook()
        expected = _fixture_text(fixture_file, "templates/expected_precommit_hook.yaml")
        assert rendered == expected

    def test_devenv_template_matches_snapshot(self, fixture_file: callable) -> None:
        rendered = render_devenv_snippet()
        expected = _fixture_text(fixture_file, "templates/expected_devenv_snippet.nix")
        assert rendered == expected

    def test_template_validation_rejects_invalid_inputs(self) -> None:
        with pytest.raises(ValueError):
            render_default_config(vault_mode="symlink")
        with pytest.raises(ValueError):
            render_precommit_hook(validate_command="")
        with pytest.raises(ValueError):
            render_devenv_snippet(validate_task_name="")

    def test_workflow_template_renders_expected_commands(self) -> None:
        rendered = render_github_pages_workflow(
            validate_command="devenv shell -- bullish-ssg validate",
            build_dry_run_command="devenv shell -- bullish-ssg build --dry-run",
            deploy_dry_run_command="devenv shell -- bullish-ssg deploy --dry-run",
        )

        assert "name: Bullish SSG CI" in rendered
        assert "bullish-ssg validate" in rendered
        assert "bullish-ssg build --dry-run" in rendered
        assert "bullish-ssg deploy --dry-run" in rendered
