# Patio — Refactor & App Store Launch Execution Plan
> A linear, ordered process for one main agent (with its own subagent teams) to work through, top to bottom.
> Each item still lists `owns_files` and `blocked_by` — not for parallel dispatch, but so that if the main agent
> *does* spin up subagents for a single item (e.g. splitting the gitignore/port/logging cleanup across a few
> workers), it knows which sub-pieces are genuinely independent of each other internally. Across items, treat
> this as strictly sequential: finish one, check it off, move to the next.
> Update `status` as items complete. Don't skip ahead — several items are gated for real reasons, not just ordering preference.

> **Mobile-first pivot (2026-07-02):** The end target is a **React Native (Expo) iOS app shipped on the App Store**,
> not a web app. Stage M (conversion) runs FIRST, before the backend refactor stages. Stage 10 (App Store
> submission) runs LAST because Apple review makes the Stage 0/5 security and money bugs launch-blockers:
> you cannot ship a public app with unauthenticated destructive routes and a double-payout settlement path.
> The CRA web app's retirement is now an unscheduled item (**X.6**, moved out of Stage M on 2026-07-05) rather than a gating step in the execution line; the Flask API stays exactly where it is (Render) and all
> backend stages (0–8) apply unchanged to the API the mobile app consumes.

> **Schema source of truth (2026-07-05):** `DATABASE.md` at repo root is the trusted, conceptual description of the
> live Supabase schema (the two-worlds model, table meanings, and drift/gotchas), reconstructed from the live
> `information_schema`. `backend/models.py` is **untrusted**. Every DB-touching item below
> (0.3, 0.8, 3.1, 4.1, 5.1–5.3, 10.2, X.3, X.7) should be read against `DATABASE.md`.

---

## STAGE M — React Native conversion (do this first)

