# bullish-ssg: Opinionated Obsidian → GitHub Pages

## Concept Document

**Status:** Draft v3 — Revised for local-first tooling
**Last Updated:** 2026-04-03
**Related:** [ZENSICAL_RESEARCH.md](./ZENSICAL_RESEARCH.md), [GITHUB_PAGES_INTEGRATION.md](./GITHUB_PAGES_INTEGRATION.md), [REPO_DOCS_STRATEGY.md](./REPO_DOCS_STRATEGY.md)

---

## 1. Problem Statement

We need an **opinionated, low-friction way** to turn Obsidian vault pages into professional websites hosted on GitHub Pages. The solution must:

- Accept **Obsidian Markdown** as-is — wikilinks, callouts, embeds, canvas, tags
- Produce a **polished static site** with search, graph view, light/dark mode
- Be **fully local-first** — no dependence on GitHub Actions for the build/deploy loop
- Use **devenv.sh** for environment management and task orchestration
- Use **prek** for git hook automation (build validation, link checking)
- Use **Act** for local CI testing when GitHub Actions workflows exist
- Be **reusable** across multiple repos/vaults with minimal per-repo config
- Require **zero Obsidian-to-Markdown preprocessing** — the SSG handles the dialect natively

### What Changed from v2

v2 was built around Zensical (MkDocs Material successor) + GitHub Actions reusable workflows + Copier templates. Three problems:

1. **Zensical doesn't speak Obsidian** — wikilinks, callouts, embeds all need preprocessing
2. **GitHub Actions dependency** — the entire build/deploy loop lived in CI, making local iteration slow
3. **Copier adds a dependency** — another tool to install and maintain across repos

v3 replaces the stack:
- **Kiln** instead of Zensical — native Obsidian support, zero preprocessing
- **devenv.sh tasks** instead of GitHub Actions — local-first automation
- **prek** instead of pre-commit — Rust-based, single binary, git hook management
- **Act** for local CI testing — run workflows without pushing

---

## 2. Architecture

### 2.1 The Stack

```
┌─────────────────────────────────────────────────────────────┐
│                     bullish-ssg                              │
│                                                              │
│  Python library that orchestrates:                           │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Kiln    │  │ devenv   │  │  prek    │  │   Act    │   │
│  │  (SSG)   │  │  (env +  │  │ (hooks)  │  │  (CI)    │   │
│  │          │  │  tasks)  │  │          │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │          │
│       ▼              ▼              ▼              ▼          │
│  Obsidian     Environment    Pre-commit     Local CI         │
│  vault →      setup +        validation     workflow         │
│  static HTML  build tasks    + build check  testing          │
│                                                              │
│  Output: site/ → GitHub Pages via `gh` CLI                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 How It Fits Together

```
┌────────────────────────────────────────────────────────────┐
│              Obsidian Vault (source of truth)                │
│                                                              │
│  vault/                                                      │
│  ├── index.md              ← Landing page                    │
│  ├── guides/                                                 │
│  │   ├── getting-started.md                                  │
│  │   └── configuration.md                                    │
│  ├── reference/                                              │
│  │   ├── api.md                                              │
│  │   └── cli.md                                              │
│  ├── .obsidian/            ← Obsidian config (ignored)       │
│  └── assets/               ← Images, attachments             │
└────────────────────┬───────────────────────────────────────┘
                     │
          kiln generate (via devenv task)
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│              Built Site                                      │
│                                                              │
│  site/                                                       │
│  ├── index.html                                              │
│  ├── guides/getting-started/index.html                       │
│  ├── sitemap.xml                                             │
│  └── ...static assets...                                     │
└────────────────────┬───────────────────────────────────────┘
                     │
          gh pages deploy (via devenv task)
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│              GitHub Pages                                    │
│                                                              │
│  https://<owner>.github.io/<repo>/                           │
└────────────────────────────────────────────────────────────┘
```

### 2.3 Per-Repo Footprint

| File | Purpose | Changes often? |
|------|---------|---------------|
| `devenv.nix` | Environment + tasks + processes | Rarely (once set up) |
| `devenv.yaml` | Nix inputs | Rarely |
| `.pre-commit-config.yaml` | prek hook definitions | Rarely |
| `bullish-ssg.toml` | Site config (name, URL, theme) | Sometimes |
| `.gitignore` addition | `site/` entry | Never |

The vault itself (Obsidian `docs/` or `vault/` directory) is the content — no wrapper files, no Jinja templates, no workflow YAML to maintain per-repo.

---

## 3. Component Details

### 3.1 Kiln (SSG Engine)

**What it does**: Converts Obsidian vault → static HTML.

- Single Go binary, zero runtime deps
- `kiln generate` builds, `kiln serve` previews locally
- Native handling of all Obsidian syntax (wikilinks, callouts, embeds, canvas, tags)
- Built-in graph view, search, themes, light/dark mode
- SEO: auto-generated meta tags, sitemaps, robots.txt

**Configuration**: Kiln reads vault structure directly. Optional configuration via a config file for site metadata (name, URL, theme selection). The `bullish-ssg.toml` config wraps Kiln's options with opinionated defaults.

### 3.2 devenv.sh (Environment + Tasks)

**What it does**: Manages the development environment and orchestrates build/deploy/serve tasks.

```nix
# devenv.nix — key additions

