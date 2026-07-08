# Project Standards

Project-specific conventions that extend the global code-standards and system-standards. Do not duplicate rules already in those files.

## Reliability

- **Connection management**: This codebase opens raw psycopg2 connections per-request via `get_db()`. Early-return paths (404, 403, etc.) must not close resources with bare `cur.close(); conn.close()` pairs — these miss the exception path. Wrap the handler body in `try/finally: cur.close(); conn.close()` instead.

## Safety & Security

- **JWT payload types**: `get_player_id()` returns `payload["id"]` directly. Always coerce to `int` immediately after the None guard (`player_id = int(player_id)`). PyJWT preserves the type of the encoded value, but this is an implicit contract — make it explicit at the extraction site so a future JWT-minting change (e.g. `str(user_id)`) does not silently break participation checks.

## Observability

- **Use `logger.exception()` for caught exceptions**: In request-handler `except` blocks, prefer `logger.exception("message")` over `logger.error("message: %s", e)`. Both log at ERROR level, but `exception()` automatically appends the full traceback without extra kwargs — essential for post-mortems when the same exception type can arise from many code paths.
