# Bullish-SSG Code Review

**Date:** 2026-04-03
**Reviewer:** Claude (automated)
**Version:** 0.1.0
**Scope:** Full codebase — architecture, code quality, tests, tooling, and readiness assessment

---

## Executive Summary

Bullish-SSG is an opinionated static-site generator library that bridges Obsidian vaults to GitHub Pages deployments. The project is **well-structured and functional** with 208 passing tests and 88% code coverage. The architecture is clean with clear separation of concerns across modules.

**Verdict: Solid foundation, but not production-ready.** There are several categories of issues ranging from a genuine bug to style modernization. The most impactful issues are a name-error bug in `patchers.py`, 27 mypy errors, and 68 ruff lint violations.

### Scorecard

| Category | Score | Notes |
|---|---|---|
| Architecture | **A** | Clean module separation, clear data flow |
| Code Quality | **B** | Good patterns, but lint/type issues |
| Test Coverage | **A-** | 88% coverage, 208 tests, good fixture use |
| Documentation | **B-** | README is adequate; inline docs good; AGENTS.md is a stub |
| CLI UX | **B+** | All 7 commands implemented; good error messages |
| Deployment Safety | **B** | Dry-run support everywhere; branch deployer is complex |
| Tooling Health | **C+** | mypy fails (27 errors), ruff fails (68 errors) |

---

## 1. Architecture Overview

### Module Map (3,697 LOC source, 3,076 LOC tests)

```
bullish_ssg/
├── cli.py                  # Typer CLI — 7 commands, single entry point
├── config/
│   ├── schema.py           # Pydantic v2 models (BullishConfig root)
│   ├── loader.py           # TOML loading + upward directory search
│   └── writer.py           # Config file mutation (upsert vault settings)
├── content/
│   ├── classify.py         # Content routing: page/post/doc + slug + permalink
│   ├── discovery.py        # File discovery with ignore patterns
│   └── frontmatter.py      # YAML frontmatter parsing via python-frontmatter
├── validate/
│   ├── rules.py            # FrontmatterValidator, SymlinkValidator, OrphanValidator, ValidationRunner, WikilinkValidator
│   └── wikilinks.py        # WikilinkParser (regex), PageIndex, HeadingExtractor, WikilinkResolver
├── vault_link/
│   ├── manager.py          # Symlink CRUD with repair/force modes
│   └── resolver.py         # Path resolution for direct/symlink vault modes
├── render/
│   └── kiln.py             # Subprocess adapter for external "kiln" tool
├── deploy/
│   ├── gh_pages.py         # `gh pages deploy` adapter
│   ├── branch_pages.py     # Git branch-based deploy workflow
│   └── preflight.py        # Pre-deploy validation (config, vault, build)
├── init/
│   ├── scaffold.py         # Orchestrates all init patchers
│   ├── patchers.py         # Idempotent file patchers (config, gitignore, devenv, etc.)
│   └── templates.py        # Template rendering for generated files
│   └── templates/          # .tmpl files for config, devenv, pre-commit, CI workflow
├── integrations/           # Empty — placeholder module
└── reporting/              # Empty — placeholder module
```

### Data Flow

```
User CLI → config/loader → vault_link/resolver → content/discovery
                                                      ↓
                                               content/frontmatter
                                                      ↓
                                               content/classify
                                                      ↓
                                   ┌──────────────────┴──────────────┐
                                   ↓                                 ↓
                            validate/rules                    render/kiln
                            validate/wikilinks                     ↓
                                                            deploy/preflight
                                                                   ↓
                                                         deploy/gh_pages OR
                                                         deploy/branch_pages
```

### Architectural Strengths

1. **Clean separation of concerns** — Each module has a single responsibility. The CLI is a thin shell that delegates to domain modules.
2. **Pydantic v2 config schema** — Typed, validated configuration with good defaults and alias support for backward compatibility.
3. **Idempotent scaffolding** — The `init` command uses a patcher pattern that safely merges/creates files without overwriting user customization.
4. **Dual vault modes** — The direct/symlink abstraction cleanly handles both "docs are in the repo" and "docs are in an external Obsidian vault" cases.
5. **Wikilink resolution pipeline** — Full Obsidian-compatible wikilink parsing with heading anchors, block references, aliases, and a page index for resolution.
6. **Dry-run support** — Every destructive command (build, serve, deploy, init) supports `--dry-run`.

