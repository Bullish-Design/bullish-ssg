"""Template rendering utilities for generated integration snippets."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def render_default_config(
    *,
    site_name: str = "My Bullish Site",
    site_url: str = "http://localhost:8000/",
    vault_mode: str = "direct",
    vault_source_path: str | None = None,
    vault_link_path: str = "docs",
) -> str:
    """Render default `bullish-ssg.toml` content."""
    if vault_mode not in {"direct", "symlink"}:
        raise ValueError("vault_mode must be either 'direct' or 'symlink'")
    if vault_mode == "symlink" and not vault_source_path:
        raise ValueError("vault_source_path is required when vault_mode='symlink'")

    vault_source_path_line = ""
    if vault_mode == "symlink":
        vault_source_path_line = f'source_path = "{vault_source_path}"\n'

    template = _read_template("bullish-ssg.toml.tmpl")
    return template.format(
        site_name=site_name,
        site_url=site_url,
        vault_mode=vault_mode,
        vault_source_path_line=vault_source_path_line,
        vault_link_path=vault_link_path,
    )


def render_precommit_hook(*, validate_command: str = "bullish-ssg validate") -> str:
    """Render pre-commit local hook snippet."""
    if not validate_command.strip():
        raise ValueError("validate_command must not be empty")
    template = _read_template("precommit_hook.yaml.tmpl")
    return template.format(validate_command=validate_command)


def render_devenv_snippet(
    *,
    validate_command: str = "bullish-ssg validate",
    validate_task_name: str = "bullish-ssg:validate",
) -> str:
    """Render devenv task/script snippet."""
    if not validate_command.strip():
        raise ValueError("validate_command must not be empty")
    if not validate_task_name.strip():
        raise ValueError("validate_task_name must not be empty")
    template = _read_template("devenv_snippet.nix.tmpl")
    return template.format(
        validate_command=validate_command,
        validate_task_name=validate_task_name,
    )


def render_github_pages_workflow(
    *,
    validate_command: str = "devenv shell -- bullish-ssg validate",
    build_dry_run_command: str = "devenv shell -- bullish-ssg build --dry-run",
    deploy_dry_run_command: str = "devenv shell -- bullish-ssg deploy --dry-run",
) -> str:
    """Render optional GitHub Actions workflow."""
    commands = [validate_command, build_dry_run_command, deploy_dry_run_command]
    if any(not command.strip() for command in commands):
        raise ValueError("workflow commands must not be empty")
    template = _read_template("github_pages_workflow.yaml.tmpl")
    return template.format(
        validate_command=validate_command,
        build_dry_run_command=build_dry_run_command,
        deploy_dry_run_command=deploy_dry_run_command,
    )


def _read_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    return path.read_text(encoding="utf-8")
