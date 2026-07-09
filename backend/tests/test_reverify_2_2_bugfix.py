"""
Re-verification tests for item 2.2 Bug Fixer pass (commit ecb068f).

Verifies three specific changes:
  1. ProxyFix(x_for=1) is in the wsgi_app chain on the Flask app
  2. 429 error handler returns JSON {"retry_after": 60} (static, not e.retry_after)
  3. limiter decorators appear BEFORE token_required on the 4 wallet routes:
       - create_bet (bets_routes.py)
       - accept_bet (accept_routes.py)
       - accept_cpu_bet (accept_routes.py)
       - submit_stats (submit_routes.py)
"""

import ast
import os
from pathlib import Path

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-reverify-2-2")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

BACKEND_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Criterion 1: ProxyFix in wsgi_app chain
# ---------------------------------------------------------------------------

class TestProxyFixInChain:
    """ProxyFix(x_for=1) must wrap app.wsgi_app after factory runs."""

    @pytest.fixture(scope="class")
    def app(self):
        from backend.app import create_app
        return create_app()

    def test_proxyfix_wraps_wsgi_app(self, app):
        """app.wsgi_app must be a ProxyFix instance (x_for=1)."""
        from werkzeug.middleware.proxy_fix import ProxyFix
        wsgi = app.wsgi_app
        assert isinstance(wsgi, ProxyFix), (
            f"app.wsgi_app is {type(wsgi).__name__}, expected ProxyFix. "
            "ProxyFix must be applied in create_app() so Flask-Limiter reads "
            "the real client IP from X-Forwarded-For."
        )

    def test_proxyfix_x_for_is_1(self, app):
        """ProxyFix must be configured with x_for=1 (trust exactly one proxy hop)."""
        from werkzeug.middleware.proxy_fix import ProxyFix
        wsgi = app.wsgi_app
        assert isinstance(wsgi, ProxyFix), "app.wsgi_app must be ProxyFix"
        assert wsgi.x_for == 1, (
            f"ProxyFix.x_for == {wsgi.x_for}, expected 1. "
            "x_for=1 trusts one X-Forwarded-For hop (the Render LB)."
        )

    def test_proxyfix_in_app_py_source(self):
        """app.py source must contain ProxyFix import and assignment."""
        src = (BACKEND_DIR / "app.py").read_text()
        assert "ProxyFix" in src, "ProxyFix must be imported in app.py"
        assert "app.wsgi_app = ProxyFix" in src, (
            "app.wsgi_app must be assigned to a ProxyFix instance in app.py"
        )
        assert "x_for=1" in src, "ProxyFix must be configured with x_for=1"


# ---------------------------------------------------------------------------
# Criterion 2: 429 handler returns static retry_after: 60
# ---------------------------------------------------------------------------

class TestRetryAfterStatic:
    """429 handler must return {"retry_after": 60} (static int, not e.retry_after)."""

    @pytest.fixture(scope="class")
    def app(self):
        from backend.app import create_app
        a = create_app()
        a.config["TESTING"] = True
        a.config["RATELIMIT_ENABLED"] = True
        a.config["RATELIMIT_STORAGE_URL"] = "memory://"
        return a

    def test_429_handler_has_static_60_in_source(self):
        """error_handlers.py must have static 'retry_after': 60, not e.retry_after."""
        src = (BACKEND_DIR / "error_handlers.py").read_text()
        # The fix: static 60, not the dynamic e.retry_after (which is None in Flask-Limiter 4.x)
        assert '"retry_after": 60' in src or "'retry_after': 60" in src, (
            "error_handlers.py must contain static 'retry_after': 60 "
            "in the 429 handler. Using e.retry_after returns None in Flask-Limiter 4.x."
        )
        assert "e.retry_after" not in src, (
            "error_handlers.py must NOT use e.retry_after (always None in Flask-Limiter 4.x); "
            "use static 60 instead."
        )

    def test_429_response_contains_retry_after_60(self, app):
        """Live 429 response must include retry_after == 60 in JSON body."""
        from unittest.mock import MagicMock, patch

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur

        with app.test_client() as client:
            with patch("backend.app.get_db", return_value=mock_conn), \
                 patch("backend.routes._db.get_db", return_value=mock_conn), \
                 patch("backend.auth.get_db", return_value=mock_conn):

                # Hammer /register (10/min limit) to trigger 429
                last_resp = None
                for i in range(12):
                    last_resp = client.post(
                        "/register",
                        json={
                            "username": f"ratelimituser{i}",
                            "email": f"rlu{i}@test.com",
                            "password": "pass123"
                        },
                        headers={"X-Forwarded-For": "10.1.2.3"}
                    )

        assert last_resp is not None
        # At least one response should be 429
        assert last_resp.status_code == 429, (
            f"Expected 429 after 12 /register calls, got {last_resp.status_code}"
        )
        data = last_resp.get_json()
        assert data is not None, "429 response must be valid JSON"
        assert "retry_after" in data, (
            f"429 JSON body must contain 'retry_after' key; got keys: {list(data.keys())}"
        )
        assert data["retry_after"] == 60, (
            f"429 JSON 'retry_after' must be 60 (static); got {data['retry_after']!r}"
        )


