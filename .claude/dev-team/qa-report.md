# QA Report
**Task:** Item 1.1 — `@token_required` decorator: build and apply to all protected routes
**Branch:** auto/stage0-0.8
**Date:** 2026-07-09
**Gate mode:** tests+behavioral

## VERDICT: PASS

## Criteria Checked

- No route body calls `get_player_id()` — AST body scan of all 15 handlers in app.py + auth.py, plus assertion that `get_player_id` is not defined in app.py — PASS
- No inline `jwt.decode()` in route handlers — body-level regex scan of all 15 handlers — PASS
- All 15 protected routes have `@token_required` — AST decorator check for each route in app.py (14 routes) and auth.py (`get_current_user`) — PASS
- Public routes (`/register`, `/login`, `/leaderboard`) are NOT decorated — AST decorator-absence check for all three — PASS
- Valid JWT → 200/non-401 for `/create_bet`, `/pvp_bets`, `/ongoing_bets`, `/me` (4 routes) — behavioral tests with mocked DB — PASS
- Missing JWT → 401 for `/create_bet`, `/pvp_bets`, `/ongoing_bets`, `/me` — behavioral tests with Flask test client — PASS
- Invalid/forged JWT → 401 for `/create_bet`, `/pvp_bets`, `/ongoing_bets`, `/me` — behavioral tests — PASS
- Public routes reachable without token: `/leaderboard` returns 200, `/register` and `/login` do not respond with "Unauthorized" — PASS
- Pre-existing test suite (128 behavioral + 67 new = 195 total) — all pass — PASS

## Tests Added

- `backend/tests/test_token_required_1_1.py` — 67 tests covering: (A) static no-`get_player_id()` scan across all 15 handlers + `get_player_id` deletion from app.py; (B) `@token_required` presence check on all 15 protected routes; (C) `@token_required` absence check on 3 public routes; (D) no inline `jwt.decode()` in 15 handler bodies; (E) behavioral auth-gate enforcement for 4 routes (missing/invalid/valid JWT); (F) public route accessibility without token.
  - Note: 3 tests (`test_me_valid_jwt_returns_200`, `test_register_*`, `test_login_*`) required patching `psycopg2.connect` rather than per-module `get_db` to survive `test_dead_bets_blueprint_removed.py::test_auth_module_imports_cleanly` which pops+reimports `backend.auth` and leaves the Flask-registered closures bound to the old module's `get_db` copy.

## Not Verifiable

- Live smoke pass against real Postgres — DATABASE_URL is a fake DSN in test environment; all behavioral checks run through the Flask test client with mocked DB connections. The behavioral checks confirm routing and auth gate wiring; real DB connectivity is not testable here.
