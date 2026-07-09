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
