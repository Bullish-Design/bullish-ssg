# SSG Engine Research

## Table of Contents

1. [Candidate Engines](#1-candidate-engines)
2. [Kiln (Recommended)](#2-kiln-recommended)
3. [Zensical](#3-zensical)
4. [Comparison](#4-comparison)
5. [Obsidian-Specific Markdown](#5-obsidian-specific-markdown)
6. [Deployment Tooling](#6-deployment-tooling)

---

## 1. Candidate Engines

The core requirement is converting **Obsidian vault pages** into static HTML for GitHub Pages. This means native handling of wikilinks (`[[page]]`), callouts (`> [!NOTE]`), embeds, LaTeX math, Mermaid diagrams, and the broader Obsidian Markdown dialect.

Two serious candidates emerged:

| Engine | Language | Obsidian-native? | Config format | Package |
|--------|----------|-------------------|---------------|---------|
| **Kiln** | Go | Yes — purpose-built | Obsidian vault structure | `go install` single binary |
| **Zensical** | Rust + Python | No — needs preprocessing | TOML (`zensical.toml`) | `pip install zensical` |

## 2. Kiln (Recommended)

**Repository**: https://github.com/otaleghani/kiln
**Website**: https://kiln.talesign.com/

Kiln is an open-source SSG built specifically for Obsidian vaults. Its "Parity First" philosophy means if it works in Obsidian, it works in the browser.

### Key Features

- **Wikilinks**: Full `[[page]]`, `[[page|alias]]`, `[[page#heading]]` support
- **Callouts**: All Obsidian callout types including collapsible
- **Embeds**: Note embeds, image embeds, PDF embeds
- **Canvas files**: Renders `.canvas` files as interactive views
- **Graph view**: Global and local graph visualizations
- **LaTeX math**: MathJax/KaTeX rendering
- **Mermaid diagrams**: Native fenced code block support
- **Search**: Built-in full-text search
- **Themes**: Multiple themes with light/dark mode
- **SEO**: Auto-generated meta tags, sitemaps, robots.txt, canonical URLs
- **HTMX-powered**: Instant client-side navigation

### Technical Details

- Single Go binary, zero runtime dependencies
- Two commands: `kiln generate` (build), `kiln serve` (local preview)
- Outputs standard HTML/CSS/JS — compatible with any static host
- No config file needed by default — reads vault structure directly
- Custom Mode allows using Obsidian as a headless CMS with custom templates

### Why Kiln Over Zensical

Zensical is excellent for structured documentation (API refs, user guides), but it treats Markdown as standard CommonMark/GFM. Obsidian's extended syntax (`[[wikilinks]]`, callouts, embeds, canvas) would require a preprocessing pipeline to convert into standard markdown before Zensical could consume it.

Kiln eliminates that entire translation layer. Point it at a vault, get a website.

## 3. Zensical

**Repository**: https://github.com/zensical/zensical (3.9k stars)
**Website**: https://zensical.org/

Successor to Material for MkDocs by squidfunk. Rust core, Python distribution. Currently v0.0.29 (early, expect breaking changes).

### Strengths

- Fast builds (Rust core)
- Polished default theme with rich navigation features
- Instant navigation, prefetching, breadcrumbs, tabs
- Code copy, annotations, edit-on-GitHub buttons
- Built-in search with highlighting
- `zensical.toml` configuration
- Strong docs-site conventions (nav hierarchy, section indexes)

### Weaknesses for This Use Case

- No native Obsidian syntax support
- Wikilinks must be converted to standard `[text](url)` links
- Callouts need conversion (Zensical uses admonition syntax from MkDocs)
- No canvas support
- No graph view
- `docs_dir` cannot be `.` — must be a subdirectory
- Early release with expected breaking changes

### When Zensical Would Be Better

If the content is structured documentation written in standard Markdown (API references, user guides, tutorials), Zensical provides superior navigation features and a more polished documentation-specific experience.

## 4. Comparison

| Feature | Kiln | Zensical |
|---------|------|----------|
| Obsidian wikilinks | Native | Needs preprocessing |
| Obsidian callouts | Native (all types + collapsible) | Partial (admonition syntax differs) |
| Obsidian embeds | Native | Not supported |
| Canvas files | Native | Not supported |
| Graph view | Built-in (global + local) | Not available |
| Mermaid diagrams | Native | Native |
| LaTeX math | Native | Supported |
| Search | Built-in full-text | Built-in with highlighting |
| Light/dark mode | Multiple themes | Palette toggle |
| Navigation tabs | No | Yes |
| Section hierarchy | File tree based | Explicit nav config |
| Edit-on-GitHub | Not documented | Built-in |
| Config overhead | Zero (reads vault) | `zensical.toml` required |
| Runtime deps | None (single binary) | Python 3.x |
| Build speed | Fast (Go) | Fast (Rust) |

## 5. Obsidian-Specific Markdown

Features that differentiate Obsidian Markdown from standard GFM:

| Feature | Syntax | Standard GFM? |
|---------|--------|---------------|
| Wikilinks | `[[page]]`, `[[page\|alias]]` | No |
| Heading links | `[[page#heading]]` | No |
| Block references | `[[page#^block-id]]` | No |
| Embeds | `![[note]]`, `![[image.png]]` | No |
| Callouts | `> [!TYPE]` | Partial (GitHub supports 5 types) |
| Collapsible callouts | `> [!TYPE]+` / `> [!TYPE]-` | No |
| Tags | `#tag` inline | No (treated as heading) |
| Frontmatter | YAML `---` block | Partial |
| Canvas | `.canvas` JSON files | No |
| Comments | `%%comment%%` | No |
| Highlights | `==highlighted==` | No |

Any SSG that doesn't natively handle these needs a preprocessing step. Kiln handles all of them. Zensical handles none of the Obsidian-specific ones.

## 6. Deployment Tooling

### devenv.sh

Already in use in this repo. Provides:
- **Tasks**: Dependency-aware automation units (`devenv tasks run`)
- **Processes**: Long-lived services (`devenv up`) — useful for `kiln serve`
- **Scripts**: Shell shortcuts available in devenv shell
- **Pre-commit hooks**: Built-in support (but we prefer prek — see below)

### prek (j178/prek)

Rust-based pre-commit replacement. Single binary, no Python dependency.
- Compatible with `.pre-commit-config.yaml`
- Parallel hook execution
- Built-in workspace/monorepo support
- Manages language toolchains automatically

Use cases for bullish-ssg:
- Pre-commit: lint markdown, validate frontmatter, check broken wikilinks
- Pre-push: full site build + link validation

### Act (nektos/act)

Runs GitHub Actions workflows locally via Docker.
- Reads `.github/workflows/` directly
- Matches GitHub runner environment
- No commit/push required to test
- 69.7k GitHub stars, actively maintained

Use case: Test the GitHub Pages deployment workflow locally before pushing, without relying on GitHub's CI infrastructure for the development loop.

---

*Sources*:
- [Kiln SSG](https://kiln.talesign.com/)
- [Kiln GitHub](https://github.com/otaleghani/kiln)
- [Zensical GitHub](https://github.com/zensical/zensical)
- [Zensical Documentation](https://zensical.org/docs/)
- [prek GitHub](https://github.com/j178/prek)
- [Act GitHub](https://github.com/nektos/act)
- [devenv.sh Tasks](https://devenv.sh/tasks/)
- [devenv.sh Processes](https://devenv.sh/processes/)
- [Obsidian Markdown Reference](https://www.markdowntools.io/obsidian-cheat-sheet)
