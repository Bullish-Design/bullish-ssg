# Repo Documentation Hosting Strategy — Local-First

## Table of Contents

1. [Goal](#1-goal)
2. [Architecture: Obsidian Vault as Source](#2-architecture-obsidian-vault-as-source)
3. [Per-Repo Setup](#3-per-repo-setup)
4. [Vault Structure Conventions](#4-vault-structure-conventions)
5. [devenv.nix Configuration](#5-devenvnix-configuration)
6. [prek Hook Configuration](#6-prek-hook-configuration)
7. [bullish-ssg.toml Configuration](#7-bullish-ssgtoml-configuration)
8. [Automation Flow](#8-automation-flow)
9. [What "Automatic" Means in Practice](#9-what-automatic-means-in-practice)
10. [Multi-Repo Adoption](#10-multi-repo-adoption)
11. [Handling Edge Cases](#11-handling-edge-cases)
12. [Implementation Checklist](#12-implementation-checklist)

---

## 1. Goal

*"Edit docs in Obsidian, push, website updates."*

More specifically:
1. **Obsidian is the authoring tool** — wikilinks, callouts, embeds, canvas all work
2. **No manual build step** — prek pre-push hook builds automatically
3. **No CI dependency** — local build + deploy via `gh pages deploy`
4. **Optional CI safety net** — GitHub Actions workflow for auto-deploy on push
5. **Docs evolve with code** — same repo, same branch, same PR
6. **Reproducible environment** — devenv.sh ensures identical tooling everywhere

## 2. Architecture: Obsidian Vault as Source

```
my-project/
├── devenv.nix                    # Environment + tasks
├── devenv.yaml                   # Nix inputs
├── bullish-ssg.toml              # Site configuration
├── .pre-commit-config.yaml       # prek hooks
├── .gitignore                    # Includes site/
├── docs/                         # ← Obsidian vault (source of truth)
│   ├── .obsidian/                # Obsidian app config (gitignored)
│   ├── index.md                  # Landing page
│   ├── guides/
│   │   ├── getting-started.md
│   │   └── configuration.md
│   ├── reference/
│   │   ├── api.md
│   │   └── cli.md
│   └── assets/                   # Images, attachments
│       └── diagram.png
├── .github/workflows/            # OPTIONAL
│   └── pages.yml                 # CI deploy (safety net)
├── site/                         # Build output (gitignored)
└── src/                          # Project source code
```

Key points:
- `docs/` is an Obsidian vault — open it in Obsidian, edit naturally
- `.obsidian/` is gitignored (personal Obsidian settings)
- `site/` is gitignored (generated output)
- No conversion layer between Obsidian and the SSG

## 3. Per-Repo Setup

### First-time setup

```bash
# In an existing repo with devenv.sh:
devenv shell

# Install bullish-ssg
uv add --dev bullish-ssg

# Initialize
bullish-ssg init

# Prompts:
#   Site name: My Project
#   URL: https://owner.github.io/repo/
#   Vault dir: docs  [default]
#   Deploy method: gh-pages  [default]
#   Add CI workflow? no  [default]

# Install prek hooks
prek install

# Enable GitHub Pages (one time)
# → Settings → Pages → Source → GitHub Actions
# Or via CLI:
gh api repos/{owner}/{repo}/pages -X POST -f build_type=workflow
```

### What `bullish-ssg init` creates/modifies

| File | Action | Content |
|------|--------|---------|
| `bullish-ssg.toml` | CREATE | Site config with opinionated defaults |
| `.pre-commit-config.yaml` | CREATE or MERGE | prek hook definitions |
| `devenv.nix` | MODIFY | Add tasks, scripts, packages, process |
| `.gitignore` | MODIFY | Append `site/` and `.obsidian/` |
| `docs/index.md` | CREATE (if missing) | Minimal landing page |
| `.github/workflows/pages.yml` | CREATE (if requested) | CI deploy workflow |

## 4. Vault Structure Conventions

### Directory layout

Kiln reads the vault directory structure to generate navigation. Organize docs logically:

```
docs/
├── index.md              # Site landing page (required)
├── getting-started.md    # Top-level pages appear in root nav
├── guides/               # Directories become nav sections
│   ├── index.md          # Section landing page (optional)
│   ├── installation.md
│   └── usage.md
├── reference/
│   ├── api.md
│   └── cli.md
└── assets/               # Images, attachments
    ├── screenshot.png
    └── architecture.svg
```

### Frontmatter (optional)

```yaml
---
title: Getting Started        # Page title (overrides filename)
description: Quick start guide # Meta description
tags: [guide, beginner]       # Obsidian tags
publish: true                 # Control which pages are published
---
```

The `publish` frontmatter key lets you keep draft/private notes in the vault without publishing them. `bullish-ssg validate` checks for this.

### Obsidian features that just work

| Feature | Syntax | Rendered as |
|---------|--------|------------|
| Wikilinks | `[[other-page]]` | HTML link to other page |
| Aliased links | `[[other-page\|display text]]` | Link with custom text |
| Heading links | `[[page#heading]]` | Link to specific heading |
| Embeds | `![[note]]` | Inline content from other note |
| Image embeds | `![[image.png]]` | Rendered image |
| Callouts | `> [!NOTE] Title` | Styled callout box |
| Collapsible | `> [!NOTE]+ Title` | Expandable callout |
| Tags | `#tag` | Clickable tag |
| Highlights | `==text==` | Highlighted text |
| Mermaid | ` ```mermaid ` | Rendered diagram |
| LaTeX | `$formula$` | Rendered math |
| Canvas | `file.canvas` | Interactive canvas view |

## 5. devenv.nix Configuration

After `bullish-ssg init`, the devenv.nix gains:

```nix
{ pkgs, lib, config, inputs, ... }:

{
  packages = [
    pkgs.git
    pkgs.uv
    pkgs.gh           # GitHub CLI for deployment
    # Kiln installed via binary in enterShell
  ];

  languages.python = {
    enable = true;
    version = "3.13";
    venv.enable = true;
    uv.enable = true;
  };

  # Scripts (quick shortcuts)
  scripts.build.exec = "kiln generate";
  scripts.serve.exec = "kiln serve";
  scripts.deploy.exec = "bullish-ssg deploy";
  scripts.validate.exec = "bullish-ssg validate && bullish-ssg check-links";

  # Tasks (dependency-aware, cached)
  tasks."ssg:build" = {
    exec = "kiln generate";
    execIfModified = [ "docs/**/*.md" "docs/**/*.canvas" "bullish-ssg.toml" ];
  };

  tasks."ssg:deploy" = {
    exec = "bullish-ssg deploy";
    after = [ "ssg:build" ];
  };

  tasks."ssg:validate" = {
    exec = "bullish-ssg validate && bullish-ssg check-links";
  };

  # Dev server as managed process
  processes.docs = {
    exec = "kiln serve";
  };

  enterShell = ''
    # Install Kiln binary if not present
    if ! command -v kiln &> /dev/null; then
      echo "Installing Kiln..."
      # Platform-specific binary download
      # (or: go install github.com/otaleghani/kiln/cmd/kiln@latest)
    fi

    echo "bullish-ssg environment ready"
    echo "  build:    devenv tasks run ssg:build"
    echo "  serve:    devenv up"
    echo "  deploy:   devenv tasks run ssg:deploy"
    echo "  validate: devenv tasks run ssg:validate"
  '';
};
```

## 6. prek Hook Configuration

```yaml
# .pre-commit-config.yaml
repos:
  # Fast checks (pre-commit)
  - repo: local
    hooks:
      - id: validate-frontmatter
        name: Validate frontmatter
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

  # Heavy checks (pre-push)
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

Install once: `prek install`

After that, prek runs automatically on every `git commit` and `git push`.

## 7. bullish-ssg.toml Configuration

```toml
[site]
name = "My Project"
url = "https://owner.github.io/repo/"
description = "Project documentation"
vault_dir = "docs"
site_dir = "site"

[site.theme]
name = "default"
mode = "auto"             # "light" | "dark" | "auto"

[deploy]
method = "gh-pages"       # "gh-pages" | "branch"
branch = "main"

[vault]
# Patterns to exclude from the published site
ignore_patterns = [
  ".obsidian/**",
  ".trash/**",
  "templates/**",
  "**/private/**",
]

# Frontmatter key that controls publish status
publish_key = "publish"
publish_default = true    # Publish by default? (false = opt-in publishing)

[hooks]
pre_commit = ["validate-frontmatter", "trailing-whitespace", "end-of-file-fixer"]
pre_push = ["build-site", "check-links"]
```

## 8. Automation Flow

### Local workflow (primary)

```
Edit in Obsidian
       ↓
git add + git commit
       ↓
prek pre-commit: validate frontmatter, whitespace ← FAST (~1s)
       ↓
git push
       ↓
prek pre-push: kiln generate, check-links ← HEAVIER (~5-10s)
       ↓
bullish-ssg deploy (manual, or auto via CI)
       ↓
Site live at https://owner.github.io/repo/
```

### CI workflow (optional safety net)

```
git push to main
       ↓
GitHub Actions triggers pages.yml
       ↓
Checkout → Install Kiln → kiln generate → upload artifact → deploy
       ↓
Site live (automated, ~1-2 minutes)
```

### Dev preview

```
devenv up
       ↓
kiln serve starts on localhost:8000
       ↓
Edit docs in Obsidian → browser auto-refreshes
```

## 9. What "Automatic" Means in Practice

| Scenario | What happens |
|----------|-------------|
| Edit a doc in Obsidian, commit + push | prek validates, builds, checks links. If CI enabled: auto-deploys. |
| Add a new page | Appears in site nav automatically (Kiln reads directory structure) |
| Add a wikilink `[[new-page]]` | prek pre-push checks it resolves; if not, push blocked |
| Delete a page | Disappears from site. prek warns about broken incoming links |
| Add an image via Obsidian paste | Image saved to `assets/`, `![[image.png]]` renders in site |
| Create a canvas file | Rendered as interactive canvas in the site |
| Run `devenv up` | Local preview server starts, watches for changes |
| Run `bullish-ssg deploy` | Builds + deploys in one command |
| Push to feature branch | Nothing — only `main` triggers CI (if enabled) |

## 10. Multi-Repo Adoption

### Rolling out to existing repos

```bash
cd /path/to/existing-repo

# Must already have devenv.sh
bullish-ssg init
prek install

# If repo already has a docs/ directory:
# → bullish-ssg init detects it and skips creating docs/index.md
# → Existing .md files are immediately usable

# If repo has no docs/ directory:
# → bullish-ssg init creates docs/ with a starter index.md
```

### What varies per repo

| Setting | Varies? | Example |
|---------|---------|---------|
| `site.name` | Yes | "Remora", "Cairn", "Bullish SSG" |
| `site.url` | Yes | `https://bullish-design.github.io/remora-v2/` |
| `vault_dir` | Rarely | `docs` (default), sometimes `vault` or `wiki` |
| Theme/mode | Rarely | Most will use defaults |
| Deploy method | Rarely | `gh-pages` for most |
| Hooks | No | Same hooks everywhere |
| devenv tasks | No | Same task definitions everywhere |

### What's centralized

bullish-ssg itself is the centralization mechanism. When Kiln updates or conventions change, update the bullish-ssg package. Each repo picks up changes on next `uv sync`.

No reusable workflows. No Copier templates. No separate "docs-system" repo. The Python package IS the single source of truth for build/deploy logic.

## 11. Handling Edge Cases

### Existing `docs/` with standard Markdown (no Obsidian syntax)

Works fine — Kiln handles standard Markdown as a subset. Wikilinks/callouts just won't be present.

### Mixed vault: some pages private

Use `publish: false` in frontmatter or the `vault.ignore_patterns` config:

```toml
[vault]
ignore_patterns = ["**/private/**", "**/drafts/**"]
```

Or set `publish_default = false` and opt-in individual pages with `publish: true`.

### Large vaults (hundreds of pages)

Kiln is a Go binary and builds fast. devenv.sh `execIfModified` ensures only changed content triggers rebuilds. prek runs hooks in parallel.

### Repos without devenv.sh

bullish-ssg requires devenv.sh — it's an opinionated tool. For repos that can't use devenv, the CLI commands (`bullish-ssg build`, `bullish-ssg deploy`) still work standalone, but the task orchestration and reproducible environment benefits are lost.

### Obsidian plugins that generate non-standard content

Some Obsidian plugins produce syntax that only renders in Obsidian (e.g., Dataview queries, Templater output). These won't render in Kiln. Options:
- Use `cssclass` frontmatter to hide plugin-specific content
- Keep plugin-generated pages in an ignored directory
- Use Obsidian's publish-aware frontmatter to exclude them

### Broken wikilinks

`bullish-ssg check-links` scans all `.md` files for `[[wikilinks]]` and verifies each target exists in the vault. Broken links are reported with file + line number. The pre-push hook prevents pushing with broken links.

## 12. Implementation Checklist

### Phase 1: Prove the Pipeline
- [ ] Install Kiln in devenv.nix
- [ ] Create a test vault with wikilinks, callouts, embeds, canvas
- [ ] Run `kiln generate` and verify output quality
- [ ] Run `kiln serve` and verify local preview
- [ ] Deploy to GitHub Pages via `gh pages deploy site/`
- [ ] Verify site renders correctly at the public URL

### Phase 2: bullish-ssg CLI
- [ ] Create package structure with CLI (click/typer)
- [ ] Implement `init` command (scaffolding)
- [ ] Implement `build` command (wraps `kiln generate`)
- [ ] Implement `serve` command (wraps `kiln serve`)
- [ ] Implement `deploy` command (wraps `gh pages deploy`)
- [ ] Implement `validate` command (frontmatter checks)
- [ ] Implement `check-links` command (wikilink verification)
- [ ] Implement `bullish-ssg.toml` parsing with pydantic

### Phase 3: Automation Integration
- [ ] Write devenv.nix task/script/process definitions
- [ ] Write `.pre-commit-config.yaml` for prek
- [ ] Test `prek install` + commit/push hooks
- [ ] Test `devenv tasks run ssg:build` with `execIfModified`
- [ ] Test `devenv up` for dev server process
- [ ] Write optional GitHub Actions workflow
- [ ] Test workflow locally with Act

### Phase 4: Multi-Repo Adoption
- [ ] Test `bullish-ssg init` on a repo with existing docs/
- [ ] Test `bullish-ssg init` on a fresh repo
- [ ] Test on 2-3 real projects
- [ ] Document the setup and workflow
- [ ] Iterate based on real usage

---

*Sources*:
- [Kiln SSG](https://kiln.talesign.com/)
- [devenv.sh](https://devenv.sh/)
- [prek](https://github.com/j178/prek)
- [Act](https://github.com/nektos/act)
- [GitHub Pages](https://docs.github.com/en/pages)
