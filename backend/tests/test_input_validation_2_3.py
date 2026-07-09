"""
QA tests for item 2.3 — Input validation layer.

Done when:
  - Mutating routes reject malformed payloads with 400 + consistent JSON {"error": "..."}
  - No KeyError/ValueError/IndexError from input parsing reaches the client as a 500

Gate mode: tests+behavioral (Flask test client with mocked DB)

Criteria:
  1. /register missing username → 400
  2. /login missing email → 400
  3. /submit_stats with non-numeric yourScoreA → 400
  4. /submit_stats with missing yourPlayer (Shots Made game) → 400
  5. /cpu/* with gameSize="" → 400
  6. /create_bet missing matchup → 400
  7. All existing 272 tests must pass (verified by running this file in context)

Tests use Flask test client with mocked DB — no live Postgres connection required.
"""

import os

# Set env vars before any backend module is imported so config.py picks them up.
os.environ.setdefault("SECRET_KEY", "test-secret-qa-2-3")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import json
from unittest.mock import MagicMock, patch

import jwt
import pytest

from backend.app import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-2-3"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def make_mock_conn(fetchone_return=None, fetchall_return=None):
    """Build a mock DB connection with configurable return values."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    mock_cursor.description = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def _assert_400_json(response, *, context: str):
    """Assert status=400 and body is JSON with an 'error' key."""
    assert response.status_code == 400, (
        f"{context}: expected 400, got {response.status_code}: "
        f"{response.get_data(as_text=True)}"
    )
    data = response.get_json()
    assert data is not None, f"{context}: response body is not valid JSON"
    assert "error" in data, (
        f"{context}: JSON response is missing 'error' key — got: {data}"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ===========================================================================
# Criterion 1 — /register: missing username → 400
# ===========================================================================


class TestRegisterValidation:
    """Criterion 1: /register rejects missing required fields with 400."""

    def test_register_missing_username_returns_400(self, client):
        """/register with email + password but no username → 400."""
        response = client.post(
            "/register",
            json={"email": "test@example.com", "password": "secret123"},
        )
        _assert_400_json(response, context="/register missing username")

    def test_register_missing_email_returns_400(self, client):
        """/register with username + password but no email → 400."""
        response = client.post(
            "/register",
            json={"username": "alice", "password": "secret123"},
        )
        _assert_400_json(response, context="/register missing email")

    def test_register_missing_password_returns_400(self, client):
        """/register with username + email but no password → 400."""
        response = client.post(
            "/register",
            json={"username": "alice", "email": "test@example.com"},
        )
        _assert_400_json(response, context="/register missing password")

    def test_register_empty_body_returns_400(self, client):
        """/register with an empty body → 400 (not 500 from KeyError)."""
        response = client.post("/register", json={})
        _assert_400_json(response, context="/register empty body")

    def test_register_no_body_returns_400(self, client):
        """/register with no body at all → 400 (not 500 or 415)."""
        response = client.post(
            "/register",
            data="",
            content_type="application/json",
        )
        _assert_400_json(response, context="/register no body")

    def test_register_null_username_returns_400(self, client):
        """/register with username=null → 400 (null treated as missing)."""
        response = client.post(
            "/register",
            json={"username": None, "email": "test@example.com", "password": "secret123"},
        )
        _assert_400_json(response, context="/register null username")

    def test_register_validation_module_accepts_complete_payload(self):
        """require_fields called with all /register fields returns (data, None) — no 400 guard fires.

        Source-level check: confirms that a complete payload passes the validation
        logic without touching the rate limiter or DB.
        """
        from backend.validation import require_fields

        with app.app_context():
            data = {"username": "alice", "email": "alice@example.com", "password": "secret123"}
            result, err = require_fields(data, "username", "email", "password")
        assert err is None, f"require_fields rejected a complete /register payload: {err}"
        assert result is data


# ===========================================================================
# Criterion 2 — /login: missing email → 400
# ===========================================================================


class TestLoginValidation:
    """Criterion 2: /login rejects missing required fields with 400."""

    def test_login_missing_email_returns_400(self, client):
        """/login with password but no email → 400."""
        response = client.post(
            "/login",
            json={"password": "secret123"},
        )
        _assert_400_json(response, context="/login missing email")

    def test_login_missing_password_returns_400(self, client):
        """/login with email but no password → 400."""
        response = client.post(
            "/login",
            json={"email": "alice@example.com"},
        )
        _assert_400_json(response, context="/login missing password")

    def test_login_empty_body_returns_400(self, client):
        """/login with empty body → 400 (not 500 from KeyError)."""
        response = client.post("/login", json={})
        _assert_400_json(response, context="/login empty body")

    def test_login_no_body_returns_400(self, client):
        """/login with no body → 400."""
        response = client.post(
            "/login",
            data="",
            content_type="application/json",
        )
        _assert_400_json(response, context="/login no body")

    def test_login_null_email_returns_400(self, client):
        """/login with email=null → 400 (null treated as missing)."""
        response = client.post(
            "/login",
            json={"email": None, "password": "secret123"},
        )
        _assert_400_json(response, context="/login null email")

    def test_login_validation_module_accepts_complete_payload(self):
        """require_fields called with all /login fields returns (data, None) — no 400 guard fires.

        Source-level check: confirms that a complete payload passes the validation
        logic without touching the rate limiter or DB.
        """
        from backend.validation import require_fields

        with app.app_context():
            data = {"email": "alice@example.com", "password": "secret123"}
            result, err = require_fields(data, "email", "password")
        assert err is None, f"require_fields rejected a complete /login payload: {err}"
        assert result is data


# ===========================================================================
# Criterion 3 — /submit_stats: non-numeric yourScoreA → 400
# ===========================================================================


class TestSubmitStatsNonNumericScore:
    """Criterion 3: submit_stats with non-numeric score fields → 400.

    IMPLEMENTATION FINDING: The CPU path (status='CPU') uses coerce_int to validate
    yourScoreA/yourScoreB and correctly returns 400 on non-numeric input.
    The PvP path (status='accepted') only calls require_fields (presence check) but
    does NOT call coerce_int — non-numeric values are passed to the DB UPDATE as-is.
    This is a code gap: PvP non-numeric scores do NOT currently → 400.

    These tests verify the CPU path (which is implemented correctly) and expose
    the PvP gap as a FAIL (tests 1 and 2 below).
    """

    def _make_pvp_score_bet(self):
        """PvP (non-CPU) Score bet — the path that lacks coerce_int."""
        return {
            "id": "bet-score-001",
            "posterid": 1,
            "accepterid": 2,
            "status": "accepted",   # PvP path
            "gametype": "Score",
            "gameplayed": "Caps",
            "gamesize": "2v2",
            "linenumber": 10.5,
            "linetype": "Over",
            "amount": 50,
            "yourteama": ["alice", "bob"],
            "yourteamb": ["charlie", "dave"],
            "oppteama": None,
            "oppteamb": None,
            "yourscorea": None,
            "yourscoreb": None,
            "oppscorea": None,
            "oppscoreb": None,
            "yourplayer": None,
            "oppplayer": None,
            "yourshots": None,
            "oppshots": None,
            "youroutcome": None,
            "oppoutcome": None,
            "poster": "alice",
        }

    def _make_cpu_score_bet(self):
        """CPU Score bet — the path that correctly uses coerce_int."""
        return {
            "id": "bet-cpu-score-001",
            "posterid": 0,        # House
            "accepterid": 1,
            "status": "CPU",      # CPU path
            "gametype": "Score",
            "gameplayed": "Caps",
            "gamesize": "2v2",
            "linenumber": 10.5,
            "linetype": "Over",
            "amount": 50,
            "yourteama": ["alice", "bob"],
            "yourteamb": ["charlie", "dave"],
            "oppteama": None,
            "oppteamb": None,
            "yourscorea": 7,
            "yourscoreb": 5,
            "oppscorea": None,
            "oppscoreb": None,
            "yourplayer": None,
            "oppplayer": None,
            "yourshots": None,
            "oppshots": None,
            "youroutcome": None,
            "oppoutcome": None,
            "poster": "house",
        }

    def test_submit_stats_pvp_non_numeric_yourScoreA_returns_400(self, client):
        """/submit_stats PvP Score bet with yourScoreA='abc' → 400 (not 500/ValueError).

        EXPECTED FAIL: PvP path missing coerce_int — non-numeric score not rejected.
        This test exposes the code gap (criterion 3 not fully met on PvP path).
        """
        bet = self._make_pvp_score_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [bet, bet]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-score-001",
                    json={
                        "yourTeamA": ["alice", "bob"],
                        "yourTeamB": ["charlie", "dave"],
                        "yourScoreA": "abc",      # non-numeric
                        "yourScoreB": 5,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
        _assert_400_json(response, context="/submit_stats PvP non-numeric yourScoreA")

    def test_submit_stats_pvp_non_numeric_yourScoreB_returns_400(self, client):
        """/submit_stats PvP Score bet with yourScoreB='not-a-number' → 400.

        EXPECTED FAIL: PvP path missing coerce_int — non-numeric score not rejected.
        """
        bet = self._make_pvp_score_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [bet, bet]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-score-001",
                    json={
                        "yourTeamA": ["alice", "bob"],
                        "yourTeamB": ["charlie", "dave"],
                        "yourScoreA": 7,
                        "yourScoreB": "not-a-number",  # non-numeric
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
        _assert_400_json(response, context="/submit_stats PvP non-numeric yourScoreB")

    def test_submit_stats_cpu_non_numeric_yourScoreA_returns_400(self, client):
        """/submit_stats CPU Score bet with yourScoreA='abc' → 400 (CPU path uses coerce_int)."""
        bet = self._make_cpu_score_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = bet
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)  # accepter of the CPU bet
                response = client.post(
                    "/submit_stats/bet-cpu-score-001",
                    json={
                        "yourTeamA": ["alice", "bob"],
                        "yourTeamB": ["charlie", "dave"],
                        "yourScoreA": "abc",      # non-numeric — CPU path must → 400
                        "yourScoreB": 5,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
        _assert_400_json(response, context="/submit_stats CPU non-numeric yourScoreA")

    def test_submit_stats_numeric_scores_pass_validation(self, client):
        """/submit_stats PvP Score bet with valid integer scores does NOT return 400."""
        bet = self._make_pvp_score_bet()
        # After first SELECT, route UPDATEs then does a second SELECT
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [bet, bet]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-score-001",
                    json={
                        "yourTeamA": ["alice", "bob"],
                        "yourTeamB": ["charlie", "dave"],
                        "yourScoreA": 7,
                        "yourScoreB": 5,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code != 400, (
            f"/submit_stats valid score payload got 400: {response.get_data(as_text=True)}"
        )


# ===========================================================================
# Criterion 4 — /submit_stats: missing yourPlayer (Shots Made) → 400
# ===========================================================================


class TestSubmitStatsMissingPlayer:
    """Criterion 4: submit_stats Shots Made with missing yourPlayer → 400."""

    def _make_shots_bet(self):
        return {
            "id": "bet-shots-001",
            "posterid": 1,
            "accepterid": 2,
            "status": "accepted",
            "gametype": "Shots Made",
            "gameplayed": "Caps",
            "gamesize": "1v1",
            "linenumber": 8.5,
            "linetype": "Over",
            "amount": 50,
            "yourteama": None,
            "yourteamb": None,
            "oppteama": None,
            "oppteamb": None,
            "yourscorea": None,
            "yourscoreb": None,
            "oppscorea": None,
            "oppscoreb": None,
            "yourplayer": None,
            "oppplayer": None,
            "yourshots": None,
            "oppshots": None,
            "youroutcome": None,
            "oppoutcome": None,
            "poster": "alice",
        }

    def test_submit_stats_missing_yourPlayer_shots_game_returns_400(self, client):
        """/submit_stats Shots Made missing yourPlayer → 400."""
        bet = self._make_shots_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = bet
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-shots-001",
                    json={"yourShots": 9},  # missing yourPlayer
                    headers={"Authorization": f"Bearer {token}"},
                )
        _assert_400_json(response, context="/submit_stats missing yourPlayer (Shots Made)")

    def test_submit_stats_missing_yourShots_shots_game_returns_400(self, client):
        """/submit_stats Shots Made missing yourShots → 400."""
        bet = self._make_shots_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = bet
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-shots-001",
                    json={"yourPlayer": "alice"},  # missing yourShots
                    headers={"Authorization": f"Bearer {token}"},
                )
        _assert_400_json(response, context="/submit_stats missing yourShots (Shots Made)")

    def test_submit_stats_missing_body_returns_400(self, client):
        """/submit_stats with no body at all → 400 (not 500 from data=None).

        Note: @token_required fires before the body guard, so a valid JWT must be
        present for the body check to be reached.  A valid JWT is included here.
        The body guard fires before get_db() so no DB mock is needed.
        """
        bet = self._make_shots_bet()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = bet
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                response = client.post(
                    "/submit_stats/bet-shots-001",
                    data="",
                    content_type="application/json",
                    headers={"Authorization": f"Bearer {make_jwt(1)}"},
                )
        _assert_400_json(response, context="/submit_stats no body")

    def test_submit_stats_valid_shots_payload_not_400(self, client):
        """/submit_stats Shots Made with both yourPlayer + yourShots → NOT 400."""
        bet = self._make_shots_bet()
        updated = dict(bet)
        updated["yourplayer"] = "alice"
        updated["yourshots"] = 9
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [bet, updated]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                response = client.post(
                    "/submit_stats/bet-shots-001",
                    json={"yourPlayer": "alice", "yourShots": 9},
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert response.status_code != 400, (
            f"/submit_stats valid shots payload got 400: {response.get_data(as_text=True)}"
        )


# ===========================================================================
# Criterion 5 — /cpu/* with gameSize="" → 400
# ===========================================================================


class TestCpuRoutesGameSizeValidation:
    """Criterion 5: CPU creation routes reject gameSize="" with 400."""

    CPU_ROUTES = [
        "/cpu/create_caps_shots_bet",
        "/cpu/create_caps_score_bet",
        "/cpu/create_pong_shots_bet",
        "/cpu/create_pong_score_bet",
        "/cpu/create_beerball_shots_bet",
        "/cpu/create_beerball_score_bet",
    ]

    def _cpu_token(self):
        """Return a JWT for player_id=0 (the House / CPU account)."""
        return make_jwt(player_id=0)

    def test_empty_string_gameSize_rejected_on_caps_shots(self, client):
        """/cpu/create_caps_shots_bet with gameSize="" → 400 (not IndexError 500)."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_caps_shots_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_caps_shots_bet gameSize=''")

    def test_empty_string_gameSize_rejected_on_caps_score(self, client):
        """/cpu/create_caps_score_bet with gameSize="" → 400."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_caps_score_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_caps_score_bet gameSize=''")

    def test_empty_string_gameSize_rejected_on_pong_shots(self, client):
        """/cpu/create_pong_shots_bet with gameSize="" → 400."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_pong_shots_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_pong_shots_bet gameSize=''")

    def test_empty_string_gameSize_rejected_on_pong_score(self, client):
        """/cpu/create_pong_score_bet with gameSize="" → 400."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_pong_score_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_pong_score_bet gameSize=''")

    def test_empty_string_gameSize_rejected_on_beerball_shots(self, client):
        """/cpu/create_beerball_shots_bet with gameSize="" → 400."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_beerball_shots_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_beerball_shots_bet gameSize=''")

    def test_empty_string_gameSize_rejected_on_beerball_score(self, client):
        """/cpu/create_beerball_score_bet with gameSize="" → 400."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_beerball_score_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_beerball_score_bet gameSize=''")

    def test_non_digit_gameSize_rejected(self, client):
        """/cpu/create_caps_shots_bet with gameSize='xyz' → 400 (not digit prefix)."""
        token = self._cpu_token()
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_caps_shots_bet",
                json={"gameSize": "xyz"},
                headers={"Authorization": f"Bearer {token}"},
            )
        _assert_400_json(response, context="/cpu/create_caps_shots_bet gameSize='xyz'")

    def test_valid_gameSize_passes_validation_guard(self, client):
        """/cpu/create_caps_shots_bet with gameSize='1v1' passes the gameSize guard (not a 400)."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # empty players list → "Not enough players" 400, not gameSize 400
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        token = self._cpu_token()
        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                response = client.post(
                    "/cpu/create_caps_shots_bet",
                    json={"gameSize": "1v1"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        # The gameSize guard must not fire ("Invalid gameSize" not in response)
        body = response.get_data(as_text=True)
        assert "Invalid gameSize" not in body, (
            f"/cpu/create_caps_shots_bet valid gameSize='1v1' triggered gameSize error: {body}"
        )


# ===========================================================================
# Criterion 6 — /create_bet: missing matchup → 400
# ===========================================================================


class TestCreateBetValidation:
    """Criterion 6: /create_bet rejects missing required fields with 400."""

    def _auth_headers(self, player_id: int = 1):
        return {"Authorization": f"Bearer {make_jwt(player_id)}"}

    def _full_payload(self):
        return {
            "matchup": "alice vs bob",
            "gameType": "Shots Made",
            "gamePlayed": "Caps",
            "gameSize": "1v1",
            "amount": 50,
            "lineType": "Over",
            "lineNumber": 8.5,
        }

    def test_create_bet_missing_matchup_returns_400(self, client):
        """/create_bet with no matchup field → 400."""
        payload = self._full_payload()
        del payload["matchup"]

        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json=payload,
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet missing matchup")

    def test_create_bet_missing_gameType_returns_400(self, client):
        """/create_bet with no gameType field → 400."""
        payload = self._full_payload()
        del payload["gameType"]

        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json=payload,
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet missing gameType")

    def test_create_bet_missing_gamePlayed_returns_400(self, client):
        """/create_bet with no gamePlayed field → 400."""
        payload = self._full_payload()
        del payload["gamePlayed"]

        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json=payload,
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet missing gamePlayed")

    def test_create_bet_missing_gameSize_returns_400(self, client):
        """/create_bet with no gameSize field → 400."""
        payload = self._full_payload()
        del payload["gameSize"]

        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json=payload,
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet missing gameSize")

    def test_create_bet_empty_body_returns_400(self, client):
        """/create_bet with empty body → 400 (not 500 from KeyError)."""
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json={},
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet empty body")

    def test_create_bet_null_matchup_returns_400(self, client):
        """/create_bet with matchup=null → 400 (null treated as missing)."""
        payload = self._full_payload()
        payload["matchup"] = None

        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json=payload,
                headers=self._auth_headers(),
            )
        _assert_400_json(response, context="/create_bet null matchup")

    def test_create_bet_valid_payload_not_400(self, client):
        """/create_bet with all required fields does NOT return 400."""
        player_row = ("alice",)  # (username,) from SELECT username FROM players
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = player_row
        mock_cursor.rowcount = 1  # caps debit succeeds
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                response = client.post(
                    "/create_bet",
                    json=self._full_payload(),
                    headers=self._auth_headers(),
                )
        assert response.status_code != 400, (
            f"/create_bet valid payload got 400: {response.get_data(as_text=True)}"
        )


# ===========================================================================
# Criterion 7 — validate.py unit tests (pure function, no HTTP layer)
# ===========================================================================


class TestValidationHelpers:
    """Unit tests for the validation.py pure helpers — no Flask context needed."""

    def test_require_fields_returns_data_when_all_present(self):
        """require_fields returns (data, None) when all fields present."""
        from backend.validation import require_fields

        # Need a Flask app context for jsonify
        with app.app_context():
            data = {"a": 1, "b": "hello"}
            result_data, err = require_fields(data, "a", "b")
        assert err is None
        assert result_data is data

    def test_require_fields_returns_error_on_missing_field(self):
        """require_fields returns (None, (response, 400)) when a field is missing."""
        from backend.validation import require_fields

        with app.app_context():
            data = {"a": 1}
            result_data, err = require_fields(data, "a", "b")
        assert result_data is None
        assert err is not None
        resp, code = err
        assert code == 400
        body = resp.get_json()
        assert "error" in body
        assert "b" in body["error"]

    def test_require_fields_null_value_treated_as_missing(self):
        """require_fields treats a field sent as None as missing."""
        from backend.validation import require_fields

        with app.app_context():
            data = {"username": None, "email": "x@x.com", "password": "pw"}
            result_data, err = require_fields(data, "username", "email", "password")
        assert err is not None
        resp, code = err
        assert code == 400

    def test_require_fields_empty_data_returns_error(self):
        """require_fields on an empty dict returns error."""
        from backend.validation import require_fields

        with app.app_context():
            result_data, err = require_fields({}, "field")
        # Empty dict is falsy → "Request body required" path
        assert err is not None
        resp, code = err
        assert code == 400

    def test_require_fields_none_data_returns_error(self):
        """require_fields on None data (missing body) returns error."""
        from backend.validation import require_fields

        with app.app_context():
            result_data, err = require_fields(None, "field")
        assert err is not None
        resp, code = err
        assert code == 400

    def test_coerce_int_valid_int_returns_value(self):
        """coerce_int('5', 'field') → (5, None)."""
        from backend.validation import coerce_int

        with app.app_context():
            val, err = coerce_int("5", "score")
        assert val == 5
        assert err is None

    def test_coerce_int_integer_input_returns_value(self):
        """coerce_int(5, 'field') — integer input passes through."""
        from backend.validation import coerce_int

        with app.app_context():
            val, err = coerce_int(5, "score")
        assert val == 5
        assert err is None

    def test_coerce_int_non_numeric_returns_error(self):
        """coerce_int('abc', 'score') → (None, (response, 400))."""
        from backend.validation import coerce_int

        with app.app_context():
            val, err = coerce_int("abc", "yourScoreA")
        assert val is None
        assert err is not None
        resp, code = err
        assert code == 400
        body = resp.get_json()
        assert "error" in body
        assert "yourScoreA" in body["error"]

    def test_coerce_int_none_returns_error(self):
        """coerce_int(None, 'field') → 400 (TypeError caught)."""
        from backend.validation import coerce_int

        with app.app_context():
            val, err = coerce_int(None, "field")
        assert err is not None
        _, code = err
        assert code == 400

    def test_coerce_int_float_string_returns_error(self):
        """coerce_int('3.14', 'field') → 400 (float strings are not valid ints)."""
        from backend.validation import coerce_int

        with app.app_context():
            val, err = coerce_int("3.14", "field")
        assert err is not None
        _, code = err
        assert code == 400


# ===========================================================================
# No-500 smoke tests — spot-check that validation errors never reach client as 500
# ===========================================================================


class TestNo500OnBadInput:
    """Confirm that malformed inputs return 4xx, never 500."""

    def test_register_bad_input_not_500(self, client):
        response = client.post("/register", json={"username": "only-field"})
        assert response.status_code != 500, (
            f"/register bad input returned 500: {response.get_data(as_text=True)}"
        )

    def test_login_bad_input_not_500(self, client):
        response = client.post("/login", json={})
        assert response.status_code != 500, (
            f"/login empty body returned 500: {response.get_data(as_text=True)}"
        )

    def test_create_bet_empty_body_not_500(self, client):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/create_bet",
                json={},
                headers={"Authorization": f"Bearer {make_jwt(1)}"},
            )
        assert response.status_code != 500, (
            f"/create_bet empty body returned 500: {response.get_data(as_text=True)}"
        )

    def test_cpu_route_empty_string_gameSize_not_500(self, client):
        with patch("backend.app.SECRET_KEY", TEST_SECRET):
            response = client.post(
                "/cpu/create_caps_shots_bet",
                json={"gameSize": ""},
                headers={"Authorization": f"Bearer {make_jwt(0)}"},
            )
        assert response.status_code != 500, (
            f"/cpu/create_caps_shots_bet gameSize='' returned 500: {response.get_data(as_text=True)}"
        )
