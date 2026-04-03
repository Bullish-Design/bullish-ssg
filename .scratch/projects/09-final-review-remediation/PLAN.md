# PLAN

NO SUBAGENTS: Execute all tasks directly in this agent.

1. Apply critical fixes and tooling migration: patcher NameError, migrate mypy->ty, and run baseline lint/type/test commands.
2. Apply high-priority architecture fixes: deployer protocol, ContentType enum, TOML read/write modernization, remove circular-import workaround, deploy URL resolution, and vault-link coverage improvements.
3. Apply medium/low fixes: document placeholders and kiln dependency, narrow broad exception catches, branch deploy robustness, pre-commit edge test, cleanup unused variable, devenv task additions, pyproject URLs, AGENTS guidance polish.
4. Run ruff/ty/tests and iterate until clean.
5. Update project tracking files with outcomes.

NO SUBAGENTS: Keep all implementation and testing local.
