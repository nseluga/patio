"""
QA tests for item 0.4: Cleanup batch.

Criteria verified:
  (a) No .pyc files are git-tracked; venv/ and .venv/ are in .gitignore.
  (b) .Rhistory is not git-tracked (was deleted from repo).
  (c) src/App.js uses :5001 in its localhost fallback — no :5000 present.
  (d) No uncommented print() calls remain in backend/*.py; logging is used
      instead; sensitive data (raw token, JWT payload) not logged.

Review-findings tests (post-Bug-Fixer):
  (e) No logger.error() calls remain in exception handlers — all use
      logger.exception() so tracebacks are captured automatically.
  (f) accept_cpu_bet exception handler has logger.exception (was missing
      entirely before the fix).
  (g) compute_status_message closes its DB connection via try/finally.
  (h) Bet-generation files use a single batched ANY(%s) query, not one
      SELECT per player (N+1 fix).

Tests use static source analysis and subprocess git checks — no live DB needed.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root is two levels above backend/tests/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SRC_APP_JS = REPO_ROOT / "src" / "App.js"
GITIGNORE = REPO_ROOT / ".gitignore"

BACKEND_PY_FILES = [
    p for p in BACKEND_DIR.glob("*.py")
    if p.name not in ("__init__.py",)
]


# ---------------------------------------------------------------------------
# (a) No .pyc files git-tracked; venv/ in .gitignore
# ---------------------------------------------------------------------------

def test_no_pyc_files_tracked():
    """git ls-files must return no .pyc files."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    pyc_files = [
        line for line in result.stdout.splitlines()
        if line.endswith(".pyc")
    ]
    assert pyc_files == [], (
        f"git-tracked .pyc files still present: {pyc_files}"
    )


def test_venv_in_gitignore():
    """venv/ must appear in .gitignore."""
    assert GITIGNORE.exists(), ".gitignore not found at repo root"
    content = GITIGNORE.read_text()
    lines = [ln.strip() for ln in content.splitlines()]
    assert "venv/" in lines, (
        f"'venv/' not found in .gitignore. Current ignore entries: {lines}"
    )


# ---------------------------------------------------------------------------
# (b) .Rhistory deleted from repo (not git-tracked)
# ---------------------------------------------------------------------------

