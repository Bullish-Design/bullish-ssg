# bullish-ssg Implementation Overview

Status: Draft v1
Date: 2026-04-03
Audience: Maintainers and implementers of bullish-ssg

## Table of Contents

1. Vision and Product Scope  
   Defines what bullish-ssg is, who it serves, and the docs-first plus blog-capable target.
2. Core Principles (Opinionated Defaults)  
   Establishes the non-negotiable design constraints that guide implementation decisions.
3. Goals and Non-Goals  
   Clarifies what is in scope for v1 and what is intentionally deferred.
4. System Architecture  
   Describes the major runtime and build-time components and their responsibilities.
5. Content Model and Information Architecture  
   Defines how docs pages, blog posts, notes, and assets are represented and discovered.
6. Build Pipeline  
   Specifies the end-to-end generation flow from vault discovery through output artifacts.
7. URL, Routing, and Navigation Strategy  
   Defines canonical URL rules and navigation behavior across docs and blog modes.
8. Rendering and Presentation Requirements  
   Describes rendering behavior, theme expectations, and UX features powered by Kiln.
9. Configuration Specification (`bullish-ssg.toml`)  
   Defines the config surface, defaults, and precedence model.
10. CLI and Task Surface  
    Defines user-facing commands and how they map to internal orchestrator behavior.
11. Integration Contracts (devenv, prek, Act, GitHub Pages)  
    Specifies how local automation and optional CI integrate with bullish-ssg.
12. Validation and Quality Gates  
    Defines link validation, frontmatter checks, publish filters, and build blocking rules.
13. Scaffolding and Repo Mutation Policy (`init`)  
    Defines idempotent repo setup behavior and safe file-editing strategy.
14. Deployment Model  
    Specifies primary and fallback deployment methods and prerequisites.
15. Requirements (Functional and Non-Functional)  
    Consolidates implementation requirements into testable statements.
16. Reference Package Structure  
    Proposes a concrete Python package/module layout for implementation.
17. Testing Strategy  
    Defines test layers and minimum coverage for reliable operation.
18. Migration Guidance (Zensical-era Concepts to Kiln-native)  
    Maps prior assumptions to the new implementation direction.
19. Phased Delivery Plan  
    Breaks implementation into practical delivery phases with exit criteria.
20. Risks and Mitigations  
    Lists major project risks and how to reduce them.
21. Initial Open Decisions  
    Captures choices that should be finalized early in implementation.

## 1) Vision and Product Scope

`bullish-ssg` is an opinionated library/CLI that turns an Obsidian vault into a GitHub Pages website with minimal per-repo setup and a local-first workflow.

Primary scope for v1:
- Docs-centric publishing from Obsidian markdown with native Obsidian syntax support.
- GitHub Pages deployment with `gh pages deploy` as default.
- Reproducible local workflow through devenv + prek.
- Built-in support for linking `docs/` to an external Obsidian vault via symlink.

Secondary scope for v1 (enabled, but not the primary UX path):
- Blog/article publishing in the same site using frontmatter + directory conventions.
- Hybrid docs + blog information architecture in one vault/repo.

Long-term scope:
- Reusable across many repos with stable conventions, low maintenance overhead, and strong default quality gates.

## 2) Core Principles (Opinionated Defaults)

1. Obsidian-native first.
- No markdown preprocessing layer for core Obsidian constructs (`[[wikilinks]]`, callouts, embeds, `.canvas`, tags).
- Kiln is the default renderer because it directly supports the required syntax.

2. Local-first delivery loop.
- Build, validate, preview, and deploy should run locally.
- CI is optional safety net, not the primary execution path.

3. Minimal per-repo ceremony.
- One config file (`bullish-ssg.toml`), a predictable task/hook setup, and idempotent scaffolding.
- Avoid template sprawl and avoid requiring a separate “docs infrastructure” repo.
- Keep repo-local content path contract (`docs/`) while allowing external vault storage through managed symlinks.

4. Safe automation.
- `init` must be additive/idempotent and avoid destructive rewrites.
- Validation failures should block unsafe deploys.

5. Docs-first, blog-capable.
- Docs workflows should feel frictionless.
- Blog/article support should share the same primitives rather than introducing a second toolchain.

## 3) Goals and Non-Goals

Goals:
- Convert Obsidian vault content into a polished static site for GitHub Pages.
- Ship a stable CLI surface: `init`, `build`, `serve`, `deploy`, `validate`, `check-links`.
- Support mixed content types (docs + posts) with clear URL and navigation rules.
- Integrate with devenv tasks and prek hooks out-of-the-box.
- Enforce structural quality (frontmatter validity, internal link integrity, publish filtering).