# ---------------------------------------------------------------------------
# Criterion 3: limiter decorators appear BEFORE token_required on 4 wallet routes
# ---------------------------------------------------------------------------

class TestDecoratorOrderOnWalletRoutes:
    """
    The 4 wallet routes must have @limiter.limit(...) appear before @token_required
    in the decorator list. In Python AST, decorators are applied bottom-up but
    listed top-down — so the last decorator in the list is innermost (applied first).

    For the rate limiter to fire before auth:
      The decorator stack (top to bottom in source) must be:
        @route       ← outermost (applied last)
        @limiter.limit(...)  ← middle
        @token_required  ← innermost (applied first, closest to the function)

    In AST terms: limiter.limit appears at a LOWER index than token_required.
    """

    def _parse_func_decorators(self, path: Path, func_name: str):
        """Return the list of decorator AST nodes for the named function."""
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return node.decorator_list
        raise AssertionError(f"{func_name}() not found in {path}")

    def _decorator_name(self, dec) -> str:
        """Return a human-readable name for a decorator node."""
        if isinstance(dec, ast.Call):
            return self._decorator_name(dec.func)
        if isinstance(dec, ast.Attribute):
            return f"{self._decorator_name(dec.value)}.{dec.attr}"
        if isinstance(dec, ast.Name):
            return dec.id
        return ast.dump(dec)

    def _find_decorator_index(self, decorators, predicate) -> int:
        """Return index of first decorator matching predicate, or -1."""
        for i, dec in enumerate(decorators):
            if predicate(dec):
                return i
        return -1

    def _is_limiter_limit(self, dec) -> bool:
        """True if decorator is limiter.limit(...)."""
        if isinstance(dec, ast.Call):
            f = dec.func
            return (
                isinstance(f, ast.Attribute)
                and f.attr == "limit"
                and isinstance(f.value, ast.Name)
                and f.value.id == "limiter"
            )
        return False

    def _is_token_required(self, dec) -> bool:
        """True if decorator is @token_required."""
        if isinstance(dec, ast.Name):
            return dec.id == "token_required"
        if isinstance(dec, ast.Call):
            return self._is_token_required(dec.func)
        return False

    def _assert_limiter_before_token_required(self, path: Path, func_name: str):
        """Assert limiter.limit appears before token_required in the decorator list."""
        decs = self._parse_func_decorators(path, func_name)
        names = [self._decorator_name(d) for d in decs]

        limiter_idx = self._find_decorator_index(decs, self._is_limiter_limit)
        token_idx = self._find_decorator_index(decs, self._is_token_required)

        assert limiter_idx != -1, (
            f"{func_name}(): @limiter.limit not found; decorators: {names}"
        )
        assert token_idx != -1, (
            f"{func_name}(): @token_required not found; decorators: {names}"
        )
        assert limiter_idx < token_idx, (
            f"{func_name}(): @limiter.limit (index {limiter_idx}) must appear BEFORE "
            f"@token_required (index {token_idx}) in source so limiter fires first. "
            f"Decorator order (top→bottom in source): {names}"
        )

    def test_create_bet_limiter_before_token_required(self):
        self._assert_limiter_before_token_required(
            BACKEND_DIR / "routes" / "bets_routes.py", "create_bet"
        )

    def test_accept_bet_limiter_before_token_required(self):
        self._assert_limiter_before_token_required(
            BACKEND_DIR / "routes" / "accept_routes.py", "accept_bet"
        )

    def test_accept_cpu_bet_limiter_before_token_required(self):
        self._assert_limiter_before_token_required(
            BACKEND_DIR / "routes" / "accept_routes.py", "accept_cpu_bet"
        )

    def test_submit_stats_limiter_before_token_required(self):
        self._assert_limiter_before_token_required(
            BACKEND_DIR / "routes" / "submit_routes.py", "submit_stats"
        )
