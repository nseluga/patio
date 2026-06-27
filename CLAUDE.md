# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Efficiency Rules

- **Batch independent tool calls.** Before issuing any tool call, check if other calls could start at the same time without depending on this result. If yes, issue them together in one turn. Sequential is only correct when B depends on A's output.
- **Use dedicated file tools.** Never use `Bash(cat file)`, `Bash(head file)`, or `Bash(tail file)` — use `Read` with `limit`/`offset`. Never use `Bash(sed -i)` to edit files — use `Edit`.
- **Batch git commands.** Always run `git status`, `git diff`, and `git log` together in a single turn, never one at a time.

## Commands

**Backend** (run from project root):
```bash
pip install -r backend/requirements.txt
flask --app backend/app run --port 5001
```

**Frontend:**
```bash
npm install
npm start
```

The frontend dev server proxies API requests to `http://localhost:5001` (configured in `package.json`). Both must run simultaneously for local development.

**Tests:**
```bash
npm test  # React unit tests (minimal coverage — only CRA boilerplate)
```

## Architecture

Full-stack social betting app for backyard games (Caps, Pong, Beerball). Players use virtual currency ("caps") to place Over/Under bets on game stats.

### Backend (`backend/`)

Flask app with no ORM — all queries use raw `psycopg2` with `RealDictCursor`.

- **`app.py`** — All bet endpoints. Auth is checked via `get_player_id()` which decodes the JWT from the `Authorization: Bearer <token>` header.
- **`auth.py`** — Blueprint with `/register`, `/login`, `/me` routes. New players start with 500 caps; caps refresh by +100 if >7 days since last login.
- **`db.py`** — Single `get_db()` function returning a psycopg2 connection from `DATABASE_URL`.
- **`config.py`** — Reads `DATABASE_URL` and `SECRET_KEY` from env vars.
- **`models.py`** — Table creation scripts only; not used at runtime (tables live in Supabase).
- **`stats_utils.py`** — Stat recording and rolling aggregate updates (`insert_stat`, `update_player_aggregate`, `get_or_create_bettable_player`).
- **`caps_bet_generation.py` / `pong_bet_generation.py` / `beerball_bet_generation.py`** — CPU (House) bet line generation using scipy/numpy. Lines are biased ~4% in the house's favor.

**CPU bet creation endpoints** (`/cpu/create_*`) require player_id == 0 (the CPU account). They pull from `player_stat_aggregates` to build statistically-informed lines.

### Database Schema (Supabase/Postgres)

Key tables:
- **`players`** — App users. `caps_balance` is the virtual currency. `id = 0` is the reserved CPU/House account.
- **`bets`** — Unified table for all bet types. `status`: `'posted'` → `'accepted'` → `'submitted'` (PvP) or `'CPU'` (house bets, never changes).
- **`cpu_acceptances`** — Tracks which users accepted which CPU bets (`match_confirmed`, `attempted` flags).
- **`bettable_players`** — Players named in bets (game participants, not necessarily app users).
- **`bettable_player_stats`** — Raw per-game stat rows logged when bets resolve.
- **`player_stat_aggregates`** — Rolling `mean`, `std`, `mean_last_5`, `n_games`, `win_rate`, `defensive_value` per `(player_name, game_played, game_type, stat_name, team_size)`.

**Bet fields** vary by `gameType`:
- `"Score"` — `yourTeamA/B` (JSONB arrays of player names), `yourScoreA/B`, mirror `opp*` fields
- `"Shots Made"` — `yourPlayer`, `yourShots`, `oppPlayer`, `oppShots`
- `"Other"` — `yourOutcome`, `oppOutcome`

Stats are confirmed when both poster and accepter submit matching values. On match, caps are awarded (winner gets 2× the wager amount).

### Frontend (`src/`)

React 19 + React Router. Auth state lives in `UserContext` and is persisted to `localStorage` (`token`, `playerId`, `username`). Ongoing bets are also stored in `localStorage`.

**Pages** (all behind auth guard in `App.js`):
- `/pvp` — Browse and accept open PvP bets from other players
- `/house` (`CPU.js`) — Browse and accept CPU/House bets
- `/ongoing` — View accepted bets, submit game stats, see match status
- `/leaderboard` — Top 5 players by caps balance
- `/profile` — Personal stats and bet history
- `/messages` — Messaging page

**`src/api.js`** — Axios instance with base URL from `REACT_APP_API_URL` env var (falls back to `http://localhost:5001`). Attaches JWT automatically via request interceptor.

**`src/utils/betCreation.js`** — `createStandardBet()` factory that normalizes bet objects by `gameType`.

**`src/utils/acceptHandling.js`** — Helpers for accepting bets and syncing to `localStorage`.

## Environment Variables

Backend: `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL`
Frontend: `REACT_APP_API_URL`

See `.env.example` for template. Backend vars are set in Render dashboard; frontend vars in Vercel dashboard.

## Deployment

- **Backend → Render**: start command `flask --app backend/app run --host=0.0.0.0 --port=$PORT` (see `Procfile`)
- **Frontend → Vercel**: standard Create React App build