Non-goals (v1):
- Replacing Kiln’s renderer/theming engine with a custom templating system.
- A plugin marketplace or fully dynamic extension runtime.
- Multi-target host support beyond GitHub Pages parity (Netlify/Cloudflare can come later).
- Full CMS/editor UI; Obsidian remains the authoring environment.

## 4) System Architecture

High-level component model:

1. CLI Layer (`bullish_ssg.cli`)
- Parses command line inputs.
- Resolves config and workspace context.
- Dispatches to application services.

2. Config Layer (`bullish_ssg.config`)
- Loads `bullish-ssg.toml`.
- Applies defaults and normalization.
- Validates schema and reports actionable errors.

3. Vault Link Resolver (`bullish_ssg.vault_link`)
- Resolves effective vault source when `docs/` is a symlink.
- Validates that symlink target exists and is readable before build/serve/deploy.
- Creates/repairs the symlink when requested by `init`/`link-vault`.

4. Content Index Layer (`bullish_ssg.content`)
- Discovers files in `vault_dir`.
- Parses frontmatter and computes logical content types.
- Builds an internal content graph (pages, posts, assets, links).

5. Validation Layer (`bullish_ssg.validate`)
- Frontmatter policy checks.
- Publish visibility checks.
- Wikilink resolution and orphan detection.

6. Renderer Adapter Layer (`bullish_ssg.render`)
- Invokes Kiln with the resolved project config.
- Encapsulates command invocation, arguments, and errors.
- Keeps renderer-specific logic isolated for future extensibility.

7. Deploy Layer (`bullish_ssg.deploy`)
- Executes deployment flow.
- Supports `gh pages deploy` (primary) and `gh-pages` branch (fallback).
- Performs preflight checks before side effects.

8. Scaffolding Layer (`bullish_ssg.init`)
- Creates/updates project files (`bullish-ssg.toml`, `devenv.nix`, `.pre-commit-config.yaml`, `.gitignore`).
- Performs idempotent targeted edits.

9. Integration Templates (`bullish_ssg.templates`)
- Owns canonical task/hook/workflow snippets used by `init`.

## 5) Content Model and Information Architecture

Canonical content classes:

1. Docs pages
- Default content class for markdown files in `vault_dir`.
- Hierarchy driven by filesystem structure.

2. Blog posts/articles
- Identified by either:
  - Frontmatter `type = "post"`, or
  - Path under configured blog roots (default: `blog/`, `posts/`).
- Requires date/slug normalization for stable ordering and URLs.

3. Standalone pages
- Identified by `type = "page"` when explicit routing is needed.

4. Assets
- Binary/static files referenced by embeds or links.

Recommended frontmatter schema (v1 baseline):

```yaml
---
title: "Readable Title"
description: "Short summary"
publish: true
draft: false
slug: "custom-url-segment"
type: "doc"      # doc | post | page
date: 2026-04-03  # required for type=post
updated: 2026-04-03
tags: ["docs", "release"]
category: "guides"
order: 10
canonical_url: "https://example.com/path/"
---
```

Classification rules:
- If `publish` is explicitly `false`, exclude from output regardless of type.
- If `draft` is `true`, exclude from production build unless `--include-drafts` is passed.
- If no `type` is set, infer from path conventions; fallback to `doc`.

## 6) Build Pipeline

Pipeline phases for `bullish-ssg build`:

1. Load config + environment context.
2. Resolve vault source path (`docs/` direct directory or `docs/` symlink target).
3. Discover vault files and parse content metadata.
4. Apply publish filtering and type classification.
5. Run validation suite (or quick subset with `--quick`).
6. Invoke Kiln generation with resolved paths and site metadata.
7. Post-build checks:
- required output dirs exist,
- optional sitemap/canonical URL consistency checks,
- link-check pass against generated structure.
8. Emit build summary:
- counts by content type,
- effective vault source path (including resolved symlink target),
- skipped files,
- warnings/errors,
- output path.

Output contract:
- Deterministic output directory (`site_dir`, default `site/`).
- Non-zero exit on validation/build failure.
- Human-readable summary plus machine-readable JSON report (optional `--report`).

## 7) URL, Routing, and Navigation Strategy

