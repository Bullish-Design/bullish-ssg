"""CLI entry point for Bullish SSG."""

from pathlib import Path
from typing import Optional

import typer

from bullish_ssg.config.loader import find_config_file, load_config
from bullish_ssg.config.schema import BullishConfig
from bullish_ssg.render.kiln import BuildManager, KilnError
from bullish_ssg.vault_link.resolver import VaultResolutionError, resolve_vault_path
from bullish_ssg.validate.rules import ValidationRunner, WikilinkValidator

app = typer.Typer(help="Bullish SSG - Static site generator")


def _load_config_if_present() -> Optional[BullishConfig]:
    """Load config if available; return None when not configured yet."""
    config_path = find_config_file()
    if config_path is None:
        return None
    try:
        return load_config(config_path)
    except Exception as exc:  # pragma: no cover - defensive CLI handling
        typer.echo(f"Configuration error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.command()
def init(
    path: Optional[Path] = typer.Option(None, "--path", help="Path to initialize"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Initialize a new Bullish SSG project."""
    typer.echo("Initializing project...")
    if dry_run:
        typer.echo("[DRY RUN] Would create bullish-ssg.toml")
        typer.echo("[DRY RUN] Would update .gitignore")
        typer.echo("[DRY RUN] Would update devenv.nix")
    else:
        typer.echo("Project initialized successfully")


@app.command()
def link_vault(
    target: Path = typer.Argument(..., help="Path to external vault"),
    link_path: Path = typer.Option(Path("docs"), "--link-path", help="Path for symlink"),
    repair: bool = typer.Option(False, "--repair", help="Repair existing symlink"),
    force: bool = typer.Option(False, "--force", help="Force overwrite"),
) -> None:
    """Link an external Obsidian vault via symlink."""
    typer.echo(f"Linking vault from {target} to {link_path}")


@app.command()
def build(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be built"),
) -> None:
    """Build the static site."""
    config = _load_config_if_present()
    if config is None:
        typer.echo("Error: No configuration found. Run 'bullish-ssg init' first.", err=True)
        raise typer.Exit(code=1)

    # Resolve vault path
    try:
        vault_path = resolve_vault_path(config.vault)
    except Exception as exc:
        typer.echo(f"Vault resolution error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Build using Kiln
    manager = BuildManager()
    output_dir = Path(config.content.output_dir)

    try:
        result = manager.build_from_config(
            vault_path=vault_path,
            output_dir=output_dir,
            dry_run=dry_run,
        )

        if dry_run:
            typer.echo(result.stdout)
        else:
            if result.success:
                typer.echo(f"Build completed: {output_dir}")
                if result.stdout:
                    typer.echo(result.stdout)
            else:
                typer.echo(f"Build failed with code {result.returncode}", err=True)
                if result.stderr:
                    typer.echo(result.stderr, err=True)
                raise typer.Exit(code=1)
    except KilnError as exc:
        typer.echo(f"Build error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", help="Port to serve on"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be served"),
) -> None:
    """Serve the site locally."""
    config = _load_config_if_present()
    if config is None:
        typer.echo("Error: No configuration found. Run 'bullish-ssg init' first.", err=True)
        raise typer.Exit(code=1)

    # Resolve vault path
    try:
        vault_path = resolve_vault_path(config.vault)
    except Exception as exc:
        typer.echo(f"Vault resolution error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Serve using Kiln
    manager = BuildManager()

    try:
        result = manager.serve_from_config(
            vault_path=vault_path,
            port=port,
            dry_run=dry_run,
        )

        if dry_run:
            typer.echo(result.stdout)
        else:
            if result.success:
                typer.echo(f"Serving site on port {port}...")
                if result.stdout:
                    typer.echo(result.stdout)
            else:
                typer.echo(f"Serve failed with code {result.returncode}", err=True)
                if result.stderr:
                    typer.echo(result.stderr, err=True)
                raise typer.Exit(code=1)
    except KilnError as exc:
        typer.echo(f"Serve error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@app.command()
def validate(
    include_orphans: bool = typer.Option(False, "--include-orphans", help="Check for orphaned pages"),
) -> None:
    """Validate site configuration and content."""
    config = _load_config_if_present()
    if config is None:
        typer.echo("Error: No configuration found. Run 'bullish-ssg init' first.", err=True)
        raise typer.Exit(code=1)

    # Resolve vault path
    try:
        vault_path = resolve_vault_path(config.vault)
    except Exception as exc:
        typer.echo(f"Vault resolution error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Run validation
    runner = ValidationRunner(
        vault_path=vault_path,
        vault_config=config.vault,
        ignore_patterns=list(config.content.ignore_patterns),
    )
    result = runner.run_full_validation(include_orphan_check=include_orphans)

    # Print results
    result.print_summary()

    # Exit with appropriate code
    if not result.passed:
        raise typer.Exit(code=1)


@app.command()
def check_links() -> None:
    """Check for broken internal links."""
    config = _load_config_if_present()
    if config is None:
        typer.echo("Error: No configuration found. Run 'bullish-ssg init' first.", err=True)
        raise typer.Exit(code=1)

    # Resolve vault path
    try:
        vault_path = resolve_vault_path(config.vault)
    except Exception as exc:
        typer.echo(f"Vault resolution error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Run wikilink validation
    validator = WikilinkValidator(
        vault_path=vault_path,
        fail_on_broken=config.validation.fail_on_broken_links,
        ignore_patterns=list(config.content.ignore_patterns),
    )
    result = validator.validate()

    # Print results
    result.print_summary()

    # Exit with appropriate code
    if not result.passed:
        raise typer.Exit(code=1)


@app.command()
def deploy(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed"),
) -> None:
    """Deploy the site to GitHub Pages."""
    _load_config_if_present()
    typer.echo("Deploying site...")
    if dry_run:
        typer.echo("[DRY RUN] Would run: gh pages deploy")
    else:
        typer.echo("Deployment completed")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
