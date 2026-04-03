# bullish-ssg Implementation Guide (Intern Execution Runbook)

Status: Draft v1
Date: 2026-04-03
Primary reference: `../01-zensical-github-pages/IMPLEMENTATION_OVERVIEW.md`

## Table of Contents

1. How to Use This Guide  
   Explains execution order, quality bar, and when to stop and ask for help.
2. Definition of Done  
   Lists objective completion criteria for this implementation.
3. Prerequisites and Environment Setup  
   Covers toolchain setup and the mandatory first-session dependency sync.
4. Recommended Branch and Commit Strategy  
   Defines branch naming, commit granularity, and PR hygiene.
5. Step 1: Create Package Skeleton and CLI Entry Point  
   Establishes project structure and command scaffold.
6. Step 2: Implement Config Schema and Loader  
   Adds `bullish-ssg.toml` parsing, defaults, and validation.
7. Step 3: Implement Vault Link Management (`docs/` Symlink)  
   Adds built-in support for external Obsidian vault linking.
8. Step 4: Implement Content Discovery and Frontmatter Parsing  
   Adds file indexing and metadata extraction.
9. Step 5: Implement Content Classification and Routing Metadata  
   Adds docs/post/page typing and URL metadata.
10. Step 6: Implement Wikilink Parsing and Resolution  
    Adds Obsidian link integrity checks with line-level diagnostics.
11. Step 7: Implement Validation Commands (`validate`, `check-links`)  
    Exposes validation through CLI and exit code policy.
12. Step 8: Implement Kiln Build and Serve Adapters  
    Adds renderer integration for local build/preview.
13. Step 9: Implement Deployment Adapters and Preflight  
    Adds `gh pages deploy` and branch fallback flows.
14. Step 10: Implement Scaffolding (`init`) and Repo Patchers  
    Adds idempotent setup for config, devenv, hooks, and ignores.
15. Step 11: Implement `link-vault` Command and Repair Workflow  
    Adds explicit symlink create/update/repair command.
16. Step 12: Add Integration Templates (devenv, prek, optional CI)  
    Centralizes generated snippets and template tests.
17. Step 13: Add End-to-End Test Fixtures and Full Test Matrix  
    Adds realistic docs/blog/symlink fixtures and command-level tests.
18. Step 14: Documentation, Dry Run, and Handoff Checklist  
    Final docs and verification before handing to maintainer.
19. Troubleshooting Playbook  
    Common failure modes and fast remediation paths.
20. Appendix A: Suggested Test File Map  
    Concrete test module/file layout.
21. Appendix B: Suggested Initial Milestone Breakdown  
    Sprint-friendly grouping for intern execution.

## 1) How to Use This Guide

- Execute steps in order.
- Do not skip tests at the end of a step.
- If a step fails tests, do not proceed; fix failures first.
- Use small commits: one step per commit whenever feasible.
- If you hit 3 failed attempts on one blocker, create `ISSUE_01.md` (or next number) in this project directory and document attempts.
- Use fixture-driven tests: keep canonical sample files under `tests/fixtures/` and avoid writing markdown/config sample content inline inside test functions.

### Execution style expected from intern:
- Test-driven development where practical: write/adjust failing tests first, then implement, then pass.
- Keep code changes focused on the current step.
- Prefer deterministic behavior and explicit errors over hidden fallbacks.

### Fixture policy:
- Store sample markdown, TOML, and vault trees under `tests/fixtures/`.
- Tests may still use `tmp_path` for isolated runtime state (symlinks, copied fixture trees, temporary working dirs).
- Do not generate test sample content via `write_text(...)` in test bodies unless the sample cannot be represented as a reusable fixture.

## 2) Definition of Done

All of the following must be true:
- CLI commands implemented and usable: `init`, `link-vault`, `build`, `serve`, `validate`, `check-links`, `deploy`.
- `docs/` symlink mode works end-to-end with an external vault target.
- Config schema validates all required fields and mode-specific constraints.
- Validation catches broken wikilinks with file+line diagnostics.
- Build and serve run through Kiln adapter.
- Deploy works via `gh pages deploy` primary path, with explicit fallback adapter for branch mode.
- `init` is idempotent and does not destroy existing files.
- Automated tests cover critical success and failure paths.
- Guide-level handoff docs are updated and usable by maintainer.

