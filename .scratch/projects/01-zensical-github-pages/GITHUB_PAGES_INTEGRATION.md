# GitHub Pages Integration — Local-First Approach

## Table of Contents

1. [Overview](#1-overview)
2. [Deployment Methods](#2-deployment-methods)
3. [Recommended: `gh pages deploy`](#3-recommended-gh-pages-deploy)
4. [Alternative: gh-pages Branch](#4-alternative-gh-pages-branch)
5. [Optional: GitHub Actions Workflow](#5-optional-github-actions-workflow)
6. [Local CI Testing with Act](#6-local-ci-testing-with-act)
7. [devenv.sh Task Orchestration](#7-devenvsh-task-orchestration)
8. [prek Hook Integration](#8-prek-hook-integration)
9. [GitHub Repository Settings](#9-github-repository-settings)
10. [URL & Domain](#10-url--domain)
11. [Security Considerations](#11-security-considerations)

---

## 1. Overview

The deployment philosophy is **local-first**: the primary build and deploy loop runs on the developer's machine using devenv.sh tasks, not in GitHub Actions. CI workflows exist as an optional safety net, tested locally with Act before pushing.

```
                 LOCAL (primary)                    REMOTE (optional)
                 ──────────────                     ────────────────
Edit vault ──→ prek validates ──→ git push ──→ GitHub Actions deploys
     │              │                                    │
     ▼              ▼                                    ▼
kiln serve    kiln generate                     (same pipeline,
(live preview) (pre-push hook)                   automated on push)
     │              │
     ▼              ▼
browser        gh pages deploy
               (manual or task)
```

## 2. Deployment Methods

| Method | Mechanism | Requires | Best for |
|--------|-----------|----------|----------|
| `gh pages deploy` | Upload artifact via GitHub API | `gh` CLI | Modern, clean, no branch pollution |
| `gh-pages` branch | Push built files to branch | `git` | Legacy, works without `gh` CLI |
| GitHub Actions | CI builds + deploys on push | `.github/workflows/` | Automated safety net |

All three produce the same result: static HTML at `https://<owner>.github.io/<repo>/`.

## 3. Recommended: `gh pages deploy`

The `gh pages deploy` command uploads the built `site/` directory directly to GitHub Pages via the API. No separate branch, no artifact actions, no workflow required.

### Usage

```bash
# Build first
kiln generate

# Deploy
gh pages deploy site/
```

### Via bullish-ssg

```bash
# Build + deploy in one command
bullish-ssg deploy
```

### Via devenv task

```bash
devenv tasks run ssg:deploy
```

### How it works

1. `kiln generate` builds the vault into `site/`
2. `gh pages deploy site/` uploads `site/` as a GitHub Pages deployment artifact
3. GitHub serves the content at the configured URL

**Advantages**:
- No `gh-pages` branch cluttering git history
- No GitHub Actions workflow required
- Direct API upload — fast
- Works from any machine with `gh` authenticated

**Requirements**:
- `gh` CLI installed and authenticated (`gh auth login`)
- GitHub Pages enabled in repo settings (Source: GitHub Actions)

## 4. Alternative: gh-pages Branch

For environments where `gh` CLI isn't available or for repos that already use the branch-based approach:

```bash
# Build
kiln generate

# Deploy to gh-pages branch
# (bullish-ssg handles the git operations)
bullish-ssg deploy --method branch
```

This creates/updates a `gh-pages` branch with the contents of `site/`. The repo must be configured with Pages Source set to "Deploy from a branch" → `gh-pages` / `/ (root)`.

## 5. Optional: GitHub Actions Workflow

A minimal workflow for repos that want automated deploys on push to `main`:

```yaml
# .github/workflows/pages.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'bullish-ssg.toml'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Install Kiln
        run: |
          KILN_VERSION="latest"  # or pin a version
          curl -sSfL https://github.com/otaleghani/kiln/releases/latest/download/kiln-linux-amd64 -o /usr/local/bin/kiln
          chmod +x /usr/local/bin/kiln

      - name: Build site
        run: kiln generate

      - uses: actions/upload-pages-artifact@v4
        with:
          path: site

      - uses: actions/deploy-pages@v4
        id: deploy
```

**Key differences from v2**:
- Kiln instead of Zensical (no Python needed)
- Single binary install (curl + chmod) instead of pip install
- Same build command the developer runs locally
- This workflow is **optional** — the primary deploy path is local

### Path filtering

The `paths` filter ensures the workflow only runs when vault content or config changes, saving CI minutes. Remove it to build on every push.

## 6. Local CI Testing with Act

Test the GitHub Actions workflow locally before pushing:

```bash
# Run the push event workflow
devenv shell -- act push -W .github/workflows/pages.yml

# Run with a specific job
devenv shell -- act push -j deploy

# Dry run (show what would execute)
devenv shell -- act push -n

# Use a specific Docker image for the runner
devenv shell -- act push -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

### What Act validates

- Workflow YAML syntax is correct
- Steps execute in order
- Kiln installs and builds successfully in a clean environment
- Artifact upload step succeeds

### What Act doesn't validate

- Actual GitHub Pages deployment (the `deploy-pages` action needs real GitHub infrastructure)
- OIDC token generation
- GitHub Pages URL resolution

For full end-to-end validation, use `bullish-ssg deploy` to deploy to the actual GitHub Pages environment.

## 7. devenv.sh Task Orchestration

### Task Definitions

```nix
# devenv.nix additions

tasks."ssg:build" = {
  exec = ''
    echo "Building site..."
    kiln generate
    echo "Site built to site/"
  '';
  execIfModified = [ "docs/**/*.md" "bullish-ssg.toml" ];
};

tasks."ssg:deploy" = {
  exec = ''
    echo "Deploying to GitHub Pages..."
    gh pages deploy site/
    echo "Deployed."
  '';
  after = [ "ssg:build" ];
};

tasks."ssg:validate" = {
  exec = ''
    bullish-ssg validate
    bullish-ssg check-links
  '';
};

tasks."ssg:ci" = {
  exec = ''
    act push -W .github/workflows/pages.yml
  '';
};

# Dev server as a managed process
processes.docs = {
  exec = "kiln serve";
  cwd = ".";
};
```

### Usage

```bash
# Build (skips if no changes)
devenv tasks run ssg:build

# Build + deploy (dependency chain)
devenv tasks run ssg:deploy

# Validate vault content
devenv tasks run ssg:validate

# Test CI workflow locally
devenv tasks run ssg:ci

# Start dev server
devenv up
```

### Task dependency graph

```
ssg:validate ─────────────────────────────────
                                               │
ssg:build ────→ ssg:deploy                     │
    │                                          │
    └── (execIfModified: docs/**/*.md)         │
                                               │
ssg:ci ────────────────────────────────────────┘
                 (independent, uses Act)
```

## 8. prek Hook Integration

### Pre-commit hooks (fast, run on every commit)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate Obsidian frontmatter
        entry: bullish-ssg validate --quick
        language: python
        files: '\.md$'
        types: [markdown]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
        files: '\.md$'
      - id: end-of-file-fixer
        files: '\.md$'
      - id: check-yaml
```

### Pre-push hooks (heavier, run before push)

```yaml
  - repo: local
    hooks:
      - id: build-site
        name: Build site
        entry: kiln generate
        language: system
        always_run: true
        stages: [pre-push]

      - id: check-links
        name: Check wikilinks
        entry: bullish-ssg check-links
        language: python
        always_run: true
        stages: [pre-push]
```

### Installing hooks

```bash
# prek installs hooks from .pre-commit-config.yaml
devenv shell -- prek install
```

prek runs hooks in parallel, so pre-commit checks are fast even with multiple hooks.

## 9. GitHub Repository Settings

One-time setup per repo:

### For `gh pages deploy` (recommended)

1. **Settings → Pages → Source**: Select **GitHub Actions**
2. No branch configuration needed
3. `gh pages deploy` uploads artifacts directly

### For gh-pages branch

1. **Settings → Pages → Source**: Select **Deploy from a branch**
2. **Branch**: `gh-pages`, folder: `/ (root)`

### For GitHub Actions workflow

1. **Settings → Pages → Source**: Select **GitHub Actions**
2. The workflow handles everything

### Enabling Pages via CLI

```bash
# Check current Pages config
gh api repos/{owner}/{repo}/pages

# Enable Pages with GitHub Actions source
gh api repos/{owner}/{repo}/pages -X POST \
  -f build_type=workflow

# Or with branch source
gh api repos/{owner}/{repo}/pages -X POST \
  -f source[branch]=gh-pages -f source[path]=/
```

`bullish-ssg init` can automate this step if `gh` is available and authenticated.

## 10. URL & Domain

### Default URL

```
https://<owner>.github.io/<repo>/
```

### Custom domain

1. **Settings → Pages → Custom domain**: Enter domain
2. Add `CNAME` file to vault root (Kiln copies it to `site/`)
3. Configure DNS: CNAME record pointing to `<owner>.github.io`

### Site URL in config

```toml
# bullish-ssg.toml
[site]
url = "https://owner.github.io/repo/"
```

Must match the actual deployment URL for correct sitemap generation and canonical URLs.

## 11. Security Considerations

### Local deployment

- `gh` CLI uses OAuth token from `gh auth login`
- Token needs `repo` scope (or fine-grained: Pages write)
- No secrets stored in repo

### CI deployment (if using workflow)

| Permission | Reason |
|------------|--------|
| `contents: read` | Checkout repo |
| `pages: write` | Deploy to Pages |
| `id-token: write` | OIDC token for deployment auth |

These are GitHub's standard Pages permissions. No PATs or secrets needed — OIDC handles auth.

### prek security

- prek supports `--cooldown-days` for auto-update checks (supply chain protection)
- Hook repos are pinned by `rev` in `.pre-commit-config.yaml`
- Local hooks (`repo: local`) run your own code, no external dependency

---

*Sources*:
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [gh CLI Pages](https://cli.github.com/manual/gh_api)
- [Act Documentation](https://nektosact.com)
- [devenv.sh Tasks](https://devenv.sh/tasks/)
- [devenv.sh Processes](https://devenv.sh/processes/)
- [prek GitHub](https://github.com/j178/prek)
