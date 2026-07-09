"""
QA tests for item 2.2 — Error handlers + CORS scoping + Flask-Limiter.

Done when:
  (1) 404 returns JSON with "error" key
  (2) 429 rate limit fires on repeated calls
  (3) CORS origins list doesn't contain hardcoded vercel placeholder when FRONTEND_URL unset
  (4) limiter decorators present on the 6 target routes (AST check)
  (5) error handlers registered on app

Tests:
  (A) Error handlers: each HTTP error code returns JSON with "error" key and correct status
  (B) 404 specifically: JSON body contains "error" key
  (C) CORS origins: no hardcoded placeholder when FRONTEND_URL not set
  (D) CORS origins: includes localhost:3000 always; includes FRONTEND_URL when set
  (E) Rate limiter: flask-limiter in requirements.txt
  (F) Rate limiter: limiter decorators present on 6 target routes (AST check)
  (G) Rate limiter: 429 fires on repeated requests (live test-client)
  (H) Error handlers registered: 404/429/500 wired on the Flask app
"""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Set env before importing app so the factory sees the correct values
os.environ.setdefault("SECRET_KEY", "test-secret-qa-2-2")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")
# Ensure FRONTEND_URL is NOT set for most tests (may already be unset)
FRONTEND_URL_BACKUP = os.environ.pop("FRONTEND_URL", None)

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app_no_frontend_url():
    """Create a fresh app instance with FRONTEND_URL unset."""
    env_backup = os.environ.pop("FRONTEND_URL", None)
    try:
        from backend.app import create_app
        app = create_app()
        return app
    finally:
        if env_backup is not None:
            os.environ["FRONTEND_URL"] = env_backup


def _make_app_with_frontend_url(url: str):
    """Create a fresh app instance with FRONTEND_URL set to `url`."""
    old = os.environ.get("FRONTEND_URL")
    os.environ["FRONTEND_URL"] = url
    try:
        from backend.app import create_app
        app = create_app()
        return app
    finally:
        if old is None:
            os.environ.pop("FRONTEND_URL", None)
        else:
            os.environ["FRONTEND_URL"] = old


def _get_cors_origins(app) -> list:
    """Extract the CORS origins list from the app's after_request stack via CORS extension."""
    # Flask-CORS stores per-resource config in app.extensions['cors']
    # or we can extract from the CORS wrapper around the app.
    # The most reliable approach: re-parse the create_app source.
    # Instead, we create a real test client and inspect the CORS header on a preflight.
    with app.test_client() as client:
        resp = client.options(
            "/leaderboard",
            headers={
                "Origin": "https://your-app.vercel.app",
                "Access-Control-Request-Method": "GET",
            }
        )
        allowed = resp.headers.get("Access-Control-Allow-Origin", "")
    return allowed


# ---------------------------------------------------------------------------
# (A) Error Handlers — each registered code returns JSON {"error": ...}
# ---------------------------------------------------------------------------

