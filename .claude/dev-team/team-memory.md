# Dev-team memory log

## 2026-07-09 — dev-team-auto — Item 3.1 — Sport module collapse
- **Outcome:** DONE — 2 review passes (1 fix pass), full track (flag:--opus), branch `auto/stage0-0.8`, commit cba0b49
- **What happened:** Opus Engineer captured golden master (12 fixed inputs × original modules → json), built bet_generation.py with SportConfig frozen dataclass + CAPS/PONG/BEERBALL configs, deleted 3 originals. Opus Review found Important: seam was dead (routes still called concrete functions by name). Bug Fixer wired routes through cfg.predict_shots/predict_score. Second review clean.
- **What worked:** Golden-master-first approach — capturing before refactoring gave a reliable regression check. Verbatim copy of per-sport callables into SportConfig fields preserved all constants without risk of drift.
- **What failed:** First Engineer pass created the seam but didn't wire routes through it. Opus review caught this correctly.
- **Remember next run:** 334 tests as of 3.1 done. bet_generation.py structure: SportConfig frozen dataclass with predict_shots/predict_score callables; CAPS/PONG/BEERBALL module-level instances; shared assemble_matchup, adjust, team_strength_multiplier, snap_to_half_point. Routes import CAPS/PONG/BEERBALL and call .predict_shots/.predict_score — no bare generate_biased_* calls. Golden master in backend/tests/golden_master_3_1.json (12 values, must rebaseline if line math changes).

## 2026-07-09 — dev-team-auto — Item 2.3 — Input validation layer
- **Outcome:** DONE — 3 QA+review passes (2 fix passes), full track, branch `auto/stage0-0.8`, commit 6e127cb
- **What happened:** Engineer built backend/validation.py (require_fields, coerce_int) and applied to auth.py, submit_routes.py, lines_routes.py, bets_routes.py. QA found PvP Score branch missing coerce_int for yourScoreA/B. Review then found PvP Shots and PvP Other branches also missing coerce_int (same gap, different game types). Also found lineNumber/lineType not validated in create_bet, require_fields passing empty strings, team_size=0 silent path.
- **What worked:** Fixing the QA failure (Score branch) exposed a pattern — review found same gap in 2 more branches.
- **What failed:** Engineer applied coerce_int to CPU branches but forgot PvP branches (3 of them). Review caught all.
- **Remember next run:** 322 tests as of 2.3 done. `require_fields` uses `in (None, "")` — integer 0 passes correctly. `VALID_LINE_TYPES = {"Over", "Under"}` constant in bets_routes.py. When fixing one branch of a multi-branch function, always check sibling branches for the same pattern.

## 2026-07-09 — dev-team-auto — Item 2.2 — Error handlers + CORS + Flask-Limiter
- **Outcome:** DONE — 3 review passes (2 fix passes), full track, branch `auto/stage0-0.8`, commit c73b38d
- **What happened:** Engineer added extensions.py (Limiter), error_handlers.py, ProxyFix, rate limit decorators. First review: 2 Important (ProxyFix missing, e.retry_after always None) + 2 Minor. Second review after fix: 1 new Critical (7 INSERT statements with unquoted camelCase across bets_routes.py and lines_routes.py — pre-existing). Third pass closed all.
- **What worked:** ProxyFix pattern (`app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)`) before limiter.init_app(). Static retry_after=60 for 429. Decorator order: @route → @limiter.limit → @token_required (limiter fires before auth to throttle unauthenticated brute-force).
- **What failed:** Review caught pre-existing INSERT camelCase issues in bets_routes.py and all 6 lines_routes.py CPU bet creation endpoints — these were never fixed before. e.retry_after is None in Flask-Limiter 4.x (use static value).
- **Remember next run:** 272 tests as of 2.2 done. INSERT INTO bets column names must be double-quoted — all 7 INSERTs now fixed. Flask limiter in memory:// storage, resets on dyno restart. CORS origins built dynamically from FRONTEND_URL env var (no fallback placeholder). Decorator order on rate-limited+authed routes matters: limiter before token_required.

