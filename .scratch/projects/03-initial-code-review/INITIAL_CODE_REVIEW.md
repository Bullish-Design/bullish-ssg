# INITIAL_CODE_REVIEW

Status: Initial review of intern implementation
Date: 2026-04-03
Reference baseline: `../02-bullish-ssg-implementation-guide/IMPLEMENTATION_GUIDE.md`

## Table of Contents

1. Review Scope and Method  
   What was reviewed, and how implementation status was determined.
2. Current Build/Test Evidence  
   Objective execution results from the current repository state.
3. Findings (Ordered by Severity)  
   Concrete issues that must be fixed, with file/line grounding.
4. Step-by-Step Status vs Implementation Guide  
   Status of Steps 1-14: done, partial, or not started.
5. Required Fixes in Already-Started Steps  
   Work that must be corrected before moving deeper into later steps.
6. Remaining Work Not Yet Implemented  
   Breakdown of untouched steps and what must be added.
7. Recommended Next Execution Order for the Intern  
   Practical sequence to recover momentum without compounding debt.
8. Suggested Immediate PR Scope  
   Tight scope for the next commit set.

## 1) Review Scope and Method

This review compares current code to the numbered steps in `IMPLEMENTATION_GUIDE.md`.

Inputs reviewed:
- `src/bullish_ssg/**`
- `tests/**`
- `pyproject.toml`
- git history (`git log --oneline`)
- test execution output (`devenv shell -- pytest tests/ -q`)

Evaluation criteria:
- Is required module/command present?
- Is behavior aligned with the guide objective for that step?
- Is test coverage present for the step’s explicit test requirements?
- Are there blockers/regressions that must be fixed before proceeding?

## 2) Current Build/Test Evidence

Commands executed:

```bash
devenv shell -- uv sync --extra dev
devenv shell -- pytest tests/ -q
```

Observed result:
- Dependency sync succeeded.
- Test run failed with 1 failing unit test.
- Failure: `tests/unit/test_vault_link_resolver.py::TestVaultResolverSymlinkMode::test_symlink_mode_broken_link_fails`
- Coverage summary reported ~62% total.

Failure detail:
- Expected error text for broken symlink target (`"target does not exist"`) was not produced.
- Actual behavior reports missing symlink path due `Path.exists()` behavior on broken symlinks.

## 3) Findings (Ordered by Severity)

1. Broken-symlink detection bug in resolver (test suite currently failing)
- File: `src/bullish_ssg/vault_link/resolver.py:69-72`
- Problem: symlink existence check uses `link_path.exists()` before symlink-specific checks.
- Impact: broken symlink is misclassified as “symlink does not exist,” causing incorrect diagnostics and failing test.
- Evidence: failing test at `tests/unit/test_vault_link_resolver.py:100-119`.

2. Guide-required CLI integration into real logic is not implemented
- File: `src/bullish_ssg/cli.py:10-77`
- Problem: all commands are placeholders; they are not wired to config loader, resolver, validators, renderers, or deploy adapters.
- Impact: Step 2+ requirements around operational CLI behavior are not met.

3. Step 4 frontmatter testing requirements are missing
- File: `src/bullish_ssg/content/frontmatter.py:52-166`
- Problem: parser module exists, but there are no frontmatter unit tests.
- Impact: required test gates for malformed YAML, no-frontmatter, and parse resilience are not satisfied.

4. Step 5 implementation is incomplete and currently untracked
- File: `src/bullish_ssg/content/classify.py` (untracked in git status)
- Problem: classifier exists in working tree but has no tests and is not committed.
- Impact: step progress is not reproducible; classification behavior is unverified.

5. Step 5 behavioral gaps in classifier vs guide expectations
- File: `src/bullish_ssg/content/classify.py:126-150`
- Problem: post date parsing returns `None` for invalid/missing dates; it does not enforce required-date policy for posts.
- File: `src/bullish_ssg/content/classify.py:180-204`
- Problem: collision helper returns collisions but does not enforce a fail path in classifier flow.
- Impact: “misconfigured posts fail early” and “slug collision fails” requirements are not yet met.

6. Config schema has drift from guide contract
- File: `src/bullish_ssg/config/schema.py:17-100`
- Problem: key names and section shape differ from implementation guide examples (`site.title` vs `site.name`, `content.source_dir` vs `site.vault_dir`, etc.).
- Impact: future scaffolding/templates and docs may diverge from runtime behavior unless normalized now.

7. Step 6 onward are not started (except empty package placeholders)
- Files: `src/bullish_ssg/validate/__init__.py`, `render/__init__.py`, `deploy/__init__.py`, `init/__init__.py`, `integrations/__init__.py`, `reporting/__init__.py`
- Problem: no substantive implementations for validation engine, wikilink resolver, kiln adapter, deployment adapters, scaffolding patchers, template rendering, or integration tests.
- Impact: large backlog still pending after the initial foundational steps.

## 4) Step-by-Step Status vs Implementation Guide

