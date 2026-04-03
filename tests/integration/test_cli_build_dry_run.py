"""Integration tests for build and serve CLI commands."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bullish_ssg.cli import app

runner = CliRunner()


@pytest.fixture
def healthy_vault(tmp_path: Path) -> Path:
    """Create a healthy vault fixture."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create a valid config
    config_file = tmp_path / "bullish-ssg.toml"
    config_file.write_text("""
[site]
name = "Test Site"
url = "https://example.com/"

[content]
source_dir = "docs"
output_dir = "site"

[vault]
mode = "direct"
""")

    # Create a valid markdown file
    index_file = docs_dir / "index.md"
    index_file.write_text("""---
title: Index
---

# Welcome

This is the index.
""")

    return tmp_path


@pytest.fixture
def config_no_vault(tmp_path: Path) -> Path:
    """Create a config file without a vault."""
    config_file = tmp_path / "bullish-ssg.toml"
    config_file.write_text("""
[site]
name = "Test Site"
url = "https://example.com/"

[content]
source_dir = "nonexistent"
output_dir = "site"

[vault]
mode = "direct"
""")

    return tmp_path


class TestBuildCommand:
    """Tests for build CLI command."""

    def test_build_no_config_fails(self, tmp_path: Path) -> None:
        # Use a temp directory without config
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["build"])
            assert result.exit_code == 1
            assert "No configuration found" in result.output
        finally:
            os.chdir(original_dir)

    def test_build_dry_run_shows_command(self, healthy_vault: Path) -> None:
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(healthy_vault)
            result = runner.invoke(app, ["build", "--dry-run"])

            assert result.exit_code == 0
            assert "[DRY RUN]" in result.output
            assert "kiln generate" in result.output
            assert "--source" in result.output
            assert "--output" in result.output
        finally:
            os.chdir(original_dir)

    def test_build_reports_failure_on_error(self, tmp_path: Path) -> None:
        """Test that build command surfaces errors."""
        import os

        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create a valid config
        config_file = tmp_path / "bullish-ssg.toml"
        config_file.write_text("""
[site]
name = "Test Site"
url = "https://example.com/"

[content]
source_dir = "docs"
output_dir = "site"

[vault]
mode = "direct"
""")

        # Create a valid markdown file
        index_file = docs_dir / "index.md"
        index_file.write_text("""---
title: Index
---

# Welcome
""")

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            # This will fail because kiln is not installed
            result = runner.invoke(app, ["build"])

            # Should fail with non-zero exit code
            assert result.exit_code != 0
            assert "error" in result.output.lower() or "not found" in result.output.lower()
        finally:
            os.chdir(original_dir)


class TestServeCommand:
    """Tests for serve CLI command."""

    def test_serve_no_config_fails(self, tmp_path: Path) -> None:
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(app, ["serve"])
            assert result.exit_code == 1
            assert "No configuration found" in result.output
        finally:
            os.chdir(original_dir)

    def test_serve_dry_run_shows_command(self, healthy_vault: Path) -> None:
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(healthy_vault)
            result = runner.invoke(app, ["serve", "--port", "3000", "--dry-run"])

            assert result.exit_code == 0
            assert "[DRY RUN]" in result.output
            assert "kiln serve" in result.output
            assert "--port" in result.output
            assert "3000" in result.output
        finally:
            os.chdir(original_dir)

    def test_serve_requires_config(self, config_no_vault: Path) -> None:
        """Test that serve requires valid configuration."""
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(config_no_vault)
            # This should fail because the vault path doesn't exist
            result = runner.invoke(app, ["serve"])

            # Should fail due to missing vault
            assert result.exit_code == 1
        finally:
            os.chdir(original_dir)


class TestBuildCommandDryRun:
    """Tests specifically for build --dry-run behavior."""

    def test_dry_run_does_not_execute(self, healthy_vault: Path) -> None:
        """Verify dry-run does not actually run commands."""
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(healthy_vault)
            # Check that output dir doesn't exist before
            output_dir = healthy_vault / "site"
            assert not output_dir.exists()

            result = runner.invoke(app, ["build", "--dry-run"])

            # Should succeed without creating output
            assert result.exit_code == 0
            assert not output_dir.exists()
        finally:
            os.chdir(original_dir)

    def test_dry_run_includes_expected_args(self, healthy_vault: Path) -> None:
        """Verify dry-run shows expected command arguments."""
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(healthy_vault)
            result = runner.invoke(app, ["build", "--dry-run"])

            assert result.exit_code == 0
            output = result.output

            # Check for expected command structure
            assert "kiln generate" in output
            assert "--source" in output
            assert "--output" in output
            assert "docs" in output  # source directory name
            assert "site" in output  # output directory name
        finally:
            os.chdir(original_dir)
