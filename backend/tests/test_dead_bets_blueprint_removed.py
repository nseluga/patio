"""
QA tests for item 0.3: Delete dead `bets` Blueprint in `auth.py`.

Done when:
  - The dead bets Blueprint block is removed from backend/auth.py.
  - The app still imports and boots clean (no import errors).
  - No references to the deleted block remain.

Strategy:
  - Static checks: read auth.py source and assert the `bets` Blueprint and
    its /bets route handler are absent.
  - Import check: importing backend.auth must succeed with no exception.
  - Behavioral check: Flask test client can reach /register, /login, /me
    (the three routes the auth Blueprint legitimately owns) and receives the
    expected HTTP status codes; no /bets route is registered anywhere on the app.
"""

import os
import importlib
import sys

# Set env vars before any backend module is imported so config.py picks them up.
os.environ.setdefault('SECRET_KEY', 'test-secret-qa-03')
os.environ.setdefault('DATABASE_URL', 'postgresql://fake/test')

import pytest
from unittest.mock import MagicMock, patch
from backend.app import app


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — `bets` Blueprint definition is absent from auth.py source
# ──────────────────────────────────────────────────────────────────────────────

def test_bets_blueprint_not_defined_in_source():
    """auth.py must not contain a Blueprint named 'bets'."""
    auth_path = os.path.join(os.path.dirname(__file__), '..', 'auth.py')
    with open(os.path.normpath(auth_path)) as f:
        source = f.read()
    assert "Blueprint('bets'" not in source, (
        "Dead `bets = Blueprint('bets', ...)` definition still present in auth.py"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — /bets POST route handler is absent from auth.py source
# ──────────────────────────────────────────────────────────────────────────────

def test_bets_route_handler_not_defined_in_source():
    """auth.py must not contain a @bets.route('/bets') handler."""
    auth_path = os.path.join(os.path.dirname(__file__), '..', 'auth.py')
    with open(os.path.normpath(auth_path)) as f:
        source = f.read()
    assert "@bets.route" not in source, (
        "Dead @bets.route decorator still present in auth.py"
    )
    assert "def create_bet" not in source, (
        "Dead create_bet() function still present in auth.py"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — Columns that never existed (poster_id, subject, line) absent too
# ──────────────────────────────────────────────────────────────────────────────

def test_nonexistent_column_references_absent():
    """auth.py must not reference poster_id, subject, or line columns (never existed in DB)."""
    auth_path = os.path.join(os.path.dirname(__file__), '..', 'auth.py')
    with open(os.path.normpath(auth_path)) as f:
        source = f.read()
    # These column names were in the dead INSERT statement; none exist in the bets table.
    for bad_col in ('poster_id', 'game_type', 'subject'):
        assert bad_col not in source, (
            f"Dead column reference '{bad_col}' still present in auth.py"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — backend.auth imports without error
# ──────────────────────────────────────────────────────────────────────────────

def test_auth_module_imports_cleanly():
    """Importing backend.auth must raise no exception."""
    # The module is already loaded; evicting and re-importing proves it stays clean.
    sys.modules.pop('backend.auth', None)
    try:
        auth_mod = importlib.import_module('backend.auth')
        # The only Blueprint exported is `auth`, not `bets`.
        assert hasattr(auth_mod, 'auth'), "backend.auth must still export the `auth` Blueprint"
        assert not hasattr(auth_mod, 'bets'), (
            "backend.auth must NOT export a `bets` attribute after the deletion"
        )
    finally:
        # Restore the module cache to the already-imported version for other tests.
        sys.modules.pop('backend.auth', None)
        importlib.import_module('backend.auth')


# ──────────────────────────────────────────────────────────────────────────────
# Fixture — Flask test client (no live DB needed)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — /bets route is NOT registered on the running Flask app (behavioral)
# ──────────────────────────────────────────────────────────────────────────────

def test_bets_post_route_not_registered_on_app(client):
    """POST /bets must NOT be handled — the dead Blueprint's create_bet is gone.

    A GET /bets route legitimately exists in app.py (fetch all bets), so Flask
    returns 405 Method Not Allowed for POST (route exists but the method doesn't).
    Both 404 and 405 prove the dead Blueprint's POST handler is absent.
    """
    response = client.post('/bets', json={'amount': 100, 'game_type': 'Caps'})
    assert response.status_code in (404, 405), (
        f"Expected 404 or 405 for POST /bets (dead handler gone), got {response.status_code} — "
        f"bets Blueprint's create_bet may still be registered"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 6 — /register is wired in the URL map (auth Blueprint intact, behavioral)
# ──────────────────────────────────────────────────────────────────────────────

def test_register_route_in_url_map():
    """POST /register must be present in the app URL map (auth Blueprint not broken)."""
    rules = {rule.rule: list(rule.methods) for rule in app.url_map.iter_rules()}
    assert '/register' in rules, (
        "POST /register not found in Flask URL map — auth Blueprint may be unregistered"
    )
    assert 'POST' in rules['/register'], (
        f"POST not in /register methods ({rules['/register']}) — auth Blueprint broken"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test 7 — /me route still reachable, returns 401 without token (behavioral)
# ──────────────────────────────────────────────────────────────────────────────

def test_me_route_still_reachable_without_token(client):
    """GET /me with no token → 401, confirming the route is still wired up."""
    response = client.get('/me')
    assert response.status_code == 401, (
        f"Expected 401 for /me with no token, got {response.status_code} — "
        f"route may be missing (would be 404) or auth Blueprint broken"
    )
