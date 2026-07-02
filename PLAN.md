# Patio — Refactor Execution Plan
> A linear, ordered process for one main agent (with its own subagent teams) to work through, top to bottom.
> Each item still lists `owns_files` and `blocked_by` — not for parallel dispatch, but so that if the main agent
> *does* spin up subagents for a single item (e.g. splitting the gitignore/port/logging cleanup across a few
> workers), it knows which sub-pieces are genuinely independent of each other internally. Across items, treat
> this as strictly sequential: finish one, check it off, move to the next.
> Update `status` as items complete. Don't skip ahead — several items are gated for real reasons, not just ordering preference.

---

## STAGE 0 — Security fixes (do first)

### 0.1 — Fix `/submit_stats/<bet_id>` missing auth check
- **status:** not started
- **owns_files:** `app.py` (route handler only — the `/submit_stats` function block)
- **blocked_by:** none
- **blocks:** 4.1 (sport module collapse touches the same handler logic)
- **task:** Route currently trusts `playerId` from the request body. Replace with standard JWT-decode: extract user from token, verify it matches the player on the bet, reject otherwise. Do this with a manual decode for now — do NOT wait for the Stage 1 decorator to exist. This is a standalone patch.
- **done when:** a request with a forged `playerId` and another user's valid JWT is rejected with 401/403.

### 0.2 — Remove hardcoded JWT secret fallback
- **status:** not started
- **owns_files:** wherever `SECRET_KEY = os.getenv(...)` is defined (likely `app.py` or `config.py`)
- **blocked_by:** none
- **blocks:** nothing
- **task:** Remove the `"your-secret-key"` fallback. App should raise/fail at startup if `SECRET_KEY` env var is unset.
- **done when:** app fails to boot locally with `SECRET_KEY` unset, and boots normally with it set.

### 0.3 — Delete dead `bets` Blueprint in `auth.py`
- **status:** not started
- **owns_files:** `auth.py` (lines ~174–219 only)
- **blocked_by:** none
- **blocks:** nothing
- **task:** Delete the unregistered, schema-mismatched Blueprint block.
- **done when:** block is removed, app still imports/boots clean.

### 0.4 — Cleanup batch (gitignore, stray files, port mismatch, logging)
- **status:** not started
- **owns_files:** `.gitignore`, `src/pages/.Rhistory` (delete), `backend/py/` (delete), `backend/__pycache__/` (untrack), `App.js` + `api.js` (port constant only), any `print()` call sites
- **blocked_by:** none
- **blocks:** nothing
- **task:** (a) `__pycache__/`/`*.pyc` are ALREADY in `.gitignore` but the files are still tracked — `git rm -r --cached backend/__pycache__ backend/py` (the `backend/py/` dir is a stray committed `.pyc` dump); also add `venv/` to `.gitignore` (only `.venv/` is ignored today); (b) delete `.Rhistory`; (c) port mismatch: `App.js` line ~31 `/me` fetch falls back to `:5000` while `api.js`/README use `:5001` — pick `:5001` and fix `App.js`; (d) swap `print()` for `logging` with levels.
- **done when:** all four sub-items checked off; `git ls-files | grep -E '\.pyc$'` returns nothing.
- **subagent note:** these four sub-pieces don't touch each other and are genuinely fine to hand to parallel subagents *within this one item* if you want — they just all need to land before Stage 0 is considered done.

### 0.5 — Route auth inventory + client-supplied identity (found in audit)
- **status:** not started
- **owns_files:** `app.py` (route handlers: `cleanup_bets`, `get_all_bets`, `get_pvp_bets`, `create_bet`)
- **blocked_by:** none
- **blocks:** 1.1 (the decorator needs the full list of which routes are "protected" — this item produces that list)
- **task:** Several endpoints are currently unauthenticated and must be gated: (a) `/cleanup_bets` runs destructive `DELETE`s with NO auth — anyone can wipe the table; (b) `/bets` (`get_all_bets`) dumps every bet unauthenticated; (c) `/pvp_bets` trusts a `playerId` query param instead of the JWT; (d) `/create_bet` is authed but inserts the **client-supplied `posterId`/`poster`/`status`/`id`** — derive poster identity server-side from the token and stop trusting those fields. Produce a definitive per-route auth table so 1.1 applies the decorator everywhere it belongs.
- **done when:** every mutating/data-exposing route either requires a valid JWT (and uses server-derived identity) or is explicitly, intentionally public with a comment saying why; forged `posterId` in `/create_bet` is ignored.