## 3) Prerequisites and Environment Setup

### 3.1 Tools

Ensure these are available in your dev environment:
- `devenv`
- `uv`
- `git`
- `gh`
- `kiln` (or install path covered by project tooling)
- `pytest`

### 3.2 Mandatory first-session command

Per repo rules, run this before first test execution:

```bash
devenv shell -- uv sync --extra dev
```

### 3.3 Baseline sanity checks

Run:

```bash
devenv shell -- python --version
devenv shell -- pytest --version
devenv shell -- uv --version
```

Expected result:
- All commands succeed.
- Python/pytest/uv are available inside devenv shell.

If any command fails:
- Fix environment first.
- Do not start implementation until baseline checks pass.

## 4) Recommended Branch and Commit Strategy

- Branch name format: `feat/bullish-ssg-<step>-<short-topic>`.
- Commit style: one step = one commit (or one commit per coherent sub-step).
- Commit message style:
  - `feat(config): add schema + loader with validation`
  - `test(links): add heading anchor resolution cases`

Suggested cadence:
1. Create branch.
2. Complete one step fully (including tests).
3. Commit and push.
4. Open/update PR.
5. Repeat.

## 5) Step 1: Create Package Skeleton and CLI Entry Point

### Objective

Create project layout and a CLI skeleton that supports command registration without implementing business logic yet.

### Implementation tasks

1. Create package structure under `src/bullish_ssg/`:
- `__init__.py`
- `cli.py`
- empty module directories (`config`, `vault_link`, `content`, `validate`, `render`, `deploy`, `init`, `integrations`, `reporting`) each with `__init__.py`.

2. Add CLI framework dependency if missing (`typer` or `click`; pick one and stay consistent).

3. Implement command stubs:
- `init`
- `link-vault`
- `build`
- `serve`
- `validate`
- `check-links`
- `deploy`

4. Ensure each stub returns a clear placeholder message and non-error exit code.

5. Add console entry point in project config (e.g., `pyproject.toml`).

### Testing required after Step 1

Write tests first:
- CLI smoke test verifies `--help` works.
- CLI command registration test verifies each command appears in help output.

Run:

```bash
devenv shell -- pytest tests/ -k "cli and help" -q
```

Pass criteria:
- Command list includes all 7 required commands.
- CLI exits with code 0 for help and stubs.

## 6) Step 2: Implement Config Schema and Loader

### Objective

Implement strict config parsing for `bullish-ssg.toml` with defaults and mode-specific validation.

### Implementation tasks

1. Add config models in `src/bullish_ssg/config/schema.py`.
2. Implement loader in `src/bullish_ssg/config/loader.py`:
- locate config file,
- parse TOML,
- apply defaults,
- raise descriptive errors on invalid values.

3. Include required sections:
- `site`
- `content`
- `vault`
- `validation`
- `deploy`
- `hooks`

4. Enforce these key constraints:
- `site.url` absolute and trailing slash.
- `vault.mode` in `{direct, symlink}`.
- `vault.source_path` required when `mode=symlink`.
- `vault.link_path` defaults to `docs`.

5. Wire config loading into CLI startup path (lazy load for command paths that need it).

### Testing required after Step 2

Write tests first:
- valid minimal config parses.
- missing required fields fail with explicit error message.
- invalid `vault.mode` fails.
- `symlink` mode without `source_path` fails.
- `site.url` validation cases (missing scheme, missing trailing slash).

Run:

```bash
devenv shell -- pytest tests/ -k "config" -q
```

Pass criteria:
- All positive cases parse to expected model values.
- All negative cases fail with deterministic and readable diagnostics.

## 7) Step 3: Implement Vault Link Management (`docs/` Symlink)

### Objective

Implement robust symlink resolution and management so repo-local `docs/` can point to an external Obsidian vault.

### Implementation tasks

1. Add `src/bullish_ssg/vault_link/resolver.py`:
- resolve effective vault path from config,
- in `direct` mode: validate `link_path`/`vault_dir` is directory,
- in `symlink` mode: validate `link_path` is symlink and resolves to target.

2. Add `src/bullish_ssg/vault_link/manager.py`:
- create symlink,
- update/repair symlink,
- detect non-symlink conflicts at `link_path` and fail safely.

