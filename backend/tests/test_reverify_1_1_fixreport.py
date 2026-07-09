"""
Re-verification tests for item 1.1 fix-report findings.

The Bug Fixer applied 3 findings after the initial QA PASS:
  1. Dead `import jwt` removed from app.py
  2. jwt.exceptions.InvalidKeyError added to the catch tuple in utils/auth.py
  3. All 6 CPU-only route guards changed from 401 to 403

Each test below pins one of those findings. All three must pass for the
re-verification gate to clear.
"""

import ast
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("SECRET_KEY", "test-secret-reverify")
os.environ.setdefault("DATABASE_URL", "postgresql://fake/test")

import jwt
import pytest

from backend.app import app as flask_app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_PY = BACKEND_DIR / "app.py"
UTILS_AUTH_PY = BACKEND_DIR / "utils" / "auth.py"

TEST_SECRET = "test-secret-reverify"

# CPU-only routes that must return 403 (not 401) when called by a non-CPU player.
CPU_ONLY_ROUTES = [
    "/cpu/create_caps_shots_bet",
    "/cpu/create_pong_shots_bet",
    "/cpu/create_beerball_shots_bet",
    "/cpu/create_beerball_score_bet",
    "/cpu/create_caps_score_bet",
    "/cpu/create_pong_score_bet",
]


# ---------------------------------------------------------------------------
# Finding 1: No `import jwt` in app.py (dead import removed)
# ---------------------------------------------------------------------------

def test_no_dead_jwt_import_in_app_py():
    """app.py must not import jwt at the top level; only utils/auth.py uses it."""
    src = APP_PY.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "jwt", (
                    f"app.py line {node.lineno}: dead `import jwt` still present"
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "jwt", (
                f"app.py line {node.lineno}: dead `from jwt import ...` still present"
            )


# ---------------------------------------------------------------------------
# Finding 2: InvalidKeyError in the catch tuple in utils/auth.py
# ---------------------------------------------------------------------------

def test_invalid_key_error_in_catch_tuple():
    """The decorator's except clause must include jwt.exceptions.InvalidKeyError."""
    src = UTILS_AUTH_PY.read_text()
    # Text check is sufficient — the AST form would be a tuple of Attribute nodes.
    assert "InvalidKeyError" in src, (
        "jwt.exceptions.InvalidKeyError not found in utils/auth.py — "
        "config errors will fall through to the generic except block"
    )
    # Also confirm it's in a typed except, not just a comment.
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            handler_src = ast.unparse(node.type)
            if "InvalidKeyError" in handler_src:
                found = True
                break
    assert found, (
        "InvalidKeyError appears in source text but not in any except handler type"
    )


# ---------------------------------------------------------------------------
# Finding 3: CPU-only routes return 403 (not 401) for non-CPU callers
# ---------------------------------------------------------------------------

def _make_jwt(player_id: int, secret: str = TEST_SECRET) -> str:
    return jwt.encode({"id": player_id}, secret, algorithm="HS256")


def _mock_db():
    """Return a context-managed mock connection."""
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


@pytest.mark.parametrize("route", CPU_ONLY_ROUTES)
def test_cpu_route_non_cpu_caller_returns_403(route):
    """Non-CPU authenticated player hitting a CPU-only route must get 403, not 401."""
    token = _make_jwt(player_id=42)  # player 42 is not the CPU account (0)
    with patch("backend.app.SECRET_KEY", TEST_SECRET), \
         patch("backend.utils.auth._app_module", None, create=True), \
         patch("backend.app.get_db", return_value=_mock_db()):
        client = flask_app.test_client()
        resp = client.post(
            route,
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
    # Must be 403 Forbidden (authenticated but not authorized), not 401 Unauthorized.
    assert resp.status_code == 403, (
        f"{route} returned {resp.status_code}, expected 403 for non-CPU caller"
    )
    body = resp.get_json()
    assert body.get("error") == "Forbidden", (
        f"{route} error message was {body!r}, expected 'Forbidden'"
    )


@pytest.mark.parametrize("route", CPU_ONLY_ROUTES)
def test_cpu_route_no_jwt_returns_401(route):
    """Unauthenticated caller must still get 401 (decorator fires before role check)."""
    client = flask_app.test_client()
    resp = client.post(route, json={})
    assert resp.status_code == 401, (
        f"{route} returned {resp.status_code} without JWT, expected 401"
    )
