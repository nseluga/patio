# Project Standards

Project-specific conventions that extend the global code-standards and system-standards. Do not duplicate rules already in those files.

## Reliability

- **Connection management**: This codebase opens raw psycopg2 connections per-request via `get_db()`. Early-return paths (404, 403, etc.) must not close resources with bare `cur.close(); conn.close()` pairs — these miss the exception path. Wrap the handler body in `try/finally: cur.close(); conn.close()` instead.

## Safety & Security

- **JWT payload types**: `get_player_id()` returns `payload["id"]` directly. Always coerce to `int` immediately after the None guard (`player_id = int(player_id)`). PyJWT preserves the type of the encoded value, but this is an implicit contract — make it explicit at the extraction site so a future JWT-minting change (e.g. `str(user_id)`) does not silently break participation checks.

- **Atomic caps deduction**: all caps-deduction sites must use a single-statement `UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s` (atomic check-and-debit in one round-trip); check `cur.rowcount == 0` for the insufficient-caps guard. A bare SELECT + UPDATE pair is a TOCTOU race under concurrent requests. `create_bet` (app.py:239-244) is the reference implementation; `accept_bet` (app.py:396-402) and `accept_cpu_bet` (app.py:461-469) are not yet conforming.

- **camelCase quoted-identifier rule**: Every SQL context in this codebase — SELECT, WHERE, SET, ORDER BY, INSERT column lists — must double-quote camelCase column names (`"posterId"`, `"accepterId"`, `"timePosted"`, `"gameType"`, `"lineType"`, `"lineNumber"`, `"gamePlayed"`, `"gameSize"`, etc.). The alias pattern (`"posterId" AS posterid`) is the established read-query convention; INSERT column lists and UPDATE SET clauses must use `"posterId"` (no alias). Unquoted camelCase folds to lowercase in Postgres, silently matching no column or the wrong one — causing silent zero-row returns or `column does not exist` runtime errors. Item 4.1 will rename all columns to snake_case; until then, every SQL touch must apply this rule.

## Observability

- **Use `logger.exception()` for caught exceptions**: In request-handler `except` blocks, prefer `logger.exception("message")` over `logger.error("message: %s", e)`. Both log at ERROR level, but `exception()` automatically appends the full traceback without extra kwargs — essential for post-mortems when the same exception type can arise from many code paths.

## Safety & Security (continued)

- **JWT decorator as sole auth boundary**: `@token_required` in `backend/utils/auth.py` is the only location permitted to call `jwt.decode` or read `request.headers["Authorization"]`. Route bodies must not duplicate this logic. `backend/app.py` must not import `jwt` directly. CPU-only route guards that fire after the decorator has already authenticated the caller must return `403 Forbidden`, not `401 Unauthorized`.

## Rate Limiting

- **Rate limiter proxy awareness**: `get_remote_address` reads `request.remote_addr`. On Render (and any reverse-proxy host), `ProxyFix(app, x_for=1)` must be applied in `create_app()` before `limiter.init_app(app)` so real client IPs propagate correctly; without it every user shares the load balancer's IP as their bucket key.
- **429 error handler**: `RateLimitExceeded` (Flask-Limiter 4.x) does not populate `.retry_after` on the exception object — its `__init__` never passes `retry_after` to the Werkzeug parent. Do not reference `e.retry_after` in the 429 handler; use a static window value or omit the field.
- **Limiter decorator order**: On routes decorated with both `@token_required` and `@limiter.limit`, `@limiter.limit` must be the outer decorator (listed immediately below `@bp.route`) so unauthenticated probing requests are counted against the rate limit before auth short-circuits.

## Blueprints & Modularity

- **Blueprint shim rule**: All new blueprints must import `get_db` from `backend.routes._db`, not from `backend.db` directly, so that `patch("backend.app.get_db", ...)` test patches are intercepted at call time. The same pattern applies to `SECRET_KEY` via `backend.utils.auth`.
- **Cross-blueprint helper placement**: Helpers shared between multiple blueprints (`check_stats_match`, `compute_status_message`) currently live in `bets_routes.py`. If a helper gains a third consumer or grows significantly, move it to `backend/routes/_helpers.py` rather than deepening the cross-blueprint import chain.

## Validation

- **Validation completeness rule**: When a field has both a presence requirement and a type requirement, both must be enforced at the HTTP boundary — `require_fields` for presence, `coerce_int`/`float` for type. A `require_fields`-only check does not prevent type crashes downstream. The same coerce pattern must be applied in every conditional branch of a handler (e.g., both the CPU and PvP sub-paths of `submit_stats`) — leaving any branch unguarded defeats the layer.
- **`require_fields` empty-string behavior**: The current `require_fields` helper treats `""` as present (`data.get(f) is None` is `False` for blank strings). For fields where a blank value is semantically invalid (username, password, player name), callers must add an explicit non-empty check after `require_fields`, or use a stricter helper variant that rejects empty strings.