packages = [
  pkgs.git
  pkgs.uv
  pkgs.go          # For Kiln
  pkgs.act         # For local CI testing
];

# Kiln installed via go install in enterShell or as a task

scripts.build.exec = "kiln generate";
scripts.serve.exec = "kiln serve";
scripts.deploy.exec = "gh pages deploy site/";

# Tasks with dependencies
tasks."ssg:build" = {
  exec = "kiln generate";
  execIfModified = [ "docs/**/*.md" "bullish-ssg.toml" ];
};

tasks."ssg:deploy" = {
  exec = "gh pages deploy site/";
  after = [ "ssg:build" ];
};

# Dev server as a process
processes.docs.exec = "kiln serve";
```

**Key capabilities used**:
- **Tasks**: `devenv tasks run ssg:build`, `devenv tasks run ssg:deploy`
- **`execIfModified`**: Only rebuild when vault content actually changed
- **Processes**: `devenv up` starts Kiln dev server with hot reload
- **Scripts**: Quick shortcuts (`build`, `serve`, `deploy`) in devenv shell

### 3.3 prek (Git Hooks)

**What it does**: Runs validation hooks before commit/push.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate frontmatter
        entry: bullish-ssg validate
        language: python
        files: '\.md$'

      - id: check-wikilinks
        name: Check broken wikilinks
        entry: bullish-ssg check-links
        language: python
        files: '\.md$'

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
        files: '\.md$'
      - id: end-of-file-fixer
        files: '\.md$'
```

**Pre-commit hooks**: Fast checks — frontmatter validation, trailing whitespace, EOF newlines.
**Pre-push hooks**: Heavier checks — full site build, broken link detection.

prek runs these as a single Rust binary with parallel execution. No Python runtime needed for prek itself (though our custom hooks are Python since bullish-ssg is a Python library).

### 3.4 Act (Local CI)

**What it does**: Runs GitHub Actions workflows locally via Docker.

Even though we don't *depend* on GitHub Actions for the primary workflow, we may still want a `.github/workflows/pages.yml` for:
- Automated deploys when pushing to `main` (as a safety net / CI complement)
- PR checks that validate the site builds cleanly

Act lets us test these workflows locally:

```bash
# Test the pages deployment workflow locally
devenv shell -- act push -W .github/workflows/pages.yml

# Test with a specific event
devenv shell -- act workflow_dispatch
```

The workflow itself is minimal — it calls the same `kiln generate` + `gh pages deploy` that devenv tasks do. Act just verifies the workflow YAML is correct and the steps pass in a Docker environment matching GitHub's runners.

---

## 4. The bullish-ssg Python Library

### 4.1 What It Provides

bullish-ssg is the opinionated glue layer:

