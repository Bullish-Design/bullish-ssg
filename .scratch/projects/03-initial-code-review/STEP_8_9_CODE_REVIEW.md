# STEP 8/9 Code Review

## Scope
This review covers the intern’s attempted implementation of:
- Step 8: Kiln build/serve adapters
- Step 9: Deployment adapters and preflight

Guide reference:
- `.scratch/projects/02-bullish-ssg-implementation-guide/IMPLEMENTATION_GUIDE.md` (Step 8 and Step 9)

Code reviewed:
- `src/bullish_ssg/render/kiln.py`
- `src/bullish_ssg/deploy/preflight.py`
- `src/bullish_ssg/deploy/gh_pages.py`
- `src/bullish_ssg/deploy/branch_pages.py`
- `src/bullish_ssg/cli.py`
- `tests/unit/test_render_kiln_adapter.py`
- `tests/integration/test_cli_build_dry_run.py`
- `tests/unit/test_deploy_adapters.py`

---

## Findings (ordered by severity)

## 1) High: `deploy --dry-run` still executes preflight build (violates dry-run side-effect contract)
- Files:
  - `src/bullish_ssg/cli.py:223-226`
  - `src/bullish_ssg/deploy/preflight.py:141-168`
- Problem:
  - CLI deploy always runs `preflight.run()` even for `--dry-run`.
  - Preflight always runs `_validate_build()`, which executes `KilnAdapter.build(...)` for real.
- Impact:
  - `deploy --dry-run` is not side-effect free and fails when Kiln is not installed.
  - This conflicts with Step 9 requirement: dry-run must not perform side effects.
- Evidence:
  - Command: `devenv shell -- zsh -lc 'cd tests/fixtures/validation/healthy && bullish-ssg deploy --dry-run'`
  - Output: `Preflight checks failed: Build validation failed: Command not found: kiln...`
- Required fix:
  - Introduce dry-run-aware preflight (skip actual build execution or run build in dry mode through adapter abstraction).
  - Ensure `deploy --dry-run` can succeed without invoking external side-effectful commands.

## 2) High: Branch deployer restores to the wrong branch on success path
- File: `src/bullish_ssg/deploy/branch_pages.py:92-97, 173-177`
- Problem:
  - `original_branch` is derived from `current_branch_result.stdout`.
  - In the current test flow this value can be consumed from an unrelated mocked command output and become `"Switched to branch 'gh-pages'"`.
  - `finally` then runs `git checkout <that-string>`.
- Impact:
  - Recovery/cleanup branch checkout can be wrong, causing command failure or inconsistent repo state.
- Evidence:
  - `tests/unit/test_deploy_adapters.py` fails with attempts to execute `git checkout "Switched to branch 'gh-pages'"`.
  - Failing tests:
    - `TestBranchPagesDeployer::test_branch_deploy_command_sequence`
    - `TestBranchPagesDeployer::test_branch_deploy_creates_pages_branch_if_missing`
- Required fix:
  - Validate result of `rev-parse --abbrev-ref HEAD` before use.
  - Use defensive fallback behavior if current branch cannot be determined.
  - Update tests to include the extra command call explicitly and assert checkout target correctness.

## 3) Medium: Step 9 CLI-level behavior is under-tested (adapter selection + preflight blocking + deploy dry-run)
- Files:
  - `src/bullish_ssg/cli.py:212-267`
  - test coverage currently concentrated in `tests/unit/test_deploy_adapters.py`
- Problem:
  - No dedicated integration tests for CLI deploy command behavior.
  - Guide requires testing adapter selection by config and preflight block behavior at command level.
- Impact:
  - Regressions in CLI wiring can slip through even if adapter unit tests pass.
- Required fix:
  - Add integration tests for:
    - `deploy` selecting `gh-pages` vs `branch` by config.
    - preflight failure blocking deploy invocation.
    - `deploy --dry-run` not performing side effects.

## 4) Medium: Legacy `test_cli_help` expectation still treats deploy as a stub success path
- File: `tests/unit/test_cli_help.py:76-79`
- Problem:
  - Test expects `deploy --dry-run` exit code `0` without setup.
  - Current deploy command correctly requires config + preflight.