### 0.6 — Fix or remove broken `/me` route in `auth.py` (found in audit)
- **status:** not started
- **owns_files:** `backend/auth.py` (the `/me` handler), coordinate with `App.js` `fetchUserFromBackend`
- **blocked_by:** none
- **blocks:** nothing
- **task:** `/me` is live (App.js calls it on load) but broken two ways: it calls `jwt.decode()` on the raw `Authorization` header WITHOUT stripping the `Bearer ` prefix, and it `SELECT`s columns that don't exist (`winner_id`, `poster_id`, `accepter_id`, `subject`, `player`, `line`, `game_type`, `posted_at`). Either fix it to match the real schema or replace it with a working profile endpoint. Note this is separate from the dead blueprint in 0.3.
- **done when:** `GET /me` with a valid `Bearer` token returns the user's profile + stats without error; App.js no longer silently falls into the logout/catch path.

### 0.7 — Stop leaking secrets in logs + disable debug mode (found in audit)
- **status:** not started
- **owns_files:** `app.py` (`get_player_id` print at ~71/80), `auth.py` (~113), `backend/.flaskenv`
- **blocked_by:** none
- **blocks:** nothing (but pairs naturally with 0.4d's print→logging swap)
- **task:** (a) current `print()`s dump the full decoded JWT payload and the raw `Authorization` header to logs — remove/scrub these as part of the logging swap, never log tokens or payloads; (b) `.flaskenv` sets `FLASK_ENV=development` (enables the Werkzeug debugger/console) — set to production for any non-local run and confirm the deploy command doesn't enable debug.
- **done when:** no log line contains a token or JWT payload; debug mode is off outside local dev.

---

## STAGE 1 — Auth decorator

### 1.1 — `@token_required` decorator
- **status:** not started
- **owns_files:** new `utils/auth.py`, plus every route file with a protected endpoint (`app.py` and any blueprint-adjacent route files)
- **blocked_by:** 0.1 (land the manual fix on `/submit_stats` first, then this item converts it to use the decorator — don't rewrite that handler twice in overlapping passes)
- **blocks:** 2.1 (blueprint split touches every route file — do this first so 2.1 isn't relocating code that's about to change shape)
- **task:** Build single `@token_required` decorator (or adopt `flask-jwt-extended`). Apply to every protected route. Read user from `g.user`. Convert 0.1's manual decode to use this decorator as part of this task.
- **done when:** no route does manual JWT decode; all protected routes use the decorator; existing auth tests (if any) pass.

---

## STAGE 2 — Structural reorganization

### 2.1 — App-factory + blueprints
- **status:** not started
- **owns_files:** `app.py` (full split into `create_app()` + blueprint files: `auth_routes.py`, `wallet_routes.py`, `bets_routes.py`, `lines_routes.py`, `main_routes.py`)
- **blocked_by:** 1.1
- **blocks:** 2.2, 3.1, 4.1
- **task:** Split `app.py` into app-factory pattern with ~5 domain blueprints. Reorganize only — do not rewrite route logic in this pass.
- **done when:** all routes respond identically to before; route logic is unchanged; just relocated.

### 2.2 — Error handlers + CORS scoping + Flask-Limiter
- **status:** not started
- **owns_files:** new `error_handlers.py`, CORS config block, limiter init (likely in `create_app()`)
- **blocked_by:** 2.1 (needs `create_app()` to exist as the place to register handlers/limiter)
- **blocks:** nothing
- **task:** Centralized JSON error handlers, CORS scoped to the Vercel origin only, Flask-Limiter (note Render in-memory-store caveat — fine at this scale, just document it).
- **done when:** errors return consistent JSON shape; CORS rejects non-Vercel origins; rate limiting active on at least auth + wallet-mutating routes.

### 2.3 — Input validation layer (found in audit)
- **status:** not started
- **owns_files:** new validation helpers/schemas, applied across the route files from 2.1
- **blocked_by:** 2.1 (apply per-blueprint), pairs with 2.2's error handlers
- **task:** Every route hand-parses `request.json` with no validation (e.g. `submit_stats` does `data['playerId']` and unguarded `int(...)` casts that 500 on bad input; `create_bet` accepts arbitrary fields). Add a lightweight schema layer (pydantic or marshmallow) for the mutating endpoints so malformed/missing fields return a clean 400, not a 500 or a silent bad write. Reuse the 2.2 error handler for the shape.
- **done when:** mutating routes reject malformed payloads with 400 + consistent JSON; no `KeyError`/`ValueError` reaches the client as a 500.

---

## STAGE 3 — Sport module collapse

### 3.1 — Collapse 3 sport modules → 1 parameterized module
- **status:** not started
- **owns_files:** the 3 sport modules + their single replacement file, plus the `/submit_stats` handler (already touched in 0.1/1.1 — this is the third and final touch)
- **blocked_by:** 0.1, 1.1, 2.1
- **blocks:** 7.2 (stats tests need the final module shape)
- **task:** Parameterize only genuinely identical logic across the 3 sport files. Keep real rule differences as explicit branches or injected strategies — do not force-fit a single code path where the sports actually differ.
- **done when:** one module replaces three; behavior is identical per-sport; `/submit_stats` auth + logic both reflect the final state.
- **flag: --opus** (architectural refactor across multiple files; requires side-by-side analysis of all three modules to identify natural seams and parameterization boundaries)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (this task requires human design decisions; do not attempt autonomously)

---

## STAGE 4 — Data layer migration (long pole — gates Stage 5 entirely)

### 4.1 — SQLAlchemy models + Flask-Migrate + stamp existing Supabase DB
- **status:** not started
- **owns_files:** new `models.py` (or `models/` package), migration config/folder, and — incrementally — every route file as it's ported off raw psycopg2
- **blocked_by:** 2.1 (port routes domain-by-domain into the now-existing blueprints)
- **blocks:** 5.1 (cannot build a transaction-safe wallet service against models that don't exist)
- **task:** Define SQLAlchemy models matching the existing schema exactly. Run `stamp head` against the live Supabase DB — do NOT generate a fresh migration that tries to recreate existing tables. Port routes domain-by-domain (auth → wallet → bets → lines), verifying each domain against real data before moving to the next. No big-bang cutover.
- **done when:** all routes use SQLAlchemy; `stamp` is verified correct against prod schema (test on a Supabase branch/copy first if at all possible); no raw psycopg2 calls remain.
- **flag: --opus** (highest-risk item in the whole plan because it touches live data. Don't hand this to a subagent team to move fast on — work this one yourself, step by step, with manual review of the `stamp` step before applying to the real DB. This is the one place where "ordered checklist" should slow down, not speed up.)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (live database migration cannot be undone automatically; requires human approval before stamp step)
- **audit notes:** (a) today `db.get_db()` opens a fresh psycopg2 connection per request with no pooling — configure the SQLAlchemy engine's connection pool explicitly as part of this port, don't leave it default-per-request. (b) `models.py` (the non-runtime DDL) has drifted from the live schema (`oppOutcome INTEGER` vs the TEXT it's used as; missing `cpu_acceptances`, `accepter_line_type`, the stat/aggregate tables) — model against the REAL Supabase schema, not `models.py`, and treat `models.py` as untrusted.

---

## STAGE 5 — Wallet/settlement correctness centerpiece

### 5.1 — Service layer for wallet/settlement + atomic transaction
- **status:** not started
- **owns_files:** new `services/wallet.py`, and the create/accept/settle bet route handlers that currently do check-then-act balance logic
- **blocked_by:** 4.1 (needs SQLAlchemy models + session management to exist)
- **blocks:** 7.1 (concurrency tests need this to exist), 8.1 (CI gate is meaningless without something to test)
- **task:** Move all balance mutation into one service function. Single transaction: lock wallet row (`with_for_update()`), validate, write debit + bet record + credit as a block, commit from the top of the call stack. This closes the existing check-then-act race condition — treat that bug fix as part of this task, not a separate item.
- **done when:** two concurrent requests against the same wallet cannot produce an incorrect balance (verify this manually before trusting it to the Stage 7 test suite).
- **flag: --opus** (transaction design, race condition elimination, and integration across all settlement paths; requires deep reasoning about lock ordering and atomicity)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (money-critical service layer; requires human verification of concurrency guarantees before proceeding)

### 5.2 — Refund/push semantics: stop silently burning caps (found in audit)
- **status:** not started
- **owns_files:** `cleanup_bets`, the settlement block in `submit_stats`, and the new `services/wallet.py`
- **blocked_by:** 5.1 (do this inside the wallet service so refunds are atomic too)
- **task:** Caps are deducted on create/accept but are never returned in several paths, so they silently vanish: (a) `cleanup_bets` DELETEs unaccepted `posted` bets after 7 days without refunding the poster's wager; (b) a tie produces `winner_id = None`, so the payout `UPDATE ... WHERE id = None` credits nobody and BOTH wagers disappear (no push/refund); (c) `accepted` bets that are never submitted are never cleaned up or refunded — caps stay locked forever. Add explicit refund-on-expiry, push/tie refund, and a settlement-timeout-with-refund, all through the wallet service.
- **done when:** expired-unaccepted, tied, and abandoned bets return wagers to the right players; total caps in the system is conserved across a full create→expire and create→tie cycle.
- **flag: --opus** (money-critical logic spanning multiple bet lifecycle paths; requires tracing all wager debit points and ensuring matching refund/push paths; game-theory implications of push vs. refund semantics)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (refund logic affects game fairness and cap conservation; requires human audit of all paths)

### 5.3 — Settlement idempotency: stop double-paying (found in audit)
- **status:** not started
- **owns_files:** `submit_stats` (CPU + PvP branches), `services/wallet.py`
- **blocked_by:** 5.1
- **task:** `submit_stats` has no guard against re-award. CPU path: re-posting matching stats sets `match_confirmed = TRUE` and credits `amount*2` AGAIN on every call. PvP path: relies only on `status='submitted'` flipping — make payout strictly once-only. Gate payouts on a state transition (e.g. only award when moving INTO the settled state, inside the same locked transaction as 5.1), so repeated submissions are no-ops.
- **done when:** submitting matching stats N times pays out exactly once for both CPU and PvP bets.
- **flag: --opus** (idempotency design across CPU and PvP settlement paths; requires state-machine reasoning and integrating payout guards into the 5.1 transaction boundary)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (double-payout bug is critical; requires human verification that payout guards are airtight)

---

## STAGE 6 — Portfolio/documentation

### 6.1 — README stack-honesty + Design Decisions section
- **status:** not started
- **owns_files:** `README.md`
- **blocked_by:** 4.1 (don't claim SQLAlchemy in the README until it's actually true)
- **blocks:** nothing
- **task:** Fix stack description (raw psycopg2 → SQLAlchemy, once true). Add "Design Decisions" section covering honor-system settlement, stack honesty, virtual-currency scope. Also reconcile README/CLAUDE.md claims that describe broken or stubbed behavior (the `/me` endpoint per 0.6, the messaging page/`server.js` per X.2, the local-dev port per 0.4c) — don't document features as working that aren't.
- **done when:** README matches actual code behavior with zero exceptions.

### 6.2 — Backtest or relabel "house edge" claim
- **status:** not started
- **owns_files:** wherever the house-edge claim lives (README/portfolio writeup, not app code)
- **blocked_by:** none — this is a documentation-honesty fix, not contingent on refactor progress. Fine to do early if you want it off your plate.
- **blocks:** nothing
- **task:** Either backtest the claim against real outcome data, or relabel as "designed, not yet backtested." Do not ship an unvalidated quantitative claim.
- **done when:** the claim is either backed by a backtest or explicitly hedged.

### 6.3 — Architecture diagram + portfolio writeup (sport-module refactor before/after)
- **status:** not started
- **owns_files:** docs/portfolio assets only
- **blocked_by:** 3.1 (the before/after writeup needs the "after" to exist)
- **blocks:** nothing
- **task:** Diagram React → Flask → Postgres + bet-generation flow. Write up the 3-file → 1-file sport module collapse as a portfolio talking point.
- **done when:** assets exist and accurately reflect final architecture.

---

## STAGE 7 — Test suite

### 7.1 — Settlement + balance-concurrency tests
- **status:** not started
- **owns_files:** new `tests/test_wallet.py` or similar
- **blocked_by:** 5.1
- **blocks:** 8.1
- **task:** `pytest-flask-sqlalchemy` rollback fixtures. Simulate two racing sessions against the same wallet; assert correct final balance.

### 7.2 — Line-generation stats tests
- **status:** not started
- **owns_files:** new `tests/test_lines.py` or similar
- **blocked_by:** 3.1
- **blocks:** 8.1
- **task:** `pytest.approx` / `numpy.testing.assert_allclose` against the final parameterized sport module.

### 7.3 — Test scaffolding (fixtures, conftest, CI-runnable structure)
- **status:** not started
- **owns_files:** `conftest.py`, test directory structure
- **blocked_by:** none — this is just scaffolding, no real test bodies depend on the refactor being done
- **blocks:** nothing directly, but 7.1/7.2 will want this in place first
- **task:** Set up the rollback-fixture pattern and directory structure ahead of 7.1/7.2 so you're not building fixture plumbing and real test logic at the same time.
- **subagent note:** if you want to get ahead on this while earlier stages are still running, this is the one item in the test stage that's safe to do early — it touches no app code.

### 7.4 — Bet-lifecycle integration + auth tests (found in audit)
- **status:** not started
- **owns_files:** new `tests/test_bets.py`, `tests/test_auth.py`
- **blocked_by:** 7.3 (wants the fixtures), and 0.5/5.2/5.3 (so there's correct behavior to assert)
- **blocks:** 8.1
- **task:** 7.1/7.2 only cover wallet concurrency + line stats. Add route-level tests for the full create→accept→submit→settle lifecycle (PvP and CPU), the auth boundary (forged `playerId`/`posterId` rejected per 0.1/0.5), and the refund/idempotency paths from 5.2/5.3. Frontend has no real tests (App.test.js is CRA boilerplate) — at minimum smoke-test the auth guard and one bet flow if time allows.
- **done when:** the happy path and the audit-found money bugs are each covered by a failing-before/passing-after test.

---

## STAGE 8 — CI gate

### 8.1 — GitHub Actions CI as test gate
- **status:** not started
- **owns_files:** `.github/workflows/*.yml`
- **blocked_by:** 7.1, 7.2 (a CI gate with no real tests behind it isn't a gate)
- **blocks:** nothing
- **task:** Postgres service container in the workflow; run pytest suite on push/PR. Render/Vercel already auto-deploy — this is a gate, not a deploy mechanism.

---

## STAGE 9 — Frontend

### 9.1 — Centralized Axios instance + per-domain service modules + hooks
- **status:** not started
- **owns_files:** frontend repo only — `src/services/`, `src/hooks/`, `src/api.js`
- **blocked_by:** none structurally — but see flag below
- **blocks:** nothing
- **task:** One Axios instance, service modules per domain (auth, wallet, bets, lines), a few custom hooks. Keep Context API — no Redux/feature-sliced architecture unless you exceed ~20 components or hit real cross-page state pain.
- **done when:** API calls go through service modules, not ad-hoc Axios calls scattered in components.
- **flag: --opus** (different repo/deploy target; requires tracking API contract changes from Stage 2/4 (blueprint split, SQLAlchemy port). Building against moving-target backend; coordinate architectural decisions on token storage and bet state authority across frontend/backend boundary)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (security and architecture decisions needed on token storage and state authority; cannot be resolved autonomously)
- **audit note:** `localStorage` is currently the source of truth for BOTH the JWT and ongoing-bet state (`App.js`, `acceptHandling.js`). That's an XSS-exfiltration surface for the token and lets client state diverge from the server. As part of this stage, decide on token storage (httpOnly cookie vs. accepting the localStorage tradeoff with eyes open) and make the server authoritative for bet state — don't just consolidate Axios while leaving local state as truth.

---

## UNSCHEDULED — needs definition before it can be tagged

### X.1 — "General professional grade visual improvements"
- **status:** blocked on scoping
- **task:** Not actionable as written. Before this enters the plan, name the actual surface: which component(s), what kind of change (styling pass / new view / error states / responsive fixes)? Until scoped, don't put this in front of the agent — it has no defined "done."

### X.2 — Decide the fate of the Socket.IO messaging server (found in audit)
- **status:** blocked on scoping
- **task:** `server.js` is a standalone Node/Socket.IO chat server (port 3001, `origin: "*"`, no auth) backing a stubbed 17-line `Messages.js`. It is not referenced anywhere in the rest of the plan and is effectively dead/insecure as-is. Decide: (a) cut it entirely, or (b) commit to messaging as a real feature — in which case scope auth, CORS scoping to the Vercel origin, and a deploy target for it. Until that decision is made, don't half-maintain it. Pairs with 6.1 (don't document messaging as working until it is).

---

## Order of execution (top to bottom, no skipping)
```
0.1 → 0.2 → 0.3 → 0.4 → 0.5 → 0.6 → 0.7 → 1.1 → 2.1 → 2.2 → 2.3 → 3.1 → 4.1 → 5.1 → 5.2 → 5.3 → 6.1 → 6.2 → 6.3 → 7.1 → 7.2 → 7.3 → 7.4 → 8.1 → 9.1
```
This is now a strict line, not a graph — work it top to bottom. The `blocked_by`/`blocks` fields on each item are there so you understand *why* the order is what it is (and so you don't get tempted to jump ahead on a slow stage), not so a system can route around them.

## Items NOT in this file (deferred, per stop-before lines — do not schedule)
No Redis until >1 backend instance · no Celery until settlement/line-gen is too slow for a request cycle · no Redux until ~20+ frontend components or real cross-page state pain · no full Repository/Unit-of-Work class unless swapping data stores.