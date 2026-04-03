# DECISIONS

1. Deploy preflight remains enabled for dry-run, but build validation is executed in adapter dry-run mode.
- Rationale: preserves config/vault/build-path checks while avoiding external side effects.

2. Branch deploy now fails early when current branch cannot be determined.
- Rationale: safe rollback is mandatory before any branch mutation workflow.

3. Step 8/9 integration tests are fixture-driven.
- Rationale: consistent with repository testing policy and reduces ad-hoc temp setup drift.
