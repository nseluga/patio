# Engineer Report
**Task:** Item 2.1 — Split `app.py` into app-factory pattern with 5 domain blueprints
**Branch:** auto/stage0-0.8
**Date:** 2026-07-09

## Design Decisions

- **Factory pattern**: `create_app()` in `backend/app.py` initialises Flask, CORS, and logging then registers all blueprints with local imports; a module-level `app = create_app()` at the bottom preserves `flask --app backend/app run` CLI behaviour.
- **Test patch compatibility — `get_db`**: Blueprint files import `get_db` from `backend/routes/_db.py`, a thin wrapper that does a lazy `import backend.app as _app_module; return _app_module.get_db()` at call time. This is the same pattern `backend/utils/auth.py` uses for `SECRET_KEY`, and it means all existing `patch("backend.app.get_db", ...)` test patches are honoured without any test-file changes to patch targets.
- **Test patch compatibility — `SECRET_KEY`**: `backend/app.py` re-imports and re-exports `SECRET_KEY` from `backend.config` at module level; `utils/auth.py` already lazily imports `backend.app` to pick it up. No changes needed.
- **Zero logic changes**: All route handlers were moved verbatim. SQL queries, cap deduction logic, stat recording, and response shapes are identical. The 367-line `submit_stats` handler was moved without any edits.
- **Helper placement**: `check_stats_match` and `compute_status_message` were placed in `bets_routes.py` (closest consumer); `submit_routes.py` imports them from there.
- **Blueprint naming**: No URL prefixes on any blueprint; the `/cpu/*` prefix is already embedded in the route strings in `lines_routes.py`, consistent with how it existed in the original file.
- **Test static-analysis updates**: Seven test files had hardcoded `APP_PY`-only AST helpers (`_function_source`, `_route_has_decorator`, `_function_body_source`). Each was extended with a `_SEARCH_PATHS` list covering all blueprint files; helpers now fall through to blueprint files when a function is not found in `app.py`. This is the minimum change that makes all 209 tests pass without altering any assertion logic.

## Files Changed

- `backend/app.py` — rewritten as thin factory; route code removed; re-exports `get_db` and `SECRET_KEY` for patch compatibility
- `backend/routes/__init__.py` — empty package marker
- `backend/routes/_db.py` — lazy `get_db()` indirection so `patch("backend.app.get_db")` is intercepted in all blueprint routes
- `backend/routes/bets_routes.py` — `/create_bet`, `/pvp_bets`, `/cpu_bets`, `/ongoing_bets`, `/bets` plus `check_stats_match` and `compute_status_message`
- `backend/routes/accept_routes.py` — `/accept_bet/<bet_id>`, `/accept_cpu_bet/<bet_id>`
- `backend/routes/submit_routes.py` — `/submit_stats/<bet_id>` (verbatim 367-line handler)
- `backend/routes/lines_routes.py` — all 6 `/cpu/create_*_bet` routes
- `backend/routes/main_routes.py` — `/leaderboard`, `/cleanup_bets`
- `backend/tests/test_atomic_caps_0_7.py` — extended `_function_source`/`_route_has_decorator` to search blueprint files
- `backend/tests/test_bugfix_0_8_criticals.py` — same
- `backend/tests/test_camelcase_fix_0_8.py` — same
- `backend/tests/test_cleanup_batch_0_4.py` — added `_find_function_in_backend` helper; updated two failing tests to use it
- `backend/tests/test_review_fixes_0_5.py` — extended helpers; updated `compute_status_message` import to `backend.routes.bets_routes`
- `backend/tests/test_route_auth_0_5.py` — extended helpers
- `backend/tests/test_token_required_1_1.py` — extended helpers; updated `test_protected_route_has_token_required` and `test_public_app_route_no_token_required` to search blueprint files

## Deferred / Out of Scope

- Refactoring `submit_stats` into sub-functions (PvP path / CPU path / award logic) — noted in the analysis report as a future improvement; kept verbatim per task spec.
- Adding blueprint routes to `BACKEND_PY_FILES` in `test_cleanup_batch_0_4.py` — the glob covers only `backend/*.py`; blueprint files are clean so this causes no failures and was left as-is to minimise test changes.

## Flags for Reviewer

- `backend/routes/_db.py` is a non-obvious indirection; the pattern is documented in the module docstring and mirrors `utils/auth.py`'s approach, but reviewers should be aware of it before adding new blueprints.
- `submit_routes.py` imports `check_stats_match` and `compute_status_message` from `bets_routes` — a cross-blueprint import. If these helpers grow, consider a dedicated `backend/routes/_helpers.py` module.
- The `_SEARCH_PATHS` list added to each test file will silently miss functions in new blueprint files added after this split; whoever adds a new blueprint should extend `_SEARCH_PATHS` in the tests.
