---
# Review Report
**Date:** 2026-07-07
**Files Reviewed:** 9 (backend/app.py, backend/auth.py, backend/beerball_bet_generation.py, backend/caps_bet_generation.py, backend/models.py, backend/pong_bet_generation.py, backend/stats_utils.py, src/App.js, .gitignore)
**Standards Applied:** efficiency, reliability, observability

## Summary
The logging conversion is thorough and level choices are appropriate — sensitive prints were correctly removed rather than downgraded. Two significant gaps remain: one exception handler (`accept_cpu_bet`) was skipped entirely, leaving those server failures invisible in logs; and all `logger.error("...: %s", e)` calls across the codebase drop the stack trace, which will make production post-mortems very difficult. A pre-existing DB connection leak in a per-bet helper (`compute_status_message`) and N+1 queries in the three global-strength-average functions were left untouched by the cleanup pass and should be addressed.

## Findings

### Important

**backend/app.py:436–439** — Reliability/**Log with Context** — `accept_cpu_bet`'s `except` block rolls back and returns 500 but never calls `logger.error()`; it is the only handler in the file not converted by this task, so those server errors are completely invisible in logs — Add `logger.error("Accept CPU bet error: %s", e)` before `conn.rollback()`, matching every other handler.

**backend/app.py:84,163,226,375,991,1068,1150,1259,1338,1426,1503 (and one call each in beerball/caps/pong_bet_generation.py)** — Observability/**Log at the Right Level** — All `logger.error("...: %s", e)` calls include the exception message but silently drop the traceback; in a 1 500-line file, a bare message like `"Bet insert failed: value too long for type"` gives no call chain or line number — Replace `logger.error("Foo failed: %s", e)` with `logger.exception("Foo failed")` throughout; `logger.exception()` is equivalent but auto-appends `exc_info=True`.

**backend/app.py:545–558** — Reliability/**Close Resources** — `compute_status_message` calls `get_db()` to open a new connection but only stores the cursor and calls `cur.close()`; the connection is never closed; since `get_ongoing_bets` calls this helper once per CPU bet in the result set, every request to that endpoint leaks one connection per CPU bet — Store `conn = get_db()`, wrap the body in `try/finally`, and call `conn.close()` in the finally block.

**backend/caps_bet_generation.py:80–92 / backend/pong_bet_generation.py:93–100 / backend/beerball_bet_generation.py:92–97** — Efficiency/**No N+1 Queries** — Each `get_global_*_strength_average` function fetches all score-profile rows in one query, then fires a separate `SELECT … WHERE player_name = %s` per player inside the loop — Collect all player names after the outer query, execute a single `WHERE player_name IN (…)` query, build a `{name: row}` dict, and do a dict-lookup inside the loop.

### Minor

**.gitignore:10** — Reliability/**Safe Defaults** — The engineer report states both `venv/` and `.venv/` are now covered, but the file contains only `venv/`; `.venv/` (the dotted variant used by Poetry and `python -m venv` on many systems) is untracked — Add `.venv/` on its own line so both common names are ignored.

## STANDARDS.md Updates
- Added **Observability / Use `logger.exception()` for caught exceptions** — project convention for error handlers.
---
