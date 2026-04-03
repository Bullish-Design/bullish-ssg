# CONTEXT

Completed Step 12 implementation.

Implemented:
- Added template renderer module: `src/bullish_ssg/init/templates.py`.
- Added template assets under `src/bullish_ssg/init/templates/`:
  - `bullish-ssg.toml.tmpl`
  - `precommit_hook.yaml.tmpl`
  - `devenv_snippet.nix.tmpl`
  - `github_pages_workflow.yaml.tmpl` (optional CI template)
- Refactored `init` patchers to consume rendered templates instead of hardcoded multiline strings.
- Added snapshot fixtures under `tests/fixtures/templates/`.
- Added snapshot/validation tests in `tests/unit/test_init_templates.py`.

Verification run:
- `devenv shell -- pytest tests/ -k "template or generated or config" -q` passed.
- `devenv shell -- pytest tests/unit/test_init_scaffold.py tests/integration/test_cli_init.py tests/integration/test_cli_link_vault.py -q` passed.

Next action:
- Implement Step 13 E2E fixture matrix and broaden integration tests.