class TestErrorHandlerShape:
    """All HTTP error handlers must return JSON with an 'error' key."""

    @pytest.fixture(scope="class")
    def app(self):
        from backend.app import create_app
        a = create_app()
        a.config["TESTING"] = True
        return a

    @pytest.fixture()
    def client(self, app):
        with app.test_client() as c:
            yield c

    def test_404_returns_json_error_key(self, client):
        """GET a non-existent route → 404 JSON with 'error' key."""
        resp = client.get("/this-route-does-not-exist-9999")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        data = resp.get_json()
        assert data is not None, "404 response body must be valid JSON"
        assert "error" in data, f"404 JSON must contain 'error' key; got keys: {list(data.keys())}"

    def test_405_returns_json_error_key(self, client):
        """Wrong method on a known route → 405 JSON with 'error' key."""
        # /leaderboard is GET-only; send DELETE to get 405
        resp = client.delete("/leaderboard")
        assert resp.status_code == 405, f"Expected 405, got {resp.status_code}"
        data = resp.get_json()
        assert data is not None, "405 response must be valid JSON"
        assert "error" in data, f"405 JSON must contain 'error' key; got {list(data.keys())}"

    def test_401_returns_json_error_key(self, client):
        """Protected route without token → 401 JSON with 'error' key."""
        resp = client.get("/pvp_bets")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        data = resp.get_json()
        assert data is not None, "401 response must be valid JSON"
        assert "error" in data, f"401 JSON must contain 'error' key; got {list(data.keys())}"

    def test_500_handler_registered(self, app):
        """A registered 500 handler should be present in app.error_handler_spec."""
        # Flask stores handlers by exception class under the global (None) namespace:
        # {None: {None: {ExcClass: fn, ...}, code: {ExcClass: fn}}}
        # InternalServerError is the exc class for 500.
        from werkzeug.exceptions import InternalServerError
        handlers = app.error_handler_spec
        global_handlers = handlers.get(None, {})
        # Collect all registered exception classes across all code buckets
        registered_exc_classes = set()
        for bucket in global_handlers.values():
            if isinstance(bucket, dict):
                registered_exc_classes.update(bucket.keys())
        assert InternalServerError in registered_exc_classes, (
            f"HTTP 500 (InternalServerError) error handler not registered on app; "
            f"registered exc classes: {[c.__name__ for c in registered_exc_classes]}"
        )

    def test_error_handlers_all_registered(self, app):
        """All expected error handler exception classes must be registered in error_handler_spec."""
        from werkzeug.exceptions import (
            BadRequest, Unauthorized, Forbidden, NotFound,
            MethodNotAllowed, TooManyRequests, InternalServerError,
        )
        expected_exc_classes = {
            BadRequest, Unauthorized, Forbidden, NotFound,
            MethodNotAllowed, TooManyRequests, InternalServerError,
        }
        handlers = app.error_handler_spec
        global_handlers = handlers.get(None, {})
        registered_exc_classes = set()
        for bucket in global_handlers.values():
            if isinstance(bucket, dict):
                registered_exc_classes.update(bucket.keys())
        missing = expected_exc_classes - registered_exc_classes
        assert not missing, (
            f"Error handlers not registered for: {[c.__name__ for c in missing]}"
        )


# ---------------------------------------------------------------------------
# (B) CORS — no hardcoded placeholder when FRONTEND_URL is unset
# ---------------------------------------------------------------------------

