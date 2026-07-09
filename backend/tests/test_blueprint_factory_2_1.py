"""
QA tests for item 2.1 — App-factory + blueprints.

Done when:
  - `create_app()` factory exists and returns a Flask app
  - Module-level `app = create_app()` is present for CLI compatibility
  - All 5 domain blueprint modules exist under backend/routes/
  - All 19 app routes (excluding /static) are registered on the Flask app
  - Each blueprint registers at least the routes it owns
  - Route handlers are reachable via the test client (correct status codes
    without DB — 401 for protected, 200 for public)
  - `backend/routes/_db.py` shim exists and re-exports get_db

Tests:
  (A) Factory: create_app() is importable and returns Flask instance
  (B) Factory: module-level `app` exists in backend.app
  (C) Blueprint modules: all 5 domain blueprint files importable, export their Blueprint
  (D) Route registration: all expected URL rules present on the app
  (E) Blueprint ownership: each blueprint registers its own routes
  (F) Handler reachability: test-client status codes (no DB) match expected auth guards
  (G) Shim: backend/routes/_db.py exists and has a callable get_db
"""

import importlib
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-qa-2-1")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

from flask import Flask

from backend.app import app as flask_app
from backend.app import create_app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-2-1"
BACKEND_DIR = Path(__file__).resolve().parent.parent

BLUEPRINT_MODULES = [
    ("backend.routes.bets_routes", "bets_bp"),
    ("backend.routes.accept_routes", "accept_bp"),
    ("backend.routes.submit_routes", "submit_bp"),
    ("backend.routes.lines_routes", "lines_bp"),
    ("backend.routes.main_routes", "main_bp"),
]

# All expected URL rules (excluding /static/<path:filename>)
EXPECTED_ROUTES = {
    "/create_bet",
    "/pvp_bets",
    "/cpu_bets",
    "/ongoing_bets",
    "/bets",
    "/accept_bet/<bet_id>",
    "/accept_cpu_bet/<bet_id>",
    "/submit_stats/<bet_id>",
    "/cpu/create_caps_shots_bet",
    "/cpu/create_pong_shots_bet",
    "/cpu/create_beerball_shots_bet",
    "/cpu/create_beerball_score_bet",
    "/cpu/create_caps_score_bet",
    "/cpu/create_pong_score_bet",
    "/leaderboard",
    "/cleanup_bets",
    "/register",
    "/login",
    "/me",
}

# Routes that should require a JWT (expect 401 without token)
PROTECTED_ROUTES = [
    ("POST", "/create_bet", {}),
    ("GET", "/pvp_bets", {}),
    ("GET", "/cpu_bets", {}),
    ("GET", "/ongoing_bets", {}),
    ("GET", "/bets", {}),
    ("POST", "/cleanup_bets", {}),
]

# Public routes that should NOT require a JWT
PUBLIC_ROUTES = [
    ("GET", "/leaderboard"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(player_id: int = 1) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def _registered_rule_strings(app: Flask):
    """Return the set of URL rule strings registered on app (no /static)."""
    return {
        str(r)
        for r in app.url_map.iter_rules()
        if not str(r).startswith("/static")
    }


# ---------------------------------------------------------------------------
# (A) Factory — create_app() exists and returns a Flask app
# ---------------------------------------------------------------------------

class TestFactory:
    def test_create_app_is_callable(self):
        assert callable(create_app), "create_app must be callable"

    def test_create_app_returns_flask_instance(self):
        app = create_app()
        assert isinstance(app, Flask), "create_app() must return a Flask instance"

    def test_module_level_app_exists(self):
        """flask --app backend/app run requires a module-level `app`."""
        import backend.app as app_module
        assert hasattr(app_module, "app"), "backend.app must export a module-level `app`"
        assert isinstance(app_module.app, Flask), "module-level `app` must be a Flask instance"

    def test_create_app_called_twice_returns_two_apps(self):
        """Factory should be reusable (no global state leak)."""
        app1 = create_app()
        app2 = create_app()
        assert app1 is not app2


# ---------------------------------------------------------------------------
# (B) Blueprint modules exist and export their Blueprint objects
# ---------------------------------------------------------------------------

class TestBlueprintModules:
    @pytest.mark.parametrize("module_name,attr_name", BLUEPRINT_MODULES)
    def test_blueprint_module_importable(self, module_name, attr_name):
        mod = importlib.import_module(module_name)
        assert mod is not None, f"{module_name} must be importable"

    @pytest.mark.parametrize("module_name,attr_name", BLUEPRINT_MODULES)
    def test_blueprint_attr_is_blueprint(self, module_name, attr_name):
        from flask import Blueprint
        mod = importlib.import_module(module_name)
        bp = getattr(mod, attr_name, None)
        assert bp is not None, f"{module_name} must export {attr_name}"
        assert isinstance(bp, Blueprint), f"{attr_name} must be a Flask Blueprint"

    def test_routes_package_init_exists(self):
        """backend/routes/__init__.py must exist (package marker)."""
        init_path = BACKEND_DIR / "routes" / "__init__.py"
        assert init_path.exists(), "backend/routes/__init__.py must exist"


# ---------------------------------------------------------------------------
# (C) Route registration — all 19 expected routes are on the app
# ---------------------------------------------------------------------------

class TestRouteRegistration:
    def test_all_expected_routes_registered(self):
        registered = _registered_rule_strings(flask_app)
        missing = EXPECTED_ROUTES - registered
        assert not missing, (
            f"Missing routes from Flask app: {sorted(missing)}"
        )

    def test_no_extra_unexpected_routes(self):
        """No leftover dead routes (beyond what the current blueprint set defines)."""
        registered = _registered_rule_strings(flask_app)
        # Any route beyond EXPECTED_ROUTES is unexpected — flag it.
        extra = registered - EXPECTED_ROUTES
        assert not extra, (
            f"Unexpected extra routes registered: {sorted(extra)}"
        )

    def test_total_route_count(self):
        """Exactly 19 non-static routes must be registered."""
        registered = _registered_rule_strings(flask_app)
        assert len(registered) == 19, (
            f"Expected 19 routes, got {len(registered)}: {sorted(registered)}"
        )


# ---------------------------------------------------------------------------
# (D) Per-blueprint route ownership
# ---------------------------------------------------------------------------

class TestBlueprintOwnership:
    def _routes_for_blueprint(self, app: Flask, bp_name: str):
        return {
            rule.rule
            for rule in app.url_map.iter_rules()
            if rule.endpoint.startswith(f"{bp_name}.")
        }

    def test_bets_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "bets")
        expected = {"/create_bet", "/pvp_bets", "/cpu_bets", "/ongoing_bets", "/bets"}
        assert expected <= routes, f"bets blueprint missing routes: {expected - routes}"

    def test_accept_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "accept")
        expected = {"/accept_bet/<bet_id>", "/accept_cpu_bet/<bet_id>"}
        assert expected <= routes, f"accept blueprint missing routes: {expected - routes}"

    def test_submit_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "submit")
        expected = {"/submit_stats/<bet_id>"}
        assert expected <= routes, f"submit blueprint missing routes: {expected - routes}"

    def test_lines_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "lines")
        expected = {
            "/cpu/create_caps_shots_bet",
            "/cpu/create_pong_shots_bet",
            "/cpu/create_beerball_shots_bet",
            "/cpu/create_beerball_score_bet",
            "/cpu/create_caps_score_bet",
            "/cpu/create_pong_score_bet",
        }
        assert expected <= routes, f"lines blueprint missing routes: {expected - routes}"

    def test_main_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "main")
        expected = {"/leaderboard", "/cleanup_bets"}
        assert expected <= routes, f"main blueprint missing routes: {expected - routes}"

    def test_auth_bp_owns_its_routes(self):
        routes = self._routes_for_blueprint(flask_app, "auth")
        expected = {"/register", "/login", "/me"}
        assert expected <= routes, f"auth blueprint missing routes: {expected - routes}"