## 2026-07-09 — dev-team-auto — Item 2.1 — App-factory + blueprints
- **Outcome:** DONE — 2 review passes (1 fix pass), full track, branch `auto/stage0-0.8`, commit 0f06651
- **What happened:** Engineer split ~1650-LOC flat app.py into create_app() factory + 5 blueprint files (bets, accept, submit, lines, main) in backend/routes/. Added _db.py shim for test-patch compatibility. Review found 2 Important (N+1 in get_ongoing_bets, connection leak in leaderboard) + 3 Minor. Bug Fixer applied; Minor fix introduced a ValueError when rows is empty (colnames.index called unconditionally). Orchestrator patched directly with `if rows:` guard.
- **What worked:** Lazy import shim pattern for get_db (mirrors utils/auth.py SECRET_KEY shim) — preserved all patch("backend.app.get_db") test patterns without modification. Pure verbatim move of route logic worked cleanly.
- **What failed:** Minor fix for hoisting colnames.index() broke empty-rows case — always guard index-into-colnames with `if rows:` when rows might be empty from mock.
- **Remember next run:** 245 tests as of 2.1 done. Backend structure: backend/app.py (factory), backend/routes/ (5 blueprints + __init__.py + _db.py shim), backend/utils/ (auth.py), backend/auth.py (auth blueprint). Import path: `from backend.routes._db import get_db` in blueprints. Any new blueprint must be registered in create_app().

## 2026-07-09 — dev-team-auto — Item 1.1 — @token_required decorator
- **Outcome:** DONE — 2 review passes (1 fix pass), full track, branch `auto/stage0-0.8`, commit 1445792
- **What happened:** Engineer built `backend/utils/auth.py` with the decorator, removed `get_player_id()` from app.py, converted all 15 routes, fixed `/me` inline decode. QA passed 195/195. Review found 1 Important (dead `import jwt`) + 3 Minor (InvalidKeyError catch missing, CPU routes returning 401 not 403). Bug Fixer applied all 4. Re-QA 209/209 pass. Re-review clean.
- **What worked:** Lazy SECRET_KEY import (`import backend.app` inside closure) preserved existing `patch("backend.app.SECRET_KEY")` pattern in 20+ tests — zero test updates needed for the main behavior tests.
- **What failed:** First review pass caught 1 Important + 3 Minor — all straightforward fixes.
- **Remember next run:** 209 tests as of 1.1 done. CPU-only routes use `@token_required` + `if g.player_id != 0: return 403` pattern. The SECRET_KEY lazy import in utils/auth.py is intentional for test-patch compatibility — don't refactor it until 4.1 restructures imports. `backend/utils/__init__.py` exists now.

## 2026-07-09 — dev-team-auto — Item 0.8 — Fix camelCase column access breaking core reads
- **Outcome:** DONE — 2 review passes (1 fix pass), full track, branch `auto/stage0-0.8`, commit e280b42
- **What happened:** Engineer replaced `SELECT *` with explicit aliased columns (e.g., `"posterId" AS posterid`) in all 4 read handlers. First review found 2 Critical (submit_stats unquoted update columns; get_all_bets unquoted WHERE) + 2 Important + 2 Minor. Bug Fixer applied all 6. Re-review clean except 1 Minor (get_all_bets still using SELECT *). Minor applied, 128/128 tests final.
- **What worked:** Alias-to-lowercase approach (`"posterId" AS posterid`) lets all downstream dict-key access stay unchanged — zero dict-access edits needed in the handlers. Clean separation.
- **What failed:** First Engineer pass missed submit_stats dynamic UPDATE (f-string with unquoted camelCase column names), accept_bet SELECT, and cleanup_bets DELETE — these were caught by review. Also missed get_all_bets on the second pass.
- **Remember next run:** camelCase columns affected spread wider than just the 4 read handlers — submit_stats UPDATE, accept_bet SELECT/UPDATE, cleanup_bets DELETE all had unquoted camelCase. Any new handler touching `bets` must use `"camelCaseName" AS lowercase_alias`. 128 tests as of 0.8 done.

## 2026-07-09 — dev-team-auto — Item 0.7 — Stop leaking secrets in logs + disable debug
- **Outcome:** DONE — 2 attempts (1 fix pass), full track, branch `conversion`, commits 1dc003f / 1ba2482
- **What happened:** Engineer had already built 0.7 in the prior session (commit 4a8f507, merged via auto/stage0). This session completed the convergence loop: QA passed (77→90 tests), Review found 2 Critical TOCTOU races in `accept_bet`/`accept_cpu_bet` (pre-existing, not introduced by 0.7), Bug Fixer applied atomic caps pattern from `create_bet`, re-QA passed 90/90.
- **What worked:** The atomic `UPDATE ... WHERE caps_balance >= %s` + rowcount==0 → 400 pattern from `create_bet` was a clean reference — copy-paste to the two `accept_*` handlers closed both races.
- **What failed:** Review caught pre-existing TOCTOU bugs the prior session missed; required a fix-loop pass.
- **Remember next run:** PROGRESS.md was NOT updated by the previous session for 0.7 — always verify PROGRESS.md matches engineer-report.md on startup. The `accept_bet` and `accept_cpu_bet` handlers now have the same atomic caps guard as `create_bet`. Backend tests live in `backend/tests/` and run with `cd backend && python -m pytest tests/ -v` (90 tests as of 0.7 done). No worktree exists at session start — first Engineer creates one.