### M.1 — Scaffold Expo app + navigation shell
- **status:** not started
- **track:** full
- **owns_files:** new `mobile/` directory (Expo app: `app.json`/`app.config.js`, `App.js`, `package.json`), root `README.md` (dev-setup section only)
- **blocked_by:** none
- **blocks:** M.2, M.3, X.6 (web app retirement, now unscheduled)
- **task:** Create an Expo app (current Expo SDK — let the SDK pin the React/React Native version matrix, do NOT hand-roll `react-native init`) in a new `mobile/` directory alongside the existing CRA app. Install React Navigation (native stack for the auth flow + bottom-tab navigator replacing `src/components/BottomNav.js`). Wire API base URL via `EXPO_PUBLIC_API_URL` (dev: `http://localhost:5001`, or the machine's LAN IP for on-device testing). Leave the CRA app fully untouched until X.6 retires it — no big-bang deletion before the mobile app reaches parity.
- **done when:** blank Expo app boots on the iOS simulator with a tab-bar shell (PvP / House / Ongoing / Leaderboard / Profile placeholders) and a stubbed Login screen outside the tabs.

### M.2 — Fix `/me` + port the auth/API layer (SecureStore, no cookies)
- **status:** not started
- **track:** full
- **owns_files:** `mobile/src/api.js`, `mobile/src/UserContext.js`, mobile auth bootstrap, Login/Register screens; `backend/auth.py` (`/me` handler — this **pulls item 0.6 forward**, because the mobile app cannot boot against a broken `/me`)
- **blocked_by:** M.1
- **blocks:** M.3
- **task:** (a) Fix `/me` per 0.6 (strip `Bearer ` prefix before decode, SELECT only columns that exist) — do it now, not in Stage 0. (b) Port `src/api.js`: same axios-instance + `Authorization: Bearer` interceptor pattern, but token read from `expo-secure-store` instead of `localStorage`, and **drop `withCredentials`** — native clients have no cookie jar worth building on; header-token + SecureStore is the decided pattern (this resolves the token-storage question in the old 9.1 audit note). (c) Port the App.js auth-bootstrap (restore token → `GET /me` → populate `UserContext`) and the Login/Register screens.
- **done when:** register → login → relaunch-with-persisted-session → logout all work on the simulator against the local backend; token lives in SecureStore; `GET /me` returns the profile without error.

### M.3 — Port the five main screens to RN primitives
- **status:** not started
- **track:** full
- **owns_files:** `mobile/src/screens/` (PvP, CPU/House, Ongoing, Leaderboard, Profile), `mobile/src/utils/` (port `betCreation.js`, `acceptHandling.js`, `timeUtils.js`), `mobile/src/assets/` (copy PNGs)
- **blocked_by:** M.2
- **blocks:** X.6 (web app retirement, now unscheduled)
- **task:** Port each page one at a time (order: Leaderboard → Profile → PvP → CPU → Ongoing, simplest first). JSX/DOM → RN primitives (`View`/`Text`/`FlatList`/`Pressable`), the 7 CSS files → co-located `StyleSheet.create` (keep one-file-per-screen convention), `lucide-react` → `lucide-react-native`, `window.confirm`/`alert` → RN `Alert`. `betCreation.js`/`timeUtils.js` are pure JS — port unchanged. `acceptHandling.js`: swap `localStorage` for `AsyncStorage` as a parity shim only — making the server authoritative for ongoing-bet state stays a Stage 9 task, don't redesign it mid-port. Skip the 17-line Messages stub entirely (see X.2).
- **done when:** every flow that works on the web app today works on the simulator: browse/accept PvP and House bets, submit stats on Ongoing, view Leaderboard and Profile.
- **flag: --opus** (largest single chunk of the conversion — ~1,300 LOC across 5 screens with layout re-thinking for mobile viewports, not mechanical find-replace)

---

## STAGE 0 — Security fixes (first of the backend stages — Stage M precedes it by product decision)

### 0.1 — Fix `/submit_stats/<bet_id>` missing auth check
- **status:** not started
- **track:** full
- **owns_files:** `app.py` (route handler only — the `/submit_stats` function block)
- **blocked_by:** none
- **blocks:** 4.1 (sport module collapse touches the same handler logic)
- **task:** Route currently trusts `playerId` from the request body. Replace with standard JWT-decode: extract user from token, verify it matches the player on the bet, reject otherwise. Do this with a manual decode for now — do NOT wait for the Stage 1 decorator to exist. This is a standalone patch.
- **done when:** a request with a forged `playerId` and another user's valid JWT is rejected with 401/403.

### 0.2 — Remove hardcoded JWT secret fallback
- **status:** not started
- **track:** light
- **owns_files:** wherever `SECRET_KEY = os.getenv(...)` is defined (likely `app.py` or `config.py`)
- **blocked_by:** none
- **blocks:** nothing
- **task:** Remove the `"your-secret-key"` fallback. App should raise/fail at startup if `SECRET_KEY` env var is unset.
- **done when:** app fails to boot locally with `SECRET_KEY` unset, and boots normally with it set.

### 0.3 — Delete dead `bets` Blueprint in `auth.py`
- **status:** not started
- **track:** light
- **owns_files:** `auth.py` (lines ~174–219 only)
- **blocked_by:** none
- **blocks:** nothing
- **task:** Delete the unregistered, schema-mismatched Blueprint block (see `DATABASE.md` Gotcha 5 — it INSERTs columns that don't exist: `poster_id`/`subject`/`line`).
- **done when:** block is removed, app still imports/boots clean.

### 0.4 — Cleanup batch (gitignore, stray files, port mismatch, logging)
- **status:** not started
- **track:** full
- **owns_files:** `.gitignore`, `src/pages/.Rhistory` (delete), `backend/py/` (delete), `backend/__pycache__/` (untrack), `App.js` + `api.js` (port constant only), any `print()` call sites
- **blocked_by:** none
- **blocks:** nothing
- **task:** (a) `__pycache__/`/`*.pyc` are ALREADY in `.gitignore` but the files are still tracked — `git rm -r --cached backend/__pycache__ backend/py` (the `backend/py/` dir is a stray committed `.pyc` dump); also add `venv/` to `.gitignore` (only `.venv/` is ignored today); (b) delete `.Rhistory`; (c) port mismatch: `App.js` line ~31 `/me` fetch falls back to `:5000` while `api.js`/README use `:5001` — pick `:5001` and fix `App.js`; (d) swap `print()` for `logging` with levels.
- **done when:** all four sub-items checked off; `git ls-files | grep -E '\.pyc$'` returns nothing.
- **subagent note:** these four sub-pieces don't touch each other and are genuinely fine to hand to parallel subagents *within this one item* if you want — they just all need to land before Stage 0 is considered done.

### 0.5 — Route auth inventory + client-supplied identity (found in audit)
- **status:** not started
- **track:** full
- **owns_files:** `app.py` (route handlers: `cleanup_bets`, `get_all_bets`, `get_pvp_bets`, `create_bet`)
- **blocked_by:** none
- **blocks:** 1.1 (the decorator needs the full list of which routes are "protected" — this item produces that list)
- **task:** Several endpoints are currently unauthenticated and must be gated: (a) `/cleanup_bets` runs destructive `DELETE`s with NO auth — anyone can wipe the table; (b) `/bets` (`get_all_bets`) dumps every bet unauthenticated; (c) `/pvp_bets` trusts a `playerId` query param instead of the JWT; (d) `/create_bet` is authed but inserts the **client-supplied `posterId`/`poster`/`status`/`id`** — derive poster identity server-side from the token and stop trusting those fields. Produce a definitive per-route auth table so 1.1 applies the decorator everywhere it belongs.
- **done when:** every mutating/data-exposing route either requires a valid JWT (and uses server-derived identity) or is explicitly, intentionally public with a comment saying why; forged `posterId` in `/create_bet` is ignored.

### 0.6 — Fix or remove broken `/me` route in `auth.py` (found in audit)
- **status:** PULLED FORWARD into M.2 — the mobile app cannot boot against a broken `/me`. Do the fix there; when this row is reached, just verify it landed.
- **track:** trivial
- **owns_files:** `backend/auth.py` (the `/me` handler), coordinate with `App.js` `fetchUserFromBackend`
- **blocked_by:** none
- **blocks:** nothing
- **task:** `/me` is live (App.js calls it on load) but broken two ways: it calls `jwt.decode()` on the raw `Authorization` header WITHOUT stripping the `Bearer ` prefix, and it `SELECT`s columns that don't exist (`winner_id`, `poster_id`, `accepter_id`, `subject`, `player`, `line`, `game_type`, `posted_at`). Either fix it to match the real schema or replace it with a working profile endpoint. Note this is separate from the dead blueprint in 0.3.
- **done when:** `GET /me` with a valid `Bearer` token returns the user's profile + stats without error; App.js no longer silently falls into the logout/catch path.

### 0.7 — Stop leaking secrets in logs + disable debug mode (found in audit)
- **status:** not started
- **track:** full
- **owns_files:** `app.py` (`get_player_id` print at ~71/80), `auth.py` (~113), `backend/.flaskenv`
- **blocked_by:** none
- **blocks:** nothing (but pairs naturally with 0.4d's print→logging swap)
- **task:** (a) current `print()`s dump the full decoded JWT payload and the raw `Authorization` header to logs — remove/scrub these as part of the logging swap, never log tokens or payloads; (b) `.flaskenv` sets `FLASK_ENV=development` (enables the Werkzeug debugger/console) — set to production for any non-local run and confirm the deploy command doesn't enable debug.
- **done when:** no log line contains a token or JWT payload; debug mode is off outside local dev.

### 0.8 — Fix camelCase column access breaking core reads (found in DB audit 2026-07-05)
- **status:** not started
- **track:** full
- **owns_files:** `app.py` (the read handlers: `get_pvp_bets`, the CPU/House bet reads, the ongoing-bets read), `auth.py` (`/me` bets query)
- **blocked_by:** none — standalone patch; do it early so the app stops 500ing before the big 4.1 migration
- **blocks:** nothing hard, but unblocks real QA of the X.5 redesign (screens can't load data while this is broken)
- **task:** `bets` and `bettable_player_stats` have **quoted, case-sensitive camelCase columns** (`posterId`, `gameType`, `timePosted`, `lineNumber`, `gamePlayed`, …). The read code selects them unquoted (folds to lowercase → errors) and/or reads `SELECT *` dict keys in the wrong case — the likely root cause of the pre-existing 500s on `/pvp_bets`, `/cpu_bets`, `/ongoing_bets`, `/me`. Interim fix: quote the identifiers (and/or alias them to lowercase in the SELECT) so the queries run and dict-key access matches. This is the stopgap; **4.1 renames these columns to `snake_case` permanently.** See `DATABASE.md` Gotcha 1.
- **done when:** `/pvp_bets`, `/cpu_bets`, `/ongoing_bets`, and `/me` return 200 with real data on the simulator; no camelCase `KeyError`/`column does not exist` remains in those paths.

---

## STAGE 1 — Auth decorator

### 1.1 — `@token_required` decorator
- **status:** not started
- **track:** full
- **owns_files:** new `utils/auth.py`, plus every route file with a protected endpoint (`app.py` and any blueprint-adjacent route files)
- **blocked_by:** 0.1 (land the manual fix on `/submit_stats` first, then this item converts it to use the decorator — don't rewrite that handler twice in overlapping passes)
- **blocks:** 2.1 (blueprint split touches every route file — do this first so 2.1 isn't relocating code that's about to change shape)
- **task:** Build single `@token_required` decorator (or adopt `flask-jwt-extended`). Apply to every protected route. Read user from `g.user`. Convert 0.1's manual decode to use this decorator as part of this task.
- **done when:** no route does manual JWT decode; all protected routes use the decorator; existing auth tests (if any) pass.

---

## STAGE 2 — Structural reorganization

### 2.1 — App-factory + blueprints
- **status:** not started
- **track:** full
- **owns_files:** `app.py` (full split into `create_app()` + blueprint files: `auth_routes.py`, `wallet_routes.py`, `bets_routes.py`, `lines_routes.py`, `main_routes.py`)
- **blocked_by:** 1.1
- **blocks:** 2.2, 3.1, 4.1
- **task:** Split `app.py` into app-factory pattern with ~5 domain blueprints. Reorganize only — do not rewrite route logic in this pass.
- **done when:** all routes respond identically to before; route logic is unchanged; just relocated.

### 2.2 — Error handlers + CORS scoping + Flask-Limiter
- **status:** not started
- **track:** full
- **owns_files:** new `error_handlers.py`, CORS config block, limiter init (likely in `create_app()`)
- **blocked_by:** 2.1 (needs `create_app()` to exist as the place to register handlers/limiter)
- **blocks:** nothing
- **task:** Centralized JSON error handlers, CORS lockdown, Flask-Limiter (note Render in-memory-store caveat — fine at this scale, just document it). **Mobile note:** native clients send no `Origin` header, so CORS is irrelevant to the RN app — after X.6 retires the web app there is no legitimate browser origin at all. Lock CORS down to nothing (or dev-localhost only) rather than scoping to Vercel.
- **done when:** errors return consistent JSON shape; no wildcard CORS remains; rate limiting active on at least auth + wallet-mutating routes.

### 2.3 — Input validation layer (found in audit)
- **status:** not started
- **track:** full
- **owns_files:** new validation helpers/schemas, applied across the route files from 2.1
- **blocked_by:** 2.1 (apply per-blueprint), pairs with 2.2's error handlers
- **task:** Every route hand-parses `request.json` with no validation (e.g. `submit_stats` does `data['playerId']` and unguarded `int(...)` casts that 500 on bad input; `create_bet` accepts arbitrary fields). Add a lightweight schema layer (pydantic or marshmallow) for the mutating endpoints so malformed/missing fields return a clean 400, not a 500 or a silent bad write. Reuse the 2.2 error handler for the shape.
- **done when:** mutating routes reject malformed payloads with 400 + consistent JSON; no `KeyError`/`ValueError` reaches the client as a 500.

---

## STAGE 3 — Sport module collapse

### 3.1 — Collapse 3 sport modules → 1 parameterized module
- **status:** not started
- **track:** full
- **owns_files:** the 3 sport modules + their single replacement file, plus the `/submit_stats` handler (already touched in 0.1/1.1 — this is the third and final touch)
- **blocked_by:** 0.1, 1.1, 2.1
- **blocks:** 7.2 (stats tests need the final module shape)
- **task:** **Architecture decided (2026-07-05):** a single **shared pipeline** (fetch players → build profiles → assemble matchup → apply ~4% house bias → snap to half-point) with the **per-sport line math kept sport-specific**, injected as a strategy — DV, teammate-suppression, and the differing `opportunity_factor` signatures stay explicit, NOT force-fit into one path. Put the per-sport point estimate behind a `predict_expected_stat(matchup, profiles) -> float` seam so it can later be swapped heuristic→ML without touching the pipeline (ML deliberately deferred — at current data volume a tuned heuristic beats a learner; capture the reasoning for 6.3). **Behavior-preserving:** does NOT fix the DV/win_rate gap (that's X.7 — implementing it would change line output and is intentionally out of scope here). Model against `DATABASE.md`, not `models.py`.
- **done when:** one module replaces three; a **golden-master check** (capture each original module's line output for a fixed input set *before* refactoring, then assert the new module reproduces it byte-for-byte per sport) passes — this replaces the old human design gate and is later formalized as 7.2; `/submit_stats` auth + logic both reflect the final state.
- **flag: --opus** (architectural refactor across multiple files; requires side-by-side analysis of all three modules to identify natural seams and parameterization boundaries)
- **autonomous:** OK to run autonomously now that the architecture is decided — **gated on golden-master line-parity, not human sign-off.** (The ~4% house bias is money-adjacent; the parity check is what guarantees the refactor doesn't shift it.)

---

## STAGE 4 — Data layer migration (long pole — gates Stage 5 entirely)

### 4.1 — SQLAlchemy models + Flask-Migrate + stamp existing Supabase DB
- **status:** not started
- **track:** full
- **owns_files:** new `models.py` (or `models/` package), migration config/folder, and — incrementally — every route file as it's ported off raw psycopg2
- **blocked_by:** 2.1 (port routes domain-by-domain into the now-existing blueprints)
- **blocks:** 5.1 (cannot build a transaction-safe wallet service against models that don't exist)
- **task:** Define SQLAlchemy models matching the existing schema exactly — **model against `DATABASE.md` (the trusted reference), NOT `models.py`.** Run `stamp head` against the live Supabase DB — do NOT generate a fresh migration that tries to recreate existing tables. Port routes domain-by-domain (auth → wallet → bets → lines), verifying each domain against real data before moving to the next. No big-bang cutover. **Fold in the schema-hygiene fixes from `DATABASE.md` as coordinated migrations:** (i) **rename the quoted camelCase columns on `bets` & `bettable_player_stats` to `snake_case`** (permanent fix for Gotcha 1 / the 0.8 stopgap — casing stops mattering); (ii) add **explicit FKs** for `bets.posterId`/`accepterId` → `players.id` (today they're `text` with no FK — Gotcha 2); (iii) normalize `bets.oppOutcome` (integer) vs `yourOutcome` (text) to one type (Gotcha 4).
- **done when:** all routes use SQLAlchemy; `stamp` is verified correct against prod schema (test on a Supabase branch/copy first if at all possible); no raw psycopg2 calls remain.
- **flag: --opus** (highest-risk item in the whole plan because it touches live data. Don't hand this to a subagent team to move fast on — work this one yourself, step by step, with manual review of the `stamp` step before applying to the real DB. This is the one place where "ordered checklist" should slow down, not speed up.)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (live database migration cannot be undone automatically; requires human approval before stamp step)
- **audit notes:** (a) today `db.get_db()` opens a fresh psycopg2 connection per request with no pooling — configure the SQLAlchemy engine's connection pool explicitly as part of this port, don't leave it default-per-request. (b) **`models.py` is untrusted** — it defines only `players`+`bets` and disagrees with the live schema. Model against `DATABASE.md`, reconstructed from the live `information_schema`; it documents every table, the two-worlds model, and the drift (camelCase casing, missing FKs, `oppOutcome` type, and the absent `win_rate`/`defensive_value`/`mean_last_5` aggregate columns).

---

## STAGE 5 — Wallet/settlement correctness centerpiece

### 5.1 — Service layer for wallet/settlement + atomic transaction
- **status:** not started
- **track:** full
- **owns_files:** new `services/wallet.py`, and the create/accept/settle bet route handlers that currently do check-then-act balance logic
- **blocked_by:** 4.1 (needs SQLAlchemy models + session management to exist)
- **blocks:** 7.1 (concurrency tests need this to exist), 8.1 (CI gate is meaningless without something to test)
- **task:** Move all balance mutation into one service function. Single transaction: lock wallet row (`with_for_update()`), validate, write debit + bet record + credit as a block, commit from the top of the call stack. This closes the existing check-then-act race condition — treat that bug fix as part of this task, not a separate item. (Debit/credit points + the caps-conservation invariant + the House `id=0` infinite-bankroll note are enumerated in `DATABASE.md` → "Caps economy".)
- **done when:** two concurrent requests against the same wallet cannot produce an incorrect balance (verify this manually before trusting it to the Stage 7 test suite).
- **flag: --opus** (transaction design, race condition elimination, and integration across all settlement paths; requires deep reasoning about lock ordering and atomicity)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (money-critical service layer; requires human verification of concurrency guarantees before proceeding)

### 5.2 — Refund/push semantics: stop silently burning caps (found in audit)
- **status:** not started — **semantics decided 2026-07-05 (rules below); no open design questions.**
- **track:** full
- **owns_files:** `cleanup_bets`, the settlement block in `submit_stats`, `create_bet` (line validation), and the new `services/wallet.py`
- **blocked_by:** 5.1 (do this inside the wallet service so refunds are atomic too)
- **task:** Caps are deducted on create/accept but never returned in several paths, so they vanish. Implement these **decided rules**, all through the wallet service:
  - **(Q1) No pushes anywhere.** Force PvP lines to **half-points** (validate/round at `create_bet`; CPU lines are already `±0.5`). Makes "every accepted bet has a definite winner" an invariant and kills the `winner_id = None` tie branch.
  - **(Q2) Expired unaccepted `posted` bets → refund the poster**, then remove. Keep the **7-day** window. (Manual poster-cancel deferred — fold into 9.1/X.5, not here.)
  - **(Q3) `accepted` PvP bets that never settle (ghost OR disagreeing stats) → auto-void + refund BOTH wagers after 7 days.** One path covers ghost and dispute; no arbitration mechanism (honor-system, non-cashable caps make the "griefer forces a tie" outcome harmless).
  - **(Q4) Abandoned CPU acceptances → house keeps the wager (NO refund).** The CPU wager is committed at accept-time and confirmation only *claims* a win; refunding "never confirmed" would let losers dodge losses and break the house edge. Only PvP gets timeout-refunds.
- **done when:** expired-unaccepted (refund poster), abandoned-accepted (refund both), and dispute (refund both) paths conserve caps; abandoned CPU acceptances do NOT refund; **total caps are conserved across a full create→expire and create→ghost/dispute cycle** (assert in the 7.4 tests). See `DATABASE.md` → bet lifecycle + caps economy.
- **flag: --opus** (money-critical logic spanning multiple bet lifecycle paths; trace all wager debit points and ensure matching refund paths)
- **autonomous:** design gate resolved — implement the rules above; the STOP is downgraded to **verify caps-conservation in the 7.4 tests** rather than a human design audit.

### 5.3 — Settlement idempotency: stop double-paying (found in audit)
- **status:** not started
- **track:** full
- **owns_files:** `submit_stats` (CPU + PvP branches), `services/wallet.py`
- **blocked_by:** 5.1
- **task:** `submit_stats` has no guard against re-award. CPU path: re-posting matching stats sets `match_confirmed = TRUE` and credits `amount*2` AGAIN on every call. PvP path: relies only on `status='submitted'` flipping — make payout strictly once-only. Gate payouts on a state transition (e.g. only award when moving INTO the settled state, inside the same locked transaction as 5.1), so repeated submissions are no-ops. **Note (X.3 interaction):** once House wagers move onto `cpu_acceptances` (per-acceptance amount), the CPU payout must read `2 × acceptance_wager`, not `bets.amount`, and the once-only guard keys on `cpu_acceptances.match_confirmed`. See `DATABASE.md` → cpu_acceptances + lifecycle.
- **done when:** submitting matching stats N times pays out exactly once for both CPU and PvP bets.
- **flag: --opus** (idempotency design across CPU and PvP settlement paths; requires state-machine reasoning and integrating payout guards into the 5.1 transaction boundary)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (double-payout bug is critical; requires human verification that payout guards are airtight)

---

## STAGE 6 — Portfolio/documentation

### 6.1 — README stack-honesty + Design Decisions section
- **status:** not started
- **track:** trivial
- **owns_files:** `README.md`
- **blocked_by:** 4.1 (don't claim SQLAlchemy in the README until it's actually true)
- **blocks:** nothing
- **task:** Fix stack description (raw psycopg2 → SQLAlchemy, once true). Add "Design Decisions" section covering honor-system settlement, stack honesty, virtual-currency scope. Also reconcile README/CLAUDE.md claims that describe broken or stubbed behavior (the `/me` endpoint per 0.6, the messaging page/`server.js` per X.2, the local-dev port per 0.4c) — don't document features as working that aren't.
- **done when:** README matches actual code behavior with zero exceptions.

### 6.2 — Backtest or relabel "house edge" claim
- **status:** not started
- **track:** trivial
- **owns_files:** wherever the house-edge claim lives (README/portfolio writeup, not app code)
- **blocked_by:** none — this is a documentation-honesty fix, not contingent on refactor progress. Fine to do early if you want it off your plate.
- **blocks:** nothing
- **task:** Either backtest the claim against real outcome data, or relabel as "designed, not yet backtested." Do not ship an unvalidated quantitative claim.
- **done when:** the claim is either backed by a backtest or explicitly hedged.

### 6.3 — Architecture diagram + portfolio writeup (sport-module refactor before/after)
- **status:** not started
- **track:** trivial
- **owns_files:** docs/portfolio assets only
- **blocked_by:** 3.1 (the before/after writeup needs the "after" to exist)
- **blocks:** nothing
- **task:** Diagram React Native (Expo) → Flask → Postgres + bet-generation flow. Write up the 3-file → 1-file sport module collapse and the web→mobile conversion as portfolio talking points.
- **done when:** assets exist and accurately reflect final architecture.

---

## STAGE 7 — Test suite

### 7.1 — Settlement + balance-concurrency tests
- **status:** not started
- **track:** full
- **owns_files:** new `tests/test_wallet.py` or similar
- **blocked_by:** 5.1
- **blocks:** 8.1
- **task:** `pytest-flask-sqlalchemy` rollback fixtures. Simulate two racing sessions against the same wallet; assert correct final balance.

### 7.2 — Line-generation stats tests
- **status:** not started
- **track:** full
- **owns_files:** new `tests/test_lines.py` or similar
- **blocked_by:** 3.1
- **blocks:** 8.1
- **task:** `pytest.approx` / `numpy.testing.assert_allclose` against the final parameterized sport module.

### 7.3 — Test scaffolding (fixtures, conftest, CI-runnable structure)
- **status:** not started
- **track:** light
- **owns_files:** `conftest.py`, test directory structure
- **blocked_by:** none — this is just scaffolding, no real test bodies depend on the refactor being done
- **blocks:** nothing directly, but 7.1/7.2 will want this in place first
- **task:** Set up the rollback-fixture pattern and directory structure ahead of 7.1/7.2 so you're not building fixture plumbing and real test logic at the same time.
- **subagent note:** if you want to get ahead on this while earlier stages are still running, this is the one item in the test stage that's safe to do early — it touches no app code.

### 7.4 — Bet-lifecycle integration + auth tests (found in audit)
- **status:** not started
- **track:** full
- **owns_files:** new `tests/test_bets.py`, `tests/test_auth.py`
- **blocked_by:** 7.3 (wants the fixtures), and 0.5/5.2/5.3 (so there's correct behavior to assert)
- **blocks:** 8.1
- **task:** 7.1/7.2 only cover wallet concurrency + line stats. Add route-level tests for the full create→accept→submit→settle lifecycle (PvP and CPU), the auth boundary (forged `playerId`/`posterId` rejected per 0.1/0.5), and the refund/idempotency paths from 5.2/5.3. Frontend has no real tests (App.test.js is CRA boilerplate) — at minimum smoke-test the auth guard and one bet flow if time allows.
- **done when:** the happy path and the audit-found money bugs are each covered by a failing-before/passing-after test.

---

## STAGE 8 — CI gate

### 8.1 — GitHub Actions CI as test gate
- **status:** not started
- **track:** light
- **owns_files:** `.github/workflows/*.yml`
- **blocked_by:** 7.1, 7.2 (a CI gate with no real tests behind it isn't a gate)
- **blocks:** nothing
- **task:** Postgres service container in the workflow; run pytest suite on push/PR. Render/Vercel already auto-deploy — this is a gate, not a deploy mechanism.

---

## STAGE 9 — Mobile app hardening (was: Frontend)

### 9.1 — Per-domain service modules + hooks + server-authoritative bet state
- **status:** not started
- **track:** full
- **owns_files:** `mobile/src/services/`, `mobile/src/hooks/`, `mobile/src/api.js`, `mobile/src/utils/acceptHandling.js`; backend: an ongoing-bets read endpoint if one doesn't exist by now
- **blocked_by:** M.3 (screens must exist), and practically 2.1/4.1 (API contract settles after the blueprint split and SQLAlchemy port)
- **blocks:** 10.4 (don't submit to review with client-side state as the source of truth for money-adjacent data)
- **task:** One Axios instance (exists from M.2), service modules per domain (auth, wallet, bets, lines), a few custom hooks. Keep Context API — no Redux/feature-sliced architecture unless you exceed ~20 components or hit real cross-page state pain. **Kill the AsyncStorage parity shim from M.3:** make the server authoritative for ongoing-bet state — the app fetches accepted/ongoing bets from the API, local cache is just a cache. Token storage is already settled (SecureStore, decided in M.2) — no decision left there.
- **done when:** API calls go through service modules, not ad-hoc Axios calls scattered in screens; deleting the app's local storage and reinstalling loses no bet state.
- **flag: --opus** (requires tracking API contract changes from Stage 2/4 (blueprint split, SQLAlchemy port); building against a backend that has moved since M.3)
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (state-authority migration for money-adjacent data; requires human verification against real bets)

---

## STAGE 10 — App Store launch (last, gated on security + money correctness)

### 10.1 — Production backend hardening for a public mobile launch
- **status:** not started
- **track:** full
- **owns_files:** `Procfile`, `backend/requirements.txt`, `backend/auth.py` (token lifetime/refresh), Render config
- **blocked_by:** 2.2 (limiter must exist), 0.7 (debug off)
- **blocks:** 10.4
- **task:** (a) Replace the Flask dev server in the Procfile with gunicorn (`gunicorn -w 2 'backend.app:app'` or the `create_app()` factory form post-2.1) — `flask run` will fall over under real App Store traffic. (b) Confirm the Render URL serves HTTPS-only; iOS App Transport Security requires TLS, no exceptions in `Info.plist`. (c) Give JWTs a sane expiry + a refresh path (or re-login flow the app handles gracefully) — an app in someone's pocket for months is not a browser tab.
- **done when:** production runs gunicorn; plain-HTTP requests are refused/redirected; an expired token produces a clean re-auth flow in the app, not a silent dead session.

### 10.2 — Account deletion (App Review Guideline 5.1.1(v) — mandatory)
- **status:** not started — **semantics decided 2026-07-05 (tombstone; rules below); no open design questions.**
- **track:** full
- **owns_files:** backend: new authenticated `DELETE /me` (or equivalent) route + tombstone/refund logic on `players` and the user's in-flight `bets`/`cpu_acceptances`; mobile: a delete-account action in Profile/settings
- **blocked_by:** 5.1 (deletion refunds in-flight bets via the wallet service, not raw deletes), 1.1 (must be behind the decorator)
- **blocks:** 10.4 — **Apple rejects account-based apps without in-app account deletion. Non-negotiable.**
- **task:** Implement the **decided semantics**: **tombstone the `players` row** — scrub PII (`email` → null, `username` → `deleted_<id>`, `profile_pic_url` → null), set a `deleted_at` flag, and make login/`/me` reject it. Keep the row so FKs stay coherent (`bets.posterId`/`accepterId` are `text` with **no DB FK** — Gotcha 2 — so cascades won't save you; the tombstoned row is what keeps counterparty history readable). In-flight bets: `posted` → refund + remove; `accepted` PvP → **immediate void + refund both** (don't make the counterparty wait the 7-day timeout); CPU acceptances → final, no refund (5.2 Q4). Caps balance just vanishes (non-cashable). **Do NOT touch the stats world** — `bettable_players` / `bettable_player_stats` / `player_stat_aggregates` are shared game data keyed independently of `players` (the two-worlds model in `DATABASE.md`); anonymizing a name there would corrupt other users' bets and CPU line math.
- **done when:** a user can delete their account entirely in-app; login stops working; PII is fully scrubbed; counterparties' bet history remains coherent; the stats tables are untouched; in-flight wagers are refunded per the rules above.
- **autonomous:** design gate resolved — the STOP downgrades to **verify PII fully scrubbed + counterparty coherence + stats-world untouched** (test), not a human semantics sign-off.

### 10.3 — App identity, privacy, and content-rating compliance
- **status:** not started
- **track:** trivial
- **owns_files:** `mobile/app.json`/`app.config.js` (bundle ID, icon, splash, version), privacy policy doc + hosted URL, App Store Connect metadata (worked outside the repo)
- **blocked_by:** M.3 (assets belong to the final mobile app), 6.2 (no unvalidated quantitative claims in store copy either)
- **blocks:** 10.4
- **task:** (a) Bundle ID, app icon (1024px master), splash screen, display name — the existing `logo512.png` is a starting point, not a shippable icon. (b) Privacy policy: required for any account-based app; must cover what's collected (username, bet history) and the 10.2 deletion path; host it anywhere stable and link it in App Store Connect. (c) App Privacy "nutrition label" answers matching reality. (d) Age rating: virtual-currency betting ⇒ answer "Simulated Gambling" honestly (expect 17+). **Copy rule for every word of metadata and in-app text: caps are never purchasable and never cashed out — real-money gambling framing triggers Guideline 5.3 licensing requirements this app cannot meet. Keep it a game.**
- **done when:** app builds with final identity assets; privacy policy is live at a stable URL; a dry-run of the App Store Connect questionnaire has answers for every field.

### 10.4 — EAS Build → TestFlight → App Store submission
- **status:** not started
- **track:** full
- **owns_files:** `mobile/eas.json`, Apple Developer account + App Store Connect (outside the repo)
- **blocked_by:** 10.1, 10.2, 10.3, 9.1, and Stages 0/1/2/5 complete with Stage 7 tests green — **shipping publicly multiplies every open security and double-payout bug; do not submit around them**
- **blocks:** nothing — this is the finish line
- **task:** (a) Apple Developer Program enrollment ($99/yr — human task). (b) `eas build --platform ios` with production `EXPO_PUBLIC_API_URL` pointing at Render. (c) TestFlight beta with real users through full bet lifecycles (create → accept → submit → settle → refund) against production. (d) Fix what the beta finds, then submit for review. Expect at least one rejection round on a betting-adjacent app; respond with the no-real-money facts from 10.3.
- **done when:** the app is live on the App Store.
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (publishing to the App Store is an outward-facing, human-owned action)

---

## UNSCHEDULED — needs definition before it can be tagged

### X.1 — "General professional grade visual improvements"
- **status:** **SUPERSEDED by X.5 (2026-07-05).** The vague "visual improvements" ask has been scoped into the X.5 minimalist redesign; do not action X.1 separately.

### X.2 — Decide the fate of the Socket.IO messaging server (found in audit)
- **status:** RESOLVED — decision (a), cut it. The web-app retirement item (now unscheduled — see **X.6**) deletes `server.js`, and the Messages stub is not ported to mobile (M.3). If messaging ever becomes a committed feature, it enters the plan as a new scoped item (auth, deploy target, push notifications on mobile — see X.4).

### X.3 — CPU/House bet auto-generation + player-chosen wager (decided 2026-07-05)
- **status:** scoped — ready to implement (no open questions). Not launch-blocking (an empty House screen passes review), but needed before real users rely on it.
- **owns_files:** the `/cpu/create_*` handlers + a new `POST /cpu/generate_daily` endpoint (`app.py` today; the lines blueprint after 2.1), `caps_bet_generation.py`/`pong_bet_generation.py`/`beerball_bet_generation.py`, the CPU accept + `submit_stats` CPU branch, a new **wager column on `cpu_acceptances`**, and a **GitHub Actions scheduled workflow** (`.github/workflows/`)
- **blocked_by:** none hard, but the wager change rides on 5.1 (wallet service) and 5.3 (once-only CPU payout); mechanism/auth account for 2.1 (blueprint split) and 4.1 (SQLAlchemy port) so it isn't rewritten twice
- **blocks:** nothing — does NOT block App Store submission (10.4)
- **task (two parts):**
  - **(A) Auto-generation — mechanism decided: free external scheduler.** Render Cron Jobs are **not free** (~$1/mo min, no free tier), so instead a **GitHub Actions scheduled workflow (free)** runs ~once/day and calls a new **`POST /cpu/generate_daily`** on the existing Render web service, guarded by a **`CRON_SECRET`** header. It generates **~3 bets/day**, de-duped/bounded (only create up to a target, skip duplicate matchups) with stale-CPU pruning. Generation stays server-side under the `player_id == 0` identity; do NOT expose an unauthenticated generation route.
  - **(B) Player-chosen wager on House bets.** Move the wager **off `bets.amount` and onto `cpu_acceptances`** (two users can accept the same House line at different amounts). Accept flow takes a wager, debited via the 5.1 wallet service; **min 10 caps, max = the player's current balance** (house has effectively infinite bankroll — see `DATABASE.md` caps economy); payout is `2 × acceptance_wager`, exactly once (5.3).
- **done when:** House bets appear/refresh automatically with no human in the loop (workflow runs in prod, `/cpu/generate_daily` authenticated, generation idempotent/bounded); a user can pick their House wager (10..balance) and win/lose exactly that amount once. See `DATABASE.md` → cpu_acceptances.

### X.4 — Messaging feature (only if committed as a product decision)
- **status:** **confirmed cut through launch (2026-07-05)** — do NOT schedule until messaging is a committed product decision. Supersedes the "new scoped item" note in X.2.
- **owns_files:** (if built) a new backend messaging Blueprint + its tables/models, mobile message screen(s) under `mobile/src/screens/`, push-notification wiring (Expo push / APNs), a UGC moderation/report/block surface, and an API service module under `mobile/src/services/`
- **blocked_by:** a committed product decision to build messaging; practically also 1.1 (auth decorator), 2.1 (blueprint pattern), 4.1 (models) so it's built on the final backend shape
- **blocks:** nothing
- **task:** X.2 resolved messaging as "cut it" — `server.js` and the old Socket.IO/Messages stub are deleted as part of the web-app retirement (X.6) and must NOT be revived. If ever revisited, it is a **from-scratch mini-project**, not a bolt-on: authenticated (behind `@token_required`, no unauthenticated socket server); a defined backend surface (new Flask Blueprint + its own tables); mobile push notifications for backgrounded delivery; **and the App Store UGC stack Apple requires under Guideline 1.2 — content filtering, an in-app report mechanism, block-user, and a published contact.** Scope transport (polling vs. WebSocket vs. push-only), storage/retention, and abuse/rate-limiting before any implementation.
- **done when:** N/A until scoped — cannot enter execution without a product decision and a defined backend + push + moderation design.

### X.5 — RN minimalist redesign (Kalshi-style, in-house design system) — direction decided 2026-07-05
- **status:** scoped — direction & anchor decided; per-screen checklist to be enumerated before rollout. (Best QA'd after 0.8 so screens actually load data.)
- **owns_files:** `mobile/src/screens/` (PvP, CPU/House, Ongoing, Leaderboard, Profile) + a new `mobile/src/theme/` (design tokens) and `mobile/src/components/` (shared primitives). Frontend only — not backend, not `mobile/src/utils/`.
- **blocked_by:** M.3 (screens exist); practically 0.8 (screens must load data to QA the redesign)
- **blocks:** nothing (but should land before 10.3/10.4 so the store screenshots show the final look)
- **task:** This is a **genuine redesign**, not a polish pass (supersedes the old "polish, not re-layout" framing and X.1). Direction: **minimalist / modern, Kalshi-style — less clutter, more whitespace, sleek and professional.**
  - **Approach: in-house design system (NOT a UI library).** A library (Paper = Material, fights the aesthetic; Tamagui/gluestack = build overkill for 5 screens) is the wrong tool for a custom look. Build **design tokens** (`mobile/src/theme/` — existing palette promoted to tokens + a 4/8/16 spacing scale, type scale, radius) and **core primitives** (`Screen`, `Card`, `ListRow`, `Button`, plus `LoadingView` / `EmptyState` / `ErrorState`), then rebuild the 5 screens on them.
  - **Palette: pastel purple is the sole accent on white.** Accent `#8B7CF6`, accent-tint `#EEEAFB`, accent-pressed `#6F5FE0`; ground `#FFFFFF`/`#FAFAFA`, border `#ECECEC`, text `#1A1A1A`/muted `#6B6B6B`/faint `#9A9A9A`. **No green accents.** Over/Under distinguished by fill + ↑/↓ arrow, not color. **Red (`#C0392B`) reserved strictly for errors/destructive actions**, never as an accent.
  - **Anchor screen approved: PvP, "minimal dense rows" (Variant B)** — drop the `back1.png` photo background for a flat white ground; bets are list rows split by hairline dividers with a small purple (fill/outline) line badge and a compact purple `Accept` pill. This locks the visual language for the other four screens.
  - Cover the new surfaces in the redesign: X.3's House **wager input** and any manual-cancel UX, so screens aren't restyled twice.
  - Include the three interaction states everywhere: **loading** (spinner/skeleton), **empty** (no open PvP/House bets, no ongoing bets, empty leaderboard), **error** (failed fetch/submit → visible message + retry, not a silent blank).
- **done when:** token layer + shared primitives exist; all 5 screens rebuilt in the minimalist purple language with loading/empty/error states; the PvP anchor matches the approved Variant B; no green accents remain. Enumerate the per-screen gap checklist (read each screen) before handing to `dt-ui` / an agent.

### X.6 — Retire the web app + repo restructure (moved out of Stage M)
- **status:** unscheduled — pulled out of the Stage M execution line on 2026-07-05. No longer gates the backend stages; run it whenever mobile parity is confirmed and there is a committed decision to stop maintaining the CRA web app. Still requires human confirmation before executing.
- **owns_files:** root `package.json`, `src/`, `public/`, `server.js` (delete), `README.md`, `CLAUDE.md`, `.gitignore`
- **blocked_by:** M.3 (parity first)
- **blocks:** nothing — was on the Stage M line, but no scheduled item depends on it anymore (10.3 now keys off M.3 for final app assets)
- **task:** (a) Delete the CRA app (`src/`, `public/`, `react-scripts` and the `proxy` field) once M.3 parity is confirmed — the product runs on mobile, not on computer. (b) Delete `server.js` — this executes decision (a) of X.2; if messaging ever becomes a real feature it gets rebuilt with auth as a scoped item (see X.4). (c) Update README/CLAUDE.md commands (Expo start replaces `npm start`; Vercel frontend deploy notes removed or marked legacy). (d) Cancel/park the Vercel deployment.
- **done when:** fresh clone + `cd mobile && npx expo start` + backend run instructions are the documented (and working) dev loop; no CRA or Socket.IO code remains on `main`.
- ⚠️ **AUTONOMOUS RUN — STOP HERE** (deleting the working web app is irreversible in effect even if git-recoverable; requires human confirmation that mobile parity is real)

### X.7 — Implement `win_rate` / `defensive_value` / `mean_last_5` aggregates (found in DB audit 2026-07-05)
- **status:** unscheduled — not launch-blocking. Optional line-gen sophistication; schedule when you want CPU lines to actually use defensive value / win rate.
- **owns_files:** `player_stat_aggregates` (add columns via a 4.1-style migration), `stats_utils.py` (populate them), the sport line-generation modules (consume them via the `predict_expected_stat` seam from 3.1)
- **blocked_by:** 3.1 (do NOT fold into the behavior-preserving collapse — this intentionally *changes* line output, which would break 3.1's golden-master parity), and 4.1 (add columns through the migration flow)
- **blocks:** nothing
- **task:** `player_stat_aggregates` is missing `win_rate`, `defensive_value`, and `mean_last_5` — columns the generation code (esp. beerball) reads from a "profile" and that `stats_utils` tries to update. Today those reads fall back to hardcoded `0.5` defaults, so the DV/win-rate sophistication is **inert** (see `DATABASE.md` Gotcha 3). Add the columns, populate them in `stats_utils` (recency window for `mean_last_5`, W/L for `win_rate`, the existing DV computation for `defensive_value`), and wire them into the per-sport `predict_expected_stat`. Re-baseline the golden-master (line output will legitimately shift).
- **done when:** the three columns exist and are populated; line generation consumes real DV/win_rate/mean_last_5 instead of defaults; a fresh golden-master is captured for the new (intended) behavior.

---

## Order of execution (top to bottom, no skipping)
```
M.1 → M.2 → M.3 → 0.1 → 0.2 → 0.3 → 0.4 → 0.5 → 0.6(verify, landed in M.2) → 0.7 → 0.8 → 1.1 → 2.1 → 2.2 → 2.3 → 3.1 → 4.1 → 5.1 → 5.2 → 5.3 → 6.1 → 6.2 → 6.3 → 7.1 → 7.2 → 7.3 → 7.4 → 8.1 → 9.1 → 10.1 → 10.2 → 10.3 → 10.4
```
(X.3 / X.4 / X.5 / X.6 / X.7 are intentionally off this line — unscheduled items run on demand, not gating steps. X.6 web-app retirement runs on human confirmation of mobile parity; X.7 aggregate columns and X.3/X.5 are slotted when you choose to pick them up.)

This is now a strict line, not a graph — work it top to bottom. The `blocked_by`/`blocks` fields on each item are there so you understand *why* the order is what it is (and so you don't get tempted to jump ahead on a slow stage), not so a system can route around them. Stage M runs first by explicit product decision (mobile is the product); Stage 10 runs last because App Store submission is gated on every security and money-correctness stage in between.

## Items NOT in this file (deferred, per stop-before lines — do not schedule)
No Redis until >1 backend instance · no Celery until settlement/line-gen is too slow for a request cycle · no Redux until ~20+ frontend components or real cross-page state pain · no full Repository/Unit-of-Work class unless swapping data stores.