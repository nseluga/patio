# Patio — Refactor Progress

> Tracks what has actually landed against [PLAN.md](./PLAN.md). Update this file (not just the
> per-item `status` fields in PLAN.md) whenever a stage item is completed, so a fresh session can
> tell what's done without re-auditing the whole codebase.

**Last verified against code:** 2026-07-05

## Where we're at (one paragraph)

**Code:** M.1–M.3 are complete on the `conversion` branch (Expo app with all five screens ported); **no
backend/refactor code has landed yet.** ⚠️ The app currently **500s on core reads** (`/pvp_bets`, `/cpu_bets`,
`/ongoing_bets`, `/me`) — root cause now identified as camelCase column case-sensitivity (new item **0.8**).
**Planning:** a 2026-07-05 grilling session **resolved every human-input gate that was a *decision*** (vs. an
irreversible-action verification), rewrote the affected PLAN.md items with concrete specs, moved the web-app
deletion out of Stage M into unscheduled **X.6**, added **0.8** and **X.7**, and produced **[`DATABASE.md`](./DATABASE.md)**
— the new trusted schema reference (the old CLAUDE.md schema bullet and `models.py` were both stale).

## Status by stage

| Stage | Item | Status |
|---|---|---|
| M | M.1 — Scaffold Expo app + navigation shell | ✅ done (commit 35d6a17) |
| M | M.2 — Fix `/me` + port auth/API layer (SecureStore) | ✅ done (commit 2752114; absorbs 0.6) |
| M | M.3 — Port five main screens to RN primitives | ✅ done (Leaderboard/Profile/PvP/CPU/Ongoing) |
| 0 | 0.1 — `/submit_stats/<bet_id>` auth check | ✅ done full — JWT decode replaces body playerId; 403 for non-participants; try/finally connection safety (commit 75af568) |
| 0 | 0.2 — Remove hardcoded JWT secret fallback | ✅ done light — RuntimeError at import if SECRET_KEY unset (commit b891c5b) |
| 0 | 0.3 — Delete dead `bets` Blueprint in `auth.py` | ✅ done light — 46-line dead Blueprint removed; app boots clean (commit 6591677) |
| 0 | 0.4 — Cleanup batch (gitignore/stray files/port/logging) | ✅ done full — untrack .pyc, delete .Rhistory, fix :5001 port, print→logging; N+1 batch fix in bet-gen files (commit dc254f5) |
| 0 | 0.5 — Route auth inventory | ✅ done full — cleanup_bets/bets/pvp_bets gated; create_bet server-side identity + atomic caps debit; route-auth-table produced (commit 7f30fb6) |
| 0 | 0.6 — Fix/remove broken `/me` | ✅ done in M.2 — verified: Bearer stripped, valid columns only |
| 0 | 0.7 — Stop leaking secrets in logs + disable debug | ✅ done full — `.flaskenv` → production/debug-off; atomic caps fix in accept_bet/accept_cpu_bet; 90/90 tests (commit 1dc003f) |
| 0 | **0.8 — Fix camelCase column access breaking core reads** | ✅ done full — explicit quoted aliases in all 4 handlers + submit_stats/accept_bet/cleanup_bets/get_all_bets; 128/128 tests (commit e280b42) |
| 1 | 1.1 — `@token_required` decorator | ✅ done full — backend/utils/auth.py decorator; all 15 routes converted; get_player_id() removed; 209/209 tests (commit 1445792) |
| 2 | 2.1 — App-factory + blueprints | ✅ done full — create_app() factory; 5 blueprint files in backend/routes/; 245/245 tests (commit 0f06651) |
| 2 | 2.2 — Error handlers + CORS scoping + Flask-Limiter | ✅ done full — JSON error handlers, ProxyFix, CORS dynamic origins, rate limits on auth+wallet routes; 272/272 tests (commit c73b38d) |
| 2 | 2.3 — Input validation layer | ✅ done full — backend/validation.py (require_fields, coerce_int); applied to 4 route files; all crash paths → 400; 322/322 tests (commit 6e127cb) |
| 3 | 3.1 — Sport module collapse | ✅ done full — backend/bet_generation.py (SportConfig + CAPS/PONG/BEERBALL configs); golden-master 12/12; routes dispatch through seam; 334/334 tests (commit cba0b49) |
| 4 | 4.1 — SQLAlchemy migration | not started — **now also owns** camelCase→snake_case rename, explicit FKs, `oppOutcome` normalize (still STOP: live DB) |
| 5 | 5.1 — Wallet/settlement service | not started (STOP retained: concurrency verification) |
| 5 | 5.2 — Refund/push semantics | not started — **semantics decided** (half-point PvP lines; refund expired/void+refund abandoned; CPU house-keeps; STOP → test) |
| 5 | 5.3 — Settlement idempotency | not started (STOP retained: double-pay verification) |
| 6 | 6.1–6.3 — Docs/portfolio | not started |
| 7 | 7.1–7.4 — Test suite | not started |
| 8 | 8.1 — CI gate | not started |
| 9 | 9.1 — Mobile service modules + server-authoritative state | not started (STOP retained) |
| 10 | 10.1 — Production backend hardening | not started |
| 10 | 10.2 — Account deletion | not started — **semantics decided** (tombstone players; refund in-flight; stats-world untouched; STOP → test) |
| 10 | 10.3 — App identity/privacy/rating | not started |
| 10 | 10.4 — EAS Build → TestFlight → submission | not started (STOP retained: outward-facing) |

