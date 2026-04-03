# PLAN

NO SUBAGENTS: Execute all tasks directly in this agent.

1. Make deploy preflight dry-run aware to avoid side effects.
2. Fix branch deploy original-branch capture/restore logic and harden cleanup behavior.
3. Align stale CLI-help deploy expectation with current command contract.
4. Convert Step 8 build/serve integration tests to fixture-driven workspaces.
5. Add Step 9 CLI deploy integration tests (adapter selection, preflight blocking, dry-run behavior).
6. Update/repair unit tests for branch deploy sequence and preflight dry-run.
7. Run Step 8/9 targeted test suites and iterate until green.

NO SUBAGENTS: Keep all implementation and testing local.
