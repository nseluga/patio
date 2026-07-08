"""
QA tests for item 0.5 re-verification: review-finding fixes applied by Bug Fixer.

New criteria (beyond original 0.5 PASS):
  1. /cleanup_bets returns 403 for non-House authenticated users (player_id != 0)
  2. /bets is paginated (LIMIT/OFFSET) and filtered to the caller's own bets
  3. /create_bet uses atomic caps UPDATE; rowcount==0 returns 400 (insufficient caps)
  4. compute_status_message takes conn as a parameter; does NOT call get_db() internally

Tests use both static source analysis (AST/regex) and Flask test-client behavioral checks
with a mocked DB — no live Postgres connection required.
"""

import ast
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, call, patch

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
APP_PY = REPO_ROOT / "backend" / "app.py"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


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
# Criterion 1 — /cleanup_bets: 403 for non-House users
# ===========================================================================


def test_cleanup_bets_source_has_403_guard():
    """/cleanup_bets source must have player_id != 0 guard returning 403."""
    src = _function_source("cleanup_bets")
    assert src, "cleanup_bets function not found in app.py"
    assert "403" in src, (
        "cleanup_bets has no 403 response — it must forbid non-House (player_id != 0) users"
    )
    # The guard must reference player_id 0 somehow
    assert "!= 0" in src or "== 0" in src, (
        "cleanup_bets does not compare player_id to 0 (House guard missing)"
    )


