"""
QA tests for item 0.5: Route auth inventory + client-supplied identity fixes.

Done when:
  - /cleanup_bets requires valid JWT (401 without one)
  - /bets requires valid JWT (401 without one)
  - /pvp_bets uses JWT identity to filter, not playerId query param (401 without token)
  - /create_bet ignores client-supplied posterId/poster/status/id and derives them
    server-side from JWT + DB

Tests use both static source analysis (AST/regex) and the Flask test client with a
mocked DB — no live Postgres connection required.
"""

import ast
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

# Set env vars before any backend module is imported so config.py picks them up.
os.environ.setdefault("SECRET_KEY", "test-secret-qa-0-5")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-0-5"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_PY = BACKEND_DIR / "app.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def make_mock_conn(fetchone_return=None, fetchall_return=None, description=None):
    """Return a mock DB connection/cursor with configurable return values."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    mock_cursor.description = description if description is not None else []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def _function_source(func_name: str) -> str:
    """Return the full source of a top-level function in app.py."""
    source = APP_PY.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ===========================================================================
# (A) Static source analysis
# ===========================================================================


def test_cleanup_bets_source_has_auth_guard():
    """/cleanup_bets must call get_player_id() and return 401 if None."""
    src = _function_source("cleanup_bets")
    assert src, "cleanup_bets function not found in app.py"
    assert "get_player_id()" in src, "cleanup_bets does not call get_player_id()"
    assert "401" in src, "cleanup_bets has no 401 response guard"


def test_get_all_bets_source_has_auth_guard():
    """/bets (get_all_bets) must call get_player_id() and return 401 if None."""
    src = _function_source("get_all_bets")
    assert src, "get_all_bets function not found in app.py"
    assert "get_player_id()" in src, "get_all_bets does not call get_player_id()"
    assert "401" in src, "get_all_bets has no 401 response guard"


def test_pvp_bets_source_uses_jwt_not_query_param():
    """/pvp_bets must call get_player_id() and must NOT read from request.args."""
    src = _function_source("get_pvp_bets")
    assert src, "get_pvp_bets function not found in app.py"
    assert "get_player_id()" in src, "get_pvp_bets does not call get_player_id()"
    assert "request.args" not in src, (
        "get_pvp_bets still reads from request.args — identity must come from JWT"
    )
    assert "401" in src, "get_pvp_bets has no 401 guard"


def test_create_bet_source_server_side_identity():
    """/create_bet must not use bet.get() for posterId, poster, status, or id;
    must generate UUID server-side and hardcode status='posted'."""
    src = _function_source("create_bet")
    assert src, "create_bet function not found in app.py"

    # Client-supplied fields that must NOT be trusted
    for bad_key in ("posterId", "poster", "status", "id"):
        for quote in ("'", '"'):
            bad_expr = f"bet.get({quote}{bad_key}{quote})"
            assert bad_expr not in src, (
                f"create_bet reads '{bad_key}' from the request body via {bad_expr} — "
                f"must derive server-side"
            )

    assert "uuid4()" in src, "create_bet does not generate a UUID via uuid4()"
    assert "'posted'" in src, "create_bet does not hardcode status='posted'"
    assert "get_player_id()" in src, "create_bet does not call get_player_id()"


# ===========================================================================
# (B) Behavioral tests: /cleanup_bets
# ===========================================================================


def test_cleanup_bets_no_jwt_returns_401(client):
    """POST /cleanup_bets without an Authorization header → 401."""
    response = client.post("/cleanup_bets")
    assert response.status_code == 401, (
        f"Expected 401 (no JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_cleanup_bets_forged_jwt_returns_401(client):
    """POST /cleanup_bets with a JWT signed by the wrong key → 401."""
    forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
    response = client.post(
        "/cleanup_bets",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401, (
        f"Expected 401 (forged JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_cleanup_bets_valid_jwt_proceeds(client):
    """POST /cleanup_bets with a valid JWT must pass the auth gate (not 401)."""
    mock_conn = make_mock_conn()

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/cleanup_bets",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code != 401, (
        f"Valid JWT was still rejected with 401: {response.get_data(as_text=True)}"
    )


# ===========================================================================
# (C) Behavioral tests: /bets
# ===========================================================================


def test_bets_no_jwt_returns_401(client):
    """GET /bets without an Authorization header → 401."""
    response = client.get("/bets")
    assert response.status_code == 401, (
        f"Expected 401 (no JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_bets_forged_jwt_returns_401(client):
    """GET /bets with a JWT signed by the wrong key → 401."""
    forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
    response = client.get(
        "/bets",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401, (
        f"Expected 401 (forged JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_bets_valid_jwt_proceeds(client):
    """GET /bets with a valid JWT must pass the auth gate (not 401)."""
    mock_conn = make_mock_conn(fetchall_return=[])

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.get(
                "/bets",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code != 401, (
        f"Valid JWT was still rejected with 401: {response.get_data(as_text=True)}"
    )


# ===========================================================================
# (D) Behavioral tests: /pvp_bets
# ===========================================================================


def test_pvp_bets_no_jwt_returns_401(client):
    """GET /pvp_bets without an Authorization header → 401."""
    response = client.get("/pvp_bets")
    assert response.status_code == 401, (
        f"Expected 401 (no JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_pvp_bets_query_param_alone_returns_401(client):
    """GET /pvp_bets with only a playerId query param (no JWT) → still 401.

    The old route accepted ?playerId=N as identity; the fix rejects any request
    that lacks a valid JWT regardless of query params.
    """
    response = client.get("/pvp_bets?playerId=1")
    assert response.status_code == 401, (
        f"Expected 401 (query param without JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_pvp_bets_forged_jwt_returns_401(client):
    """GET /pvp_bets with a JWT signed by the wrong key → 401."""
    forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
    response = client.get(
        "/pvp_bets",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401, (
        f"Expected 401 (forged JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_pvp_bets_valid_jwt_no_query_param_returns_200(client):
    """GET /pvp_bets with a valid JWT and no playerId query param → 200.

    Confirms the JWT-based identity path works end-to-end.
    """
    mock_conn = make_mock_conn(fetchall_return=[])

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.get(
                "/pvp_bets",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, (
        f"Expected 200 for valid JWT (no query param), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


# ===========================================================================
# (E) Behavioral tests: /create_bet — server-side identity
# ===========================================================================


def test_create_bet_no_jwt_returns_401(client):
    """POST /create_bet without an Authorization header → 401."""
    response = client.post("/create_bet", json={"amount": 50})
    assert response.status_code == 401, (
        f"Expected 401 (no JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_create_bet_forged_jwt_returns_401(client):
    """POST /create_bet with a JWT signed by the wrong key → 401."""
    forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
    response = client.post(
        "/create_bet",
        json={"amount": 50},
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert response.status_code == 401, (
        f"Expected 401 (forged JWT), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_create_bet_client_identity_fields_ignored(client):
    """POST /create_bet: client supplies posterId=999, poster='attacker',
    status='accepted', and id='fake-id'. The route must succeed (201) using
    JWT-derived identity (player 1) and DB-fetched username, not the client values."""
    # Player row returned by DB for the JWT player (id=1): (username, caps_balance)
    player_row = ("alice", 500)
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = player_row
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    CLIENT_FAKE_ID = "client-supplied-fake-id"

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/create_bet",
                json={
                    "amount": 50,
                    "posterId": 999,            # must be ignored → JWT player_id=1
                    "poster": "attacker",       # must be ignored → DB username 'alice'
                    "status": "accepted",       # must be ignored → hardcoded 'posted'
                    "id": CLIENT_FAKE_ID,       # must be ignored → server-generated UUID
                    "matchup": "1v1",
                    "lineType": "Over",
                    "lineNumber": 10.5,
                    "gameType": "Caps",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    # 201 confirms the route completed with valid server-side identity (not 401/400/500).
    assert response.status_code == 201, (
        f"Expected 201 when client-supplied identity fields are present, "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )

    # Verify the client-supplied fake ID was never passed to the DB — server UUID used instead.
    all_execute_args = [str(call) for call in mock_cursor.execute.call_args_list]
    for call_str in all_execute_args:
        assert CLIENT_FAKE_ID not in call_str, (
            f"Client-supplied id '{CLIENT_FAKE_ID}' found in a DB execute() call — "
            f"server must generate its own UUID, not trust the client.\n"
            f"Execute call: {call_str}"
        )

    # Verify DB was queried with JWT player_id=1 (not client-supplied 999).
    # The first execute() is SELECT username, caps_balance FROM players WHERE id = %s.
    first_execute = mock_cursor.execute.call_args_list[0]
    # args[1] is the params tuple passed to execute()
    params = first_execute[0][1] if len(first_execute[0]) > 1 else first_execute[1].get("vars", ())
    assert 1 in params, (
        f"DB was NOT queried with JWT player_id=1; params were: {params}. "
        f"Server must use JWT identity, not client-supplied posterId=999."
    )
    assert 999 not in params, (
        f"Client-supplied posterId=999 was passed to DB — should have been ignored."
    )