### Architectural Concerns

1. **External `kiln` dependency is opaque** — The render module shells out to an external `kiln` binary. There's no documentation of what `kiln` is, where to install it, or what it expects. This is the single biggest usability gap.
2. **Placeholder modules** — `integrations/` and `reporting/` are empty stubs with no code. These should either be removed or their intended purpose documented.
3. **Bottom-of-file import** — `validate/rules.py:366` has imports at the bottom of the file to avoid circular dependencies. This is a code smell indicating the module is doing too much. The `WikilinkValidator` class should arguably live in `validate/wikilinks.py`.

---

## 2. Bugs

### BUG-1: Undefined name `PRECOMMIT_BLOCK` in patchers.py (CRITICAL)

**File:** `src/bullish_ssg/init/patchers.py:97`
**Severity:** Critical — will crash at runtime

```python
if "repos:" not in text:
    updated = "repos:\n" + PRECOMMIT_BLOCK  # ← NameError!
```

The variable `PRECOMMIT_BLOCK` is never defined. It should be `hook_block` (the local variable from line 85). This path is reached when a `.pre-commit-config.yaml` exists but doesn't contain `repos:`, which is an edge case but absolutely reachable.

**Confirmed by:** `mypy` reports `F821 undefined-name` and `mypy` reports `error: Name "PRECOMMIT_BLOCK" is not defined`.

### BUG-2: Unused variable in wikilinks.py

**File:** `src/bullish_ssg/validate/wikilinks.py:113`

```python
full_path = self.vault_path / relative_path  # never used
```

The `PageIndex.add_page` method constructs `full_path` but never uses it. This is harmless but indicates possibly incomplete logic (was it meant to verify the file exists?).

---

## 3. Type Safety (mypy: 27 errors)

### 3a. Missing type stubs (3 errors)

The `toml` library lacks type stubs. **Fix:** Add `types-toml` and `types-PyYAML` to dev dependencies, or migrate to `tomllib` (stdlib in Python 3.11+).

### 3b. Pydantic `default_factory` with `BaseModel` (15 errors)

```python
content: ContentConfig = Field(default_factory=lambda: ContentConfig())
```

mypy strict mode expects all named arguments when calling `ContentConfig()` because fields have defaults assigned via `Field()`, not as plain class attributes. This is a known Pydantic-mypy interaction issue. **Fix:** Install `pydantic[mypy]` plugin or use `model_config` to configure mypy compatibility.

### 3c. Type assignment in CLI deploy (1 error)

```python
adapter = GHPagesDeployer(config.deploy)
# ...
adapter = BranchPagesDeployer(config.deploy)  # type mismatch
```

Both deployers share an identical `deploy()` interface but don't share a protocol/ABC. **Fix:** Define a `Deployer` protocol or ABC.

### 3d. Missing type annotations in validate/rules.py (2 errors)

```python
diagnostics = []  # needs: list[ValidationDiagnostic]
```

### 3e. Generic dict without type args (1 error)

```python
def status(self) -> dict:  # should be dict[str, Any]
```

---

## 4. Lint Issues (ruff: 68 errors)

| Rule | Count | Description | Auto-fixable |
|------|-------|-------------|--------------|
| UP045 | 52 | `Optional[X]` → `X \| None` (PEP 604) | Yes |
| B008 | 3 | Mutable default in function args (Typer `Option()` calls — false positive) | No |
| I001 | 3 | Unsorted imports | Yes |
| UP035 | 3 | Deprecated import (`typing.Optional`) | Yes |
| F541 | 2 | f-string without placeholders | Yes |
| E402 | 1 | Module import not at top of file (circular import workaround in rules.py) | No |
| F821 | 1 | Undefined name (BUG-1 above) | No |
| F841 | 1 | Unused variable (BUG-2 above) | Yes |
| UP024 | 1 | `OSError` alias → use `OSError` directly | Yes |
| UP042 | 1 | `str(Enum)` → just `Enum` | No |

**61 of 68 are auto-fixable** with `ruff check --fix`. The remaining 7 need manual attention.

---

## 5. Test Quality Assessment

### 5a. Coverage Summary (88% overall)

