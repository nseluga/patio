# Patio — Refactor Progress

> Tracks what has actually landed against [PLAN.md](./PLAN.md). Update this file (not just the
> per-item `status` fields in PLAN.md) whenever a stage item is completed, so a fresh session can
> tell what's done without re-auditing the whole codebase.

**Last verified against code:** 2026-07-01

## Status by stage

| Stage | Item | Status |
|---|---|---|
| M | M.1 — Scaffold Expo app + navigation shell | not started |
| M | M.2 — Fix `/me` + port auth/API layer (SecureStore) | not started (absorbs 0.6) |
| M | M.3 — Port five main screens to RN primitives | not started |
| M | M.4 — Retire web app + repo restructure | not started |
| 0 | 0.1 — `/submit_stats/<bet_id>` auth check | not started (still reads `playerId` from request body) |
| 0 | 0.2 — Remove hardcoded JWT secret fallback | not started (`config.py` still has `"your-secret-key"` default) |
| 0 | 0.3 — Delete dead `bets` Blueprint in `auth.py` | not started (still present, unregistered) |
| 0 | 0.4 — Cleanup batch (gitignore/stray files/port/logging) | not started (`backend/py/`, `backend/__pycache__/` still tracked; `.Rhistory` still present; `venv/` not in `.gitignore`) |
| 0 | 0.5 — Route auth inventory (`cleanup_bets`, `get_all_bets`, `get_pvp_bets`, `create_bet`) | not started |
| 0 | 0.6 — Fix/remove broken `/me` route | pulled forward into M.2 (verify only when reached) |
| 0 | 0.7 — Stop leaking secrets in logs + disable debug mode | not started (`.flaskenv` still sets `FLASK_ENV=development`) |
| 1 | 1.1 — `@token_required` decorator | not started |
| 2 | 2.1–2.3 | not started |
| 3 | 3.1 — Sport module collapse | not started |
| 4 | 4.1 — SQLAlchemy migration | not started |
| 5 | 5.1–5.3 — Wallet/settlement service | not started |
| 6 | 6.1–6.3 — Docs/portfolio | not started |
| 7 | 7.1–7.4 — Test suite | not started |
| 8 | 8.1 — CI gate | not started |
| 9 | 9.1 — Mobile service modules + server-authoritative bet state | not started |
| 10 | 10.1 — Production backend hardening (gunicorn/ATS/token expiry) | not started |
| 10 | 10.2 — Account deletion (App Review 5.1.1(v)) | not started |
| 10 | 10.3 — App identity, privacy, content-rating compliance | not started |
| 10 | 10.4 — EAS Build → TestFlight → App Store submission | not started |

## Summary

No stage of PLAN.md has been started yet — the repo is still at its pre-refactor baseline.
The plan was restructured on 2026-07-02 for the mobile-first pivot: Stage M (React Native/Expo
conversion) now runs first, and Stage 10 (App Store launch) runs last, gated on the security and
money-correctness stages. X.2 is resolved (cut `server.js`, executed in M.4).
Next up per the execution order: **Stage M**, starting with M.1 (scaffold the Expo app).

## How to update this file

After finishing a plan item: flip its row here to `done` (with a one-line note on what changed,
e.g. commit hash or brief description), and update the matching `status:` field in PLAN.md to
keep both in sync.
