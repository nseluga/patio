# Review Report
**Date:** 2026-07-09
**Item:** 3.1 — Sport module collapse (bet_generation.py)
**Files Reviewed:** 4 (bet_generation.py, lines_routes.py, test_golden_master_3_1.py, test_cleanup_batch_0_4.py)
**Standards Applied:** efficiency, scalability, reliability, security

## Summary
The Sport-module collapse is sound and behavior-preserving: the six line generators are copied verbatim from the deleted modules, every numeric constant (recency 0.1, margin std 1.5, percentiles, 9.5 pong cap, per-sport norms) matches, the negative-margin Over→Under flip is preserved, and the shared `snap_to_half_point` reproduces the original `round ± 0.5` exactly. Golden-master parity verified (12/12 pass) and no runtime importer of the deleted modules remains. The strategy seam is real but only partially realized for the stated ML-swap goal, and one test-coverage guard silently went vacuous. No correctness, security, or performance regressions found.

## Findings

### Important
- bet_generation.py:705-706 / lines_routes.py:76,160,268,364,457,541 — Reliability (seam not fully realized) — the decided "predict seam for future ML swap" is only half-built: `SportConfig` carries `predict_shots`/`predict_score`, but routes still import and call the six concrete `generate_biased_*` functions by name instead of dispatching through the config (`CAPS.predict_shots(...)`). The config fields are dead for line generation, so an ML swap would still require editing every route. Fix: call `cfg.predict_shots`/`cfg.predict_score` in the routes so the injected callable is the sole line-gen entry point.

### Minor
- test_cleanup_batch_0_4.py:271-274 — Reliability (silent coverage loss) — `BET_GEN_FILES` still lists the three deleted filenames; the `if not fpath.exists(): continue` guards make `test_no_logger_error_in_exception_handlers` and the print/logging checks pass vacuously, so `bet_generation.py` is no longer scanned for `logger.error`/print leaks (it currently uses only debug/warning, so no active violation). Fix: repoint `BET_GEN_FILES` to `["bet_generation.py"]`.
- bet_generation.py:742 — Efficiency (dead export) — the `SPORTS` dict is defined but unused by routes or tests; harmless, but confirms the string-keyed dispatch path was never wired. Fix: use it for route dispatch (ties into the Important finding) or drop it.
- lines_routes.py:439-447 — Efficiency (per-player query in loop) — caps-score `safe_shots` issues one SELECT per player inside a comprehension (N+1); pre-existing and explicitly left as-is by the engineer to avoid behavior change, noted only for a future batch-fetch item.

## Verification
- Golden-master parity: 12/12 pass; frozen outputs match originals byte-for-byte incl. the negative-margin flip (caps_score → 0.5/"Under").
- Constants: recency 0.1, std 1.5, percentiles 0.47/0.53 (caps/beerball) and 0.48/0.52 + 9.5 cap (pong), and all per-sport norms (÷8/÷16, ÷10/÷10, ÷3/÷10) preserved exactly → ~4% house bias intact for all 6 combinations.
- Opportunity factors: caps thresholds, pong advantage×suppression, beerball skill×DV-sigmoid all copied unchanged.
- No runtime importer of the deleted modules; only guarded test refs and comments remain.

## STANDARDS.md Updates
none

---

# Review Re-verification (post-Bug-Fixer cba0b49)
**Date:** 2026-07-09

## VERDICT: PASS — Important finding closed; no new issues introduced

## Important Finding (dead seam) — CLOSED
The dead seam is fully resolved. `lines_routes.py` no longer imports or calls any `generate_biased_*` function by name. All 6 line-generation call sites dispatch through `CAPS/PONG/BEERBALL.predict_shots/.predict_score`. An ML swap now only requires rebinding the `predict_shots`/`predict_score` fields on a `SportConfig` — no route edits needed.

Imports (lines_routes.py:11-22): only `BEERBALL, CAPS, PONG, assemble_matchup` + score profile/global-strength helpers. The six concrete function names are absent from the import list entirely.

## Minor Findings — Status
- `BET_GEN_FILES` stale filename list (test_cleanup_batch_0_4.py) — CLOSED. Repointed to `["bet_generation.py"]`; scan no longer passes vacuously.
- `SPORTS` dead export (bet_generation.py:742) — DEFERRED (harmless, rationale documented in fix-report).
- caps-score `safe_shots` N+1 (lines_routes.py:433-444) — DEFERRED (pre-existing, out of scope).

## Golden-master seam verification
`test_golden_master_3_1.py` now imports only `CAPS, PONG, BEERBALL` from `bet_generation` and calls `.predict_shots`/`.predict_score` on the config objects. The docstring explicitly states the config callables are the pinned surface. 12/12 pass through the dispatch path.

## No New Issues
The Bug Fixer's changes are minimal and targeted: 6 call-site rewrites in routes + 12 golden-master assertion rewrites + 1 test list repoint. No new imports, no new logic paths, no added complexity. Code quality is unchanged from the original review's assessment.