Base URL strategy:
- `site.url` is authoritative and required for canonical URL generation.
- Support repository subpath deployments (`https://owner.github.io/repo/`) without broken links.

Default routing model:
- Docs: `/...` path mirrors vault structure (minus file extension).
- Blog: `/blog/<slug>/` or `/blog/<yyyy>/<mm>/<slug>/` (configurable).
- Index pages:
  - Root index resolved from `index.md`.
  - Section indexes resolved from directory `index.md` files.

Navigation model:
- Docs navigation primarily file-tree derived.
- Blog navigation supports reverse-chronological listing by `date`.
- Preserve Kiln-native graph/search experience for cross-link discovery.

Slug policy:
- Prefer explicit `slug` when provided.
- Otherwise derive from filename with stable normalization (lowercase, dash-separated).
- On collisions, fail with actionable error.

## 8) Rendering and Presentation Requirements

Renderer choice for v1:
- Kiln is required/default renderer.
- `bullish-ssg` is an orchestration layer, not a replacement renderer.

Required UX capabilities in generated site:
- Full Obsidian markdown parity for supported syntax.
- Full-text search.
- Graph view (global/local where Kiln supports it).
- Theme mode support (light/dark/auto).
- SEO baseline outputs (sitemap, meta descriptions, canonical URL support).

Presentation policy:
- Theme choices are exposed as config options but constrained to known-good defaults.
- Avoid bespoke styling systems in v1; leverage Kiln’s native theme model.

## 9) Configuration Specification (`bullish-ssg.toml`)

Top-level sections:

```toml
[site]
name = "My Site"
url = "https://owner.github.io/repo/"
description = "Project docs and updates"
vault_dir = "docs"
site_dir = "site"

[site.theme]
name = "default"
mode = "auto" # light | dark | auto

[content]
default_type = "doc"
blog_dirs = ["blog", "posts"]
posts_url_style = "date-slug" # date-slug | slug

[vault]
mode = "direct" # direct | symlink
source_path = "" # required when mode = "symlink" (absolute or repo-relative)
link_path = "docs" # in-repo path that should point to source_path
ignore_patterns = [".obsidian/**", ".trash/**", "templates/**"]
publish_key = "publish"
publish_default = true

[validation]
fail_on_broken_wikilinks = true
fail_on_orphans = false
require_post_date = true

[deploy]
method = "gh-pages" # gh-pages (gh CLI) | branch
branch = "main"
pages_branch = "gh-pages"

[hooks]
pre_commit = ["validate-frontmatter", "trailing-whitespace", "end-of-file-fixer"]
pre_push = ["build-site", "check-links"]
```

Config precedence:
1. CLI flags
2. Environment variables (optional mapped subset)
3. `bullish-ssg.toml`
4. internal defaults

Config validation rules:
- `site.url` must be absolute URL and end with `/`.
- `vault_dir`/`link_path` must exist as a directory in `direct` mode.
- In `symlink` mode, `link_path` must exist as a symlink and resolve to `source_path`.
- In `symlink` mode, resolved `source_path` must exist and be readable.
- `site_dir` must not be nested under ignored patterns.
- Deploy method-specific fields must be present.

## 10) CLI and Task Surface

Primary CLI commands:

1. `bullish-ssg init`
- Interactive or non-interactive scaffold setup.
- Writes/merges required repo files.
- Supports selecting `vault.mode` and creating `docs/` symlink to external vault.

2. `bullish-ssg link-vault`
- Creates or updates `docs/` symlink to a target Obsidian vault path.
- Updates `bullish-ssg.toml` (`vault.mode`, `source_path`, `link_path`) idempotently.

3. `bullish-ssg build`
- Runs full local build pipeline.
- Supports `--quick` and `--include-drafts`.

4. `bullish-ssg serve`
- Runs local preview via Kiln.
- Uses same config and publish filtering expectations as build.

5. `bullish-ssg validate`
- Frontmatter + publish policy checks.

6. `bullish-ssg check-links`
- Wikilink resolution checks with file/line diagnostics.

7. `bullish-ssg deploy`
- Runs preflight + build + deployment.

Expected command semantics:
- Predictable exit codes.
- Clear structured errors.
- No hidden side effects beyond explicit command intent.

## 11) Integration Contracts (devenv, prek, Act, GitHub Pages)

devenv integration requirements:
- Provide canonical tasks:
  - `ssg:build`
  - `ssg:deploy`
  - `ssg:validate`
  - `ssg:ci` (optional)
