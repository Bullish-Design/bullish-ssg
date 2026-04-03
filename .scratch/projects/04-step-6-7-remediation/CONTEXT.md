# CONTEXT

Task:
- Complete all Step 6 and Step 7 fixes/improvements from prior review findings.

What was implemented:
- `src/bullish_ssg/validate/wikilinks.py`
  - Added unpublished/excluded target policy handling in resolver.
  - Added shared `normalize_page_ref` helper.
  - Removed unused `slug_extractor` parameter from `build_page_index`.
- `src/bullish_ssg/validate/rules.py`
  - Implemented orphan detection in `ValidationRunner.run_full_validation(include_orphan_check=True)`.
  - Added publishability gating for orphan/link analysis (`draft`/`published` metadata policy).
  - Fixed `WikilinkValidator` stats to count all parsed links, not only diagnostics.
  - Added `files_with_issues` stat.
  - Updated summary printing to include stats even when validation passes cleanly.
- Tests/fixtures:
  - Replaced `tests/integration/test_cli_validate.py` tmp-file setup with fixture-driven workspaces.
  - Added fixture sets under `tests/fixtures/validation/*` for healthy, malformed frontmatter, broken links, symlink-broken, orphan case, and unpublished target scenarios.
  - Extended unit tests in `tests/unit/test_wikilinks.py` and `tests/unit/test_validate_rules.py`.
  - Updated `tests/unit/test_cli_help.py` for config-required behavior of `validate`/`check-links`.
- Docs:
  - Updated Step 6/7 testing notes in `.scratch/projects/02-bullish-ssg-implementation-guide/IMPLEMENTATION_GUIDE.md` to require committed fixtures over ad-hoc inline sample construction.

Verification run status:
- `devenv shell -- pytest tests/unit/test_wikilinks.py tests/unit/test_validate_rules.py tests/integration/test_cli_validate.py tests/unit/test_cli_help.py -q` passed.
- `devenv shell -- pytest tests/ -k "wikilink or heading or anchor" -q` passed.
- `devenv shell -- pytest tests/ -k "validate or check_links" -q` passed.