class TestCORSOrigins:
    def test_no_placeholder_when_frontend_url_unset(self):
        """When FRONTEND_URL is not set, cors_origins must not contain any placeholder."""
        # Inspect the create_app source directly via AST to verify the dynamic-only path
        app_src = (BACKEND_DIR / "app.py").read_text()
        # The hardcoded placeholder that was removed
        assert "your-app.vercel.app" not in app_src, (
            "Hardcoded 'your-app.vercel.app' placeholder found in app.py — "
            "CORS origins must be built dynamically, not hardcoded"
        )
        assert "your_app.vercel.app" not in app_src, (
            "Hardcoded vercel.app placeholder variant found in app.py"
        )

    def test_cors_origin_list_has_no_placeholder_at_runtime(self):
        """When FRONTEND_URL is unset, the origins list must only be ['http://localhost:3000']."""
        env_backup = os.environ.pop("FRONTEND_URL", None)
        try:
            from backend.app import create_app
            app = create_app()
            # Extract CORS config from Flask-CORS extension data
            cors_ext = app.extensions.get("cors", None)
            if cors_ext is not None:
                # Flask-CORS >=4: app.extensions['cors'] holds the CORS object
                # We can also check via a preflight request
                pass
            # Use preflight to confirm placeholder is not allowed
            with app.test_client() as client:
                # The placeholder domain
                resp = client.options(
                    "/leaderboard",
                    headers={
                        "Origin": "https://your-app.vercel.app",
                        "Access-Control-Request-Method": "GET",
                    }
                )
                allowed = resp.headers.get("Access-Control-Allow-Origin", "")
            assert "your-app.vercel.app" not in allowed, (
                f"Placeholder vercel URL allowed by CORS when FRONTEND_URL is unset; "
                f"Access-Control-Allow-Origin: {allowed}"
            )
        finally:
            if env_backup is not None:
                os.environ["FRONTEND_URL"] = env_backup

    def test_cors_always_includes_localhost(self):
        """http://localhost:3000 must always be in CORS origins regardless of FRONTEND_URL."""
        env_backup = os.environ.pop("FRONTEND_URL", None)
        try:
            from backend.app import create_app
            app = create_app()
            with app.test_client() as client:
                resp = client.options(
                    "/leaderboard",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                    }
                )
                allowed = resp.headers.get("Access-Control-Allow-Origin", "")
            assert "localhost:3000" in allowed or allowed == "*", (
                f"http://localhost:3000 not in CORS Allow-Origin; got: {allowed}"
            )
        finally:
            if env_backup is not None:
                os.environ["FRONTEND_URL"] = env_backup

    def test_cors_includes_frontend_url_when_set(self):
        """When FRONTEND_URL is set, it must appear in the CORS allowed origins."""
        test_url = "https://patio-test.vercel.app"
        old = os.environ.get("FRONTEND_URL")
        os.environ["FRONTEND_URL"] = test_url
        try:
            from backend.app import create_app
            app = create_app()
            with app.test_client() as client:
                resp = client.options(
                    "/leaderboard",
                    headers={
                        "Origin": test_url,
                        "Access-Control-Request-Method": "GET",
                    }
                )
                allowed = resp.headers.get("Access-Control-Allow-Origin", "")
            assert test_url in allowed or allowed == "*", (
                f"FRONTEND_URL '{test_url}' not reflected in CORS Allow-Origin; got: {allowed}"
            )
        finally:
            if old is None:
                os.environ.pop("FRONTEND_URL", None)
            else:
                os.environ["FRONTEND_URL"] = old


# ---------------------------------------------------------------------------
# (C) Flask-Limiter in requirements.txt
# ---------------------------------------------------------------------------

class TestRequirementsTxt:
    def test_flask_limiter_in_requirements(self):
        """flask-limiter must appear in backend/requirements.txt."""
        req_path = BACKEND_DIR / "requirements.txt"
        assert req_path.exists(), "backend/requirements.txt must exist"
        content = req_path.read_text().lower()
        assert "flask-limiter" in content, (
            "flask-limiter not found in backend/requirements.txt"
        )


# ---------------------------------------------------------------------------
# (D) Limiter decorators present on target routes (AST check)
# ---------------------------------------------------------------------------

class TestLimiterDecoratorsAST:
    """
    Parse each route module and verify that the target functions have a
    @limiter.limit(...) decorator applied.
    """

    def _has_limiter_limit_decorator(self, func_node: ast.FunctionDef) -> bool:
        """Return True if the function has a @limiter.limit(...) decorator."""
        for dec in func_node.decorator_list:
            # Match `limiter.limit(...)` — an ast.Call whose func is ast.Attribute
            if isinstance(dec, ast.Call):
                f = dec.func
                if (
                    isinstance(f, ast.Attribute)
                    and f.attr == "limit"
                    and isinstance(f.value, ast.Name)
                    and f.value.id == "limiter"
                ):
                    return True
        return False

    def _get_func_nodes(self, source_path: Path) -> dict:
        """Return {func_name: FunctionDef} for all top-level and class-level functions."""
        tree = ast.parse(source_path.read_text())
        funcs = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                funcs[node.name] = node
        return funcs

    def test_register_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "auth.py")
        assert "register" in funcs, "register() not found in auth.py"
        assert self._has_limiter_limit_decorator(funcs["register"]), (
            "auth.py:register() missing @limiter.limit decorator"
        )

    def test_login_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "auth.py")
        assert "login" in funcs, "login() not found in auth.py"
        assert self._has_limiter_limit_decorator(funcs["login"]), (
            "auth.py:login() missing @limiter.limit decorator"
        )

    def test_create_bet_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "routes" / "bets_routes.py")
        assert "create_bet" in funcs, "create_bet() not found in bets_routes.py"
        assert self._has_limiter_limit_decorator(funcs["create_bet"]), (
            "bets_routes.py:create_bet() missing @limiter.limit decorator"
        )

    def test_accept_bet_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "routes" / "accept_routes.py")
        assert "accept_bet" in funcs, "accept_bet() not found in accept_routes.py"
        assert self._has_limiter_limit_decorator(funcs["accept_bet"]), (
            "accept_routes.py:accept_bet() missing @limiter.limit decorator"
        )

    def test_accept_cpu_bet_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "routes" / "accept_routes.py")
        assert "accept_cpu_bet" in funcs, "accept_cpu_bet() not found in accept_routes.py"
        assert self._has_limiter_limit_decorator(funcs["accept_cpu_bet"]), (
            "accept_routes.py:accept_cpu_bet() missing @limiter.limit decorator"
        )

    def test_submit_stats_has_limiter(self):
        funcs = self._get_func_nodes(BACKEND_DIR / "routes" / "submit_routes.py")
        assert "submit_stats" in funcs, "submit_stats() not found in submit_routes.py"
        assert self._has_limiter_limit_decorator(funcs["submit_stats"]), (
            "submit_routes.py:submit_stats() missing @limiter.limit decorator"
        )


