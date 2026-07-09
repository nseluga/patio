"""
Thin DB accessor that routes through backend.app so that test patches on
``backend.app.get_db`` are picked up at request time — the same pattern used
in ``backend/utils/auth.py`` for ``SECRET_KEY``.
"""


def get_db():
    """Return a live psycopg2 connection, or the test-patched mock."""
    import backend.app as _app_module
    return _app_module.get_db()
