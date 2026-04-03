# bullish-ssg

Opinionated static-site tooling for Obsidian-first docs and blog publishing to GitHub Pages.

## Install

```bash
devenv shell -- uv sync --extra dev
```

## Commands

- `bullish-ssg init`
- `bullish-ssg link-vault <vault-path> [--link-path docs] [--repair] [--force]`
- `bullish-ssg validate`
- `bullish-ssg check-links`
- `bullish-ssg build [--dry-run]`
- `bullish-ssg serve [--port 8000] [--dry-run]`
- `bullish-ssg deploy [--dry-run]`

## Quickstart (Direct Mode)

```bash
# in your repo
devenv shell -- bullish-ssg init

# put content in docs/
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
devenv shell -- bullish-ssg build --dry-run
devenv shell -- bullish-ssg deploy --dry-run
```

Direct mode config snippet:

```toml
[vault]
mode = "direct"
link_path = "docs"
```

## Quickstart (Symlink Mode for Obsidian Vault)

```bash
# create/update docs -> /absolute/path/to/your/vault
devenv shell -- bullish-ssg link-vault /absolute/path/to/your/vault

# validate + preview deploy pipeline
devenv shell -- bullish-ssg validate
devenv shell -- bullish-ssg check-links
devenv shell -- bullish-ssg build --dry-run
devenv shell -- bullish-ssg deploy --dry-run
```

Symlink mode config snippet:

```toml
[vault]
mode = "symlink"
source_path = "/absolute/path/to/your/vault"
link_path = "docs"
```

## Deployment Modes

`bullish-ssg` supports:
- `deploy.method = "gh-pages"` (primary path via `gh pages deploy`)
- `deploy.method = "branch"` (branch-based fallback adapter)

In both modes, deploy runs preflight checks first:
- config validation
- vault resolution
- dry-run aware build check

## Troubleshooting Symlink Issues

- Symptom: `Expected symlink at docs, but found a directory`
  - Fix: run `bullish-ssg link-vault /path/to/vault --force` only if replacing that path is intentional.
- Symptom: `Symlink target does not exist`
  - Fix: run `bullish-ssg link-vault /new/path/to/vault --repair`.
- Symptom: `Symlink target mismatch`
  - Fix: run `bullish-ssg link-vault /configured/path --repair`.
- Symptom: permission denied when creating link
  - Fix: ensure write permissions to repo path and read permissions to the vault path.

## Notes

- Dry-run deploy still expects `deploy.site_dir` to exist.
- Fixture-driven tests live in `tests/fixtures/` and integration coverage in `tests/integration/`.
