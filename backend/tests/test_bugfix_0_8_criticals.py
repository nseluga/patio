"""
Re-verification tests for item 0.8 Bug Fixer pass (commit f3a0812).

Covers the two Critical findings applied by the Bug Fixer that were not
explicitly tested in test_camelcase_fix_0_8.py:

  Critical-1: submit_stats dynamic UPDATE SET clause must quote camelCase
               column names so Postgres does not fold them to lowercase.
  Critical-2: get_all_bets WHERE clause must use "posterId"/"accepterId"
               (quoted) not the bare unquoted names.

Also covers the two Important findings (accept_bet SELECT alias, dead guard).
"""

import ast
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret-qa-0-8b")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app as flask_app
from backend.auth import auth  # noqa: F401 — registers blueprint

TEST_SECRET = "test-secret-qa-0-8b"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_PY = REPO_ROOT / "backend" / "app.py"


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def _source(func_name: str) -> str:
    text = APP_PY.read_text()
    tree = ast.parse(text)
    lines = text.splitlines()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return "\n".join(lines[node.lineno - 1: node.end_lineno])
    return ""


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ===========================================================================
# Critical-1: submit_stats dynamic UPDATE SET uses quoted camelCase columns
# ===========================================================================


def test_submit_stats_score_update_fields_are_quoted():
    """submit_stats update_fields for Score gametype must use double-quoted column names."""
    src = _source("submit_stats")
    assert src, "submit_stats not found in app.py"
    # All four Score columns must appear as quoted strings inside the list
    for col in ('"yourTeamA"', '"yourTeamB"', '"yourScoreA"', '"yourScoreB"',
                '"oppTeamA"', '"oppTeamB"', '"oppScoreA"', '"oppScoreB"'):
        assert col in src, (
            f"submit_stats missing quoted column {col} in update_fields — "
            f"Postgres will fold unquoted names to lowercase and hit the wrong column"
        )


def test_submit_stats_shots_made_update_fields_are_quoted():
    """submit_stats update_fields for Shots Made gametype must use quoted column names."""
    src = _source("submit_stats")
    for col in ('"yourPlayer"', '"oppPlayer"', '"yourShots"', '"oppShots"'):
        assert col in src, (
            f"submit_stats missing quoted column {col} in update_fields for Shots Made"
        )


def test_submit_stats_other_update_fields_are_quoted():
    """submit_stats update_fields for Other gametype must use quoted column names."""
    src = _source("submit_stats")
    for col in ('"yourOutcome"', '"oppOutcome"'):
        assert col in src, (
            f"submit_stats missing quoted column {col} in update_fields for Other"
        )


def test_submit_stats_set_clause_builds_from_update_fields():
    """The SET clause f-string must interpolate the quoted field names directly."""
    src = _source("submit_stats")
    # The fix puts quoted identifiers into update_fields and uses
    # f"{field} = %s" in the set_clause join. If they were instead passed
    # as bare strings (like 'yourTeamA') the bug would still be present.
    # Check that the f-string expansion pattern is present.
    assert 'f"{field} = %s"' in src or "f'{field} = %s'" in src, (
        "submit_stats set_clause does not use f'{field} = %s' — "
        "UPDATE SET generation pattern has changed"
    )


def test_submit_stats_no_bare_unquoted_camelcase_in_update_fields():
    """submit_stats must NOT have unquoted camelCase column names in update_fields lists."""
    src = _source("submit_stats")
    # Unquoted appearance would look like: update_fields += ["yourTeamA", ...]
    # i.e., a plain string literal without the leading '"' inside the list.
    # We look for the pre-fix pattern: a string that is exactly the column name
    # with no inner double-quotes (e.g. '"yourTeamA"' is fine, '"yourTeamA"' is fine,
    # but 'yourTeamA' without the inner quotes is the bug).
    bare_pattern = re.compile(
        r"""update_fields\s*\+=\s*\[['"](?!")[a-z]""", re.IGNORECASE
    )
    # The pattern after the fix always starts with a leading '"' inside the string:
    # '"yourTeamA"' — so the character after the opening quote is '"'.
    # If we find a string that starts with a lowercase letter (not '"'), it's unquoted.
    matches = bare_pattern.findall(src)
    assert not matches, (
        f"submit_stats has unquoted camelCase column name in update_fields: {matches}"
    )


# ===========================================================================
# Critical-2: get_all_bets WHERE uses quoted "posterId"/"accepterId"
# ===========================================================================


