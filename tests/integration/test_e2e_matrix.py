"""End-to-end fixture matrix for command-level flows."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app
from bullish_ssg.content.classify import ContentClassifier, SlugCollisionError, enforce_no_slug_collisions
from bullish_ssg.content.discovery import ContentDiscovery
from bullish_ssg.content.frontmatter import FrontmatterParser

runner = CliRunner()


def run_in_workspace(workspace: Path, args: list[str], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(workspace)
    return runner.invoke(app, args)


@pytest.fixture
def docs_only_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("e2e/docs_only_direct")


@pytest.fixture
def docs_blog_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("e2e/docs_blog_direct")


@pytest.fixture
def symlink_workspace(fixture_copy: callable) -> Path:
    workspace = fixture_copy("e2e/symlink_mode_repo")
    (workspace / "docs").symlink_to(workspace / "vault-external")
    return workspace


@pytest.fixture
def broken_links_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("e2e/broken_links")


@pytest.fixture
def slug_collision_workspace(fixture_copy: callable) -> Path:
    return fixture_copy("e2e/slug_collision")


class TestE2ECommands:
    def test_docs_only_direct_mode_commands(self, docs_only_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        validate = run_in_workspace(docs_only_workspace, ["validate"], monkeypatch)
        links = run_in_workspace(docs_only_workspace, ["check-links"], monkeypatch)
        build = run_in_workspace(docs_only_workspace, ["build", "--dry-run"], monkeypatch)
        deploy = run_in_workspace(docs_only_workspace, ["deploy", "--dry-run"], monkeypatch)

        assert validate.exit_code == 0
        assert links.exit_code == 0
        assert build.exit_code == 0
        assert deploy.exit_code == 0

    def test_docs_blog_direct_mode_classification_matrix(self, docs_blog_workspace: Path) -> None:
        vault_path = docs_blog_workspace
        discovery = ContentDiscovery(vault_path, include_assets=False)
        parser = FrontmatterParser(vault_path)
        classifier = ContentClassifier(vault_path=vault_path, blog_dirs=["blog"], default_type="doc")

        markdown = list(discovery.discover_markdown())
        routes = [classifier.classify(item.relative_path, parser.parse(item.path).metadata) for item in markdown]

        assert any(route.content_type == "post" for route in routes)
        assert any(route.content_type == "doc" for route in routes)
        assert any(route.permalink.startswith("/blog/") for route in routes)

    def test_symlink_mode_validate_and_links(self, symlink_workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        validate = run_in_workspace(symlink_workspace, ["validate"], monkeypatch)
        links = run_in_workspace(symlink_workspace, ["check-links"], monkeypatch)

        assert validate.exit_code == 0
        assert links.exit_code == 0

    def test_broken_links_fixture_fails_check_links(
        self,
        broken_links_workspace: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        result = run_in_workspace(broken_links_workspace, ["check-links"], monkeypatch)

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "broken" in result.output.lower()

    def test_slug_collision_fixture_fails_collision_check(self, slug_collision_workspace: Path) -> None:
        vault_path = slug_collision_workspace / "docs"
        discovery = ContentDiscovery(vault_path, include_assets=False)
        parser = FrontmatterParser(vault_path)
        classifier = ContentClassifier(vault_path=vault_path, default_type="doc")

        markdown = list(discovery.discover_markdown())
        routes = [classifier.classify(item.relative_path, parser.parse(item.path).metadata) for item in markdown]

        with pytest.raises(SlugCollisionError):
            enforce_no_slug_collisions(routes)

    def test_unpublished_filter_matrix(self, fixture_copy: callable, monkeypatch: pytest.MonkeyPatch) -> None:
        workspace = fixture_copy("validation/unpublished_target")
        result = run_in_workspace(workspace, ["check-links"], monkeypatch)

        assert result.exit_code == 0
        assert "unpublished/excluded" in result.output.lower()

    def test_init_dry_run_and_link_vault_flow(
        self,
        tmp_path: Path,
        fixture_copy: callable,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        vault = fixture_copy("vault/source_vault")
        dry_init = run_in_workspace(tmp_path, ["init", "--dry-run"], monkeypatch)
        link = run_in_workspace(tmp_path, ["link-vault", str(vault)], monkeypatch)

        assert dry_init.exit_code == 0
        assert "[DRY RUN]" in dry_init.output
        assert link.exit_code == 0
        assert (tmp_path / "docs").is_symlink()
