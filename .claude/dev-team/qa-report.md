---
# QA Report
**Task:** Item 0.5 — Route auth inventory + review-finding fixes (re-verification after Bug Fixer pass)
**Branch:** auto/stage0
**Date:** 2026-07-07
**Gate mode:** tests+behavioral

## VERDICT: PASS

## Criteria Checked

- `/cleanup_bets` requires valid JWT (401 without one) — source analysis + behavioral no-JWT, forged-JWT, valid-JWT-proceeds — PASS
- `/bets` requires valid JWT (401 without one) — source analysis + behavioral no-JWT, forged-JWT, valid-JWT-proceeds — PASS
- `/pvp_bets` uses JWT identity, not `playerId` query param; 401 without token — source confirms no `request.args` read; behavioral: no-JWT-401, query-param-alone-still-401, forged-JWT-401, valid-JWT-no-param-200 — PASS
- `/create_bet` ignores client-supplied `posterId`/`poster`/`status`/`id` and derives server-side — source confirms no `bet.get()` for those keys + `uuid4()` + `'posted'`; behavioral: no-JWT-401, forged-JWT-401, client-fields-ignored-201 with execute() inspection confirming JWT identity — PASS
- `/cleanup_bets` returns 403 for non-House authenticated users (player_id != 0) — source has `player_id != 0 → 403` guard; behavioral: player_id=1 returns 403, player_id=0 does NOT return 403 — PASS
- `/bets` is paginated (LIMIT/OFFSET, default 50, cap 100) and filtered to caller's own bets (posterid OR accepterid) — source analysis confirms LIMIT/OFFSET, posterid/accepterid WHERE clause, `min(..., 100)` cap; behavioral: page/per_page params forwarded to DB execute() call — PASS
- `/create_bet` uses atomic caps UPDATE (single UPDATE ... WHERE caps_balance >= %s); rowcount==0 returns 400 — source confirms atomic UPDATE pattern and rowcount check; behavioral: rowcount=0 mock → 400 "Insufficient caps", rowcount=1 mock → 201 — PASS
- `compute_status_message` takes `conn` as a parameter; does NOT call `get_db()` internally — source: `conn` in signature, `get_db()` absent; behavioral: calling with mock_conn triggers cursor on passed conn, `get_db` never called — PASS

## Tests Added

- `backend/tests/test_review_fixes_0_5.py` — 14 new tests: 6 static source-analysis + 8 behavioral Flask test-client; covers /cleanup_bets 403 guard, /bets pagination+filtering, /create_bet atomic caps + insufficient-caps path, compute_status_message conn-pass refactor; all mocked DB, no live Postgres required
- `backend/tests/test_cleanup_batch_0_4.py` (updated) — `test_compute_status_message_closes_connection` updated from the old design (expected `conn = get_db()` internally) to the correct new design (expects `conn` parameter, no `get_db()`, cursor closed in finally)

Full suite: **68/68 passed**, 0 regressions

## Not Verifiable

none
---