# ---------------------------------------------------------------------------
# (E) Handler reachability — test client hits routes and gets expected status
#     Protected routes (no token) → 401
#     Public routes → 200 (with a mocked DB cursor)
# ---------------------------------------------------------------------------

class TestHandlerReachability:
    @pytest.fixture()
    def client(self):
        flask_app.config["TESTING"] = True
        with flask_app.test_client() as c:
            yield c

    @pytest.mark.parametrize("method,url,data", PROTECTED_ROUTES)
    def test_protected_route_requires_token(self, client, method, url, data):
        """Routes with @token_required must return 401 when no JWT is provided."""
        resp = getattr(client, method.lower())(url, json=data)
        assert resp.status_code == 401, (
            f"{method} {url}: expected 401 without token, got {resp.status_code}"
        )

    def test_leaderboard_public_no_token_needed(self, client):
        """GET /leaderboard must be accessible without a JWT."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [("alice", 500), ("bob", 300)]
        mock_cur.description = [("username",), ("caps_balance",)]
        mock_conn.cursor.return_value = mock_cur

        with patch("backend.app.get_db", return_value=mock_conn), \
             patch("backend.routes._db.get_db", return_value=mock_conn):
            resp = client.get("/leaderboard")

        assert resp.status_code == 200, (
            f"GET /leaderboard: expected 200 without token, got {resp.status_code}"
        )

    def test_protected_route_valid_token_passes_auth(self, client):
        """GET /pvp_bets with a valid JWT must pass the auth gate (not 401)."""
        token = _make_token(player_id=1)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_cur.description = []
        mock_conn.cursor.return_value = mock_cur

        # Patch both the DB connection and the SECRET_KEY the auth decorator reads
        # at request time so our token is accepted.
        with patch("backend.app.get_db", return_value=mock_conn), \
             patch("backend.routes._db.get_db", return_value=mock_conn), \
             patch("backend.app.SECRET_KEY", TEST_SECRET):
            resp = client.get(
                "/pvp_bets",
                headers={"Authorization": f"Bearer {token}"}
            )

        assert resp.status_code != 401, (
            f"GET /pvp_bets with valid JWT returned 401; auth gate is broken"
        )


# ---------------------------------------------------------------------------
# (F) _db.py shim exists and is callable
# ---------------------------------------------------------------------------

class TestDbShim:
    def test_db_shim_module_importable(self):
        mod = importlib.import_module("backend.routes._db")
        assert mod is not None

    def test_db_shim_exports_get_db(self):
        from backend.routes._db import get_db
        assert callable(get_db), "backend.routes._db.get_db must be callable"

    def test_db_shim_delegates_to_backend_app(self):
        """Patching backend.app.get_db must be picked up by the shim."""
        mock_conn = MagicMock()
        with patch("backend.app.get_db", return_value=mock_conn):
            from backend.routes._db import get_db
            result = get_db()
        assert result is mock_conn, (
            "backend.routes._db.get_db must delegate through backend.app.get_db"
            " so test patches are honoured"
        )

    def test_patch_compat_backend_app_get_db_re_exported(self):
        """backend.app must re-export get_db for patch compatibility."""
        import backend.app as app_module
        assert hasattr(app_module, "get_db"), (
            "backend.app must re-export get_db for `patch('backend.app.get_db')` to work"
        )
        assert callable(app_module.get_db)
