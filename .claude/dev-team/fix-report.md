---
# Fix Report
**Date:** 2026-07-07
**Findings addressed:** 10 of 10 total: 0 QA failures + 10 review findings (5 from logging/N+1 pass + 5 from item 0.5 route-auth pass)

## Changes Made

### Item 0.5 Route Auth Fixes (this pass)
- `backend/app.py:166–167` — Added `if player_id != 0: return 403` guard to `/cleanup_bets`; was accessible by any authenticated user — review Important
- `backend/app.py:237–244` — Replaced SELECT caps_balance + Python check + separate UPDATE with a single atomic `UPDATE ... WHERE caps_balance >= %s`; `rowcount == 0` returns 400 eliminating TOCTOU race in `/create_bet` — review Important
- `backend/app.py:1041–1053` — Added `?page` / `?per_page` (default 50, max 100) LIMIT/OFFSET pagination and `WHERE posterid = %s OR accepterid = %s` filter to `/bets`; was returning full unscoped table dump — review Important
- `backend/app.py:595` — Refactored `compute_status_message` signature to accept `conn` instead of calling `get_db()` internally; creates a short-lived `RealDictCursor` on the passed connection and closes it in finally; eliminates one leaked connection per CPU bet per `/ongoing_bets` request — review Important
- `backend/app.py:516,775,813` — Updated all three `compute_status_message` call sites to pass `conn` — review Important
- `backend/app.py:109–114` — Replaced broad `except Exception` in `get_player_id()` with `except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidTokenError, KeyError)` for expected JWT errors; added separate `except Exception` fallback that calls `logger.exception()` — review Minor

