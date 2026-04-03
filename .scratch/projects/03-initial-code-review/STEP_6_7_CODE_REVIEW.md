# STEP 6/7 Code Review

## Scope
This review covers the intern’s attempted implementation of:
- Step 6: Wikilink parsing and resolution
- Step 7: Validation commands (`validate`, `check-links`)

Guide reference:
- `.scratch/projects/02-bullish-ssg-implementation-guide/IMPLEMENTATION_GUIDE.md` (Step 6 and Step 7 sections)

Code reviewed:
- `src/bullish_ssg/validate/wikilinks.py`
- `src/bullish_ssg/validate/rules.py`
- `src/bullish_ssg/cli.py`
- `tests/unit/test_wikilinks.py`
- `tests/unit/test_validate_rules.py`
- `tests/integration/test_cli_validate.py`

Test evidence command:
```bash
devenv shell -- pytest tests/unit/test_wikilinks.py tests/unit/test_validate_rules.py tests/integration/test_cli_validate.py -q
```

Result summary:
- Unit tests for Step 6 and Step 7 logic are largely passing.
- Integration tests for Step 7 currently fail (`9 failed`) due to test harness misuse (`cwd` argument to `CliRunner.invoke`).

---

## Findings (ordered by severity)

## 1) High: Step 7 integration tests are invalid due to `CliRunner.invoke(..., cwd=...)`
- File: `tests/integration/test_cli_validate.py` lines 113, 119, 126, 133, 139, 149, 187, 195, 205, 209, 213
- Problem: Typer/Click `CliRunner.invoke` in this environment does not accept `cwd`. Every test invocation with `cwd` fails before command logic executes.
- Evidence: test failures return `TypeError("Context.__init__() got an unexpected keyword argument 'cwd'")`.
- Impact: Step 7 acceptance criteria are not actually validated in integration tests.
- Required fix:
  - Replace `cwd=` strategy with `with runner.isolated_filesystem():` and copy sample fixtures into that filesystem, or use `monkeypatch.chdir(...)` before `invoke`.
  - Keep tests fixture-driven (sample files), not ad-hoc file construction.

## 2) High: Optional orphan validation is wired but not implemented
- File: `src/bullish_ssg/validate/rules.py` lines 278-281
- Problem: `ValidationRunner.run_full_validation(include_orphan_check=True)` reaches a `pass` placeholder.
- Impact: `bullish-ssg validate --include-orphans` does not perform the promised check from Step 7 requirements.
- Required fix:
  - Implement orphan analysis using discovered pages + incoming wikilink targets.
  - Add unit/integration coverage for `--include-orphans` behavior.

## 3) Medium: `check-links` stats are incorrect (`total_links` counts diagnostics, not links)
- File: `src/bullish_ssg/validate/rules.py` lines 390-407
- Problem: `total_links` increments only when a diagnostic exists, so healthy links are never counted.
- Impact: Step 7 output quality requirement (“total checks” visibility) is not met reliably.
- Required fix:
  - Count parsed links independently from diagnostics (e.g., parse each file first, then resolve each link, increment total for every parsed link).
  - Keep `broken_links` as error-only count.

## 4) Medium: Step 6 test coverage misses unpublished/excluded-page policy case from guide
- File: `tests/unit/test_wikilinks.py`
- Problem: guide explicitly requires testing links to excluded/unpublished pages (fail/warn per policy), but there is no such test and no policy hook in resolver.
- Impact: one of Step 6 required scenarios is unverified and currently undefined in implementation.
- Required fix:
  - Define policy behavior for excluded/unpublished targets.
  - Implement behavior in resolver/validator and add test coverage.

## 5) Medium: Step 7 integration tests currently create temporary files inline instead of using dedicated sample fixtures
- File: `tests/integration/test_cli_validate.py`
- Problem: tests build config/docs files in test bodies.
- Impact: conflicts with current project direction to validate against real sample fixture files/directories.
- Required fix:
  - Add fixture directories under `tests/fixtures/` for:
    - healthy validation case,
    - malformed frontmatter case,
    - broken-link case,
    - symlink-mode broken case.
  - Use `fixture_copy` and isolated test workspace.

## 6) Low: Unused parameter suggests unfinished Step 6 API surface
- File: `src/bullish_ssg/validate/wikilinks.py` line 335
- Problem: `build_page_index(..., slug_extractor: callable = None)` parameter is unused.
- Impact: dead API surface and confusion for future maintainers.
- Required fix:
  - Either implement custom slug extractor support or remove the parameter.

---

## Step-by-step status vs guide

## Step 6 (Wikilink parsing/resolution)
Implemented:
- Parser for `[[page]]`, `[[page|alias]]`, `[[page#heading]]`, `[[page#^block-id]]` exists.
- Page index exists.
- Heading extraction/normalization and anchor validation exists.
- Diagnostics include source file, line number, raw link reason.

Partially implemented / missing:
- Excluded/unpublished page policy behavior and tests are not present.

## Step 7 (Validation commands)
Implemented:
- `validate` command wired to config load, vault resolution, validation runner, summary, exit code.
- `check-links` command wired to wikilink validator + `fail_on_broken_links`.
- Frontmatter rule and symlink rule implementation exists.

Partially implemented / missing:
- Optional orphan check is not implemented (`pass` placeholder).
- Integration tests are broken by incorrect CLI runner usage.
- Reporting details are partially present but stats are incorrect for total link checks.
- Integration test suite needs conversion to sample fixture-driven approach.

---

## Prioritized fix plan for intern
1. Fix `tests/integration/test_cli_validate.py` harness (`cwd` removal) so tests execute CLI logic.
2. Convert Step 7 integration scenarios to sample fixture directories under `tests/fixtures/` and use `fixture_copy`.
3. Implement orphan check in `ValidationRunner.run_full_validation` and add tests for `--include-orphans`.
4. Correct `WikilinkValidator` stats accounting (`total_links`, `broken_links`) and assert it in tests.
5. Add Step 6 policy tests (excluded/unpublished targets) and implement policy behavior.
6. Remove or implement `slug_extractor` in `build_page_index`.

---

## Bottom line
The intern has built a meaningful portion of Steps 6 and 7, especially core parser/resolver and command wiring. The largest blockers are test validity (integration harness bug), missing orphan-check implementation, and incomplete alignment with fixture-driven testing/policy coverage required by the implementation guide.
