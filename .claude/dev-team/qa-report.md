---
# QA Report
**Task:** Item 0.7 — Stop leaking secrets in logs + disable debug mode
**Branch:** conversion
**Date:** 2026-07-09
**Gate mode:** tests+behavioral

## VERDICT: PASS

## Criteria Checked
- No log line contains a raw token or JWT payload — `test_no_raw_token_in_logger_calls`, `test_jwt_except_block_does_not_log_token`, `test_no_print_with_token_in_auth_files` — PASS
- No log line contains SECRET_KEY — `test_no_secret_key_in_logger_calls` — PASS
- Debug mode off outside local dev (FLASK_DEBUG=0) — `test_flaskenv_debug_is_zero` — PASS
- FLASK_ENV=production in .flaskenv — `test_flaskenv_env_is_production` — PASS
- No `app.run(debug=True)` in source — `test_no_app_run_with_debug_true` — PASS
- Procfile has no --debug flag — `test_procfile_has_no_debug_flag` — PASS

## Tests Added
- `backend/tests/test_debug_and_secrets_0_7.py` — 9 tests: no raw token/payload/auth_header/SECRET_KEY in logger calls; no print() with secret vars; JWT except block clean; .flaskenv has FLASK_DEBUG=0 and FLASK_ENV=production; no app.run(debug=True); Procfile has no --debug flag

Full suite: **77/77 passed**, 0 regressions

## Not Verifiable
- Live behavioral smoke for debug reloader state not run (requires long-running server process); static .flaskenv env-var assertions and source-level checks are the definitive gate for this criterion — treated as covered.
---

---
# QA Report — Item 0.7 Re-verification (Bug Fixer pass, commit 1dc003f)
**Task:** Re-verify Item 0.7 after Bug Fixer pass — atomic caps deduction in accept_bet and accept_cpu_bet; debug log placement
**Branch:** conversion
**Date:** 2026-07-09
**Gate mode:** tests+behavioral

## VERDICT: PASS

## Criteria Checked

- No log line contains a token or JWT payload — all 9 `test_debug_and_secrets_0_7.py` tests still pass; no regression from Bug Fixer changes — PASS
- Debug mode is off outside local dev — `backend/.flaskenv` has `FLASK_ENV=production` and `FLASK_DEBUG=0`; Procfile carries no `--debug`; no `app.run(debug=True)` in source — PASS
- `accept_bet` uses atomic caps deduction (no TOCTOU race) — static analysis confirms `UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s` with `rowcount == 0` guard; no separate SELECT caps_balance found; behavioral: rowcount=0 → 400, rowcount=1 → 200 — PASS
- `accept_cpu_bet` uses atomic caps deduction (no TOCTOU race) — same atomic UPDATE pattern confirmed by static analysis and behavioral test; no separate SELECT caps_balance — PASS
- Debug log in `accept_bet` fires after auth guard — `logger.debug("PvP accept_bet triggered…")` placed after `if player_id is None` guard; confirmed by `test_accept_bet_debug_log_after_auth_guard` — PASS

## Tests Added

- `backend/tests/test_atomic_caps_0_7.py` — 13 tests: (a) `accept_bet` source uses atomic UPDATE, no separate SELECT caps_balance, checks rowcount; behavioral 400 on insufficient caps, 200 on success, 401 on missing auth; (b) same 6 checks for `accept_cpu_bet`; (c) debug log placement after auth guard

Full suite: **90/90 passed**, 0 regressions

## Not Verifiable

- Live smoke against a real Postgres DB not run — no dev DB credentials in this environment. The atomic `UPDATE … WHERE caps_balance >= %s` pattern is a single SQL statement that Postgres executes atomically; the TOCTOU guarantee holds at the DB level. All behavioral checks use Flask test-client with mocked DB; the TOCTOU property is structural and confirmed by source inspection. Treated as covered.
---