# ---------------------------------------------------------------------------
# (E) Rate limiting fires: 429 on repeated requests
# ---------------------------------------------------------------------------

class TestRateLimitFires:
    """Trigger the rate limiter on /login (10/min limit) by hammering it."""

    @pytest.fixture(scope="class")
    def rate_limit_app(self):
        """App with RATELIMIT_ENABLED and very tight per-test limits."""
        from backend.app import create_app
        app = create_app()
        app.config["TESTING"] = True
        # Flask-Limiter respects RATELIMIT_ENABLED; ensure it's on
        app.config["RATELIMIT_ENABLED"] = True
        # Use memory storage (already default) and reset between test runs
        app.config["RATELIMIT_STORAGE_URL"] = "memory://"
        return app

    def test_429_fires_on_register_after_limit_exceeded(self, rate_limit_app):
        """
        POST /register 11 times in a row should hit the '10 per minute' limit
        and return 429 with JSON {"error": ...} on the 11th call.
        """
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with rate_limit_app.test_client() as client:
            with patch("backend.app.get_db", return_value=mock_conn), \
                 patch("backend.routes._db.get_db", return_value=mock_conn), \
                 patch("backend.auth.get_db", return_value=mock_conn):

                last_status = None
                for i in range(11):
                    resp = client.post(
                        "/register",
                        json={
                            "username": f"user{i}",
                            "email": f"u{i}@test.com",
                            "password": "testpass123"
                        },
                        headers={"X-Forwarded-For": "10.0.0.1"}
                    )
                    last_status = resp.status_code

                assert last_status == 429, (
                    f"Expected 429 after 11 /register calls, got {last_status}"
                )
                # Also verify the 429 body has "error" key
                data = resp.get_json()
                assert data is not None, "429 response must be valid JSON"
                assert "error" in data, (
                    f"429 JSON body must contain 'error' key; got {list(data.keys())}"
                )

    def test_429_json_has_error_key(self, rate_limit_app):
        """The 429 handler specifically must return JSON with 'error' key."""
        # Hit /login 11 times to trigger the rate limit there too
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        # Make fetchone return None so login returns 401 (not 200) for valid checks
        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cur

        with rate_limit_app.test_client() as client:
            with patch("backend.app.get_db", return_value=mock_conn), \
                 patch("backend.routes._db.get_db", return_value=mock_conn), \
                 patch("backend.auth.get_db", return_value=mock_conn):

                for i in range(11):
                    resp = client.post(
                        "/login",
                        json={"email": "x@x.com", "password": "wrong"},
                        headers={"X-Forwarded-For": "10.0.0.2"}
                    )

                assert resp.status_code == 429
                data = resp.get_json()
                assert data is not None
                assert "error" in data, (
                    f"429 response JSON missing 'error' key; got: {data}"
                )
