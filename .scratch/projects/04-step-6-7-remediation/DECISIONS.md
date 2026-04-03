# DECISIONS

1. Unpublished/excluded link policy is warning-level in Step 6/7.
- Rationale: guide allows fail or warn per policy; warning preserves author feedback without failing publish on intentionally excluded content.

2. Orphan detection only evaluates publishable pages.
- Rationale: drafts/unpublished pages should not create noise in orphan reporting.

3. Integration tests use copied fixture workspaces + cwd switch.
- Rationale: avoids unsupported `CliRunner.invoke(..., cwd=...)` usage and enforces real sample-file validation.