3. Normalize path handling:
- accept absolute or repo-relative `source_path`,
- store normalized absolute path internally during runtime.

4. Expose helpful error messages:
- broken symlink,
- missing target,
- permission denied,
- conflicting existing file/dir.

### Testing required after Step 3

Write tests first:
- direct mode with existing docs dir passes.
- symlink mode with valid link passes.
- symlink mode with broken target fails.
- symlink mode where `link_path` exists as normal dir fails safely.
- repair mode updates incorrect symlink to new target.

Use temporary directories/fixtures for filesystem tests.
Base file content should come from `tests/fixtures/` and be copied into temp workspaces as needed.

Run:

```bash
devenv shell -- pytest tests/ -k "vault_link or symlink" -q
```

Pass criteria:
- Resolver returns deterministic effective path.
- Manager never silently replaces non-symlink directories/files.
- Errors provide exact failing path and required fix.

## 8) Step 4: Implement Content Discovery and Frontmatter Parsing

### Objective

Index vault content and parse frontmatter metadata used by classification and validation.

### Implementation tasks

1. Add `src/bullish_ssg/content/discovery.py`:
- recursive file discovery under effective vault path,
- include markdown and relevant asset extensions,
- apply ignore patterns from config.

2. Add `src/bullish_ssg/content/frontmatter.py`:
- parse YAML frontmatter,
- return structured metadata + raw body,
- provide precise parse errors with file context.

3. Define a content record model (dataclass/pydantic) with:
- source path,
- relative path,
- content type placeholder,
- metadata fields,
- raw markdown text.

### Testing required after Step 4

Write tests first:
- discovery respects ignore patterns (`.obsidian/**`, templates, etc.).
- frontmatter parses valid input correctly.
- malformed frontmatter yields actionable error.
- files without frontmatter still parse with defaults.
- tests consume real fixture markdown files (valid, invalid YAML, and no frontmatter cases).

Run:

```bash
devenv shell -- pytest tests/ -k "discovery or frontmatter" -q
```

Pass criteria:
- File indexing count matches fixture expectations.
- Parsing is deterministic and resilient.
- Invalid frontmatter errors include file path and line context when possible.

## 9) Step 5: Implement Content Classification and Routing Metadata

### Objective

Classify files into docs/posts/pages and compute routing metadata required for output consistency.

### Implementation tasks

1. Add `src/bullish_ssg/content/classify.py`:
- infer `type` from frontmatter first,
- fallback to path-based defaults (`blog_dirs` => post),
- fallback to config `default_type`.

2. Implement slug generation:
- use frontmatter `slug` when provided,
- otherwise normalize filename,
- detect collisions and fail.

3. Implement post metadata normalization:
- require `date` for posts if configured,
- parse and normalize date values.

4. Add route model:
- docs route,
- blog route (`date-slug` vs `slug` style),
- index page conventions.

### Testing required after Step 5

Write tests first:
- frontmatter `type` overrides path inference.
- `blog/` files infer post type when `type` absent.
- slug collision fails with both file paths in error.
- date requirements enforced for posts.
- route generation matches expected URLs.

Run:

```bash
devenv shell -- pytest tests/ -k "classify or route or slug" -q
```

Pass criteria:
- Classification and route outputs are deterministic.
- Misconfigured posts fail early with clear diagnostics.

## 10) Step 6: Implement Wikilink Parsing and Resolution

### Objective

Implement Obsidian wikilink parser/resolver and heading-anchor validation.

### Implementation tasks

1. Add `src/bullish_ssg/validate/wikilinks.py`:
- parse patterns:
  - `[[page]]`
  - `[[page|alias]]`
  - `[[page#heading]]`
  - `[[page#^block-id]]` (block ref can be warning-only in v1)

2. Build page index for target resolution.

3. Resolve heading anchors:
- normalize headings consistently,
- verify anchor exists in target doc.

4. Return diagnostics with:
- source file,
- line number,
- raw link,
- reason for failure.

### Testing required after Step 6

Write tests first:
- valid basic wikilinks resolve.
- aliased links resolve correctly.
- missing page fails with source line.
- missing heading anchor fails.
- links to excluded unpublished pages fail or warn per policy.
- tests must use committed fixture content under `tests/fixtures/` (do not construct markdown/config samples inline in test bodies).