- Impact:
  - Step 9 test target (`-k "deploy or preflight"`) currently fails due stale expectation, masking real failures.
- Evidence:
  - `devenv shell -- pytest tests/ -k "deploy or preflight" -q` includes failure in `test_deploy_stub_returns_success`.
- Required fix:
  - Align this test with current command contract (expects config requirement failure), or move deploy behavior assertions into dedicated integration tests and keep help test focused on command listing.

## 5) Medium: Step 8 integration tests still rely on inline temp file creation rather than committed sample fixtures
- File: `tests/integration/test_cli_build_dry_run.py`
- Problem:
  - Tests generate config/content inline via `write_text` fixtures.
- Impact:
  - Inconsistent with current project testing direction toward committed sample fixtures; higher maintenance and less realistic fixture re-use.
- Required fix:
  - Mirror Step 6/7 approach: add fixture directories for build/serve scenarios and run tests from copied fixture workspaces.

## 6) Low: Unused `PreflightError` symbol and no typed failure channel in preflight flow
- Files:
  - `src/bullish_ssg/deploy/preflight.py:12-15`
  - imports in `src/bullish_ssg/cli.py:12`
- Problem:
  - `PreflightError` exists but is not used by preflight execution path.
- Impact:
  - Minor clarity issue; failure model is mixed (structured `PreflightResult` + broad exception catches).
- Required fix:
  - Either remove dead exception type or use it consistently for exceptional preflight failure modes.

---

## Step-by-step status vs guide

## Step 8 (Kiln build/serve adapters)
Implemented:
- `render/kiln.py` provides command abstraction (`SubprocessRunner`) and result capture.
- `KilnAdapter.build()` and `KilnAdapter.serve()` exist with dry-run support.
- CLI `build` and `serve` are wired to adapter path and surface errors.
- Unit and integration coverage exists and generally passes.

Partially implemented / gaps:
- Integration tests still use inline temp content instead of committed fixture directories.

## Step 9 (deploy adapters + preflight)
Implemented:
- `deploy/preflight.py`, `deploy/gh_pages.py`, `deploy/branch_pages.py` are present.
- CLI `deploy` runs preflight, selects adapter by config method, and invokes deploy.
- Unit tests cover many adapter/preflight behaviors.

Partially implemented / gaps:
- `deploy --dry-run` still triggers real build preflight.
- Branch deploy cleanup path has branch-selection correctness bug.
- Step 9 test target is not green due stale deploy CLI-help expectation and branch deploy test failures.
- Missing CLI-level integration tests for adapter selection and preflight blocking.

---

## Test evidence

Commands run:
```bash
devenv shell -- pytest tests/unit/test_render_kiln_adapter.py -q
devenv shell -- pytest tests/integration/test_cli_build_dry_run.py -q
devenv shell -- pytest tests/unit/test_deploy_adapters.py -q
devenv shell -- pytest tests/ -k "deploy or preflight" -q
devenv shell -- zsh -lc 'cd tests/fixtures/validation/healthy && bullish-ssg deploy --dry-run'
```

Results summary:
- Step 8 unit/integration tests pass.
- Step 9 tests currently fail in branch deploy sequence and stale deploy CLI-help expectation.
- Manual dry-run command shows preflight build execution and Kiln dependency in dry-run path.

---

## Prioritized remediation plan for intern
1. Make deploy preflight dry-run aware so `deploy --dry-run` has no build/deploy side effects.
2. Fix `BranchPagesDeployer` original-branch detection and checkout restoration robustness.
3. Update branch deploy tests to model the real command sequence (including `rev-parse`) and assert exact checkout target.
4. Replace stale `test_deploy_stub_returns_success` with config-required behavior or move it to proper integration coverage.
5. Add CLI integration tests for Step 9 acceptance criteria (adapter selection, preflight block, dry-run no side effects).
6. Refactor Step 8 integration tests to fixture-driven setup for consistency with current testing policy.

---

## Bottom line
Step 8 implementation is largely in good shape. Step 9 has meaningful progress, but key correctness and contract issues remain, especially around `deploy --dry-run` behavior and branch deploy branch-restoration logic. These should be fixed before considering Step 9 complete.
