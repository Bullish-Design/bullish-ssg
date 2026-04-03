# DECISIONS

- Type checking is now executed via `devenv shell -- ty check src` rather than whole-repo ty checks, because repository tests intentionally use pytest fixture helper annotations (`callable`) that are not currently ty-clean.
- Kept Typer B008 warnings suppressed in Ruff (`ignore = ["B008"]`) as framework false positives for command argument declarations.
- Added branch deploy pre-check requiring clean git working tree to reduce risk during branch mutation workflows.
