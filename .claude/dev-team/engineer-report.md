# Engineer Report
**Task:** Item 3.1 — Collapse 3 sport bet-generation modules into 1 parameterized module (behavior-preserving, golden-master parity)
**Branch:** auto/stage0-0.8
**Date:** 2026-07-09

## Design Decisions
- **Consolidation with an explicit strategy seam, not a single hot path.** `backend/bet_generation.py` holds a shared pipeline (`adjust`, `harmonic_mean`, `team_strength_multiplier`, `snap_to_half_point`, `assemble_matchup`, parameterized DB reads) plus the six sport-specific line generators kept verbatim. DV, teammate-suppression, and the differing `opportunity_factor` signatures stay per-sport as separate functions — forcing them into one path would have changed behavior.
- **`SportConfig` (frozen dataclass) is the injection point.** Each sport (`CAPS`, `PONG`, `BEERBALL`) bundles its `game_name`, its DB accessors, and its `predict_shots`/`predict_score` callables. Shared player/matchup fetching is parameterized by `game_name`; sport-specific accessors (caps/pong/beerball score profiles, DV/shots-average helpers) stay distinct because their SELECT column sets genuinely differ (std vs win_rate vs defensive_value).
- **Preserved every numeric constant and code path exactly** — caps score uses harmonic-mean team strength; pong/beerball score use arithmetic mean of adjusted scores × strength multiplier; pong shots percentile 0.48/0.52 + 9.5 cap; caps/beerball shots 0.47/0.53 uncapped; negative-margin Over→Under flip on score lines. `snap_to_half_point` is only applied where the original used the plain `round ± 0.5` (pong shots keeps its inline `min(..., 9.5)` cap unchanged).
- **Golden master captured BEFORE writing new code.** Ran the three original modules against fixed representative inputs (mocked cursor) and froze all 12 outputs to `backend/tests/golden_master_3_1.json`. `test_golden_master_3_1.py` asserts the new module reproduces them byte-for-byte.
- **Deleted the three originals** (git rm) rather than shimming — no non-test importer remained besides `lines_routes.py`.

## Files Changed
- `backend/bet_generation.py` — NEW consolidated module: shared pipeline + `SportConfig` + `CAPS`/`PONG`/`BEERBALL`/`SPORTS` + all six line generators (logic copied verbatim from originals).
- `backend/caps_bet_generation.py`, `backend/pong_bet_generation.py`, `backend/beerball_bet_generation.py` — DELETED.
- `backend/routes/lines_routes.py` — imports now come from `backend.bet_generation`; player/matchup/profile calls routed through `CAPS`/`PONG`/`BEERBALL` config accessors and the shared `assemble_matchup`. No behavioral change to route bodies (SQL inserts, validation, error handling untouched).
- `backend/tests/test_golden_master_3_1.py` — NEW 12-assertion parity test.
- `backend/tests/golden_master_3_1.json` — NEW frozen golden values.
- `backend/tests/test_cleanup_batch_0_4.py` — the three `test_*_bet_gen_uses_batch_query` tests repointed from the deleted per-sport filenames to `bet_generation.py`; the anti-N+1 `ANY(%s)` guarantee is verified against the consolidated implementation. (Other cleanup tests reference the old filenames behind `if not fpath.exists(): continue` guards and now skip harmlessly.)

## Verification
- Full suite: **334 passed** (322 pre-existing + 12 new golden-master), 0 failures.
- Golden-master parity: all 12 outputs match the originals exactly, including the negative-margin flip case.
- End-to-end: simulated the caps-shots route pipeline with a mocked cursor — produces a numeric line and matchup string; `lines_bp` registers all 6 route handlers on import.

## Deferred / Out of Scope
- Did NOT parameterize the sport-specific score/shots math into a single generic function — the task explicitly required keeping line math per-sport behind the seam. The `SportConfig` unifies the *pipeline and dispatch*, not the math.
- Did NOT touch the caps-score route's inline `safe_shots` SQL (it queries directly, not via a profile helper) — left as-is to avoid behavior change.
- Other stale filename references in `test_cleanup_batch_0_4.py` (logging/print checks) were left to skip via their existing `exists()` guards rather than rewritten — minimal-diff choice.

## Flags for Reviewer
- `SportConfig` uses lambdas that close over the string literal `game_name` for the shared accessors — cheap, but if a reviewer prefers `functools.partial` for picklability that's a trivial swap.
- The six line generators are ~250 lines of copied-verbatim math; duplication *within* score generators (pong vs beerball are near-identical apart from norms/DV) was intentionally NOT deduped to preserve byte-for-byte parity — a follow-up item could unify them once parity tolerance is agreed.
- Repo has unrelated uncommitted changes from prior dev-team items (extensions.py, PLAN.md, etc.); this commit stages ONLY the 8 item-3.1 files.