Run:

```bash
devenv shell -- pytest tests/ -k "wikilink or heading anchor" -q
```

Pass criteria:
- Parser handles core syntax reliably.
- Diagnostics are specific enough to fix broken links quickly.

## 11) Step 7: Implement Validation Commands (`validate`, `check-links`)

### Objective

Expose frontmatter, structure, symlink, and link validation behind CLI commands.

### Implementation tasks

1. In `src/bullish_ssg/validate/` implement:
- frontmatter rule checks,
- optional orphan checks,
- symlink health checks (mode-aware).

2. Wire `validate` command:
- config load,
- resolver execution,
- validation suite,
- summary output and exit code.

3. Wire `check-links` command:
- dedicated wikilink validation pipeline,
- fail-on-broken behavior from config.

4. Standardize error/report format for human-readable output.

### Testing required after Step 7

Write tests first:
- `validate` passes on healthy fixture.
- `validate` fails on malformed frontmatter.
- `validate` fails when symlink target is broken in symlink mode.
- `check-links` fails when broken wikilink exists.
- CLI exit codes are non-zero on failure.
- integration tests must run from copied fixture workspaces (for example via `fixture_copy` + `monkeypatch.chdir`) and avoid ad-hoc `write_text` setup for sample docs/config files.

Run:

```bash
devenv shell -- pytest tests/ -k "validate or check-links" -q
```

Pass criteria:
- Command output includes total checks, warning/error counts, and failed files.
- Exit codes are consistent and script-friendly.

## 12) Step 8: Implement Kiln Build and Serve Adapters

### Objective

Implement renderer adapter layer that invokes Kiln for build and local serve.

### Implementation tasks

1. Add `src/bullish_ssg/render/kiln.py`:
- `build()` wrapper for `kiln generate`.
- `serve()` wrapper for `kiln serve`.

2. Ensure build path uses resolved effective vault source.

3. Add command execution abstraction (`subprocess` wrapper) that captures:
- command,
- exit code,
- stdout/stderr.

4. Wire CLI commands `build` and `serve` to this adapter.

5. Add optional `--dry-run` for build command to print planned invocation.

### Testing required after Step 8

Write tests first:
- command construction test for generate/serve invocation args.
- subprocess failure propagates meaningful error.
- dry-run mode avoids execution and prints expected command.
- integration tests should run against committed fixture workspaces under `tests/fixtures/` (avoid inline `write_text` setup for sample docs/config content).

For integration, use command mocking if Kiln is unavailable in CI.

Run:

```bash
devenv shell -- pytest tests/ -k "render or kiln or build command" -q
```

Optional local smoke test:

```bash
devenv shell -- bullish-ssg build --dry-run
devenv shell -- bullish-ssg serve --help
```

Pass criteria:
- Adapter produces stable command invocations.
- Build and serve commands surface failures clearly.

## 13) Step 9: Implement Deployment Adapters and Preflight

### Objective

Implement deployment with validation/build preflight and two deploy adapters.

### Implementation tasks

1. Add `src/bullish_ssg/deploy/preflight.py`:
- ensure config valid,
- ensure vault path resolvable,
- ensure build succeeds before deploy.

2. Add `src/bullish_ssg/deploy/gh_pages.py`:
- run `gh pages deploy <site_dir>`.

3. Add `src/bullish_ssg/deploy/branch_pages.py`:
- prepare branch deploy flow (explicit and isolated implementation).

4. Wire `deploy` command:
- run preflight,
- choose adapter by config,
- print resulting URL/method.

5. Add `--dry-run` to deploy command.

### Testing required after Step 9

Write tests first:
- deploy command selects correct adapter by config.
- deploy blocked when preflight validation fails.
- dry-run does not perform side effects.
- gh adapter command invocation correctness.
- deploy integration tests should use committed fixture workspaces and verify that `deploy --dry-run` works without requiring external binaries (`kiln`, `gh`) to be installed.

Run:

```bash
devenv shell -- pytest tests/ -k "deploy or preflight" -q
```

Pass criteria:
- No deployment occurs when validation/build fails.
- Adapter selection and command invocations are deterministic.

## 14) Step 10: Implement Scaffolding (`init`) and Repo Patchers

### Objective

Implement idempotent setup command for repo automation.

