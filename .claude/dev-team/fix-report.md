# Fix Report
**Date:** 2026-07-09
**Item:** 3.1 — Sport module collapse (bet_generation.py)
**Findings addressed:** 2 of 3 review findings (1 Important + 1 Minor applied; 2 remaining Minors deferred with rationale)

## Changes Made
- backend/routes/lines_routes.py:11-22 — dropped the six `generate_biased_*` concrete imports; routes now import only the config objects, shared `assemble_matchup`, and the score-profile / global-strength helpers still used directly in route bodies — review Important
- backend/routes/lines_routes.py (6 call sites: caps/pong/beerball shots + caps/pong/beerball score) — line generation now dispatches through `CAPS.predict_shots`/`PONG.predict_shots`/`BEERBALL.predict_shots` and `.predict_score`, making the `SportConfig` callables the sole line-gen entry point (an ML swap now touches only the config binding, not every route) — review Important
- backend/tests/test_golden_master_3_1.py — repointed all 12 assertions from `bg.generate_biased_*` to the config dispatch path (`CAPS/PONG/BEERBALL.predict_shots/.predict_score`); removed the now-unused `bet_generation as bg` import; added a docstring note explaining the seam is the pinned surface — review Important (test now exercises the actual dispatch path)
- backend/tests/test_cleanup_batch_0_4.py:271-276 — repointed `BET_GEN_FILES` from the three deleted per-sport filenames to `["bet_generation.py"]` so `test_no_logger_error_in_exception_handlers` scans the consolidated module instead of passing vacuously via the `exists()` guard — review Minor

## Disputed
none

## Deferred
- bet_generation.py:742 (`SPORTS` dead export) — Minor. The Important-finding fix wires dispatch through the concrete config objects (`CAPS`/`PONG`/`BEERBALL`) the routes already reference, so string-keyed dispatch via `SPORTS` is not needed here. Left in place (harmless, available for a future game-name-driven dispatch site) rather than dropped — dropping was the reviewer's alternative, not a requirement.
- lines_routes.py:439-447 (caps-score `safe_shots` N+1) — Minor, explicitly flagged by the reviewer as pre-existing and left as-is by the engineer to avoid behavior change; noted for a future batch-fetch item, out of scope for this fix.

## Verification
- `python -m pytest tests/ --tb=short -q` → **334 passed**, 4 warnings (pre-existing pytest deprecation warnings, unrelated).
- Golden-master parity (12/12) still holds through the config dispatch path — byte-for-byte outputs unchanged.
- `grep generate_biased` over routes + golden-master test → no remaining call-by-name references; the concrete functions survive only as the callables bound onto the configs.
- Committed as `cba0b49` on branch `auto/stage0-0.8`.
