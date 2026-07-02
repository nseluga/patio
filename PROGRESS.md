# Patio — Refactor Progress

> Tracks what has actually landed against [PLAN.md](./PLAN.md). Update this file (not just the
> per-item `status` fields in PLAN.md) whenever a stage item is completed, so a fresh session can
> tell what's done without re-auditing the whole codebase.

**Last verified against code:** 2026-07-01

## Status by stage

| Stage | Item | Status |
|---|---|---|
| 0 | 0.1 — `/submit_stats/<bet_id>` auth check | not started (still reads `playerId` from request body) |
| 0 | 0.2 — Remove hardcoded JWT secret fallback | not started (`config.py` still has `"your-secret-key"` default) |
| 0 | 0.3 — Delete dead `bets` Blueprint in `auth.py` | not started (still present, unregistered) |
| 0 | 0.4 — Cleanup batch (gitignore/stray files/port/logging) | not started (`backend/py/`, `backend/__pycache__/` still tracked; `.Rhistory` still present; `venv/` not in `.gitignore`) |
| 0 | 0.5 — Route auth inventory (`cleanup_bets`, `get_all_bets`, `get_pvp_bets`, `create_bet`) | not started |
| 0 | 0.6 — Fix/remove broken `/me` route | not started |
| 0 | 0.7 — Stop leaking secrets in logs + disable debug mode | not started (`.flaskenv` still sets `FLASK_ENV=development`) |
| 1 | 1.1 — `@token_required` decorator | not started |
| 2 | 2.1–2.3 | not started |
| 3 | 3.1 — Sport module collapse | not started |
| 4 | 4.1 — SQLAlchemy migration | not started |
| 5 | 5.1–5.3 — Wallet/settlement service | not started |
| 6 | 6.1–6.3 — Docs/portfolio | not started |
| 7 | 7.1–7.4 — Test suite | not started |
| 8 | 8.1 — CI gate | not started |
| 9 | 9.1 — Frontend Axios/service layer | not started |

## Summary

No stage of PLAN.md has been started yet — the repo is still at its pre-refactor baseline.
Next up per the execution order: **Stage 0**, starting with 0.1 (auth on `/submit_stats`).

## How to update this file

After finishing a plan item: flip its row here to `done` (with a one-line note on what changed,
e.g. commit hash or brief description), and update the matching `status:` field in PLAN.md to
keep both in sync.