| Module | Coverage | Gap Analysis |
|--------|----------|-------------|
| config/schema.py | 100% | Excellent |
| init/scaffold.py | 100% | Excellent |
| deploy/gh_pages.py | 100% | Excellent |
| validate/rules.py | 95% | Very good; uncovered: `validate_file` method on `WikilinkResolver` |
| render/kiln.py | 94% | Good; uncovered: `FileNotFoundError` and `SubprocessError` handlers |
| init/patchers.py | 93% | Good; uncovered: edge cases in devenv/pre-commit patcher |
| content/discovery.py | 91% | Good; uncovered: non-existent/non-dir vault path early returns |
| init/templates.py | 91% | Good; uncovered: validation error branches |
| validate/wikilinks.py | 90% | Good; uncovered: `validate_files` batch method, content cache path |
| config/writer.py | 90% | Good; uncovered: FileNotFoundError, non-dict vault section |
| content/frontmatter.py | 89% | Good; uncovered: property accessors, `_is_under_vault` edge |
| config/loader.py | 88% | Good; uncovered: `get_config_path` and `has_config` helpers |
| vault_link/resolver.py | 88% | Good; uncovered: non-dir vault, OSError in resolve, `_describe_path` |
| content/classify.py | 87% | Good; uncovered: some error branches, `slug` URL style |
| deploy/branch_pages.py | 85% | Acceptable; the actual deploy workflow steps are mostly untested (subprocess calls) |
| deploy/preflight.py | 79% | Weak; multiple checks have uncovered paths |
| cli.py | 76% | Acceptable for CLI; many branches are integration-level |
| vault_link/manager.py | 76% | Weakest non-CLI module; `repair`, `remove`, `status`, `_remove_path` largely untested |

### 5b. Test Structure Strengths

- **208 tests** organized cleanly into `unit/` and `integration/` directories
- **Fixture-driven** testing with dedicated `tests/fixtures/` tree covering configs, content, wikilinks, deploy scenarios
- **E2E matrix test** (`test_e2e_matrix.py`) exercises multiple fixture scenarios end-to-end
- **CLI testing** via `typer.testing.CliRunner` — good pattern
- **Good isolation** — tests use `tmp_path`, monkeypatch, and fixture copies

### 5c. Test Gaps

1. **`vault_link/manager.py` (76%)** — The symlink manager has real filesystem logic (create, repair, remove, force overwrite) that needs better coverage. `repair()`, `remove()`, and `status()` methods are substantially untested.
2. **`deploy/preflight.py` (79%)** — Several preflight check failure paths aren't exercised.
3. **No negative test for BUG-1** — The `PRECOMMIT_BLOCK` NameError isn't caught by any test because the specific code path (pre-commit exists but lacks `repos:`) is untested.
4. **No test for `deploy/branch_pages.py` actual deploy flow** — Only dry-run is tested. The real subprocess chain (checkout, rm, copy, commit, push) is uncovered.

---

## 6. Code Quality Details

### 6a. Strengths

- **Consistent docstrings** — Every public class and method has a docstring with Args/Returns/Raises sections.
- **Dataclass and Pydantic usage** — Clean data modeling with `@dataclass` for internal data and Pydantic for config.
- **Error hierarchy** — Custom exceptions per module (`SymlinkError`, `KilnError`, `FrontmatterParseError`, `ClassificationError`, `VaultResolutionError`, `SlugCollisionError`).
- **Safe defaults** — `parse_safe()`, `_load_config_if_present()`, and similar patterns provide graceful fallbacks.
- **Relative symlinks** — `VaultLinkManager` creates relative symlinks for portability, which is the right choice.

### 6b. Design Patterns

| Pattern | Where Used | Assessment |
|---------|-----------|------------|
| Adapter | `KilnAdapter`, `GHPagesDeployer`, `BranchPagesDeployer` | Good — isolates subprocess calls |
| Builder | `ContentClassifier`, `PageIndex` | Good — progressive construction |
| Runner/Result | `ValidationRunner` → `ValidationResult`, `SubprocessRunner` → `CommandResult` | Good — clean separation |
| Patcher/Scaffolder | `init/patchers.py` → `scaffold.py` | Good — idempotent file mutations |
| Factory | `conftest.py` fixtures | Good test pattern |

### 6c. Concerns

