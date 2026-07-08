"""
QA tests for item 0.2: Remove hardcoded JWT secret fallback.

Done when:
  - App fails to boot (raises RuntimeError or similar at import/startup)
    with SECRET_KEY unset in the environment.
  - App boots normally when SECRET_KEY is set.

Strategy: config.py raises RuntimeError at module-load time.  We force
re-imports by evicting the module (and any module that has already imported
it transitively) from sys.modules, then manipulate os.environ to test each
branch.  Each test restores the environment to avoid cross-test pollution.
"""

import importlib
import os
import sys
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Modules whose cached copies must be evicted before re-importing config.py
# so that Python actually re-executes the module body.
_CONFIG_MODULES = [
    'backend.config',
    'backend',
]


def _evict_config():
    """Remove backend.config (and backend package) from the module cache."""
    for mod in _CONFIG_MODULES:
        sys.modules.pop(mod, None)


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Missing SECRET_KEY raises RuntimeError at import time
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_secret_key_raises_runtime_error():
    """Importing config without SECRET_KEY set must raise RuntimeError."""
    original = os.environ.pop('SECRET_KEY', None)
    _evict_config()
    try:
        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            importlib.import_module('backend.config')
    finally:
        # Restore environment and evict again so other tests get a clean slate.
        if original is not None:
            os.environ['SECRET_KEY'] = original
        _evict_config()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Empty string SECRET_KEY also raises RuntimeError
#
# `not ""` is True, so an empty string must be treated the same as a missing
# var — it would produce a trivially forgeable JWT.
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_secret_key_raises_runtime_error():
    """An empty-string SECRET_KEY is as dangerous as a missing one; must also raise."""
    original = os.environ.get('SECRET_KEY')
    os.environ['SECRET_KEY'] = ''
    _evict_config()
    try:
        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            importlib.import_module('backend.config')
    finally:
        if original is not None:
            os.environ['SECRET_KEY'] = original
        else:
            os.environ.pop('SECRET_KEY', None)
        _evict_config()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Valid SECRET_KEY allows normal import (no exception)
# ─────────────────────────────────────────────────────────────────────────────

def test_valid_secret_key_boots_without_error():
    """Config imports cleanly and SECRET_KEY is exposed when the env var is set."""
    os.environ['SECRET_KEY'] = 'test-long-random-secret-for-qa'
    _evict_config()
    try:
        config = importlib.import_module('backend.config')
        assert config.SECRET_KEY == 'test-long-random-secret-for-qa', (
            f"Expected SECRET_KEY to equal the env var value, got: {config.SECRET_KEY!r}"
        )
    finally:
        _evict_config()


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — No hardcoded fallback remains in config.py
#
# Guard against accidental re-introduction of the old default string.
# ─────────────────────────────────────────────────────────────────────────────

def test_no_hardcoded_fallback_in_source():
    """config.py must not contain the old hardcoded secret string."""
    config_path = os.path.join(
        os.path.dirname(__file__), '..', 'config.py'
    )
    with open(os.path.normpath(config_path)) as f:
        source = f.read()
    assert 'your-secret-key' not in source, (
        "Hardcoded fallback 'your-secret-key' still present in backend/config.py"
    )
    # Also confirm there's no inline default passed to os.getenv for SECRET_KEY.
    # The only acceptable form is os.getenv("SECRET_KEY") with no second arg.
    import re
    bad_pattern = re.compile(
        r'os\.getenv\s*\(\s*["\']SECRET_KEY["\']\s*,',
        re.IGNORECASE,
    )
    assert not bad_pattern.search(source), (
        "os.getenv('SECRET_KEY', <default>) found in config.py — remove the fallback"
    )
