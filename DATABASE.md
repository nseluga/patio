# DATABASE.md — Patio schema reference (conceptual + gotchas)

> **Purpose:** the single trusted description of the live Supabase/Postgres schema and *what it means in the app*.
> The tables live in Supabase; `backend/models.py` is **NOT** the source of truth (it only defines `players` and
> `bets`, and has drifted — see [Drift & gotchas](#drift--gotchas)). This file was reconstructed from the live
> `information_schema` (PK/unique/FK + columns) plus how the code actually uses each table.
> When schema and code disagree, this file describes the **schema**, and calls out the disagreement.

---

## The one mental model that makes everything click: two worlds bridged by `bets`

The app has **two completely separate identity spaces** that share no keys with each other:

1. **Account world — `players`.** App users: login, caps balance, profile. `players.id` is an integer.
2. **Stats world — `bettable_players` → `bettable_player_stats` → `player_stat_aggregates`.**
   People *named in games* (the participants a bet is about). Keyed by `bettable_players.id` (integer) and by
   name string. **A `bettable_player` is NOT an app user** and need not correspond to one.

**These two worlds do not overlap and are not meant to.** A `player` (app user) can post a bet about a set of
`bettable_players` that **does not include themselves**. The stats/aggregates that drive CPU line generation are
computed **per `bettable_player`**, never per app user. There is no FK, no shared id, and no required name match
between `players` and `bettable_players`.

The **only** thing connecting the two worlds is the **`bets`** table, which carries *both*:
- a `posterId` / `accepterId` pointing at the **account world** (`players`), and
- game content (`matchup`, `yourTeamA/B`, `yourPlayer`, …) naming the **stats world** (`bettable_players`).

```
  ACCOUNT WORLD                    BRIDGE                         STATS WORLD
  ─────────────                    ──────                         ───────────
  players ──posterId/accepterId──▶ bets ──(names in game content)──▶ bettable_players
    │  (text, NOT a DB FK)          │  id (uuid)                        │ id (int), name (unique)
    │                               │                                   │
    │                               ├─▶ cpu_acceptances                 ├─▶ bettable_player_stats
    │   accepter_id (int, real FK) ─┘   (id = bet id, accepter_id)      │     subject_player ─(FK)─▶ bettable_players.id
    │                                                                   │
    └───────────────────────────────────────────────────────────────  └─▶ player_stat_aggregates
                                                                              player_id ─(FK)─▶ bettable_players.id
```

**Practical consequence (drives PLAN 10.2):** deleting an app user (`players` row) must **not** touch the stats
world. `bettable_players` / `bettable_player_stats` / `player_stat_aggregates` are shared game data referenced by
*other* users' bets and by line generation; anonymizing or deleting a name there would corrupt other users' history
and the CPU line math. Account deletion tombstones the `players` row only.

---

## Tables

### `players` — app users / accounts (Account world)
Login, virtual currency, profile, lifetime PvP counters. All columns lowercase (no casing gotcha here).

| column | type | notes |
|---|---|---|
| `id` | integer PK | **`id = 0` is the reserved CPU / House account.** Never a real person. |
| `username` | text, UNIQUE, NOT NULL | |
| `email` | text, UNIQUE, NOT NULL | PII. |
| `password_hash` | text, NOT NULL | pbkdf2:sha256 (werkzeug). |
| `profile_pic_url` | text | |
| `caps_balance` | integer, default 0 | Virtual currency. **Not purchasable, not cashable** (keep it that way — App Store framing, PLAN 10.3). New users start at **500** (set in `/register`, not a DB default). |
| `pvp_bets_played` | integer, default 0 | Lifetime counter. |
| `pvp_bets_won` | integer, default 0 | Lifetime counter, incremented on PvP settle. |
| `last_caps_refresh` | timestamptz | Drives the **weekly +100 caps** top-up: on login, if `now - last_caps_refresh > 7 days` (and `id != 0`), add 100 and stamp. There is **no `last_login` column** — this is the closest thing. |
| `created_at` | timestamptz, default now() | |

### `bets` — every bet, all types (the Bridge) ⚠️ camelCase columns
One unified table for PvP and CPU/House bets across all game/stat types. **Most columns are quoted camelCase — see
the [casing gotcha](#gotcha-1-camelcase-columns-in-bets--bettable_player_stats-are-case-sensitive).**

Identity / lifecycle:
| column | type | notes |
|---|---|---|
| `id` | uuid PK, default `gen_random_uuid()` | |
| `poster` | text, NOT NULL | Denormalized poster **username** (string copy). |
| `posterId` | text | Poster's `players.id` **stored as text**. **No FK** to `players`. |
| `accepterId` | text | Accepter's `players.id` as text, null until accepted. **No FK.** |
| `status` | text, default `'posted'` | State machine — see below. |
| `timePosted` | timestamptz, default now() | Also used as the "age" for cleanup/expiry. |
| `amount` | integer, NOT NULL | Caps wagered (lowercase column). |

Bet definition:
| column | type | notes |
|---|---|---|
| `gameType` | text | `'Score'` \| `'Shots Made'` \| `'Other'` — decides which stat columns are used. |
| `gamePlayed` | text | `'Caps'` \| `'Pong'` \| `'Beerball'` \| `'Campus Golf'` \| `'Other'`. |
| `matchup` | text, NOT NULL | Human-readable matchup string (lowercase column). |
| `lineType` | text | `'Over'` \| `'Under'` — the side the **poster** took. Accepter implicitly takes the opposite. |
| `lineNumber` | double precision | The Over/Under line. **CPU lines are always half-points (`base ± 0.5`)** so they can't push. PvP lines are poster-chosen (PLAN 5.2 Q1 decision: force PvP to half-points too, so no pushes exist anywhere). |
| `gameSize` | text | `'1v1'` \| `'2v2'` \| `'3v3'` (null for `'Other'`). |

Per-`gameType` stat fields (only the relevant set is populated; poster fills `your*`, accepter fills `opp*`):
| gameType | poster fields | accepter fields |
|---|---|---|
| `Score` | `yourTeamA`,`yourTeamB` (jsonb name arrays), `yourScoreA`,`yourScoreB` (int) | `oppTeamA`,`oppTeamB`, `oppScoreA`,`oppScoreB` |
| `Shots Made` | `yourPlayer` (text), `yourShots` (int) | `oppPlayer`, `oppShots` |
| `Other` | `yourOutcome` (**text**) | `oppOutcome` (**integer** — type mismatch, see gotchas) |

### `cpu_acceptances` — who accepted which House bet (junction)
Tracks a user accepting a **CPU/House** bet. **`id` IS the bet id** (uuid, FK → `bets.id`); composite PK `(id, accepter_id)` → one row per (bet, user).
| column | type | notes |
|---|---|---|
| `id` | uuid, FK → `bets.id` | The accepted CPU bet. Part of PK. |
| `accepter_id` | integer, FK → `players.id` | The accepting user. Part of PK. |
| `match_confirmed` | boolean, default false | Set true when the user's submitted stats match the recorded game → triggers payout. |
| `attempted` | boolean, default false | Set true when the user submitted but stats did **not** match (they can retry). |

> **No wager column and no timestamp today.** PLAN X.3 (player-chosen wager on House bets) adds the wager **here**
> (per-acceptance), because two users can accept the same House line at different amounts. Settlement's CPU branch
> must then read the wager from this row, not from `bets.amount`.

### `bettable_players` — game participants (Stats world root)
| column | type | notes |
|---|---|---|
| `id` | integer PK | |
| `name` | text, UNIQUE, NOT NULL | Looked up / created case-insensitively via `get_or_create_bettable_player`. This is the identity of a "person in a game," independent of any app account. |

### `bettable_player_stats` — raw per-game stat rows ⚠️ some camelCase columns
One row per stat logged when a bet resolves. Feeds the aggregates.
| column | type | notes |
|---|---|---|
| `id` | integer PK | |
| `bet_id` | uuid, FK → `bets.id` | Which bet produced this stat. |
| `subject_player` | integer, FK → `bettable_players.id` | **The participant the stat is about** (an id, not a name). |
| `gamePlayed` | text | ⚠️ camelCase. |
| `gameType` | text | ⚠️ camelCase. |
| `stat_name` | text | e.g. shots / score. |
| `stat_value` | double precision | |
| `team` | text | e.g. `'A'`/`'B'`. |
| `team_size` | text | `'1v1'`/`'2v2'`/`'3v3'`. |
| `winning_team` | text | |

### `player_stat_aggregates` — rolling per-participant aggregates (drives CPU lines)
Unique on `(player_id, game, game_type, stat_name, team_size)`. **Keyed to `bettable_players`, not `players`.**
| column | type | notes |
|---|---|---|
| `id` | integer PK | |
| `player_id` | integer, FK → `bettable_players.id` | The participant. Part of the unique key. |
| `player_name` | text | **Denormalized copy** of `bettable_players.name`. Source of truth is `player_id`; code often queries by `player_name`, which is why both exist. |
| `game` | text | ⚠️ Code frequently passes this as `game_played` — the **column is `game`**. |
| `game_type` | text | |
| `stat_name` | text | |
| `team_size` | text | |
| `mean` | double precision | |
| `std_dev` | double precision | ⚠️ Code/docs sometimes call this `std`. |
| `sample_size` | integer, default 0 | ⚠️ Code/docs sometimes call this `n_games`. |

> **Missing-but-referenced columns:** `win_rate`, `defensive_value`, `mean_last_5` **do not exist** in this table,
> yet the CPU line-generation code (esp. beerball) reads `win_rate` / `defensive_value` from a player "profile" and
> `stats_utils` tries to *update* `defensive_value`. Today those reads fall back to hardcoded defaults
> (`profile.get("win_rate", 0.5)`), so the "defensive value / win rate" sophistication in line-gen is **effectively
> inert**. See [Drift & gotchas](#drift--gotchas) and PLAN X.7.

---

## Bet lifecycle (the `status` state machine)

```
PvP:   posted ──accept──▶ accepted ──both submit MATCHING stats──▶ submitted   (terminal, paid out)
CPU:   CPU (never changes) ; acceptance state lives in cpu_acceptances (match_confirmed / attempted)
```

- **`posted`** — PvP bet open, not yet accepted (`accepterId` null). Poster's wager already debited.
- **`accepted`** — a second user accepted (takes the opposite side). Both wagers now debited.
- **`submitted`** — PvP only; set when `check_stats_match` passes (both players submitted **matching** stats).
  Payout happens here: winner gets `2 × amount`. **This is the once-only settlement point.**
- **`CPU`** — House bets. **Never transitions.** Payout is decided per-acceptance in `cpu_acceptances`
  (`match_confirmed`), not by a status change.

**Non-obvious settlement facts (drive PLAN 5.2 / 5.3):**
- A PvP bet settles **only** when both players submit *matching* stats. If one ghosts, or they submit
  *disagreeing* stats, it stays `accepted` **forever** and caps stay locked. (PLAN 5.2 Q3: auto-void + refund both
  after 7 days.)
- `cleanup_bets` currently **DELETEs** stale bets with **no refund** (posted/submitted/CPU > 7 days). (PLAN 5.2 Q2:
  refund poster on `posted` expiry.)
- CPU payout re-awards `amount × 2` on **every** matching re-submission (no idempotency guard). (PLAN 5.3.)
- On a tie/incomplete PvP, `winner_id = None` and `UPDATE … WHERE id = None` credits nobody → both wagers vanish.
  (Eliminated by PLAN 5.2 Q1's half-point lines + Q3's void-refund.)

## Caps economy (invariant to protect)
Debit points: `create_bet` (poster), `accept_bet` (accepter), CPU `accept` (accepter). Credit points: PvP settle
(`2×` to winner), CPU win (`2×` to user). **Target invariant (PLAN 5.2): every debited wager is either paid to a
winner or refunded — total caps are conserved** except intentional sinks (CPU house edge; losing a CPU bet).
The House account (`players.id = 0`) is **not** debited on payout — it has effectively infinite bankroll, so the
only cap on a House wager is the user's own balance (PLAN X.3: min 10 / max = balance).

---

## Drift & gotchas

### Gotcha 1: camelCase columns in `bets` & `bettable_player_stats` are case-sensitive
These two tables were created in Supabase with **quoted** identifiers, so columns like `posterId`, `gameType`,
`timePosted`, `lineNumber`, `gamePlayed` are **case-sensitive**. Unquoted SQL (`SELECT posterId …`) folds to
`posterid` and **errors**; `SELECT *` returns dict keys in true case (`"posterId"`) while the code reads
`bet['posterid']` → `KeyError`. **This is the most likely root cause of the pre-existing 500s on `/pvp_bets`,
`/cpu_bets`, `/ongoing_bets`, and `/me`.**
- All other tables (`players`, `bettable_players`, `cpu_acceptances`, `player_stat_aggregates`) are lowercase — no issue.
- **Fix path:** interim = quote/alias the identifiers so reads work now (PLAN 0.8); permanent = rename these columns
  to lowercase `snake_case` during the SQLAlchemy port (PLAN 4.1), killing the footgun for good.

### Gotcha 2: `bets.posterId` / `accepterId` are `text` with NO foreign key
Account↔bet integrity is **not** enforced by the DB, and the id is stored as a string. Don't rely on cascades for
account deletion (PLAN 10.2); model this explicitly in the SQLAlchemy port (PLAN 4.1).

### Gotcha 3: `player_stat_aggregates` column drift
Code/CLAUDE.md reference `std` / `n_games` / `game_played` / `win_rate` / `defensive_value` / `mean_last_5`. Reality:
the columns are `std_dev` / `sample_size` / `game`, and `win_rate` / `defensive_value` / `mean_last_5`
**don't exist**. The DV/win-rate line-gen features are therefore inert (default 0.5). Implementing them for real is
PLAN X.7 (deliberately kept out of the behavior-preserving 3.1 collapse, since it would change line output).

### Gotcha 4: `bets.yourOutcome` (text) vs `oppOutcome` (integer)
The two "Other"-type outcome columns have mismatched types but are compared against each other in settlement.
Normalize during 4.1.

### Gotcha 5: `backend/models.py` is untrusted
It defines only `players` + `bets`, is missing the four other tables, and disagrees with the live schema
(`oppOutcome INTEGER`, `posterId TEXT REFERENCES players(id)` — a text col referencing an int PK). Treat this file
as legacy DDL, not truth. There is also a **dead** `bets` Blueprint in `auth.py` that INSERTs non-existent columns
(`poster_id`, `subject`, `line`) — deleted by PLAN 0.3.

---

## How PLAN.md items map to this schema
- **0.3** — deletes the dead `bets` Blueprint (Gotcha 5). · **0.8** (proposed) — interim camelCase read fix (Gotcha 1).
- **3.1** — sport-module collapse; behavior-preserving (does **not** fix Gotcha 3's DV/win_rate).
- **4.1** — SQLAlchemy port: model the real schema here (not `models.py`); resolve Gotchas 1/2/4 (rename camelCase→snake_case, explicit FKs, normalize `oppOutcome`).
- **5.1 / 5.2 / 5.3** — wallet/settlement correctness; see [lifecycle](#bet-lifecycle-the-status-state-machine) & caps invariant.
- **10.2** — account deletion: tombstone `players` only; never touch the stats world (two-worlds model).
- **X.3** — per-acceptance wager column added to `cpu_acceptances`.
- **X.7** (proposed) — implement `win_rate` / `defensive_value` aggregates (Gotcha 3).
</content>
</invoke>
