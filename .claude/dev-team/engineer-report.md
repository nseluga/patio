# Engineer Report
**Task:** Item 1.1 — Build `@token_required` decorator and apply to all protected routes
**Branch:** auto/stage0-0.8
**Date:** 2026-07-09

## Design Decisions

- **New module `backend/utils/auth.py`** — decorator lives here to avoid circular imports; `backend/utils/__init__.py` created as empty package marker
- **SECRET_KEY resolved lazily at request time** via `import backend.app as _app_module; secret_key = _app_module.SECRET_KEY` inside the `decorated()` closure — this respects existing `patch("backend.app.SECRET_KEY", ...)` patterns in 20+ tests without any changes to those files
- **g.player_id stored as int** — `int(payload['id'])` in the decorator eliminates the `player_id = int(player_id)` coercion that was previously in `submit_stats` only; now all routes get consistent int typing
- **get_player_id() removed entirely** from app.py — no route callers remain, so the function was deleted rather than kept as dead code
- **Inline jwt.decode() block removed from auth.py `/me`** — replaced with `@token_required` + `user_id = g.player_id`
- **CPU-only routes keep `if g.player_id != 0: return 401`** — this is a role check (not auth), so it stays in the route handler; the decorator only validates the JWT
- **accept_cpu_bet `if not player_id:` guard removed** — was a None check made redundant by the decorator; the player_id == 0 edge case (CPU account itself) was never blocked here anyway
- **Test compatibility layer** — 3 test files needed updates for static analysis assertions that previously checked for `get_player_id()` calls:
  - `test_route_auth_0_5.py`: replaced `assert "get_player_id()" in src` with `_route_has_decorator()` AST check
  - `test_camelcase_fix_0_8.py`: 2 `/me` tests patched `backend.auth.SECRET_KEY`; changed to `backend.app.SECRET_KEY` to match the decorator's lookup path
  - `test_atomic_caps_0_7.py`: `test_accept_bet_debug_log_after_auth_guard` checked for `if player_id is None:` before debug log; updated to accept `@token_required` presence as equivalent

## Files Changed

- `backend/utils/__init__.py` — new empty package marker file
- `backend/utils/auth.py` — new file: `token_required` decorator with lazy SECRET_KEY lookup, populates `g.player_id` as int, returns 401 on any JWT failure
- `backend/app.py` — removed `get_player_id()` function; added `from backend.utils.auth import token_required`; added `@token_required` to 14 routes; replaced `player_id = get_player_id() / if player_id is None` boilerplate with `player_id = g.player_id`
- `backend/auth.py` — added `from backend.utils.auth import token_required`; converted `/me` from inline `jwt.decode()` block to `@token_required` + `user_id = g.player_id`
- `backend/tests/test_route_auth_0_5.py` — added `_route_has_decorator()` helper; updated 4 static analysis tests to check for `@token_required` instead of `get_player_id()` calls
- `backend/tests/test_camelcase_fix_0_8.py` — 2 `/me` test patches changed from `backend.auth.SECRET_KEY` to `backend.app.SECRET_KEY`
- `backend/tests/test_atomic_caps_0_7.py` — added `_route_has_decorator()` helper; updated `test_accept_bet_debug_log_after_auth_guard` to treat `@token_required` presence as satisfying the "auth before debug log" ordering requirement

## Deferred / Out of Scope

- No Flask `app.config['SECRET_KEY']` integration — the lazy-import approach works and avoids changing how the app initializes
- No tests for the decorator itself in isolation — coverage comes from the 128 existing behavioral tests that all exercise protected routes

## Flags for Reviewer

- The lazy `import backend.app` inside `decorated()` runs on every request — negligible cost (Python module import cache), but worth noting as an unconventional pattern
- `accept_cpu_bet` previously had `if not player_id:` which would have blocked player_id==0 (the CPU account) from accepting; this check is now gone since the decorator allows any valid JWT through; the CPU account cannot call `/accept_cpu_bet` in normal flow but this could be flagged as a subtle behavior change
- Public routes (`/register`, `/login`, `/leaderboard`) correctly have no decorator applied