| Step | Expected | Current Status | Notes |
|---|---|---|---|
| Step 1 | Package skeleton + CLI stubs + command help tests | Implemented | Good progress; command stubs and tests exist. |
| Step 2 | Config schema/loader + constraints + CLI integration touchpoint | Partially implemented | Schema/loader + tests exist; CLI integration not wired; contract drift from guide. |
| Step 3 | Vault symlink resolver/manager + safety + tests | Partially implemented | Core logic and tests exist; one failing test; broken symlink handling bug; source-target verification gap. |
| Step 4 | Discovery + frontmatter parser + tests for both | Partially implemented | Discovery and tests exist; frontmatter exists but no tests. |
| Step 5 | Classification/routing + collision/date enforcement + tests | In progress / partial | `classify.py` exists untracked; no tests; several required behaviors missing. |
| Step 6 | Wikilink parser/resolver + anchor checks + diagnostics tests | Not started | No `validate/wikilinks.py`; no tests. |
| Step 7 | `validate`/`check-links` command wiring + failure exit policy | Not started | CLI commands are placeholders only. |
| Step 8 | Kiln build/serve adapters + dry-run + adapter tests | Not started | No `render/kiln.py`; build/serve are stubs. |
| Step 9 | Deploy preflight + gh/branch adapters + dry-run tests | Not started | No deploy adapters; deploy command is stub. |
| Step 10 | `init` scaffolding + idempotent patchers + dry-run tests | Not started | No scaffold/patchers implementation. |
| Step 11 | `link-vault` command with manager + config sync + repair | Not started | Command prints only; no manager integration. |
| Step 12 | Template system for integrations + snapshot tests | Not started | No templates; no snapshot tests. |
| Step 13 | Integration fixtures + command-level integration tests | Not started | `tests/integration` effectively empty. |
| Step 14 | Docs + dry-run walkthrough + handoff checklist | Not started | `README.md` is effectively empty. |

## 5) Required Fixes in Already-Started Steps

These should be completed before starting Step 6+.

### A. Fix Step 3 regression immediately (blocking)

1. Update symlink detection logic to distinguish:
- path missing,
- path is symlink with missing target,
- path exists but not symlink.

2. Recommended fix direction:
- check `is_symlink()` before relying on `exists()`.
- for broken link handling, use symlink-aware existence semantics.

3. Re-run:

```bash
devenv shell -- pytest tests/unit/test_vault_link_resolver.py -q
```

Pass requirement:
- `test_symlink_mode_broken_link_fails` passes.

### B. Complete Step 4 test obligations for frontmatter

Add tests covering:
- valid frontmatter parse,
- malformed YAML error path,
- no-frontmatter file behavior,
- parse-safe behavior.

Run:

```bash
devenv shell -- pytest tests/ -k "frontmatter" -q
```

Pass requirement:
- frontmatter module behavior validated by dedicated tests.

### C. Stabilize Step 5 and commit it

1. Commit `src/bullish_ssg/content/classify.py` once reviewed and tested.
2. Add tests for:
- type inference,
- slug normalization,
- route generation,
- collision detection failure path,
- date requirement enforcement for posts.

Run:

```bash
devenv shell -- pytest tests/ -k "classify or route or slug" -q
```

Pass requirement:
- all Step 5 required behaviors are covered and passing.

### D. Resolve config contract drift now (decision required)

Choose one of:
1. Align runtime schema to guide contract.
2. Update guide contract to match chosen runtime schema.

Do not leave this ambiguous, because Steps 10-12 depend on config shape.

## 6) Remaining Work Not Yet Implemented

Unstarted implementation blocks from the guide:

- Step 6: Wikilink parser/resolver and heading validation engine.
- Step 7: `validate` and `check-links` real command implementations and exit code policy.
- Step 8: Kiln adapter (`generate`, `serve`) and subprocess error handling.
- Step 9: Deploy preflight + `gh pages` and branch adapters.
- Step 10: Idempotent `init` scaffolding and patchers.
- Step 11: Functional `link-vault` command (manager integration + config sync).
- Step 12: Template-based integration scaffolding (devenv/prek/workflow).
- Step 13: Integration fixtures and end-to-end test matrix.
- Step 14: README/docs, dry-run walkthrough, handoff notes.

## 7) Recommended Next Execution Order for the Intern

1. Fix the failing Step 3 resolver behavior and get test suite green again.
2. Add missing frontmatter tests (finish Step 4 quality gate).
3. Complete and commit Step 5 with tests.
4. Implement Step 6 and Step 7 together (shared validation path).
5. Implement Step 8 and Step 9 together (execution + deploy path).
6. Implement Step 10 and Step 11 together (`init` + `link-vault` UX).
7. Implement Step 12 templates.
8. Finish Step 13 integration tests.
9. Finish Step 14 docs/handoff.

## 8) Suggested Immediate PR Scope

Recommended next PR should be narrowly scoped to:
- Fix symlink broken-target detection in resolver.
- Add frontmatter unit tests.
- Add Step 5 tests and commit classifier once passing.

Target validation command for this PR:

```bash
devenv shell -- pytest tests/ -q
```

Acceptance for merging this PR:
- zero failing tests,
- no untracked core implementation files for completed steps,
- Steps 1-5 genuinely complete and test-backed.
