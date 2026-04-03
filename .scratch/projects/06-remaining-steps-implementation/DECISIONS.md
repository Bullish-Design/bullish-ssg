# DECISIONS

- Initial decision: finalize existing Step 9 remediation before Step 10+ work to avoid mixing unrelated deltas in later commits.
- Step 10 scaffolding uses additive/idempotent patchers and avoids destructive rewrites; existing files are merged by adding missing defaults/snippets only.
- `link-vault` now self-bootstraps config when absent to provide a direct repair/setup path without forcing users to run `init` first.
- Template snapshots are stored as committed fixtures under `tests/fixtures/templates/` to keep generated outputs deterministic and reviewable.
- Step 13 matrix combines command-level integration checks with explicit content-classification assertions to cover slug-collision and post routing behavior that are not yet exposed as dedicated CLI checks.
- Step 14 manual verification was executed in an isolated temp workspace using existing committed fixtures to ensure reproducible command-level evidence without mutating the repository.