1. **`validate/rules.py` is 496 lines** and contains 6 classes + 1 helper function. This is the largest and most complex module. The bottom-of-file import and the co-location of `WikilinkValidator` (which heavily depends on `wikilinks.py` types) suggests this module should be split.

2. **ContentType is a `str` subclass, not an Enum:**
   ```python
   class ContentType(str):
       PAGE = "page"
       POST = "post"
       DOC = "doc"
   ```
   This is semantically an enum with string values. It should be `class ContentType(str, Enum)` for type safety and to prevent arbitrary string comparison. ruff UP042 flags this.

3. **`branch_pages.py` deploy flow is fragile** — The deployer performs a complex 8-step git workflow (checkout orphan branch, rm -rf, copy files, commit, push, checkout back). Errors mid-sequence could leave the repo in a bad state. The `finally` block only does `git checkout original_branch`, which may not be sufficient if the working tree is dirty.

4. **`get_deploy_url()` returns placeholder strings:**
   ```python
   return "https://<owner>.github.io/<repo>/"
   ```
   This is never resolved to actual values. It's displayed to the user in the success message, which is misleading.

5. **`cli.py` catches broad `Exception`** in multiple places:
   ```python
   except Exception as exc:  # Lines 133, 180, 327
   ```
   Some of these should be narrowed to specific exception types.

---

## 7. Dependencies Assessment

| Dependency | Version | Purpose | Assessment |
|------------|---------|---------|------------|
| `pydantic>=2.12.5` | Recent | Config schema validation | Good choice |
| `typer>=0.12.0` | Current | CLI framework | Good choice |
| `toml>=0.10.2` | Legacy | TOML parsing | **Should migrate to `tomllib`** (stdlib since 3.11, project requires 3.13) |
| `python-frontmatter>=1.0.0` | Current | YAML frontmatter | Good choice |

### Dependency Concern: `toml` vs `tomllib`

The project requires Python ≥3.13 but uses the third-party `toml` package instead of the stdlib `tomllib` (available since 3.11). This adds an unnecessary dependency and causes mypy stub issues. **However**, `tomllib` is read-only — writing TOML (needed by `config/writer.py`) would require `tomli_w` or keeping `toml` for writes only.

---

## 8. CLI Commands Review

All 7 documented commands are implemented:

| Command | Status | Dry-run | Error handling | Notes |
|---------|--------|---------|----------------|-------|
| `init` | Implemented | Yes | Good | Idempotent patchers |
| `link-vault` | Implemented | No | Good | Creates symlink + updates config |
| `validate` | Implemented | N/A | Good | Runs frontmatter + symlink checks |
| `check-links` | Implemented | N/A | Good | Full wikilink resolution |
| `build` | Implemented | Yes | Good | Delegates to Kiln |
| `serve` | Implemented | Yes | Good | Delegates to Kiln |
| `deploy` | Implemented | Yes | Good | Preflight + adapter selection |

**CLI Quality Notes:**
- Exit codes are consistent: 0 for success, 1 for user errors, 2 for config errors
- Error messages are actionable (e.g., "Run 'bullish-ssg init' first")
- `link-vault` properly validates target before symlink creation
- Deploy command runs preflight before attempting deployment

---

## 9. Security Considerations

1. **Subprocess injection** — `render/kiln.py` and `deploy/` modules pass paths to subprocess commands as list elements (not shell strings), which is the safe approach. No `shell=True` usage.
2. **Path traversal** — The vault resolver validates that paths exist and are directories. The symlink manager resolves paths before operating. No obvious traversal vulnerability.
3. **Force mode** — `link-vault --force` can `shutil.rmtree()` a directory. This is documented and gated behind an explicit flag, which is appropriate.
4. **No secrets in config** — The TOML config schema doesn't store credentials. Deploy relies on `gh` CLI auth.

---

## 10. Prioritized Issue List

### Critical (Fix Before Any Release)

| # | Issue | File | Effort |
|---|-------|------|--------|
| C1 | `PRECOMMIT_BLOCK` NameError (BUG-1) | `init/patchers.py:97` | 1 min |
| C2 | 27 mypy errors — type safety not enforced | Multiple | 1-2 hrs |
| C3 | 68 ruff violations — linter not clean | Multiple | 30 min (61 auto-fix + 7 manual) |

