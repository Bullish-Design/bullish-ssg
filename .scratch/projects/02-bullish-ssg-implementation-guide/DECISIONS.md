# DECISIONS

## 2026-04-03 — Create separate implementation-guide project

Decision:
- Create `02-bullish-ssg-implementation-guide` as a dedicated project for execution guidance.

Rationale:
- Keeps architecture decisions (project 01) separate from execution instructions (project 02).
- Matches project-per-task conventions in `.scratch/CRITICAL_RULES.md`.

## 2026-04-03 — Guide structure prioritizes test gates after each step

Decision:
- Require explicit per-step test requirements, commands, and pass criteria.

Rationale:
- Intern implementation quality depends on immediate verification.
- Prevents sequential drift where issues are discovered only at the end.
