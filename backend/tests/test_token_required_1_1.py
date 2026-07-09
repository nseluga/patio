"""
QA tests for item 1.1 — @token_required decorator.

Done when:
  - No route body calls get_player_id() anywhere in app.py or auth.py
  - No route body has inline jwt.decode() in app.py or auth.py route handlers
  - All 15 expected protected routes use @token_required
  - Public routes (/register, /login, /leaderboard) are NOT decorated
  - Valid JWT → 200/201, missing JWT → 401, invalid JWT → 401 for at least 2 routes

Tests:
  (A) Static: no get_player_id() calls in route handlers
  (B) Static: all expected protected routes have @token_required
  (C) Static: public routes do NOT have @token_required
  (D) Static: no inline jwt.decode() inside route handlers
  (E) Behavioral: valid JWT → passes auth gate; missing/invalid JWT → 401 (per-route)
"""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret-qa-1-1")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app as flask_app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_SECRET = "test-secret-qa-1-1"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_PY = BACKEND_DIR / "app.py"
AUTH_PY = BACKEND_DIR / "auth.py"

# After the blueprint split, route functions live in backend/routes/*.py.
_SEARCH_PATHS = [
    APP_PY,
    BACKEND_DIR / "routes" / "bets_routes.py",
    BACKEND_DIR / "routes" / "accept_routes.py",
    BACKEND_DIR / "routes" / "submit_routes.py",
    BACKEND_DIR / "routes" / "main_routes.py",
    BACKEND_DIR / "routes" / "lines_routes.py",
]

# All 14 protected routes in app.py (the auth blueprint's /me makes 15 total,
# but it lives in auth.py — we check that separately).
PROTECTED_ROUTES_APP_PY = [
    "cleanup_bets",
    "create_bet",
    "get_pvp_bets",
    "get_cpu_bets",
    "accept_bet",
    "accept_cpu_bet",
    "get_ongoing_bets",
    "submit_stats",
    "get_all_bets",
    "create_cpu_caps_shots_bet",
    "create_cpu_pong_shots_bet",
    "create_cpu_beerball_shots_bet",
    "create_cpu_beerball_score_bet",
    "create_cpu_caps_score_bet",
    "create_cpu_pong_score_bet",
]

# Public routes in auth.py blueprint — must NOT have @token_required.
PUBLIC_ROUTES_AUTH_PY = ["register", "login"]
# Public route in app.py — must NOT have @token_required.
PUBLIC_ROUTES_APP_PY = ["public_leaderboard"]

