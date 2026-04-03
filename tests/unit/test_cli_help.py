"""Tests for CLI help and command registration."""

from typer.testing import CliRunner
from bullish_ssg.cli import app

runner = CliRunner()


def test_cli_help_works() -> None:
    """Test that --help returns exit code 0."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Bullish SSG - Static site generator" in result.output


def test_cli_all_commands_in_help() -> None:
    """Test that all required commands appear in help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0

    required_commands = [
        "init",
        "link-vault",
        "build",
        "serve",
        "validate",
        "check-links",
        "deploy",
    ]

    for command in required_commands:
        assert command in result.output, f"Command '{command}' not found in help output"


def test_init_stub_returns_success() -> None:
    """Test that init stub returns success."""
    result = runner.invoke(app, ["init", "--dry-run"])
    assert result.exit_code == 0
    assert "DRY RUN" in result.output


def test_link_vault_stub_returns_success() -> None:
    """Test that link-vault stub returns success."""
    result = runner.invoke(app, ["link-vault", "/tmp/test-vault"])
    assert result.exit_code == 0


def test_build_stub_returns_success() -> None:
    """Test that build stub returns success."""
    result = runner.invoke(app, ["build", "--dry-run"])
    assert result.exit_code == 0


def test_serve_stub_returns_success() -> None:
    """Test that serve stub returns success."""
    result = runner.invoke(app, ["serve"])
    assert result.exit_code == 0


def test_validate_stub_returns_success() -> None:
    """Test that validate stub returns success."""
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0


def test_check_links_stub_returns_success() -> None:
    """Test that check-links stub returns success."""
    result = runner.invoke(app, ["check-links"])
    assert result.exit_code == 0


def test_deploy_stub_returns_success() -> None:
    """Test that deploy stub returns success."""
    result = runner.invoke(app, ["deploy", "--dry-run"])
    assert result.exit_code == 0
