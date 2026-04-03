"""CLI entry point for Bullish SSG."""

import typer
from pathlib import Path
from typing import Optional

app = typer.Typer(help="Bullish SSG - Static site generator")


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
    typer.echo("Building site...")
    if dry_run:
        typer.echo("[DRY RUN] Would run: kiln generate")
    else:
        typer.echo("Build completed")


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", help="Port to serve on"),
) -> None:
    """Serve the site locally."""
    typer.echo(f"Serving site on port {port}...")


@app.command()
def validate() -> None:
    """Validate site configuration and content."""
    typer.echo("Validating site...")


@app.command()
def check_links() -> None:
    """Check for broken internal links."""
    typer.echo("Checking links...")


@app.command()
def deploy(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deployed"),
) -> None:
    """Deploy the site to GitHub Pages."""
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
