# Demo Site Implementation Runbook

## Table of Contents
1. Scope and Deliverables
   What this demo must contain and what success looks like.
2. Directory Architecture
   Required content structure for publishable docs/blog and negative test fixtures.
3. Phase 0: Environment and Branch Setup
   Preconditions before writing content.
4. Phase 1: Baseline Scaffolding
   Initialize demo workspace and baseline config.
5. Phase 2: Core Documentation Content
   Build the main docs navigation and foundational pages.
6. Phase 3: Feature Demonstration Content
   Add feature pages covering vault linking, validation, rendering, and deploy behavior.
7. Phase 4: Blog and Classification Coverage
   Add post content and verify type/date routing assumptions.
8. Phase 5: Negative Test Fixtures (Non-Published)
   Add intentional failures for validation/check-links verification.
9. Phase 6: Command Verification Matrix
   Run all 7 CLI commands with explicit pass/fail expectations.
10. Phase 7: Deployment Readiness and Publish
    Dry-run deployment, optional live deploy, and evidence capture.
11. Acceptance Criteria Checklist
    Final go/no-go list.
12. Handoff Package
    Required artifacts for maintainer/intern handoff.

## 1) Scope and Deliverables

This demo site has two outputs:
- Publishable demo docs/blog site that should be valid and deployable.
- Non-published negative fixtures that intentionally fail targeted checks.

Required deliverables:
- Demo content tree (healthy) with getting-started, features, reference, and blog sections.
- Negative fixture tree (broken links/frontmatter) for test-only verification.
- Verification evidence that all 7 CLI commands were exercised.
- Deployment dry-run evidence and optional live deployment record.

## 2) Directory Architecture

Recommended structure:

```text
demo/
  healthy/
    bullish-ssg.toml
    docs/
      index.md
      getting-started/
      features/
      reference/
      blog/
    site/               # generated output (or precreated for dry-run deploy checks)
  broken/
    broken-links/
      bullish-ssg.toml
      docs/
    malformed-frontmatter/
      bullish-ssg.toml
      docs/
```

Rules:
- `demo/healthy/docs/` is the only tree intended for publish.
- `demo/broken/*` must never be used as deploy source.

## 3) Phase 0: Environment and Branch Setup

1. Create branch:
```bash
git checkout -b feat/demo-site-plan-execution
```
2. Sync environment:
```bash
devenv shell -- uv sync --extra dev
```
3. Verify tooling:
```bash
devenv shell -- python --version
devenv shell -- pytest --version
devenv shell -- bullish-ssg --help
```

Testing checkpoint:
- All commands return exit code `0`.

## 4) Phase 1: Baseline Scaffolding

1. Create `demo/healthy/` workspace.
2. From `demo/healthy`, run:
```bash
devenv shell -- bullish-ssg init
```
3. Confirm generated files:
- `bullish-ssg.toml`
- `.gitignore` additions
- `.pre-commit-config.yaml` hook entry
- `devenv.nix` snippet
- `docs/index.md`

Testing checkpoint:
```bash
devenv shell -- bullish-ssg init --dry-run
```
Expected:
- Exit `0`
- Output includes `No changes needed` or dry-run no-op equivalent.

## 5) Phase 2: Core Documentation Content

Create and link:
- `docs/index.md`
- `docs/getting-started/index.md`
- `docs/getting-started/quickstart.md`
- `docs/getting-started/configuration.md`
- `docs/reference/index.md`
- `docs/reference/cli-commands.md`
- `docs/reference/config-options.md`

Content requirements:
- Use valid frontmatter where needed.
- Add wikilinks between hub pages and detail pages.
- Include at least one heading-anchor wikilink example.

Testing checkpoint:
```bash
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
```
Expected:
- Both exit `0`.

## 6) Phase 3: Feature Demonstration Content

Add pages:
- `docs/features/index.md`
- `docs/features/vault-linking.md`
- `docs/features/content-discovery.md`
- `docs/features/frontmatter.md`
- `docs/features/classification.md`
- `docs/features/wikilinks.md`
- `docs/features/validation.md`
- `docs/features/build-and-serve.md`
- `docs/features/deploy.md`

Coverage requirements:
- Show `[[page]]`, `[[page|alias]]`, and `[[page#heading]]` examples.
- Mention block-ref case as warning-only behavior.
- Include direct mode and symlink mode explanation.

Testing checkpoint:
```bash
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
```
Expected:
- Exit `0` for both.

## 7) Phase 4: Blog and Classification Coverage

Add blog posts under `docs/blog/` with frontmatter:
- `type: post`
- `date: YYYY-MM-DD`
- `slug: ...`

Minimum posts: 3
- hello world
- feature showcase
- advanced topics

Testing checkpoint:
- Classification and route behavior via tests:
```bash
devenv shell -- pytest tests/unit/test_classify.py -q
```
- Site-level checks:
```bash
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
```
Expected:
- All pass.

## 8) Phase 5: Negative Test Fixtures (Non-Published)

Create under `demo/broken/`:
- `broken-links` fixture with missing wikilink targets.
- `malformed-frontmatter` fixture with invalid YAML frontmatter.

Important:
- Keep these out of publish tree.

Testing checkpoint:
- Broken links should fail:
```bash
# from broken-links workspace
devenv shell -- bullish-ssg check-links
```
Expected: non-zero exit.

- Malformed frontmatter should fail:
```bash
# from malformed-frontmatter workspace
devenv shell -- bullish-ssg validate
```
Expected: non-zero exit.

## 9) Phase 6: Command Verification Matrix

Run and record result for each command in `demo/healthy`:

1. `init --dry-run`
- Expected: exit `0`, no destructive writes.

2. `link-vault <path>` (run in dedicated symlink-mode demo copy)
- Expected: exit `0`, `docs` becomes symlink, config vault section updated.

3. `validate`
- Expected: exit `0` in healthy; non-zero in malformed fixture.

4. `check-links`
- Expected: exit `0` in healthy; non-zero in broken-links fixture.

5. `build --dry-run`
- Expected: exit `0`, output contains `kiln generate` command.

6. `serve --dry-run`
- Expected: exit `0`, output contains `kiln serve` command.

7. `deploy --dry-run`
- Expected: exit `0`, preflight passes, output contains deploy command.

## 10) Phase 7: Deployment Readiness and Publish

1. Ensure `deploy.site_dir` exists for dry-run deploy checks.
2. Run:
```bash
devenv shell -- bullish-ssg deploy --dry-run
```
3. If publishing live:
```bash
devenv shell -- bullish-ssg deploy
```

Testing checkpoint:
- Dry-run must pass before live deploy.
- Capture output proving preflight succeeded.

## 11) Acceptance Criteria Checklist

- [ ] Healthy demo docs/blog validate successfully.
- [ ] Healthy demo has zero broken wikilinks.
- [ ] Broken fixtures fail in expected ways.
- [ ] All 7 CLI commands executed and recorded.
- [ ] Build and deploy dry-runs show expected commands.
- [ ] Optional live deploy succeeds (if enabled).

## 12) Handoff Package

Provide:
- Demo directory tree summary.
- Command verification log (command, exit code, key output line).
- Screenshots or copied output for `validate`, `check-links`, `build --dry-run`, and `deploy --dry-run`.
- Notes on any known limitations and follow-up tasks.