def test_cleanup_bets_non_house_returns_403(client):
    """POST /cleanup_bets with a valid JWT for a normal user (player_id=1) → 403."""
    with patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        response = client.post(
            "/cleanup_bets",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403, (
        f"Expected 403 (non-House user), got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )


def test_cleanup_bets_house_not_forbidden(client):
    """POST /cleanup_bets with a valid JWT for player_id=0 (House) must NOT return 403."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=0)
            response = client.post(
                "/cleanup_bets",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code != 403, (
        f"House (player_id=0) was incorrectly forbidden with 403: "
        f"{response.get_data(as_text=True)}"
    )


# ===========================================================================
# Criterion 2 — /bets: paginated and filtered to caller's own bets
# ===========================================================================


def test_bets_source_has_pagination():
    """get_all_bets must include LIMIT and OFFSET for pagination."""
    src = _function_source("get_all_bets")
    assert src, "get_all_bets function not found in app.py"
    src_upper = src.upper()
    assert "LIMIT" in src_upper, "get_all_bets query has no LIMIT clause — pagination missing"
    assert "OFFSET" in src_upper, "get_all_bets query has no OFFSET clause — pagination missing"


def test_bets_source_filters_by_caller():
    """get_all_bets must filter results to the caller's own bets (posterid OR accepterid)."""
    src = _function_source("get_all_bets")
    assert src, "get_all_bets function not found in app.py"
    src_lower = src.lower()
    assert "posterid" in src_lower, (
        "get_all_bets query does not filter by posterid — returns unscoped dump"
    )
    assert "accepterid" in src_lower, (
        "get_all_bets query does not filter by accepterid — caller's accepted bets excluded"
    )


def test_bets_valid_jwt_returns_paginated_response(client):
    """GET /bets with a valid JWT returns 200 and the query uses LIMIT/OFFSET pagination."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.get(
                "/bets?page=2&per_page=10",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.get_data(as_text=True)}"
    )

    # Verify the DB was called with pagination params (LIMIT=10, OFFSET=10 for page 2)
    all_execute_args = [str(c) for c in mock_cursor.execute.call_args_list]
    combined = " ".join(all_execute_args)
    # The pagination values 10 and 10 (offset for page 2) must appear in execute params
    assert "10" in combined, (
        "LIMIT/OFFSET values not found in execute() calls — pagination params not forwarded to DB"
    )


def test_bets_per_page_capped_at_100(client):
    """GET /bets must cap per_page at 100 even if client requests more."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_conn.cursor.return_value  # reuse

    # Use source inspection — the cap should be in the code
    src = _function_source("get_all_bets")
    assert "100" in src, (
        "get_all_bets does not enforce a per_page cap of 100 — clients can dump entire table"
    )


# ===========================================================================
# Criterion 3 — /create_bet: atomic caps UPDATE, rowcount==0 → 400
# ===========================================================================


def test_create_bet_source_uses_atomic_update():
    """create_bet must use a single atomic UPDATE ... WHERE caps_balance >= %s."""
    src = _function_source("create_bet")
    assert src, "create_bet function not found in app.py"
    src_upper = src.upper()
    # The UPDATE must be present
    assert "UPDATE PLAYERS SET CAPS_BALANCE" in src_upper, (
        "create_bet does not have an atomic caps UPDATE statement"
    )
    # The WHERE guard must reference caps_balance (atomic compare-and-debit)
    assert "CAPS_BALANCE >=" in src_upper, (
        "create_bet atomic UPDATE does not include a WHERE caps_balance >= guard — TOCTOU not fixed"
    )


def test_create_bet_source_checks_rowcount():
    """create_bet must check cur.rowcount == 0 after the atomic UPDATE."""
    src = _function_source("create_bet")
    assert src, "create_bet function not found in app.py"
    assert "rowcount" in src, (
        "create_bet does not check cur.rowcount after the atomic UPDATE"
    )
    assert "== 0" in src, (
        "create_bet does not handle rowcount == 0 (insufficient caps path missing)"
    )


def test_create_bet_insufficient_caps_returns_400(client):
    """POST /create_bet when atomic UPDATE affects 0 rows → 400 (Insufficient caps)."""
    mock_cursor = MagicMock()
    # SELECT username returns a valid player
    mock_cursor.fetchone.return_value = ("alice",)
    # Atomic UPDATE returns rowcount=0 (no matching row → insufficient caps)
    mock_cursor.rowcount = 0
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/create_bet",
                json={
                    "amount": 9999,
                    "matchup": "1v1",
                    "lineType": "Over",
                    "lineNumber": 10.5,
                    "gameType": "Caps",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400, (
        f"Expected 400 (insufficient caps via rowcount==0), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )
    data = response.get_json()
    assert data is not None and "caps" in data.get("error", "").lower(), (
        f"400 body does not mention caps: {data}"
    )


def test_create_bet_sufficient_caps_succeeds(client):
    """POST /create_bet when atomic UPDATE affects 1 row → 201."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = ("alice",)
    mock_cursor.rowcount = 1  # UPDATE succeeded → caps deducted
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/create_bet",
                json={
                    "amount": 50,
                    "matchup": "1v1",
                    "lineType": "Over",
                    "lineNumber": 10.5,
                    "gameType": "Caps",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 201, (
        f"Expected 201 when atomic UPDATE succeeds (rowcount=1), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )


# ===========================================================================
# Criterion 4 — compute_status_message: takes conn, does NOT call get_db()
# ===========================================================================


def test_compute_status_message_source_has_conn_param():
    """compute_status_message must accept `conn` as a parameter."""
    src = _function_source("compute_status_message")
    assert src, "compute_status_message function not found in app.py"
    # Check function signature line
    first_line = src.splitlines()[0]
    assert "conn" in first_line, (
        f"compute_status_message does not declare `conn` in its signature: {first_line!r}"
    )


def test_compute_status_message_source_no_get_db_call():
    """compute_status_message must NOT call get_db() internally — it uses the passed conn."""
    src = _function_source("compute_status_message")
    assert src, "compute_status_message function not found in app.py"
    assert "get_db()" not in src, (
        "compute_status_message calls get_db() internally — should use the passed conn parameter"
    )


def test_compute_status_message_uses_passed_conn():
    """compute_status_message creates a cursor from the conn it was passed, not a new connection."""
    from backend.app import compute_status_message

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"match_confirmed": True, "attempted": False}
    mock_conn.cursor.return_value = mock_cursor

    # A minimal CPU bet dict
    bet = {"id": "bet-123", "status": "CPU"}

    # This call must NOT trigger get_db() — it should use mock_conn
    with patch("backend.app.get_db") as mock_get_db:
        compute_status_message(bet, player_id=1, conn=mock_conn)

    mock_get_db.assert_not_called(), (
        "compute_status_message called get_db() — should use the passed conn parameter"
    )
    mock_conn.cursor.assert_called(), (
        "compute_status_message did not use the passed conn to create a cursor"
    )