### High (Fix Before v0.2)

| # | Issue | File | Effort |
|---|-------|------|--------|
| H1 | No deployer protocol/ABC — type mismatch in CLI | `cli.py:305`, deploy modules | 30 min |
| H2 | `ContentType(str)` should be `ContentType(str, Enum)` | `content/classify.py:10` | 10 min |
| H3 | Migrate `toml` → `tomllib` + `tomli_w` (or keep `toml` for writes) | `config/loader.py`, `config/writer.py`, `init/patchers.py` | 1 hr |
| H4 | Circular import workaround in `validate/rules.py` | `validate/rules.py:365` | 1 hr (refactor) |
| H5 | Placeholder `get_deploy_url()` shows `<owner>` to user | `deploy/gh_pages.py:71`, `branch_pages.py:200` | 30 min |
| H6 | Improve `vault_link/manager.py` test coverage (76%) | Tests | 1-2 hrs |

### Medium (Nice to Have)

| # | Issue | File | Effort |
|---|-------|------|--------|
| M1 | Remove or document empty `integrations/` and `reporting/` modules | Multiple | 5 min |
| M2 | Document external `kiln` dependency in README | `README.md` | 15 min |
| M3 | Narrow `except Exception` catches in CLI | `cli.py` | 15 min |
| M4 | `branch_pages.py` deploy robustness (dirty worktree recovery) | `deploy/branch_pages.py` | 1 hr |
| M5 | Add test for pre-commit patcher edge case (BUG-1 path) | Tests | 15 min |
| M6 | AGENTS.md is a stub pointing to a scratch file | `AGENTS.md` | 15 min |
| M7 | Unused variable `full_path` in `PageIndex.add_page` | `validate/wikilinks.py:113` | 1 min |

### Low (Polish)

| # | Issue | File | Effort |
|---|-------|------|--------|
| L1 | `devenv.nix` doesn't include bullish-ssg validation task | `devenv.nix` | 5 min |
| L2 | `pyproject.toml` has commented-out URLs section | `pyproject.toml` | 1 min |
| L3 | `.codex` file exists with unknown purpose | Root | 1 min |

---

## 11. Recommendations

### Immediate Actions (Pre-release Gate)

1. **Fix BUG-1** — Change `PRECOMMIT_BLOCK` to `hook_block` on line 97 of `patchers.py`.
2. **Run `ruff check --fix src/`** — Auto-fixes 61 of 68 lint issues.
3. **Add `types-toml` and `types-PyYAML` to dev deps** — Or migrate to `tomllib`.
4. **Fix remaining ruff/mypy issues manually** — Especially the 7 non-auto-fixable ruff errors.

### Short-term Improvements

5. **Define a `Deployer` Protocol** — Unify `GHPagesDeployer` and `BranchPagesDeployer` under a common type.
6. **Split `validate/rules.py`** — Move `WikilinkValidator` to `validate/wikilinks.py` to eliminate the circular import.
7. **Resolve `get_deploy_url()`** — Either derive real URLs from git remote or remove the placeholder output.
8. **Increase `vault_link/manager.py` coverage** — Write tests for repair, remove, status, and force modes.

### Long-term Considerations

9. **Document `kiln` dependency** — Users need to know what to install and how.
10. **Consider replacing `kiln`** — If this is a custom tool, consider inlining the build logic or using a well-known SSG (MkDocs, Hugo, etc.) as the rendering backend.
11. **Add CI pipeline** — The GitHub Actions workflow template exists but isn't used by the project itself.
12. **Hook system** — `HookConfig` is defined but hooks are never executed in the build/deploy pipeline.

---

## 12. Conclusion

Bullish-SSG has a **well-designed architecture** and **solid test foundation** for an early-stage project. The module separation, config schema design, and wikilink resolution pipeline are particularly well done. The main gaps are:

1. One **actual bug** (NameError in patchers)
2. **Tooling not clean** (mypy and ruff both fail)
3. A few **incomplete features** (deploy URLs, hook execution, kiln documentation)
4. **Two empty placeholder modules** suggesting planned but unimplemented features

With the critical and high-priority fixes addressed (estimated 4-6 hours of work), this would be a solid v0.2 release candidate. The architecture is extensible and the test infrastructure is mature enough to support rapid iteration.