### Previous Pass (logging + N+1)
- `backend/app.py:437` — Added `logger.exception("Accept CPU bet error")` before `conn.rollback()` in `accept_cpu_bet` except block — review Important
- `backend/app.py:163,226,375,438,995,1073,1155,1263,1342,1429,1509` — Replaced all `logger.error("...: %s", e)` with `logger.exception("...")` across all 11 exception handlers — review Important
- `backend/app.py:544–557` — Fixed connection leak in `compute_status_message` (superseded by this pass's refactor) — review Important
- `backend/caps_bet_generation.py / pong_bet_generation.py / beerball_bet_generation.py` — Batched per-player stat SELECTs into single `WHERE player_name = ANY(%s)` queries — review Important
- `.gitignore:12` — Added `.venv/` line — review Minor

## Disputed
None.

## Deferred
None.

---

# Fix Report — Item 0.7 Review Findings
**Date:** 2026-07-09
**Findings addressed:** 3 of 3: 0 QA failures + 3 review findings (2 Critical, 1 Minor)

## Changes Made

- `backend/app.py:396-402` — Replaced non-atomic SELECT+UPDATE caps deduction in `accept_bet` with `UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s`; `rowcount == 0` → 400 "Insufficient caps" — review Critical
- `backend/app.py:461-469` — Replaced non-atomic SELECT+UPDATE caps deduction in `accept_cpu_bet` with the same atomic guard pattern — review Critical
- `backend/app.py:376` — Moved `logger.debug("PvP accept_bet triggered by player_id: %s", player_id)` to after the `if player_id is None` auth guard so it never fires with `None` — review Minor

## Disputed

None.

## Deferred

None. All three cited findings were applied. Commit `1dc003f` on branch `conversion`.
---

# Fix Report — Item 0.8 Review Findings
**Date:** 2026-07-09
**Findings addressed:** 6 of 6: 0 QA failures + 6 review findings (2 Critical, 2 Important, 2 Minor)

## Changes Made

- `backend/app.py:834–846` — Quoted all camelCase column names in `submit_stats` dynamic UPDATE `update_fields` list (e.g., `'"yourTeamA"'`, `'"oppTeamA"'`, `'"yourPlayer"'`, etc.) so the f-string SET clause emits `"yourTeamA" = %s` instead of `yourTeamA = %s` — review Critical
- `backend/app.py:1105–1107` — Changed `get_all_bets` WHERE clause from unquoted `posterid`/`accepterid` to `"posterId"`/`"accepterId"`; also quoted `timePosted` in ORDER BY — review Critical
- `backend/app.py:397` — Changed `accept_bet` SELECT from `SELECT amount, posterId` to `SELECT amount, "posterId" AS posterid`; prevents `column "posterid" does not exist` runtime error on every PvP bet acceptance — review Important
- `backend/app.py:653` — Fixed dead-code boolean guard `(is_poster or is_accepter) is None` to `not is_poster and not is_accepter`; the original expression is always `False` so the "Unknown user" branch was unreachable — review Important
- `backend/app.py:416` — Quoted `accepterId` in `accept_bet` UPDATE SET clause: `"accepterId" = %s` — review Minor
- `backend/app.py:176–191` — Quoted `"accepterId"`, `"timePosted"` in all three `cleanup_bets` DELETE WHERE clauses — review Minor

## Disputed

None.

## Deferred

None. All 6 cited findings applied. 113/113 tests pass on branch `auto/stage0-0.8`.
---

# Fix Report — Item 0.8 Minor Finding (get_all_bets SELECT *)
**Date:** 2026-07-09
**Findings addressed:** 1 of 1 total: 0 QA failures + 1 review finding (Minor)

## Changes Made

- `backend/app.py:1104–1113` — Replaced `SELECT *` and raw `dict(zip(colnames, row))` passthrough in `get_all_bets` with an explicit 13-column aliased SELECT matching the lowercase-alias convention (`"posterId" AS posterid`, etc.) used by `get_pvp_bets` and every other handler; added normalized output dict so response keys are consistent camelCase — review Minor
- `backend/tests/test_bugfix_0_8_criticals.py:171–173` — Updated mock `colnames` in `test_get_all_bets_returns_200_with_mocked_data` from raw camelCase names (the old `SELECT *` behavior) to lowercase aliases (`posterid`, `accepterid`, `timeposted`, etc.) matching what the real DB returns from the explicit aliased SELECT

## Disputed

None.

## Deferred

None. All 128 tests pass on branch `auto/stage0-0.8`.
---

# Fix Report — Item 2.1 Review Findings
**Date:** 2026-07-09
**Findings addressed:** 3 of 4 total: 0 QA failures + 3 review findings (1 Important, 1 Minor addressed; 2 Minor skipped per task instructions)

## Changes Made

- `backend/routes/bets_routes.py:229–256` — Batch-fetched all `cpu_acceptances` rows for CPU bets before the `for row in rows` loop in `get_ongoing_bets` using a single `WHERE id = ANY(%s) AND accepter_id = %s` query; built a `{bet_id: row_dict}` map and passed it as `cpu_acceptance_map` to `compute_status_message`, eliminating N+1 DB round-trips for CPU bets — review Important
- `backend/routes/bets_routes.py:308–340` — Updated `compute_status_message` signature to `(bet, player_id, conn, cpu_acceptance_map=None)`; when `cpu_acceptance_map` is provided (normal call path) the function performs zero DB I/O via dict lookup; falls back to querying via the caller-supplied `conn` when map is absent (legacy test call-sites), ensuring `get_db()` is never called internally — review Important
- `backend/routes/main_routes.py:15–22` — Wrapped `public_leaderboard` cursor execute + fetchall in `try/finally` block; cursor and connection are now always closed even if `cur.execute` or `cur.fetchall` raises — review Important (reliability)
- `backend/routes/_db.py:1–11` — Added module-level WARNING comment instructing blueprint authors to import `get_db` from this shim rather than directly from `backend.db`, explaining that bypassing the shim silently defeats `patch("backend.app.get_db", ...)` in tests — review Minor

## Disputed

None.

## Deferred

- `backend/routes/lines_routes.py:431–438` (`safe_shots()` inline closure) — skipped per task instructions; pre-existing inconsistency, not worth touching during this structural pass.
- `backend/tests/` (`_SEARCH_PATHS` lists) — skipped per task instructions; test infrastructure, not worth touching during this structural pass.

---

# Fix Report — Item 1.1 Review Findings
**Date:** 2026-07-09
**Findings addressed:** 3 of 3 total: 0 QA failures + 3 review findings (1 Important, 2 Minor)

## Changes Made

- `backend/app.py:6` — Removed dead `import jwt`; no route body calls any `jwt.*` symbol after migration to `@token_required` — review Important
- `backend/utils/auth.py:43` — Added `jwt.exceptions.InvalidKeyError` to the typed catch tuple alongside `DecodeError`, `InvalidTokenError`, `KeyError`; config errors now log at WARNING instead of falling to the generic `except Exception` handler at ERROR — review Minor
- `backend/app.py:1107,1187,1269,1377,1456,1543` — Changed all 6 CPU-only route guards from `return jsonify({"error": "Unauthorized"}), 401` to `return jsonify({"error": "Forbidden"}), 403`; request is authenticated (decorator passed), just not authorized — review Minor

## Disputed

None.

## Deferred

None. The fourth finding in the review (`backend/utils/auth.py:33-34` — lazy circular import of `SECRET_KEY`) was explicitly marked "deferred-safe" in the review report and is not in scope per the task instructions. All 195 tests pass on branch `auto/stage0-0.8`.
---
