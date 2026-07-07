"""
QA tests for item 0.1: /submit_stats/<bet_id> auth check.

Done when:
  - A request with a forged playerId (in body) and another user's valid JWT
    is rejected with 401 or 403.
  - The stat submission still works correctly for the legitimate player on the bet.

These tests exercise the Flask test client (behavioral path) with a mocked DB
so no live Postgres connection is required.
"""

import os

# Set env vars before any backend module is imported so config.py picks them up.
os.environ['SECRET_KEY'] = 'test-secret-qa'
os.environ['DATABASE_URL'] = 'postgresql://fake/test'

import pytest
import jwt
from unittest.mock import MagicMock, patch

# Import the Flask app after env vars are set.
from backend.app import app

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

TEST_SECRET = 'test-secret-qa'


def make_jwt(player_id: int) -> str:
    """Return a valid JWT for the given player_id signed with TEST_SECRET."""
    return jwt.encode({'id': player_id}, TEST_SECRET, algorithm='HS256')


def make_pvp_bet(poster_id: int = 1, accepter_id: int = 2) -> dict:
    """Return a minimal PvP (Shots Made) bet dict as the DB would return it."""
    return {
        'id': 'bet-test-001',
        'posterid': poster_id,
        'accepterid': accepter_id,
        'status': 'accepted',
        'gametype': 'Shots Made',
        'gameplayed': 'Caps',
        'gamesize': '2v2',
        'linenumber': 10.5,
        'linetype': 'Over',
        'amount': 100,
        'yourplayer': None,
        'oppplayer': None,
        'yourshots': None,
        'oppshots': None,
    }


def make_updated_bet_after_poster_submit(base_bet: dict) -> dict:
    """Return the bet dict as it would look after the poster submits their stats
    (only yourplayer/yourshots filled — no match yet)."""
    updated = dict(base_bet)
    updated['yourplayer'] = 'alice'
    updated['yourshots'] = 7
    # oppplayer/oppshots still None → check_stats_match returns False
    return updated


def make_mock_db(fetchone_sequence: list) -> MagicMock:
    """Build a mock DB connection whose cursor returns fetchone_sequence
    values in order across successive .fetchone() calls."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = fetchone_sequence
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — No JWT → 401
# ──────────────────────────────────────────────────────────────────────────────

def test_no_jwt_returns_401(client):
    """Request with no Authorization header is rejected before any DB work."""
    response = client.post(
        '/submit_stats/bet-test-001',
        json={'playerId': 1, 'yourPlayer': 'alice', 'yourShots': 7},
    )
    assert response.status_code == 401, (
        f"Expected 401 for missing JWT, got {response.status_code}: {response.get_data(as_text=True)}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Forged / invalid JWT → 401
# ──────────────────────────────────────────────────────────────────────────────

def test_forged_jwt_returns_401(client):
    """JWT signed with the wrong key (forged) is rejected with 401."""
    forged_token = jwt.encode({'id': 1}, 'wrong-secret', algorithm='HS256')
    response = client.post(
        '/submit_stats/bet-test-001',
        json={'playerId': 1, 'yourPlayer': 'alice', 'yourShots': 7},
        headers={'Authorization': f'Bearer {forged_token}'},
    )
    assert response.status_code == 401, (
        f"Expected 401 for forged JWT, got {response.status_code}: {response.get_data(as_text=True)}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — Valid JWT but wrong player (body has forged playerId) → 403
#
# This is the core security criterion: attacker sends their own valid JWT
# (player_id=99) but stuffs playerId=1 (the poster) in the body.
# The fix ignores the body's playerId and uses the JWT; since 99 is not
# the poster (1) or accepter (2), the handler must return 403.
# ──────────────────────────────────────────────────────────────────────────────

def test_valid_jwt_non_participant_returns_403(client):
    """Valid JWT for player 99 + forged playerId=1 in body → 403 on a PvP bet."""
    bet = make_pvp_bet(poster_id=1, accepter_id=2)
    mock_conn = make_mock_db(fetchone_sequence=[bet])

    with patch('backend.app.get_db', return_value=mock_conn):
        with patch('backend.app.SECRET_KEY', TEST_SECRET):
            token = make_jwt(player_id=99)
            response = client.post(
                '/submit_stats/bet-test-001',
                # body claims to be player 1 (the poster) — should be ignored
                json={'playerId': 1, 'yourPlayer': 'alice', 'yourShots': 7},
                headers={'Authorization': f'Bearer {token}'},
            )

    assert response.status_code == 403, (
        f"Expected 403 for non-participant, got {response.status_code}: {response.get_data(as_text=True)}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — Legitimate poster submits → 200
#
# Confirms the happy path is not broken: the actual poster (player_id=1) with
# a valid JWT can submit stats and receive a 200 response.
# ──────────────────────────────────────────────────────────────────────────────

def test_legitimate_poster_can_submit(client):
    """Valid JWT for the poster (player 1) on a PvP bet → 200 Stats processed."""
    bet = make_pvp_bet(poster_id=1, accepter_id=2)
    updated_bet = make_updated_bet_after_poster_submit(bet)

    # Cursor returns: bet (first SELECT), updated_bet (second SELECT after UPDATE)
    mock_conn = make_mock_db(fetchone_sequence=[bet, updated_bet])

    with patch('backend.app.get_db', return_value=mock_conn):
        with patch('backend.app.SECRET_KEY', TEST_SECRET):
            token = make_jwt(player_id=1)
            response = client.post(
                '/submit_stats/bet-test-001',
                json={'yourPlayer': 'alice', 'yourShots': 7},
                headers={'Authorization': f'Bearer {token}'},
            )

    data = response.get_json()
    assert response.status_code == 200, (
        f"Expected 200 for legitimate poster, got {response.status_code}: {data}"
    )
    assert data is not None and 'message' in data, (
        f"Response JSON missing 'message' key: {data}"
    )
    assert data['message'] == 'Stats processed', (
        f"Unexpected message: {data['message']}"
    )
    # Only poster submitted → no match yet.
    # check_stats_match returns a falsy value (False or '') via short-circuit and;
    # assert truthiness rather than strict identity to handle both.
    assert not data['match'], (
        f"Expected falsy match (accepter hasn't submitted), got: {data['match']!r}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — Legitimate accepter submits → 200
# ──────────────────────────────────────────────────────────────────────────────

def test_legitimate_accepter_can_submit(client):
    """Valid JWT for the accepter (player 2) on a PvP bet → 200 Stats processed."""
    bet = make_pvp_bet(poster_id=1, accepter_id=2)
    # After accepter submits, oppplayer/oppshots are filled but yourplayer/yourshots still None
    updated_bet = dict(bet)
    updated_bet['oppplayer'] = 'bob'
    updated_bet['oppshots'] = 5

    mock_conn = make_mock_db(fetchone_sequence=[bet, updated_bet])

    with patch('backend.app.get_db', return_value=mock_conn):
        with patch('backend.app.SECRET_KEY', TEST_SECRET):
            token = make_jwt(player_id=2)
            response = client.post(
                '/submit_stats/bet-test-001',
                json={'yourPlayer': 'bob', 'yourShots': 5},
                headers={'Authorization': f'Bearer {token}'},
            )

    data = response.get_json()
    assert response.status_code == 200, (
        f"Expected 200 for legitimate accepter, got {response.status_code}: {data}"
    )
    assert not data['match'], (
        f"Expected falsy match (poster hasn't submitted yet), got: {data['match']!r}"
    )