def test_get_all_bets_where_uses_quoted_poster_id():
    """get_all_bets WHERE must use quoted \"posterId\", not bare posterid."""
    src = _source("get_all_bets")
    assert src, "get_all_bets not found in app.py"
    assert '"posterId"' in src, (
        'get_all_bets WHERE clause is missing quoted "posterId" — '
        'Postgres treats the unquoted form as lowercase and matches nothing'
    )


def test_get_all_bets_where_uses_quoted_accepter_id():
    """get_all_bets WHERE must use quoted \"accepterId\", not bare accepterid."""
    src = _source("get_all_bets")
    assert '"accepterId"' in src, (
        'get_all_bets WHERE clause is missing quoted "accepterId"'
    )


def test_get_all_bets_order_by_uses_quoted_time_posted():
    """get_all_bets ORDER BY must use quoted \"timePosted\"."""
    src = _source("get_all_bets")
    assert '"timePosted"' in src, (
        'get_all_bets ORDER BY is missing quoted "timePosted"'
    )


def test_get_all_bets_no_bare_posterid_in_where():
    """get_all_bets must NOT use the bare unquoted 'posterid' in its WHERE clause."""
    src = _source("get_all_bets")
    # bare (unquoted) form would appear as: WHERE posterid = %s
    # After quoting it becomes: WHERE "posterId" = %s
    # Check that the bare unquoted form (no surrounding double-quotes) does NOT appear.
    assert 'WHERE posterid' not in src and 'OR accepterid' not in src, (
        "get_all_bets still has unquoted 'posterid' or 'accepterid' in WHERE — "
        "this caused the silent empty-result bug"
    )


def test_get_all_bets_returns_200_with_mocked_data(client):
    """GET /bets: returns 200 with a list when caller is matched by quoted column WHERE."""
    # Use a raw cursor (not RealDictCursor) since get_all_bets uses fetchall + description
    colnames = ["id", "poster", "posterId", "accepterId", "timePosted", "matchup",
                "amount", "lineType", "lineNumber", "gameType", "gamePlayed",
                "gameSize", "status"]
    description = [(name,) for name in colnames]
    row = ("bet-001", "alice", 1, 2, "2024-01-01", "alice vs bob", 50,
           "Over", 10.5, "Score", "Caps", 2, "accepted")

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [row]
    mock_cursor.description = description
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("backend.app.get_db", return_value=mock_conn), \
         patch("backend.app.SECRET_KEY", TEST_SECRET):
        token = make_jwt(player_id=1)
        resp = client.get("/bets", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200, (
        f"Expected 200 from /bets, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert isinstance(data, list) and len(data) == 1, "Expected list with one bet"
    assert data[0]["id"] == "bet-001"


def test_get_all_bets_no_auth_returns_401(client):
    """GET /bets without JWT → 401."""
    resp = client.get("/bets")
    assert resp.status_code == 401


# ===========================================================================
# Important-1: accept_bet SELECT aliases "posterId" AS posterid
# ===========================================================================


def test_accept_bet_select_uses_quoted_poster_id_alias():
    """accept_bet SELECT must quote \"posterId\" AS posterid — prevents 'column does not exist'."""
    src = _source("accept_bet")
    assert src, "accept_bet not found in app.py"
    assert '"posterId" AS posterid' in src or '"posterId"' in src, (
        'accept_bet SELECT is missing quoted "posterId" — '
        "this causes a runtime error on every PvP bet acceptance"
    )


def test_accept_bet_update_uses_quoted_accepter_id():
    """accept_bet UPDATE SET must use quoted \"accepterId\"."""
    src = _source("accept_bet")
    assert '"accepterId"' in src, (
        'accept_bet UPDATE SET missing quoted "accepterId" — '
        "Postgres will try to set the wrong (lowercase) column"
    )


# ===========================================================================
# Important-2: dead boolean guard in compute_status_message is fixed
# ===========================================================================


def test_compute_status_message_guard_is_not_is_none_form():
    """compute_status_message guard must NOT use the '(x or y) is None' dead-code form."""
    src = _source("compute_status_message")
    assert src, "compute_status_message not found in app.py"
    assert "(is_poster or is_accepter) is None" not in src, (
        "compute_status_message still uses the dead-code guard "
        "'(is_poster or is_accepter) is None' — always evaluates to False, "
        "so 'Unknown user' branch was unreachable"
    )


def test_compute_status_message_guard_is_not_is_not_none_form():
    """compute_status_message guard must use 'not is_poster and not is_accepter'."""
    src = _source("compute_status_message")
    assert "not is_poster and not is_accepter" in src, (
        "compute_status_message does not contain the corrected guard "
        "'not is_poster and not is_accepter'"
    )
