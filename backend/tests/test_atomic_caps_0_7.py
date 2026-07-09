"""
QA re-verification tests for Item 0.7 Bug Fixer pass (commit 1dc003f).

Bug Fixer applied three changes:
  (a) accept_bet: replaced SELECT+UPDATE caps deduction with atomic
      UPDATE ... WHERE caps_balance >= %s; rowcount==0 → 400
  (b) accept_cpu_bet: same atomic guard
  (c) accept_bet: moved debug log to AFTER the auth guard (player_id is None check)

Done when:
  (1) No log line contains a token or JWT payload
  (2) Debug mode is off outside local dev
  (3) accept_bet and accept_cpu_bet use atomic caps deduction (no TOCTOU race)

Tests (a) and (b) are new for this pass. Criterion (1) and (2) are already covered by
test_debug_and_secrets_0_7.py and are referenced below (run together).

Uses static source analysis + Flask test-client behavioral checks with mocked DB.
No live Postgres connection required.
"""

import ast
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret-qa-0-7")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-0-7"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_PY = BACKEND_DIR / "app.py"

# After the blueprint split, route functions live in backend/routes/*.py.
_SEARCH_PATHS = [
    APP_PY,
    BACKEND_DIR / "routes" / "bets_routes.py",
    BACKEND_DIR / "routes" / "accept_routes.py",
    BACKEND_DIR / "routes" / "submit_routes.py",
    BACKEND_DIR / "routes" / "main_routes.py",
    BACKEND_DIR / "routes" / "lines_routes.py",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def _function_source(func_name: str) -> str:
    """Return the full source of a named function, searching blueprint files too."""
    for path in _SEARCH_PATHS:
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                lines = source.splitlines()
                return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def _route_has_decorator(func_name: str, decorator_name: str) -> bool:
    """Return True if the named function (in any blueprint file) has decorator_name."""
    for path in _SEARCH_PATHS:
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                for dec in node.decorator_list:
                    dec_src = ast.unparse(dec)
                    if decorator_name in dec_src:
                        return True
    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ===========================================================================
# Criterion 3a — accept_bet: atomic caps UPDATE, rowcount==0 → 400
# ===========================================================================


def test_accept_bet_source_uses_atomic_update():
    """accept_bet must use a single atomic UPDATE ... WHERE caps_balance >= %s."""
    src = _function_source("accept_bet")
    assert src, "accept_bet function not found in app.py"
    src_upper = src.upper()
    assert "UPDATE PLAYERS SET CAPS_BALANCE" in src_upper, (
        "accept_bet does not have an atomic caps UPDATE statement — TOCTOU race not fixed"
    )
    assert "CAPS_BALANCE >=" in src_upper, (
        "accept_bet atomic UPDATE is missing WHERE caps_balance >= guard — race not eliminated"
    )


def test_accept_bet_source_no_separate_select_for_caps():
    """accept_bet must NOT do a separate SELECT caps_balance before the UPDATE."""
    src = _function_source("accept_bet")
    assert src, "accept_bet function not found in app.py"
    src_upper = src.upper()
    # A standalone SELECT of caps_balance (before an UPDATE) is the TOCTOU pattern.
    # We look for SELECT containing CAPS_BALANCE but NOT as part of an UPDATE.
    select_caps_lines = [
        line for line in src_upper.splitlines()
        if "SELECT" in line and "CAPS_BALANCE" in line
    ]
    assert not select_caps_lines, (
        "accept_bet has a separate SELECT caps_balance — TOCTOU race remains:\n"
        + "\n".join(select_caps_lines)
    )


def test_accept_bet_source_checks_rowcount():
    """accept_bet must check cur.rowcount == 0 after the atomic UPDATE."""
    src = _function_source("accept_bet")
    assert src, "accept_bet function not found in app.py"
    assert "rowcount" in src, (
        "accept_bet does not check cur.rowcount after the atomic UPDATE"
    )
    assert "== 0" in src, (
        "accept_bet does not handle rowcount == 0 (insufficient caps path missing)"
    )


def test_accept_bet_insufficient_caps_returns_400(client):
    """POST /accept_bet/<id> when atomic UPDATE affects 0 rows → 400 Insufficient caps."""
    mock_cursor = MagicMock()
    # First execute: SELECT amount, posterId FROM bets WHERE ... → returns the bet
    mock_cursor.fetchone.return_value = (50, 99)  # (amount, poster_id)
    # Atomic UPDATE returns rowcount=0 (player lacks sufficient caps)
    mock_cursor.rowcount = 0
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/accept_bet/bet-abc",
                json={"accepterLineType": "Over"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400, (
        f"Expected 400 (insufficient caps via rowcount==0), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )
    data = response.get_json()
    assert data is not None and "caps" in data.get("error", "").lower(), (
        f"400 body should mention 'caps': {data}"
    )


def test_accept_bet_sufficient_caps_succeeds(client):
    """POST /accept_bet/<id> when atomic UPDATE affects 1 row → 200."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (50, 99)  # (amount, poster_id)
    mock_cursor.rowcount = 1  # UPDATE succeeded → caps deducted
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/accept_bet/bet-abc",
                json={"accepterLineType": "Over"},
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, (
        f"Expected 200 when atomic UPDATE succeeds (rowcount=1), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )


def test_accept_bet_no_auth_returns_401(client):
    """POST /accept_bet/<id> with no token → 401."""
    response = client.post(
        "/accept_bet/bet-abc",
        json={"accepterLineType": "Over"},
    )
    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}"
    )


# ===========================================================================
# Criterion 3b — accept_cpu_bet: atomic caps UPDATE, rowcount==0 → 400
# ===========================================================================


def test_accept_cpu_bet_source_uses_atomic_update():
    """accept_cpu_bet must use a single atomic UPDATE ... WHERE caps_balance >= %s."""
    src = _function_source("accept_cpu_bet")
    assert src, "accept_cpu_bet function not found in app.py"
    src_upper = src.upper()
    assert "UPDATE PLAYERS SET CAPS_BALANCE" in src_upper, (
        "accept_cpu_bet does not have an atomic caps UPDATE statement — TOCTOU race not fixed"
    )
    assert "CAPS_BALANCE >=" in src_upper, (
        "accept_cpu_bet atomic UPDATE is missing WHERE caps_balance >= guard"
    )


def test_accept_cpu_bet_source_no_separate_select_for_caps():
    """accept_cpu_bet must NOT do a separate SELECT caps_balance before the UPDATE."""
    src = _function_source("accept_cpu_bet")
    assert src, "accept_cpu_bet function not found in app.py"
    src_upper = src.upper()
    select_caps_lines = [
        line for line in src_upper.splitlines()
        if "SELECT" in line and "CAPS_BALANCE" in line
    ]
    assert not select_caps_lines, (
        "accept_cpu_bet has a separate SELECT caps_balance — TOCTOU race remains:\n"
        + "\n".join(select_caps_lines)
    )


def test_accept_cpu_bet_source_checks_rowcount():
    """accept_cpu_bet must check cur.rowcount == 0 after the atomic UPDATE."""
    src = _function_source("accept_cpu_bet")
    assert src, "accept_cpu_bet function not found in app.py"
    assert "rowcount" in src, (
        "accept_cpu_bet does not check cur.rowcount after the atomic UPDATE"
    )
    assert "== 0" in src, (
        "accept_cpu_bet does not handle rowcount == 0 (insufficient caps path missing)"
    )


def test_accept_cpu_bet_insufficient_caps_returns_400(client):
    """POST /accept_cpu_bet/<id> when atomic UPDATE affects 0 rows → 400."""
    mock_cursor = MagicMock()
    # First fetchone: no existing cpu_acceptance for this player/bet → not already accepted
    # Second fetchone: the CPU bet row → (amount,)
    mock_cursor.fetchone.side_effect = [None, (75,)]
    # rowcount=0 on the atomic UPDATE (insufficient caps)
    mock_cursor.rowcount = 0
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/accept_cpu_bet/cpu-bet-xyz",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 400, (
        f"Expected 400 (insufficient caps via rowcount==0), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )
    data = response.get_json()
    assert data is not None and "caps" in data.get("error", "").lower(), (
        f"400 body should mention 'caps': {data}"
    )


def test_accept_cpu_bet_sufficient_caps_succeeds(client):
    """POST /accept_cpu_bet/<id> when atomic UPDATE affects 1 row → 200."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [None, (75,)]
    mock_cursor.rowcount = 1
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                "/accept_cpu_bet/cpu-bet-xyz",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200, (
        f"Expected 200 when atomic UPDATE succeeds (rowcount=1), "
        f"got {response.status_code}: {response.get_data(as_text=True)}"
    )


def test_accept_cpu_bet_no_auth_returns_401(client):
    """POST /accept_cpu_bet/<id> with no token → 401."""
    response = client.post("/accept_cpu_bet/cpu-bet-xyz")
    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}"
    )


# ===========================================================================
# Criterion (c) — debug log in accept_bet is after the auth guard
# ===========================================================================


def test_accept_bet_debug_log_after_auth_guard():
    """
    The debug log in accept_bet must not fire before auth is validated.

    With @token_required, auth is enforced before the function body runs, which
    satisfies the ordering requirement. If the function uses an inline auth guard
    ('if player_id is None') instead, it must come before the debug log.
    """
    src = _function_source("accept_bet")
    assert src, "accept_bet function not found in app.py"

    # If the function uses @token_required, auth precedes the function body entirely
    # — the debug log is guaranteed to fire only after auth succeeds.
    if _route_has_decorator("accept_bet", "token_required"):
        return

    # Fallback: inline guard check (pre-decorator style)
    lines = src.splitlines()
    auth_guard_lineno = None
    debug_log_lineno = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if auth_guard_lineno is None and re.search(r"if player_id is None", stripped):
            auth_guard_lineno = i
        if debug_log_lineno is None and re.search(r"logger\.debug.*player_id", stripped):
            debug_log_lineno = i

    if debug_log_lineno is None:
        # No debug log at all — acceptable (it could have been removed)
        return

    assert auth_guard_lineno is not None, (
        "accept_bet has no 'if player_id is None' auth guard and no @token_required — "
        "auth check is missing"
    )
    assert debug_log_lineno > auth_guard_lineno, (
        f"debug log (line {debug_log_lineno + 1} in function) appears BEFORE the auth guard "
        f"(line {auth_guard_lineno + 1} in function) — log can fire with player_id=None"
    )
