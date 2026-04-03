# DECISIONS

- Initial decision: finalize existing Step 9 remediation before Step 10+ work to avoid mixing unrelated deltas in later commits.
- Step 10 scaffolding uses additive/idempotent patchers and avoids destructive rewrites; existing files are merged by adding missing defaults/snippets only.