### Implementation tasks

1. Add scaffolding logic in `src/bullish_ssg/init/scaffold.py` and patchers in `patchers.py`.

2. Implement additive/idempotent behavior for:
- `bullish-ssg.toml` creation/merge,
- `.gitignore` additions,
- `.pre-commit-config.yaml` hook insertion/merge,
- `devenv.nix` task/script/process additions,
- starter `docs/index.md` when needed.

3. Ensure `init` supports non-interactive mode with CLI flags.

4. Add preview mode (`--dry-run`) showing intended edits.

### Testing required after Step 10

Write tests first:
- `init` on empty repo creates expected files.
- `init` on preconfigured repo merges without duplicating entries.
- running `init` twice yields no further changes (idempotent).
- `--dry-run` reports changes without writing files.

Run:

```bash
devenv shell -- pytest tests/ -k "init or scaffold or patcher" -q
```

Pass criteria:
- No destructive rewrites.
- Idempotency proven by identical filesystem state on repeated runs.

## 15) Step 11: Implement `link-vault` Command and Repair Workflow

### Objective

Provide explicit command for creating/updating `docs/` symlink and syncing config.

### Implementation tasks

1. Implement CLI command `link-vault`:
- required input target path,
- optional `--link-path` (default `docs`),
- optional `--repair` and `--force` semantics.

2. Command responsibilities:
- validate target exists,
- create/update symlink,
- update config (`vault.mode=symlink`, `source_path`, `link_path`),
- print resulting effective path.

3. Safety rules:
- if `link_path` exists as non-symlink, fail unless explicit override path is approved by flag.
- never silently delete user content.

### Testing required after Step 11

Write tests first:
- creates symlink and config updates on first run.
- second run is idempotent.
- changed target updates symlink in repair mode.
- conflict with existing non-symlink path fails safely.

Run:

```bash
devenv shell -- pytest tests/ -k "link-vault or repair" -q
```

Pass criteria:
- Command can recover a broken/moved vault link with clear user feedback.
- Config and filesystem state remain consistent.

## 16) Step 12: Add Integration Templates (devenv, prek, optional CI)

### Objective

Centralize managed snippets for generated automation files.

### Implementation tasks

1. Create template files under `src/bullish_ssg/init/templates/` for:
- `devenv` tasks/scripts/process snippets,
- `prek` hooks,
- optional GitHub Actions workflow.

2. Patchers should consume templates, not hardcoded multiline strings.

3. Ensure template variables are clearly defined and validated.

4. Add snapshot tests for generated outputs.

### Testing required after Step 12

Write tests first:
- template rendering with default config values.
- template rendering with symlink mode settings.
- patchers insert rendered templates without duplication.

Run:

```bash
devenv shell -- pytest tests/ -k "template or generated config" -q
```

Pass criteria:
- Generated snippets are stable and maintainable.
- Snapshot diffs are understandable and minimal.

## 17) Step 13: Add End-to-End Test Fixtures and Full Test Matrix

### Objective

Add realistic fixture repos/vaults and verify command flows across common scenarios.

### Implementation tasks

1. Add fixture sets for:
- docs-only direct mode,
- docs+blog direct mode,
- symlink mode with external vault,
- intentionally broken fixtures for negative tests.

2. Add command-level integration tests:
- `build`, `validate`, `check-links`, `deploy --dry-run`, `init --dry-run`, `link-vault`.

3. Add matrix test coverage for:
- direct vs symlink mode,
- publish filters,
- broken links,
- slug collisions.

### Testing required after Step 13

Run targeted suite first:

```bash
devenv shell -- pytest tests/integration -q
```

Then run full suite:

```bash
devenv shell -- pytest tests/ -q
```

Pass criteria:
- All step-level tests and full suite pass.
- No flaky tests across two consecutive runs.
- Fixture coverage exists for docs-only, docs+blog, and symlink scenarios without inline sample file generation in tests.

## 18) Step 14: Documentation, Dry Run, and Handoff Checklist

### Objective

Finalize implementation docs and provide reproducible verification steps.

### Implementation tasks

1. Update project README/docs with:
- installation,
- command quickstart,
- direct mode example,
- symlink mode example.

2. Add explicit troubleshooting section for symlink issues.