- Use `execIfModified` for docs-driven rebuild efficiency.
- In symlink mode, task inputs remain repo-local (`docs/**`) so tooling still runs from repo root.
- Provide docs preview process for `devenv up`.

prek integration requirements:
- Pre-commit hooks must be fast (`validate --quick`, formatting sanity checks).
- Pre-push hooks can be heavier (`build`, `check-links`).
- Hook setup must be generated by `init` and remain editable by users.

Act integration requirements (optional):
- If workflow exists, it should mirror local build commands.
- `ssg:ci` should run local workflow simulation consistently.

GitHub Pages contract:
- Primary deployment: `gh pages deploy <site_dir>`.
- Repo must be configured for Pages with GitHub Actions source when using artifact deploy mode.

## 12) Validation and Quality Gates

Validation categories:

1. Frontmatter schema validation.
- Type checks and required keys by content type.
- Date parsing and normalized format checks for posts.

2. Link integrity validation.
- Resolve Obsidian wikilinks and heading anchors.
- Report broken links with file + line context.

3. Publish policy validation.
- Ensure unpublished/draft content is excluded unless explicitly included.

4. Structural validation.
- Detect duplicate slugs.
- Detect missing `index.md` at critical roots when required by configured IA profile.

5. Symlink health validation.
- Verify `link_path` exists and is a symlink in `symlink` mode.
- Verify resolved target exists and is readable.
- Fail with remediation message if symlink is broken or points to wrong target.

Failure policy:
- By default, broken links and invalid frontmatter fail build/deploy.
- Orphan checks default to warnings unless configured as errors.

## 13) Scaffolding and Repo Mutation Policy (`init`)

`init` must be idempotent and safe:
- Re-running should converge, not duplicate entries.
- Existing user config should be preserved whenever possible.

Mutation strategy by file:

1. `bullish-ssg.toml`
- Create if missing.
- Merge missing keys conservatively when existing file is present.

2. `.gitignore`
- Append `site/` and vault-local ignores only if absent.

3. `.pre-commit-config.yaml`
- Insert/merge required hooks without removing unrelated hooks.

4. `devenv.nix`
- Add required packages/tasks/scripts/processes with minimal diff footprint.
- Prefer marker-based insertion or AST-aware patching when feasible.

5. `docs/index.md`
- Create starter page only when target vault root is absent.

6. `docs/` symlink (when configured)
- If `vault.mode = "symlink"`, create or update `link_path` as symlink to `source_path`.
- If `link_path` already exists as non-symlink, fail with clear error and require explicit override flag.
- Never silently replace existing directories/files at `link_path`.

## 14) Deployment Model

Primary (default): `gh pages deploy`
- Prerequisites:
  - `gh` installed and authenticated.
  - repo Pages configured for workflow/artifact deployment.
- Flow:
  1. preflight validation,
  2. build,
  3. deploy artifact from `site_dir`.

Fallback: branch deployment (`gh-pages` branch)
- Used when API artifact deployment is not viable.
- Requires explicit config selection.

Deployment invariants:
- Never deploy when validation/build fails.
- Log deployed target URL and deployment method.

## 15) Requirements (Functional and Non-Functional)

Functional requirements:
- FR-1: Must render Obsidian-native markdown constructs without preprocessing.
- FR-2: Must support docs-only and docs+blog vaults.
- FR-3: Must provide idempotent initialization of repo automation files.
- FR-4: Must validate frontmatter and wikilinks before deploy.
- FR-5: Must deploy to GitHub Pages via default local-first path.
- FR-6: Must support external Obsidian vaults by managing a repo-local `docs/` symlink target.
- FR-7: Must run build/serve/deploy consistently when `docs/` is symlinked.

Non-functional requirements:
- NFR-1: Deterministic builds with consistent output paths.
- NFR-2: Fast feedback for quick validation path (`<2s` target on small repos).
- NFR-3: Clear diagnostics with actionable errors.
- NFR-4: Minimal external dependencies beyond documented stack.
- NFR-5: Maintainable architecture with isolated renderer/deployer adapters.
- NFR-6: Symlink behavior should be stable across Linux/macOS; unsupported platforms must fail with explicit guidance.

## 16) Reference Package Structure