# Protected route in auth.py that MUST have @token_required.
PROTECTED_ROUTES_AUTH_PY = ["get_current_user"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_jwt(player_id: int) -> str:
    return jwt.encode({"id": player_id}, TEST_SECRET, algorithm="HS256")


def make_mock_conn(fetchone_return=None, fetchall_return=None, description=None):
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = fetchone_return
    mock_cursor.fetchall.return_value = fetchall_return if fetchall_return is not None else []
    mock_cursor.description = description if description is not None else []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def _route_has_decorator(func_name: str, decorator_name: str, tree: ast.Module) -> bool:
    """Return True if a top-level function in the AST has a decorator matching decorator_name."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            for dec in node.decorator_list:
                if decorator_name in ast.unparse(dec):
                    return True
    return False


def _function_body_source(func_name: str, path: Path) -> str:
    """Return function body source. Searches blueprint files if not found in path."""
    search = [path] + [p for p in _SEARCH_PATHS if p != path]
    for p in search:
        source = p.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                # node.body starts at the first statement after the def + decorators
                first_body_line = node.body[0].lineno
                lines = source.splitlines()
                return "\n".join(lines[first_body_line - 1 : node.end_lineno])
    return ""


def _collect_jwt_decode_in_body(func_name: str, path: Path) -> list[str]:
    """Return lines in the function body that contain jwt.decode() (not as decorator)."""
    body_src = _function_body_source(func_name, path)
    return [ln.strip() for ln in body_src.splitlines() if "jwt.decode(" in ln]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ===========================================================================
# (A) Static: no get_player_id() calls in route handlers
# ===========================================================================

class TestNoGetPlayerIdCalls:
    """Every protected route handler in app.py must not call get_player_id()."""

    @pytest.mark.parametrize("func_name", PROTECTED_ROUTES_APP_PY)
    def test_no_get_player_id_in_route(self, func_name):
        body_src = _function_body_source(func_name, APP_PY)
        assert body_src, f"Function '{func_name}' not found in app.py"
        assert "get_player_id()" not in body_src, (
            f"Route handler '{func_name}' still calls get_player_id() — "
            f"identity must come from g.player_id set by @token_required"
        )

    def test_no_get_player_id_in_me_handler(self):
        """auth.py /me handler must not call get_player_id()."""
        body_src = _function_body_source("get_current_user", AUTH_PY)
        assert body_src, "Function 'get_current_user' not found in auth.py"
        assert "get_player_id()" not in body_src, (
            "auth.py get_current_user still calls get_player_id()"
        )

    def test_get_player_id_not_defined_in_app_py(self):
        """get_player_id() function must have been deleted from app.py entirely."""
        tree = _parse_file(APP_PY)
        defined = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "get_player_id"
            for node in ast.walk(tree)
        )
        assert not defined, (
            "get_player_id() is still defined in app.py — it should have been deleted"
        )


# ===========================================================================
# (B) Static: all protected routes have @token_required
# ===========================================================================

class TestProtectedRoutesHaveDecorator:
    """Every protected route in app.py must carry @token_required."""

    @pytest.mark.parametrize("func_name", PROTECTED_ROUTES_APP_PY)
    def test_protected_route_has_token_required(self, func_name):
        # Search blueprint files too since routes were moved out of app.py
        found = False
        for path in _SEARCH_PATHS:
            tree = _parse_file(path)
            if _route_has_decorator(func_name, "token_required", tree):
                found = True
                break
        assert found, (
            f"Protected route '{func_name}' is missing @token_required in all blueprint files"
        )

    def test_me_handler_has_token_required(self):
        """auth.py /me (get_current_user) must have @token_required."""
        tree = _parse_file(AUTH_PY)
        assert _route_has_decorator("get_current_user", "token_required", tree), (
            "auth.py get_current_user is missing @token_required"
        )


# ===========================================================================
# (C) Static: public routes do NOT have @token_required
# ===========================================================================

class TestPublicRoutesLackDecorator:
    """Public routes must not be gated — @token_required must be absent."""

    @pytest.mark.parametrize("func_name", PUBLIC_ROUTES_AUTH_PY)
    def test_public_auth_route_no_token_required(self, func_name):
        tree = _parse_file(AUTH_PY)
        has_it = _route_has_decorator(func_name, "token_required", tree)
        assert not has_it, (
            f"Public route '{func_name}' in auth.py incorrectly has @token_required"
        )

    @pytest.mark.parametrize("func_name", PUBLIC_ROUTES_APP_PY)
    def test_public_app_route_no_token_required(self, func_name):
        # Search blueprint files too since routes were moved out of app.py
        for path in _SEARCH_PATHS:
            tree = _parse_file(path)
            has_it = _route_has_decorator(func_name, "token_required", tree)
            assert not has_it, (
                f"Public route '{func_name}' in {path.name} incorrectly has @token_required"
            )


# ===========================================================================
# (D) Static: no inline jwt.decode() inside route handlers
# ===========================================================================

class TestNoInlineJwtDecode:
    """Route bodies must not contain jwt.decode() — only the decorator may do it."""

    @pytest.mark.parametrize("func_name", PROTECTED_ROUTES_APP_PY)
    def test_no_jwt_decode_in_app_route_body(self, func_name):
        hits = _collect_jwt_decode_in_body(func_name, APP_PY)
        assert not hits, (
            f"Route handler '{func_name}' in app.py has inline jwt.decode(): {hits}"
        )

    def test_no_jwt_decode_in_me_handler_body(self):
        hits = _collect_jwt_decode_in_body("get_current_user", AUTH_PY)
        assert not hits, (
            f"auth.py get_current_user has inline jwt.decode(): {hits}"
        )


# ===========================================================================
# (E) Behavioral: JWT auth gate enforcement per route
# ===========================================================================

class TestAuthGateEnforcement:
    """Valid JWT passes; missing or invalid JWT → 401."""

    # ---- /create_bet -------------------------------------------------------

    def test_create_bet_missing_jwt_returns_401(self, client):
        resp = client.post("/create_bet", json={"amount": 50})
        assert resp.status_code == 401, (
            f"Expected 401 (no JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_create_bet_invalid_jwt_returns_401(self, client):
        forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
        resp = client.post(
            "/create_bet",
            json={"amount": 50},
            headers={"Authorization": f"Bearer {forged}"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 (bad JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_create_bet_valid_jwt_passes_auth_gate(self, client):
        mock_conn = make_mock_conn(fetchone_return=("alice",))
        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                resp = client.post(
                    "/create_bet",
                    json={"amount": 50, "matchup": "1v1", "lineType": "Over", "lineNumber": 5.5, "gameType": "Caps"},
                    headers={"Authorization": f"Bearer {token}"},
                )
        assert resp.status_code != 401, (
            f"Valid JWT was rejected with 401: {resp.get_data(as_text=True)}"
        )

    # ---- /pvp_bets ---------------------------------------------------------

    def test_pvp_bets_missing_jwt_returns_401(self, client):
        resp = client.get("/pvp_bets")
        assert resp.status_code == 401, (
            f"Expected 401 (no JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_pvp_bets_invalid_jwt_returns_401(self, client):
        forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
        resp = client.get("/pvp_bets", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401, (
            f"Expected 401 (bad JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_pvp_bets_valid_jwt_returns_200(self, client):
        mock_conn = make_mock_conn(fetchall_return=[])
        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                resp = client.get("/pvp_bets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, (
            f"Expected 200 for valid JWT, got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    # ---- /ongoing_bets (additional second route for behavioral coverage) ---

    def test_ongoing_bets_missing_jwt_returns_401(self, client):
        resp = client.get("/ongoing_bets")
        assert resp.status_code == 401, (
            f"Expected 401 (no JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_ongoing_bets_invalid_jwt_returns_401(self, client):
        forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
        resp = client.get("/ongoing_bets", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401, (
            f"Expected 401 (bad JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_ongoing_bets_valid_jwt_returns_200(self, client):
        mock_conn = make_mock_conn(fetchall_return=[])
        with patch("backend.app.get_db", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                resp = client.get("/ongoing_bets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, (
            f"Expected 200 for valid JWT, got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    # ---- /me (auth blueprint) ----------------------------------------------

    def test_me_missing_jwt_returns_401(self, client):
        resp = client.get("/me")
        assert resp.status_code == 401, (
            f"Expected 401 (no JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_me_invalid_jwt_returns_401(self, client):
        forged = jwt.encode({"id": 1}, "wrong-secret", algorithm="HS256")
        resp = client.get("/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401, (
            f"Expected 401 (bad JWT), got {resp.status_code}: {resp.get_data(as_text=True)}"
        )

    def test_me_valid_jwt_returns_200(self, client):
        # /me fetches player row then recent_bets
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("alice", "a@b.com", 500, 2, 1)
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        # Patch psycopg2.connect directly — the lowest-level seam — so this mock
        # survives test_dead_bets_blueprint_removed's pop+reimport of backend.auth.
        # (Patching backend.auth.get_db is fragile: after a reimport, the registered
        # route function still closes over the old module's get_db binding.)
        with patch("psycopg2.connect", return_value=mock_conn):
            with patch("backend.app.SECRET_KEY", TEST_SECRET):
                token = make_jwt(player_id=1)
                resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, (
            f"Expected 200 for valid JWT at /me, got {resp.status_code}: {resp.get_data(as_text=True)}"
        )


# ===========================================================================
# (F) Behavioral: public routes accessible without any token
# ===========================================================================

class TestPublicRoutesNoTokenNeeded:
    """/register, /login, /leaderboard must not require a JWT."""

    def test_leaderboard_accessible_without_token(self, client):
        mock_conn = make_mock_conn(fetchall_return=[])
        with patch("backend.app.get_db", return_value=mock_conn):
            resp = client.get("/leaderboard")
        assert resp.status_code == 200, (
            f"/leaderboard returned {resp.status_code} without a token — should be public"
        )

    def test_register_route_accessible_without_token(self, client):
        """POST /register must reach the handler (not be rejected by @token_required).
        A 400 or 500 from missing fields is acceptable; a 401 is not."""
        mock_conn = make_mock_conn()
        # Patch psycopg2.connect (lowest-level seam) so the mock survives
        # test_dead_bets_blueprint_removed's pop+reimport of backend.auth.
        with patch("psycopg2.connect", return_value=mock_conn):
            resp = client.post(
                "/register",
                json={"username": "bob", "email": "bob@example.com", "password": "pass123"},
            )
        assert resp.status_code != 401, (
            f"/register returned 401 — the route must not require a JWT (got {resp.status_code})"
        )

    def test_login_route_accessible_without_token(self, client):
        """POST /login must reach the handler without a token.
        401 due to bad credentials is fine; 401 due to missing JWT is not."""
        # Return None fetchone so login fails with "Invalid credentials" (401 from the handler),
        # but that's the right 401 path — not the decorator.
        mock_conn = make_mock_conn(fetchone_return=None)
        # Patch psycopg2.connect (lowest-level seam) for same resilience reason.
        with patch("psycopg2.connect", return_value=mock_conn):
            resp = client.post(
                "/login",
                json={"email": "x@x.com", "password": "wrong"},
            )
        # 401 from the route handler ("Invalid credentials") is acceptable.
        # We verify by checking the response body: it must NOT say "Unauthorized"
        # (which is the decorator's error message).
        body = resp.get_data(as_text=True)
        assert "Unauthorized" not in body, (
            f"/login returned 'Unauthorized' — this means @token_required is blocking it. "
            f"Login must be a public route. Response: {body}"
        )
