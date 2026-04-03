# PLAN

NO SUBAGENTS: Execute all tasks directly in this agent.

1. Finalize pending Step 9 remediation already in working tree, run Step 8/9 tests, commit, push.
2. Step 10: implement `init` scaffolding + patchers + dry-run + tests, commit, push.
3. Step 11: implement `link-vault` command with config update + repair workflow + tests, commit, push.
4. Step 12: add template-driven integration snippets and patcher/template tests, commit, push.
5. Step 13: add end-to-end fixture matrix and command-level integration tests; run integration/full suites twice for flake check, commit, push.
6. Step 14: update docs/handoff and re-run full tests, commit, push.
7. Update project tracking docs (`PROGRESS`, `CONTEXT`, `DECISIONS`, `ISSUES`) continuously.

NO SUBAGENTS: Keep all implementation and testing local.
