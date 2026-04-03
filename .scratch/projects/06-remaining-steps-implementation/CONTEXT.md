# CONTEXT

Completed Step 11 implementation.

Implemented:
- Added `link-vault` command behavior in CLI:
  - validates target path,
  - creates/repairs symlink via `VaultLinkManager`,
  - supports `--repair` and `--force`,
  - prints effective link/result messages.
- Added `src/bullish_ssg/config/writer.py` to sync `vault.mode`, `vault.source_path`, and `vault.link_path` in `bullish-ssg.toml`.
- `link-vault` now bootstraps a default config file when missing, then updates vault settings.
- Added integration tests: `tests/integration/test_cli_link_vault.py`.
- Updated CLI help test for `link-vault` to execute in an isolated temp workspace.

Verification run:
- `devenv shell -- pytest tests/ -k "link-vault or repair" -q` passed.

Next action:
- Implement Step 12 template system and make patchers consume templates.