### Unscheduled (off the execution line)

| Item | Status |
|---|---|
| X.1 — visual improvements | **SUPERSEDED by X.5** |
| X.2 — Socket.IO messaging fate | RESOLVED (cut) |
| X.3 — CPU auto-generation + player-chosen wager | **scoped, ready** (GitHub Actions cron → authed `/cpu/generate_daily`, ~3/day; wager on `cpu_acceptances`, min10/max-balance) |
| X.4 — Messaging feature | **confirmed cut through launch** (needs product decision + Guideline 1.2 stack to ever build) |
| X.5 — RN minimalist redesign | **scoped** (in-house design system, pastel-purple accent no green, Variant B PvP anchor approved; per-screen checklist pending; QA after 0.8) |
| X.6 — Retire web app + repo restructure | unscheduled (was M.4; STOP: run on human confirmation of mobile parity) |
| X.7 — Implement `win_rate`/`defensive_value`/`mean_last_5` aggregates | **NEW (2026-07-05)** — unscheduled; after 3.1/4.1; re-baselines golden-master |

## Decisions locked on 2026-07-05 (grilling session)

- **5.2 refund/push:** PvP lines forced to half-points (no pushes); refund poster on 7-day `posted` expiry;
  `accepted`-but-unsettled (ghost or dispute) auto-voids + refunds both after 7 days; abandoned CPU acceptances =
  house keeps (no refund).
- **3.1 collapse:** shared pipeline + per-sport line math behind a `predict_expected_stat` seam; golden-master
  byte-parity guard replaces the human design gate; ML explicitly deferred (heuristic wins at current data volume).
- **10.2 deletion:** tombstone the `players` row (scrub PII, kill login), refund in-flight bets, **leave the
  bettable_players stats graph untouched** (two-worlds model).
- **X.3:** free GitHub-Actions cron → authed `/cpu/generate_daily` (~3/day); player-chosen House wager stored on
  `cpu_acceptances` (min 10 / max balance), payout `2×` via the wallet service, once-only.
- **X.4:** messaging stays cut through launch.
- **X.5:** genuine redesign — minimalist/Kalshi, in-house token+primitive design system, pastel-purple sole accent
  (no green), PvP "dense rows" anchor approved.
- **DATABASE.md created** as the trusted schema reference; CLAUDE.md's schema block replaced with a pointer.
- **STOP markers still retained** (irreversible-action verification, not decisions): 4.1, 5.1, 5.3, 9.1, 10.4, X.6.

## How to update this file

After finishing a plan item: flip its row here to `done` (with a one-line note on what changed,
e.g. commit hash or brief description), and update the matching `status:` field in PLAN.md to
keep both in sync.