1. **CLI commands**: `bullish-ssg init`, `bullish-ssg build`, `bullish-ssg serve`, `bullish-ssg deploy`, `bullish-ssg validate`, `bullish-ssg check-links`
2. **Config management**: `bullish-ssg.toml` with opinionated defaults for Kiln, prek, devenv
3. **Scaffolding**: `bullish-ssg init` sets up a repo with devenv.nix additions, prek config, and site config
4. **Validation**: Frontmatter validation, wikilink checking, orphan page detection
5. **Deploy orchestration**: Wraps `gh pages deploy` with pre-flight checks

### 4.2 Config: `bullish-ssg.toml`

```toml
[site]
name = "My Project Docs"
url = "https://owner.github.io/repo/"
description = "Project documentation"
vault_dir = "docs"        # Obsidian vault location (relative to repo root)
site_dir = "site"         # Build output directory

[site.theme]
name = "default"          # Kiln theme name
mode = "auto"             # "light", "dark", or "auto" (system preference)

[deploy]
method = "gh-pages"       # "gh-pages" (gh CLI) or "branch" (push to gh-pages branch)
branch = "main"           # Source branch for deploy triggers

[hooks]
pre_commit = ["validate-frontmatter", "trailing-whitespace"]
pre_push = ["build", "check-links"]

[vault]
ignore_patterns = [".obsidian/**", ".trash/**", "templates/**"]
```

### 4.3 CLI Commands

| Command | What it does |
|---------|-------------|
| `bullish-ssg init` | Scaffold a repo: add devenv.nix tasks, prek config, bullish-ssg.toml |
| `bullish-ssg build` | Run `kiln generate` with config from `bullish-ssg.toml` |
| `bullish-ssg serve` | Run `kiln serve` for local preview with hot reload |
| `bullish-ssg deploy` | Build + deploy to GitHub Pages via `gh pages deploy` |
| `bullish-ssg validate` | Check frontmatter, wikilinks, orphan pages |
| `bullish-ssg check-links` | Verify all wikilinks resolve to existing pages |

### 4.4 Init Scaffolding

`bullish-ssg init` adds/modifies these files:

```
repo/
├── bullish-ssg.toml              ← NEW: site configuration
├── .pre-commit-config.yaml       ← NEW or MODIFIED: prek hooks
├── devenv.nix                    ← MODIFIED: add tasks + packages
├── devenv.yaml                   ← MODIFIED (if needed): add inputs
├── .gitignore                    ← MODIFIED: add site/ entry
└── docs/                         ← EXISTING or NEW: vault directory
    └── index.md                  ← NEW (if missing): landing page
```

It does NOT use Copier or any templating engine. It reads the existing files and makes targeted additions — appending to `.gitignore`, merging into `devenv.nix`, etc.

---

## 5. Workflow: Developer Experience

### 5.1 Initial Setup (Once Per Repo)

```bash
# In any existing repo with a devenv.sh environment:
devenv shell -- pip install bullish-ssg   # Or: uv add bullish-ssg
devenv shell -- bullish-ssg init

# Answer prompts:
#   Site name: My Project
#   Site URL: https://owner.github.io/repo/
#   Vault directory: docs
#   Deploy method: gh-pages

# Enable GitHub Pages (one-time):
#   Settings → Pages → Source → GitHub Actions (or gh-pages branch)
```

### 5.2 Daily Workflow

```bash
# Enter devenv environment
devenv shell

# Edit Obsidian vault (docs/) in Obsidian or any editor

# Preview locally
bullish-ssg serve
# or: devenv up  (starts Kiln as a managed process)

# Commit — prek runs pre-commit hooks automatically
git add docs/new-page.md
git commit -m "Add new page"
# → prek validates frontmatter, checks whitespace

# Push — prek runs pre-push hooks
git push
# → prek runs full build + link check before push completes

# Deploy manually (if not using CI)
bullish-ssg deploy
# → builds site, runs gh pages deploy
```

### 5.3 CI Workflow (Optional, via Act)

```bash
# Test the GitHub Actions workflow locally
devenv shell -- act push

# If the workflow passes locally, push with confidence
git push origin main
```

---

## 6. Why This Stack

### devenv.sh over Makefiles/Just/Taskfile

