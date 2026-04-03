# CONTEXT

Task:
- Implement all fixes/improvements in `.scratch/projects/03-initial-code-review/STEP_8_9_CODE_REVIEW.md`.

Implemented fixes:
- `src/bullish_ssg/deploy/preflight.py`
  - Added `run(dry_run: bool = False)` and dry-run-aware build validation (`KilnAdapter.build(..., dry_run=...)`).
- `src/bullish_ssg/cli.py`
  - Deploy command now calls `preflight.run(dry_run=dry_run)`.
  - Removed unused `PreflightError` import.
- `src/bullish_ssg/deploy/branch_pages.py`
  - Added failure handling for branch existence check and current-branch detection (`rev-parse`).
  - Added defensive failure result when current branch cannot be determined.
- Tests:
  - Updated `tests/unit/test_cli_help.py` deploy expectation to config-required failure.
  - Updated `tests/unit/test_deploy_adapters.py` for new branch deploy call flow and preflight dry-run assertions.
  - Rewrote `tests/integration/test_cli_build_dry_run.py` to fixture-driven workspace setup.
  - Added `tests/integration/test_cli_deploy_dry_run.py` for deploy adapter selection, preflight blocking, and dry-run behavior.
  - Added fixture directories under `tests/fixtures/build/*` and `tests/fixtures/deploy/*`.
- Docs:
  - Updated Step 8/9 testing notes in `.scratch/projects/02-bullish-ssg-implementation-guide/IMPLEMENTATION_GUIDE.md` to require fixture workspaces and explicit deploy dry-run expectations.

Verification:
- `devenv shell -- pytest tests/unit/test_render_kiln_adapter.py tests/integration/test_cli_build_dry_run.py tests/unit/test_deploy_adapters.py tests/integration/test_cli_deploy_dry_run.py tests/unit/test_cli_help.py -q` passed.
- `devenv shell -- pytest tests/ -k "render or kiln or build or command" -q` passed.
- `devenv shell -- pytest tests/ -k "deploy or preflight" -q` passed.
