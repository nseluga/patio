"""
QA tests for item 0.8 — Fix camelCase column access breaking core reads.

Done when:
  - /pvp_bets returns 200 with real data (no camelCase KeyError)
  - /cpu_bets returns 200 with real data (no camelCase KeyError)
  - /ongoing_bets returns 200 with real data (no camelCase KeyError)
  - /me returns 200 with real data (no camelCase KeyError)
  - No camelCase `KeyError`/`column does not exist` remains in those paths

Strategy:
  (A) Static source analysis — verify that SELECT * was replaced with explicit
      quoted column lists and lowercase aliases in the four handlers.
  (B) Behavioral tests — mock the psycopg2 cursor to return rows keyed with the
      *aliased* lowercase column names (exactly as Postgres emits for aliased
      columns) and verify that each handler produces the expected JSON shape
      without KeyError / 500.
"""

import ast
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

os.environ.setdefault("SECRET_KEY", "test-secret-qa-0-8")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app as flask_app
from backend.auth import auth  # noqa: F401 — registers blueprint

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-0-8"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_PY = BACKEND_DIR / "app.py"
AUTH_PY = BACKEND_DIR / "auth.py"

# The lowercase aliases the SELECT queries must produce.
PVP_CPU_COLS = [
    "id", "poster", "posterid", "accepterid", "timeposted",
    "matchup", "amount", "linetype", "linenumber", "gametype",
    "gameplayed", "gamesize", "status",
]
ONGOING_COLS = PVP_CPU_COLS + [
    "yourteama", "yourteamb", "oppteama", "oppteamb",
    "yourscorea", "yourscoreb", "oppscorea", "oppscoreb",
    "yourplayer", "yourshots", "oppplayer", "oppshots",
    "youroutcome", "oppoutcome",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def _source(path: Path, func_name: str) -> str:
    """Return source of a top-level function by name."""
    text = path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return "\n".join(lines[node.lineno - 1: node.end_lineno])
    return ""


def make_description(colnames):
    """Produce a cursor.description-like list of (name,) tuples for the given column names."""
    return [(name,) for name in colnames]


def make_row(colnames, overrides=None):
    """Return a tuple of placeholder values for the given column list."""
    defaults = {
        "id": "bet-001",
        "poster": "alice",
        "posterid": 1,
        "accepterid": 2,
        "timeposted": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "matchup": "alice vs bob",
        "amount": 50,
        "linetype": "Over",
        "linenumber": 10.5,
        "gametype": "Score",
        "gameplayed": "Caps",
        "gamesize": 2,
        "status": "posted",
        "yourteama": None,
        "yourteamb": None,
        "oppteama": None,
        "oppteamb": None,
        "yourscorea": None,
        "yourscoreb": None,
        "oppscorea": None,
        "oppscoreb": None,
        "yourplayer": None,
        "yourshots": None,
        "oppplayer": None,
        "oppshots": None,
        "youroutcome": None,
        "oppoutcome": None,
    }
    if overrides:
        defaults.update(overrides)
    return tuple(defaults[c] for c in colnames)


def make_mock_conn(fetchall_return=None, description=None, fetchone_return=None):
    """Build a mock psycopg2 connection with a configurable cursor."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.description = description if description is not None else []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ===========================================================================
# (A) Static source analysis — no more SELECT *
# ===========================================================================


def test_pvp_bets_no_select_star():
    """get_pvp_bets must not use SELECT * — must use explicit column list."""
    src = _source(APP_PY, "get_pvp_bets")
    assert src, "get_pvp_bets not found in app.py"
    # Must not have a bare SELECT *
    assert "SELECT *" not in src, "get_pvp_bets still uses SELECT * — camelCase columns won't be aliased"


def test_pvp_bets_has_quoted_poster_id():
    """get_pvp_bets must quote \"posterId\" to avoid silent lowercasing by Postgres."""
    src = _source(APP_PY, "get_pvp_bets")
    assert '"posterId"' in src, 'get_pvp_bets missing "posterId" quoted identifier'


def test_pvp_bets_has_posterid_alias():
    """get_pvp_bets must alias \"posterId\" AS posterid so dict access works."""
    src = _source(APP_PY, "get_pvp_bets")
    assert "posterid" in src.lower(), "get_pvp_bets missing posterid lowercase alias"


def test_cpu_bets_no_select_star():
    """get_cpu_bets must not use SELECT *."""
    src = _source(APP_PY, "get_cpu_bets")
    assert src, "get_cpu_bets not found in app.py"
    assert "SELECT *" not in src, "get_cpu_bets still uses SELECT *"


def test_cpu_bets_has_quoted_identifiers():
    """get_cpu_bets must quote camelCase columns."""
    src = _source(APP_PY, "get_cpu_bets")
    for col in ('"posterId"', '"gameType"', '"timePosted"'):
        assert col in src, f"get_cpu_bets missing quoted identifier {col}"


def test_ongoing_bets_no_select_star():
    """get_ongoing_bets must not use SELECT * (in any UNION arm)."""
    src = _source(APP_PY, "get_ongoing_bets")
    assert src, "get_ongoing_bets not found in app.py"
    assert "SELECT *" not in src, "get_ongoing_bets still uses SELECT * in at least one UNION arm"


def test_ongoing_bets_has_three_union_arms():
    """get_ongoing_bets UNION query must have three SELECT arms (covers all ongoing bet types)."""
    src = _source(APP_PY, "get_ongoing_bets")
    # Count occurrences of SELECT inside the UNION query
    union_count = src.count("UNION")
    assert union_count >= 2, (
        f"get_ongoing_bets has {union_count} UNION keywords; expected 2 (three arms)"
    )


def test_auth_me_gametype_is_quoted():
    """auth.py /me must use quoted \"gameType\" AS gametype — not bare gametype."""
    text = AUTH_PY.read_text()
    # Bare unquoted `gametype` in a SELECT would fail on a case-sensitive Postgres column.
    # The fix must use the quoted form.
    assert '"gameType"' in text, 'auth.py is missing quoted "gameType" in the /me bets query'
    # And it must not have the bare unquoted form in the SELECT list context
    assert 'SELECT gametype,' not in text and 'SELECT gametype ' not in text, (
        "auth.py /me still selects bare unquoted `gametype` — must use \"gameType\" AS gametype"
    )


def test_auth_me_poster_id_where_is_quoted():
    """auth.py /me WHERE clause must use quoted \"posterId\" and \"accepterId\"."""
    text = AUTH_PY.read_text()
    assert '"posterId"' in text, 'auth.py missing quoted "posterId" in /me query'
    assert '"accepterId"' in text, 'auth.py missing quoted "accepterId" in /me query'


# ===========================================================================
# (B) Behavioral: /pvp_bets — returns 200 + correct shape, no KeyError
# ===========================================================================


def test_pvp_bets_200_with_real_row(client):
    """GET /pvp_bets: handler produces 200 + correct JSON shape from a mocked row."""
    desc = make_description(PVP_CPU_COLS)
    row = make_row(PVP_CPU_COLS, {"status": "posted"})
    mock_conn = make_mock_conn(fetchall_return=[row], description=desc)

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=2)
        resp = client.get("/pvp_bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert isinstance(data, list) and len(data) == 1, "Expected a list with one bet"
    bet = data[0]
    # Verify key shape — these are the camelCase output keys the frontend expects
    for key in ("id", "poster", "posterId", "timePosted", "matchup", "amount",
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize", "status"):
        assert key in bet, f"Response bet is missing key '{key}': {bet}"


def test_pvp_bets_empty_returns_200_list(client):
    """GET /pvp_bets with no matching bets: returns 200 and an empty list."""
    desc = make_description(PVP_CPU_COLS)
    mock_conn = make_mock_conn(fetchall_return=[], description=desc)

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/pvp_bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, f"Expected 200 for empty list, got {resp.status_code}"
    assert resp.get_json() == [], "Expected empty list"


def test_pvp_bets_no_jwt_401(client):
    """GET /pvp_bets without JWT → 401 (auth guard still intact after fix)."""
    resp = client.get("/pvp_bets")
    assert resp.status_code == 401


# ===========================================================================
# (C) Behavioral: /cpu_bets — returns 200 + correct shape, no KeyError
# ===========================================================================


def test_cpu_bets_200_with_real_row(client):
    """GET /cpu_bets: handler produces 200 + correct JSON shape from a mocked row."""
    desc = make_description(PVP_CPU_COLS)
    row = make_row(PVP_CPU_COLS, {"status": "CPU", "posterid": 0})
    mock_conn = make_mock_conn(fetchall_return=[row], description=desc)

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/cpu_bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert isinstance(data, list) and len(data) == 1
    bet = data[0]
    for key in ("id", "poster", "posterId", "timePosted", "matchup", "amount",
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize", "status"):
        assert key in bet, f"Response bet is missing key '{key}': {bet}"


def test_cpu_bets_no_jwt_401(client):
    """GET /cpu_bets without JWT → 401."""
    resp = client.get("/cpu_bets")
    assert resp.status_code == 401


# ===========================================================================
# (D) Behavioral: /ongoing_bets — returns 200 + correct shape, no KeyError
# ===========================================================================


def test_ongoing_bets_200_with_accepted_bet(client):
    """GET /ongoing_bets: handler produces 200 + correct JSON shape for an 'accepted' bet."""
    desc = make_description(ONGOING_COLS)
    row = make_row(ONGOING_COLS, {
        "status": "accepted",
        "posterid": 1,
        "accepterid": 2,
        "gametype": "Score",
    })

    # The cursor is used twice: once for the main UNION query, once inside
    # compute_status_message which opens a RealDictCursor on the same conn.
    # We patch get_db to return a conn whose cursor() returns different objects
    # on the first call (regular cursor) vs subsequent calls (RealDictCursor).
    main_cursor = MagicMock()
    main_cursor.fetchall.return_value = [row]
    main_cursor.description = desc

    # compute_status_message's inner cursor (RealDictCursor) — no cpu_acceptance row
    inner_cursor = MagicMock()
    inner_cursor.fetchone.return_value = None

    mock_conn = MagicMock()
    # First cursor() call → main_cursor; subsequent → inner_cursor (for compute_status_message)
    mock_conn.cursor.side_effect = [main_cursor, inner_cursor]

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/ongoing_bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert isinstance(data, list) and len(data) == 1
    bet = data[0]
    for key in ("id", "poster", "posterId", "accepterId", "timePosted", "matchup", "amount",
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize", "status",
                "status_message"):
        assert key in bet, f"Response bet is missing key '{key}': {bet}"


def test_ongoing_bets_empty_returns_200_list(client):
    """GET /ongoing_bets with no matching bets: returns 200 and an empty list."""
    main_cursor = MagicMock()
    main_cursor.fetchall.return_value = []
    main_cursor.description = make_description(ONGOING_COLS)

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = main_cursor

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/ongoing_bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_ongoing_bets_no_jwt_401(client):
    """GET /ongoing_bets without JWT → 401."""
    resp = client.get("/ongoing_bets")
    assert resp.status_code == 401


# ===========================================================================
# (E) Behavioral: /me — returns 200 + correct shape, no camelCase KeyError
# ===========================================================================


def test_me_200_with_bets(client):
    """GET /me: handler produces 200 with recent_bets populated using lowercase aliases."""
    # players row: (username, email, caps_balance, pvp_bets_played, pvp_bets_won)
    player_row = ("alice", "alice@example.com", 500, 3, 2)
    # recent_bets rows: tuples matching (gametype, status, amount, timeposted) positional select
    bet_row = ("Score", "accepted", 50, datetime(2024, 1, 1, tzinfo=timezone.utc))

    mock_cursor = MagicMock()
    # fetchone for players, fetchall for bets
    mock_cursor.fetchone.return_value = player_row
    mock_cursor.fetchall.return_value = [bet_row]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.auth.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, (
        f"Expected 200, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert "username" in data and data["username"] == "alice"
    assert "recent_bets" in data
    assert len(data["recent_bets"]) == 1
    rb = data["recent_bets"][0]
    assert rb["gameType"] == "Score", f"gameType missing or wrong: {rb}"
    assert rb["status"] == "accepted"
    assert rb["amount"] == 50
    assert "timePosted" in rb


def test_me_200_empty_bets(client):
    """GET /me: returns 200 with empty recent_bets list when user has no bets."""
    player_row = ("bob", "bob@example.com", 200, 0, 0)
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = player_row
    mock_cursor.fetchall.return_value = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.auth.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=2)
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["recent_bets"] == []


def test_me_no_jwt_401(client):
    """GET /me without JWT → 401."""
    resp = client.get("/me")
    assert resp.status_code == 401


# ===========================================================================
# (F) No-KeyError regression: simulate what the old SELECT * would have caused
# ===========================================================================


def test_pvp_bets_no_keyerror_on_camelcase_keys():
    """Regression: old SELECT * returned camelCase keys; new code must handle lowercase aliases.

    Simulate the old broken scenario (dict with camelCase keys) and confirm the
    current handler code does NOT use camelCase key access on bet dicts that
    come from the cursor — it uses lowercase aliases.
    """
    src = _source(APP_PY, "get_pvp_bets")
    # If the handler still accessed camelCase dict keys it would look like bet["gameType"]
    # (double-quoted key access) — that's a KeyError with aliased lowercase columns.
    broken_accesses = [
        'bet["gameType"]', 'bet["posterId"]', 'bet["timePosted"]',
        'bet["lineType"]', 'bet["lineNumber"]', 'bet["gamePlayed"]', 'bet["gameSize"]',
    ]
    for bad in broken_accesses:
        assert bad not in src, (
            f"get_pvp_bets still accesses bet dict with camelCase key {bad!r} — "
            f"must use lowercase alias instead"
        )


def test_cpu_bets_no_keyerror_on_camelcase_keys():
    """Same regression check for get_cpu_bets."""
    src = _source(APP_PY, "get_cpu_bets")
    broken_accesses = [
        'bet["gameType"]', 'bet["posterId"]', 'bet["timePosted"]',
        'bet["lineType"]', 'bet["lineNumber"]', 'bet["gamePlayed"]', 'bet["gameSize"]',
    ]
    for bad in broken_accesses:
        assert bad not in src, (
            f"get_cpu_bets still accesses bet dict with camelCase key {bad!r}"
        )


def test_ongoing_bets_no_keyerror_on_camelcase_keys():
    """Same regression check for get_ongoing_bets."""
    src = _source(APP_PY, "get_ongoing_bets")
    broken_accesses = [
        'bet["gameType"]', 'bet["posterId"]', 'bet["timePosted"]',
        'bet["lineType"]', 'bet["lineNumber"]', 'bet["gamePlayed"]', 'bet["gameSize"]',
    ]
    for bad in broken_accesses:
        assert bad not in src, (
            f"get_ongoing_bets still accesses bet dict with camelCase key {bad!r}"
        )
