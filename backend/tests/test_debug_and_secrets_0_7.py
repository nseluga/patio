"""
QA tests for item 0.7: Stop leaking secrets in logs + disable debug mode.

Done when:
  (1) No log line in app.py or auth.py contains a token, JWT payload, or raw
      Authorization header value.
  (2) Debug mode is off outside local dev: FLASK_DEBUG=0 and FLASK_ENV=production
      in backend/.flaskenv.

Tests use static source analysis — no live DB or running server required.
"""

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FLASKENV = BACKEND_DIR / ".flaskenv"

# Files scoped to this item (engineer report confirmed these two were audited)
AUTH_FILES = [
    BACKEND_DIR / "app.py",
    BACKEND_DIR / "auth.py",
]


# ---------------------------------------------------------------------------
# Criterion 1 — No log line contains a raw token or JWT payload
# ---------------------------------------------------------------------------

def test_no_raw_token_in_logger_calls():
    """
    Logger calls in app.py and auth.py must not pass the raw token string or
    the raw Authorization header as a log argument.

    Acceptable: logger.warning("JWT decode failed: %s", e)
    Not acceptable: logger.warning("Token: %s", token)
                    logger.debug("header=%s", auth_header)
    """
    # Variable names that would expose secrets if logged
    secret_vars = [r"\btoken\b", r"\bauth_header\b", r"\bpayload\b"]
    violations: list[str] = []

    for path in AUTH_FILES:
        assert path.exists(), f"Expected file not found: {path}"
        lines = path.read_text().splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Only inspect lines that contain a logger call
            if not re.search(r"logger\.\w+\(", stripped):
                continue
            for var_pat in secret_vars:
                if re.search(var_pat, stripped):
                    violations.append(f"{path.name}:{lineno}: {stripped}")
                    break  # one violation per line is enough

    assert not violations, (
        "Logger calls reference secret-bearing variables:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_secret_key_in_logger_calls():
    """SECRET_KEY must never appear as a log argument anywhere in auth files."""
    violations: list[str] = []

    for path in AUTH_FILES:
        lines = path.read_text().splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if re.search(r"logger\.\w+\(", stripped) and "SECRET_KEY" in stripped:
                violations.append(f"{path.name}:{lineno}: {stripped}")

    assert not violations, (
        "SECRET_KEY found inside a logger call:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_print_with_token_in_auth_files():
    """
    No uncommented print() call in app.py or auth.py may reference token,
    auth_header, payload, or SECRET_KEY.
    """
    secret_vars = ["token", "auth_header", "payload", "SECRET_KEY"]
    violations: list[str] = []

    for path in AUTH_FILES:
        lines = path.read_text().splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "print(" not in stripped:
                continue
            for var in secret_vars:
                if var in stripped:
                    violations.append(f"{path.name}:{lineno}: {stripped}")
                    break

    assert not violations, (
        "print() call references a secret-bearing variable:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_jwt_except_block_does_not_log_token():
    """
    The JWT except block in get_player_id() (app.py) must log only the
    exception object, never the decoded payload or the raw token string.

    Scans each except clause and checks the first logger call following it.
    """
    app_py = BACKEND_DIR / "app.py"
    lines = app_py.read_text().splitlines()

    in_except = False
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"except\b", stripped):
            in_except = True
            continue
        if in_except and re.search(r"logger\.\w+\(", stripped):
            assert not re.search(r"\btoken\b", stripped), (
                f"app.py:{lineno}: JWT except block logs the raw token: {stripped}"
            )
            assert not re.search(r"\bpayload\b", stripped), (
                f"app.py:{lineno}: JWT except block logs the JWT payload: {stripped}"
            )
            in_except = False


# ---------------------------------------------------------------------------
# Criterion 2 — Debug mode disabled in .flaskenv
# ---------------------------------------------------------------------------

def test_flaskenv_exists():
    """.flaskenv must exist in the backend directory."""
    assert FLASKENV.exists(), f"backend/.flaskenv not found at {FLASKENV}"


def test_flaskenv_debug_is_zero():
    """FLASK_DEBUG must be set to 0 in backend/.flaskenv."""
    content = FLASKENV.read_text()
    # Accept "FLASK_DEBUG=0" with or without the leading `export `
    matches = re.findall(r"(?:export\s+)?FLASK_DEBUG\s*=\s*(\S+)", content)
    assert matches, "FLASK_DEBUG is not set in backend/.flaskenv"
    # All occurrences (there should be only one) must be 0
    non_zero = [v for v in matches if v != "0"]
    assert not non_zero, (
        f"FLASK_DEBUG has non-zero value(s) in .flaskenv: {non_zero}"
    )


def test_flaskenv_env_is_production():
    """FLASK_ENV must be set to 'production' in backend/.flaskenv."""
    content = FLASKENV.read_text()
    matches = re.findall(r"(?:export\s+)?FLASK_ENV\s*=\s*(\S+)", content)
    assert matches, "FLASK_ENV is not set in backend/.flaskenv"
    non_prod = [v for v in matches if v != "production"]
    assert not non_prod, (
        f"FLASK_ENV has non-production value(s) in .flaskenv: {non_prod}"
    )


def test_no_app_run_with_debug_true():
    """
    app.py must not contain app.run(debug=True) — debug mode enabled at the
    source level overrides env-var settings.
    """
    app_py = BACKEND_DIR / "app.py"
    source = app_py.read_text()
    bad = re.search(r"app\.run\s*\(.*debug\s*=\s*True", source)
    assert not bad, (
        "app.run(debug=True) found in app.py — remove or set debug=False"
    )


def test_procfile_has_no_debug_flag():
    """The Procfile's flask run command must not include a --debug flag."""
    procfile = REPO_ROOT / "Procfile"
    if not procfile.exists():
        pytest.skip("Procfile not found — skipping")
    content = procfile.read_text()
    assert "--debug" not in content, (
        "Procfile contains --debug flag; remove it for production safety"
    )
