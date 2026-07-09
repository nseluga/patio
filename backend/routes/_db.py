"""
Thin DB accessor that routes through backend.app so that test patches on
``backend.app.get_db`` are picked up at request time — the same pattern used
in ``backend/utils/auth.py`` for ``SECRET_KEY``.

WARNING — Blueprint authors: always import ``get_db`` from THIS module
(``backend.routes._db``), NOT directly from ``backend.db``.  Importing from
``backend.db`` bypasses the indirection that makes ``patch("backend.app.get_db",
...)`` work in tests.  Any blueprint that imports ``backend.db.get_db`` directly
will silently ignore test patches and hit the real database.
"""


def get_db():
    """Return a live psycopg2 connection, or the test-patched mock."""
    import backend.app as _app_module
    return _app_module.get_db()
