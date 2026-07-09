"""
Shared Flask extensions — instantiated here, bound to the app in create_app().

This module exists so blueprints can import the limiter object without
causing a circular import with backend.app.

Usage in blueprints:
    from backend.extensions import limiter
    @some_bp.route("/foo")
    @limiter.limit("10 per minute")
    def foo(): ...
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Render in-memory store resets on each dyno restart — fine at this scale.
limiter = Limiter(
    get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://",
)