3. Perform manual dry-run walkthrough on a clean clone:
- `init --dry-run`,
- `link-vault`,
- `validate`,
- `build --dry-run`,
- `deploy --dry-run`.

4. Prepare short handoff note with:
- what was implemented,
- test evidence,
- known limitations.

### Testing required after Step 14

Run full tests again:

```bash
devenv shell -- pytest tests/ -q
```

Optional local command smoke sequence:

```bash
devenv shell -- bullish-ssg init --dry-run
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
devenv shell -- bullish-ssg build --dry-run
devenv shell -- bullish-ssg deploy --dry-run
```

Pass criteria:
- Full suite green.
- Docs reflect actual behavior and current CLI flags.
- Another developer can follow the quickstart without hidden setup.

## 19) Troubleshooting Playbook

### Problem: `devenv shell -- uv sync --extra dev` fails

Likely causes:
- broken lock/dependency conflict,
- network access issues,
- invalid project metadata.

Actions:
1. Re-run and capture full output.
2. Validate `pyproject.toml` syntax and dependency names.
3. Resolve lockfile drift if present.
4. Do not continue implementation until sync succeeds.

### Problem: `link-vault` fails with existing `docs/` directory

Likely cause:
- existing non-symlink path conflict.

Actions:
1. Confirm existing content should be preserved.
2. Move/rename manually if intended.
3. Re-run `link-vault` with explicit flags only when safe.

### Problem: broken wikilinks reported unexpectedly

Likely causes:
- slug normalization mismatch,
- heading anchor normalization mismatch,
- target page excluded by publish rules.

Actions:
1. Check normalized target slug in diagnostics.
2. Confirm target page is publishable in current mode.
3. Add test covering that specific link pattern.

### Problem: deploy dry-run passes but real deploy fails

Likely causes:
- `gh` not authenticated,
- repo pages settings not configured,
- insufficient token permissions.

Actions:
1. Run `gh auth status`.
2. Verify repo Pages configuration.
3. Re-run deploy with verbose logging.

### Problem: flaky tests in integration suite

Likely causes:
- shared temp directories,
- nondeterministic ordering,
- hidden environment assumptions.

Actions:
1. Isolate each test fixture directory.
2. Sort file iteration explicitly.
3. Avoid reliance on wall-clock time unless frozen in test.

## 20) Appendix A: Suggested Test File Map

```text
tests/
  unit/
    test_cli_help.py
    test_config_schema.py
    test_config_loader.py
    test_vault_link_resolver.py
    test_vault_link_manager.py
    test_content_discovery.py
    test_frontmatter_parser.py
    test_classification.py
    test_wikilinks_parser.py
    test_validate_rules.py
    test_render_kiln_adapter.py
    test_deploy_adapters.py
    test_init_patchers.py
  integration/
    test_cli_validate.py
    test_cli_check_links.py
    test_cli_build_dry_run.py
    test_cli_deploy_dry_run.py
    test_cli_init_idempotent.py
    test_cli_link_vault.py
  fixtures/
    direct_docs/
    mixed_docs_blog/
    symlink_repo/
    external_vault/
    broken_links/
    malformed_frontmatter/
```

## 21) Appendix B: Suggested Initial Milestone Breakdown

Milestone 1 (Days 1-2):
- Step 1 and Step 2
- Deliverable: runnable CLI stubs + config loader with tests

Milestone 2 (Days 3-4):
- Step 3 through Step 5
- Deliverable: symlink-aware content model + classification tests

Milestone 3 (Days 5-6):
- Step 6 through Step 9
- Deliverable: validation/build/deploy logic with dry-run coverage

Milestone 4 (Days 7-8):
- Step 10 through Step 12
- Deliverable: idempotent scaffolding and template rendering

Milestone 5 (Days 9-10):
- Step 13 and Step 14
- Deliverable: full integration suite passing + docs/handoff complete

Final review checklist:
- [ ] All tests pass locally (`devenv shell -- pytest tests/ -q`).
- [ ] No failing lint/format checks (if configured).
- [ ] Guide and CLI help output match implemented behavior.
- [ ] Symlink mode validated with a real external vault path.
- [ ] Maintainer can reproduce quickstart in a clean environment.
- [ ] Tests use canonical files from `tests/fixtures/` rather than inline-generated sample markdown/config content.