```text
src/bullish_ssg/
  __init__.py
  cli.py
  config/
    __init__.py
    schema.py
    loader.py
  vault_link/
    __init__.py
    resolver.py
    manager.py
  content/
    __init__.py
    discovery.py
    frontmatter.py
    classify.py
    graph.py
  validate/
    __init__.py
    frontmatter_rules.py
    wikilinks.py
    orphans.py
  render/
    __init__.py
    kiln.py
  deploy/
    __init__.py
    gh_pages.py
    branch_pages.py
    preflight.py
  init/
    __init__.py
    scaffold.py
    patchers.py
    templates/
  integrations/
    devenv.py
    prek.py
    actions.py
  reporting/
    summary.py
    diagnostics.py
```

## 17) Testing Strategy

Test layers:

1. Unit tests
- frontmatter parsing/validation,
- link resolution,
- classification/routing decisions,
- config loading and defaults.

2. Snapshot/fixture tests
- representative vaults (docs-only, blog-only, mixed) with expected build reports.

3. Integration tests
- command execution paths (`build`, `validate`, `check-links`, `deploy --dry-run`).
- scaffolding idempotency tests across pre-existing repo states.
- symlink flows: create, repair, and fail-fast on broken targets.

4. E2E smoke tests
- small fixture repo built and deployed in dry-run mode.
- optional live deploy test gated by env vars/credentials.

Minimum v1 test gate:
- All command paths covered by at least one integration test.
- Scaffold idempotency verified on repeated runs.
- Broken link and invalid frontmatter failure modes explicitly tested.

## 18) Migration Guidance (Zensical-era Concepts to Kiln-native)

Mappings:
- Zensical preprocessing assumptions -> removed.
- MkDocs-like strict nav config -> replaced by vault-structure-first navigation.
- CI-centric workflow -> replaced by local-first `devenv + prek + gh deploy`.

What remains compatible:
- Concept of opinionated defaults.
- Strong validation prior to deploy.
- Optional CI workflow as backup automation.

Migration recommendation:
- Treat Kiln as the rendering baseline.
- Retain old Zensical notes only as historical rationale, not implementation dependencies.

## 19) Phased Delivery Plan

Phase 0: Foundation and contracts
- Finalize config schema + CLI contracts.
- Exit criteria: frozen v1 interfaces for `init/link-vault/build/serve/deploy/validate/check-links`.

Phase 1: Build + validate core
- Implement config loading, vault symlink resolver, content discovery, frontmatter checks, wikilink checks, Kiln adapter.
- Exit criteria: `build`, `validate`, `check-links` stable on mixed-content fixtures.

Phase 2: Scaffolding + integrations
- Implement `init`/`link-vault` patchers for `.gitignore`, `.pre-commit-config.yaml`, `devenv.nix`, config bootstrap, and symlink management.
- Exit criteria: repeated `init` and `link-vault` are idempotent across representative repo states.

Phase 3: Deployment + CI parity
- Implement deploy adapters and optional workflow generation/testing guidance.
- Exit criteria: successful local deploy path and documented fallback branch deploy.

Phase 4: Hardening for multi-repo adoption
- Broaden fixtures, improve diagnostics, tighten docs.
- Exit criteria: trial rollout across multiple repos with minimal manual edits.

## 20) Risks and Mitigations

1. Kiln capability gaps for edge Obsidian plugins.
- Mitigation: explicit compatibility matrix + publish ignore patterns + warning diagnostics.

2. Complex repo patching during `init`.
- Mitigation: conservative patch strategy, dry-run mode, and idempotency tests.

3. URL breakage under GitHub Pages subpaths.
- Mitigation: strict `site.url` validation and link integrity checks post-build.

4. Broken symlink or moved external vault path.
- Mitigation: preflight symlink health checks and `link-vault --repair` workflow.

5. Drift between local and optional CI workflows.
- Mitigation: single source of commands; CI should call same bullish-ssg commands.

6. Over-expanding scope into generic CMS features.
- Mitigation: enforce docs-first and local-first constraints in milestone reviews.

## 21) Initial Open Decisions

1. Post URL format default:
- `date-slug` vs `slug`.

2. Draft handling behavior in `serve`:
- include drafts by default in local preview, or require explicit flag.

3. Orphan policy default:
- warning vs hard fail.

4. Depth of `devenv.nix` patching:
- marker-based text patching vs structured parser approach.

5. Optional renderer abstraction in v1:
- keep Kiln-only adapter now, or define abstract renderer interface from day one.

6. Symlink path policy:
- store `source_path` as absolute path, repo-relative path, or support both with normalization.

Recommendation for v1:
- Choose the simplest approach that preserves clean extension seams: Kiln-only concrete adapter, but with module boundaries that make a second adapter possible later.
