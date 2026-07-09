---
# Engineer Report
**Task:** Item 0.8 — Fix camelCase column access breaking core reads
**Branch:** auto/stage0-0.8
**Date:** 2026-07-09

## Design Decisions

- **Alias approach over RealDictCursor casing fix:** Replaced `SELECT *` with explicit column lists using double-quoted camelCase identifiers aliased to lowercase (e.g., `"posterId" AS posterid`). This means all existing lowercase dict-key accesses (`bet["posterid"]`, `bet["gametype"]`, etc.) work without touching the rest of the handler logic — lower blast radius than renaming dict keys throughout.
- **Consistent alias set across all handlers:** Defined the same alias pattern across `get_pvp_bets`, `get_cpu_bets`, `get_ongoing_bets`, and both `SELECT` calls in `submit_stats` so the behavior is uniform and predictable.
- **Extended UNION queries with full explicit columns:** The UNION in `get_ongoing_bets` required repeating the column list three times (one per UNION arm) to ensure column alignment. Also pulled in all stat fields (`yourteama`, `yourshots`, etc.) needed by `compute_status_message` — `SELECT *` was silently including these; they must be kept.
- **auth.py WHERE clause also fixed:** Changed unquoted `posterId` and `accepterid` in the WHERE clause to `"posterId"` and `"accepterId"` — unquoted identifiers fold to lowercase in Postgres, which would silently fail or return wrong rows.
- **Stopgap only:** This fix is an interim measure. Item 4.1 will rename all columns to snake_case, at which point these aliases and quotes can be removed.

## Files Changed

- `backend/app.py` — Fixed `SELECT *` in `get_pvp_bets`, `get_cpu_bets`, `get_ongoing_bets`, and both `SELECT * FROM bets` calls in `submit_stats` (initial fetch + re-fetch after update) with explicit column lists and lowercase aliases; also fixed quoted identifiers in WHERE clauses (`"posterId"`, `"accepterId"`, `"timePosted"`)
- `backend/auth.py` — Fixed `/me` bets query: changed `SELECT gametype` to `SELECT "gameType" AS gametype`, added quotes to `"posterId"`, `"accepterId"`, `"timePosted"` throughout

## Deferred / Out of Scope

- `cleanup_bets`: Uses unquoted camelCase identifiers in DELETE WHERE clauses (`accepterId`, `timePosted`) — not in scope for 0.8 but may cause runtime errors; flagged for 4.1 or a dedicated fix
- `accept_bet`: `SELECT amount, posterId FROM bets` uses unquoted `posterId` in SELECT — may work by accident or fail; out of scope
- `UPDATE bets SET accepterId = %s` in `accept_bet`: unquoted column in SET clause — out of scope
- Column rename to snake_case (item 4.1) will make all these fixes obsolete

## Flags for Reviewer

- The UNION query in `get_ongoing_bets` is now verbose — three near-identical SELECT arms. If Postgres column count mismatches (UNION requires same number of columns), the query will error at runtime even if syntax is valid; verify the column count matches across all three arms (28 columns each).
- `compute_status_message` is called with the `bet` dict from `get_ongoing_bets` (regular cursor + manual dict) and also from `submit_stats` (RealDictCursor). Both now produce lowercase aliases, so the same lowercase key access in `compute_status_message` works for both callers.
- `check_stats_match` is called with `updated_bet` from `submit_stats` re-fetch — also lowercase-aliased, so `bet.get('gametype')` etc. are correct.
---