- Already in use in the repo
- Nix-based: reproducible across machines
- Tasks have dependency graphs, caching (`execIfModified`), parallel execution
- Processes give us managed dev servers
- Single `devenv shell` entry point for everything

### prek over pre-commit

- Single Rust binary, no Python runtime dependency for the hook runner itself
- Multiple times faster with parallel hook execution
- Drop-in compatible with `.pre-commit-config.yaml`
- Manages language toolchains automatically
- Built-in monorepo/workspace support

### Act over pushing-to-test

- Instant feedback — no round-trip to GitHub
- Docker-based, matches GitHub runner environment
- Tests workflow YAML correctness locally
- Doesn't consume GitHub Actions minutes
- Keeps the dev loop entirely local

### Kiln over Zensical

- Native Obsidian Markdown support — zero preprocessing
- Single binary, zero runtime deps
- Graph view, canvas support, full-text search built-in
- "Point at vault, get website" simplicity
- Zensical is better for structured docs written in standard Markdown; Kiln is purpose-built for Obsidian vaults

---

## 7. Open Questions

### Q1: Kiln maturity — is it production-ready?

Kiln is newer and less battle-tested than Zensical. Need to evaluate: stability, theme quality, customization depth, edge cases with complex vaults. Fallback plan: use Zensical with a preprocessing step if Kiln proves insufficient.

### Q2: Should bullish-ssg wrap Kiln's config entirely or pass through?

Option A: `bullish-ssg.toml` is the only config, bullish-ssg generates Kiln's config at build time.
Option B: `bullish-ssg.toml` handles orchestration (deploy, hooks), Kiln has its own config for site details.

Leaning toward A — opinionated means fewer config files for the user.

### Q3: Deploy method — `gh pages deploy` vs push to `gh-pages` branch?

`gh pages deploy` is the modern approach (artifact-based, no branch pollution). But it requires the `gh` CLI. Pushing to a `gh-pages` branch is the legacy approach but works without `gh`. Both should be supported; default to `gh pages deploy`.

### Q4: Should the GitHub Actions workflow be mandatory or optional?

The local-first philosophy says optional. Some users will want CI as a safety net (auto-deploy on push to main). Others will deploy manually. `bullish-ssg init` should ask and only scaffold the workflow if requested.

### Q5: Kiln installation — Go binary vs pre-built release?

Options:
- `go install` (requires Go in devenv)
- Download pre-built binary in devenv.nix
- Nix package if available

Pre-built binary via devenv.nix is most reproducible and doesn't require Go toolchain at runtime.

---

## 8. Implementation Plan

### Phase 1: Prove the Pipeline

1. Install Kiln in devenv.nix
2. Point it at a test Obsidian vault with wikilinks, callouts, embeds
3. Verify output quality: rendering, graph view, search, themes
4. Deploy to GitHub Pages manually via `gh pages deploy`
5. **Gate**: If Kiln output quality is insufficient, evaluate Zensical + preprocessing

### Phase 2: bullish-ssg CLI

1. Create `bullish-ssg` Python package with CLI (click or typer)
2. Implement `init`, `build`, `serve`, `deploy` commands
3. Implement `bullish-ssg.toml` config parsing (pydantic)
4. Implement `validate` and `check-links` commands

### Phase 3: devenv.sh Integration

1. Write devenv.nix task definitions for build/deploy/serve
2. Write prek hook configurations
3. Test `devenv tasks run ssg:build` and `devenv up` for dev server
4. Test prek pre-commit and pre-push hooks

### Phase 4: Act Integration

1. Write a minimal `.github/workflows/pages.yml`
2. Test locally with `act push`
3. Verify it deploys correctly when pushed to GitHub

### Phase 5: Multi-Repo Adoption

1. Test `bullish-ssg init` on 2-3 existing repos
2. Verify the scaffold output is correct
3. Document the setup and daily workflow
4. Iterate based on real usage

---

**Document History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-28 | Initial concept (Zensical + custom scripts) |
| 2.0 | 2026-03-28 | Rewrite: Zensical + reusable workflow + Copier |
| 3.0 | 2026-04-03 | Rewrite: Kiln + devenv.sh + prek + Act (local-first) |