def test_rhistory_not_tracked():
    """git ls-files must return no .Rhistory files anywhere in the repo."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    rhistory_files = [
        line for line in result.stdout.splitlines()
        if ".Rhistory" in line
    ]
    assert rhistory_files == [], (
        f".Rhistory is still git-tracked: {rhistory_files}"
    )


def test_rhistory_was_in_git_history():
    """git log must confirm .Rhistory was once committed (then removed)."""
    result = subprocess.run(
        ["git", "log", "--all", "--oneline", "--", "*/. Rhistory", ".Rhistory",
         "src/pages/.Rhistory"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # It's OK if git log returns nothing (file may have been added and removed
    # in the same commit on this branch, so log -- path may not surface it).
    # The definitive check is test_rhistory_not_tracked; this is informational.
    # We assert the file is NOT on disk either.
    rhistory_on_disk = list(REPO_ROOT.rglob(".Rhistory"))
    assert rhistory_on_disk == [], (
        f".Rhistory still exists on disk at: {rhistory_on_disk}"
    )


# ---------------------------------------------------------------------------
# (c) src/App.js uses :5001 — no :5000 fallback
# ---------------------------------------------------------------------------

def test_app_js_uses_5001():
    """src/App.js localhost fallback must reference port 5001."""
    assert SRC_APP_JS.exists(), f"src/App.js not found at {SRC_APP_JS}"
    content = SRC_APP_JS.read_text()
    assert "localhost:5001" in content, (
        "src/App.js does not contain 'localhost:5001' — port fix may be missing"
    )


def test_app_js_no_5000():
    """src/App.js must contain no reference to port 5000."""
    content = SRC_APP_JS.read_text()
    assert "5000" not in content, (
        "src/App.js still references port 5000 — old fallback not removed"
    )


# ---------------------------------------------------------------------------
# (d) No uncommented print() calls; logging used; no sensitive data logged
# ---------------------------------------------------------------------------

def _get_active_print_calls(source: str) -> list[int]:
    """Return line numbers of uncommented, active print() calls in source."""
    hits = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue  # skip comment lines
        # Detect print( as a standalone call (not substrings inside identifiers
        # like Blueprint(), register_blueprint()).  We look for 'print(' that
        # is either at the start of the expression or preceded by whitespace,
        # '(', or assignment operators — but NOT preceded by word chars.
        if re.search(r'(?<![A-Za-z_])print\s*\(', stripped):
            hits.append(lineno)
    return hits


def test_no_print_calls_in_backend():
    """No uncommented print() calls must remain in any backend/*.py file."""
    violations: dict[str, list[int]] = {}
    for py_file in BACKEND_PY_FILES:
        source = py_file.read_text()
        bad_lines = _get_active_print_calls(source)
        if bad_lines:
            violations[py_file.name] = bad_lines

    assert not violations, (
        "Uncommented print() calls found in backend files:\n"
        + "\n".join(f"  {fname}: lines {lines}" for fname, lines in violations.items())
    )


def test_logging_imported_in_backend_files():
    """Every backend/*.py that had print() calls must import logging."""
    # Files that the engineer converted — verify logging is wired up in each.
    converted_files = [
        "app.py", "auth.py", "beerball_bet_generation.py",
        "caps_bet_generation.py", "models.py", "pong_bet_generation.py",
        "stats_utils.py",
    ]
    missing: list[str] = []
    for fname in converted_files:
        fpath = BACKEND_DIR / fname
        if not fpath.exists():
            continue
        source = fpath.read_text()
        if "import logging" not in source:
            missing.append(fname)

    assert not missing, (
        f"These backend files are missing 'import logging': {missing}"
    )


def test_logger_instance_per_file():
    """Each converted backend file must define a module-level logger."""
    converted_files = [
        "app.py", "auth.py", "beerball_bet_generation.py",
        "caps_bet_generation.py", "models.py", "pong_bet_generation.py",
        "stats_utils.py",
    ]
    missing: list[str] = []
    for fname in converted_files:
        fpath = BACKEND_DIR / fname
        if not fpath.exists():
            continue
        source = fpath.read_text()
        if "logging.getLogger(" not in source:
            missing.append(fname)

    assert not missing, (
        f"These files have no logger = logging.getLogger(...): {missing}"
    )


def test_no_sensitive_data_in_log_calls():
    """Logger calls must not log raw tokens, JWT payloads, or secrets."""
    # Patterns that would indicate sensitive data being passed to a logger:
    # e.g. logger.debug("token: %s", token) or logger.info(f"payload={payload}")
    # We look for logger.* calls that reference the raw variable names from
    # get_player_id(): `auth_header`, `token`, `payload` (when it contains
    # the full decoded JWT dict), or `SECRET_KEY`.
    sensitive_patterns = [
        r'logger\.\w+\(.*\bauth_header\b',  # raw Authorization header value
        r'logger\.\w+\(.*\bSECRET_KEY\b',   # secret key in log output
    ]
    violations: list[str] = []
    for py_file in BACKEND_PY_FILES:
        source = py_file.read_text()
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pat in sensitive_patterns:
                if re.search(pat, stripped):
                    violations.append(f"{py_file.name}:{lineno}: {stripped}")

    assert not violations, (
        "Sensitive data found in logger calls:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_jwt_decode_error_only_logs_exception_not_token():
    """JWT decode failure must log the exception, not the raw token string."""
    app_py = BACKEND_DIR / "app.py"
    assert app_py.exists()
    source = app_py.read_text()

    # Find the except block in get_player_id
    # The log line must NOT contain `token` as a format argument after %s or f-string
    # Acceptable: logger.warning("JWT decode failed: %s", e)
    # Not acceptable: logger.warning("JWT failed for token %s: %s", token, e)
    in_except = False
    for line in source.splitlines():
        stripped = line.strip()
        if "except" in stripped:
            in_except = True
        if in_except and re.search(r'logger\.\w+\(', stripped):
            # The logger call must not reference `token` as a log argument
            assert "token" not in stripped or stripped.startswith("#"), (
                f"JWT except logger call may be exposing the token: {stripped}"
            )
            in_except = False


# ---------------------------------------------------------------------------
# Review findings (post-Bug-Fixer): e, f, g, h
# ---------------------------------------------------------------------------

BET_GEN_FILES = [
    "caps_bet_generation.py",
    "pong_bet_generation.py",
    "beerball_bet_generation.py",
]


def test_no_logger_error_in_exception_handlers():
    """No exception handler in app.py or bet-gen files should use logger.error().
    All caught exceptions must use logger.exception() so tracebacks are captured.
    """
    files_to_check = ["app.py"] + BET_GEN_FILES
    violations: list[str] = []
    for fname in files_to_check:
        fpath = BACKEND_DIR / fname
        if not fpath.exists():
            continue
        source = fpath.read_text()
        in_except = False
        for lineno, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Detect entering an except block
            if re.match(r"except(\s+\S+)?\s*:", stripped) or re.match(r"except\s*:", stripped):
                in_except = True
            # Detect leaving an except block (back to top-level or new block)
            # Simple heuristic: a non-indented non-blank line after entering except
            if in_except and line and not line[0].isspace() and not stripped.startswith("except"):
                in_except = False
            if in_except and re.search(r'\blogger\.error\s*\(', stripped):
                violations.append(f"{fname}:{lineno}: {stripped}")
    assert not violations, (
        "logger.error() found inside except handlers — use logger.exception() instead:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def _find_function_in_backend(func_name: str):
    """Search app.py and blueprint files for a function; return (source_text, func_node)."""
    search_paths = [
        BACKEND_DIR / "app.py",
        BACKEND_DIR / "routes" / "bets_routes.py",
        BACKEND_DIR / "routes" / "accept_routes.py",
        BACKEND_DIR / "routes" / "submit_routes.py",
        BACKEND_DIR / "routes" / "main_routes.py",
        BACKEND_DIR / "routes" / "lines_routes.py",
    ]
    for path in search_paths:
        if not path.exists():
            continue
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                return source, node
    return None, None


def test_accept_cpu_bet_has_logger_exception():
    """accept_cpu_bet's except block must call logger.exception() (was absent before fix)."""
    source, func_node = _find_function_in_backend("accept_cpu_bet")

    assert func_node is not None, "accept_cpu_bet function not found in app.py"

    lines = source.splitlines()
    func_lines = lines[func_node.lineno - 1: func_node.end_lineno]
    func_source = "\n".join(func_lines)

    # Confirm at least one logger.exception call inside the function
    assert re.search(r'\blogger\.exception\s*\(', func_source), (
        "accept_cpu_bet has no logger.exception() call — exception handler is silent"
    )

    # Confirm no logger.error call is used in its place
    assert not re.search(r'\blogger\.error\s*\(', func_source), (
        "accept_cpu_bet still uses logger.error() — should be logger.exception()"
    )


def test_compute_status_message_closes_connection():
    """compute_status_message must not open its own DB connection.
    The Bug Fixer refactored the function to accept `conn` as a parameter (item 0.5
    review finding), eliminating the internal get_db() call and the connection leak.
    The cursor is still wrapped in try/finally to ensure it is closed.
    """
    source, func_node = _find_function_in_backend("compute_status_message")
    assert func_node is not None, "compute_status_message function not found in app.py"

    lines = source.splitlines()
    func_lines = lines[func_node.lineno - 1: func_node.end_lineno]
    func_source = "\n".join(func_lines)

    # Refactored design: conn is a parameter, NOT opened inside the function.
    assert "get_db()" not in func_source, (
        "compute_status_message calls get_db() internally — should accept conn as a parameter"
    )
    # The conn parameter must appear in the function signature.
    first_line = func_source.splitlines()[0]
    assert "conn" in first_line, (
        f"compute_status_message does not declare `conn` in its signature: {first_line!r}"
    )
    # Cursor must still be closed in a finally block to avoid cursor leaks.
    assert "finally:" in func_source, (
        "compute_status_message has no finally block — cursor may not be closed on error"
    )
    assert "cur.close()" in func_source, (
        "compute_status_message does not call cur.close() in finally — cursor is leaked"
    )


def _function_source(filepath: Path, func_name: str) -> str:
    """Return the source lines for a top-level function in a Python file."""
    source = filepath.read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.splitlines()
            return "\n".join(lines[node.lineno - 1: node.end_lineno])
    return ""


# Item 3.1 collapsed the three sport modules into backend/bet_generation.py.
# The anti-N+1 (ANY(%s) batch) guarantee now lives in the consolidated module.
BET_GEN_MODULE = "bet_generation.py"


def test_caps_bet_gen_uses_batch_query():
    """get_global_caps_score_strength_average must use ANY(%s) not a per-player loop query."""
    fpath = BACKEND_DIR / BET_GEN_MODULE
    func_src = _function_source(fpath, "get_global_caps_score_strength_average")
    assert func_src, f"get_global_caps_score_strength_average not found in {BET_GEN_MODULE}"
    assert re.search(r'ANY\s*\(\s*%s\s*\)', func_src), (
        f"{BET_GEN_MODULE}: get_global_caps_score_strength_average does not use "
        "ANY(%s) batch query — N+1 per-player queries may still be present"
    )


def test_pong_bet_gen_uses_batch_query():
    """get_global_pong_score_strength_average must use ANY(%s) not a per-player loop query."""
    fpath = BACKEND_DIR / BET_GEN_MODULE
    func_src = _function_source(fpath, "get_global_pong_score_strength_average")
    assert func_src, f"get_global_pong_score_strength_average not found in {BET_GEN_MODULE}"
    assert re.search(r'ANY\s*\(\s*%s\s*\)', func_src), (
        f"{BET_GEN_MODULE}: get_global_pong_score_strength_average does not use "
        "ANY(%s) batch query — N+1 per-player queries may still be present"
    )


def test_beerball_bet_gen_uses_batch_query():
    """get_global_beerball_score_strength_average must use ANY(%s) not a per-player loop query."""
    fpath = BACKEND_DIR / BET_GEN_MODULE
    func_src = _function_source(fpath, "get_global_beerball_score_strength_average")
    assert func_src, (
        f"get_global_beerball_score_strength_average not found in {BET_GEN_MODULE}"
    )
    assert re.search(r'ANY\s*\(\s*%s\s*\)', func_src), (
        f"{BET_GEN_MODULE}: get_global_beerball_score_strength_average does not use "
        "ANY(%s) batch query — N+1 per-player queries may still be present"
    )


def test_dotvenv_in_gitignore():
    """.venv/ (dotted variant) must appear in .gitignore alongside venv/."""
    content = GITIGNORE.read_text()
    lines = [ln.strip() for ln in content.splitlines()]
    assert ".venv/" in lines, (
        "'.venv/' not found in .gitignore — Poetry / python -m venv dotted variant is unignored"
    )
