# DECISIONS

- Keep demo content split logically into:
  - `healthy` publishable docs/blog content (must pass validation), and
  - `broken` test-only fixtures (must intentionally fail targeted checks).
- Do not publish intentionally broken pages in the live docs tree.
- Use a deterministic verification matrix that checks every CLI command with explicit expected exit codes and output markers.
