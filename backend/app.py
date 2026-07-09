"""
Flask application factory for Patio.

Kept intentionally thin: imports, CORS, logging setup, and blueprint registration.
Route logic lives in backend/routes/*.py.

Re-exports `get_db` and `SECRET_KEY` at module level so existing test patches
(`patch("backend.app.get_db", ...)` and `patch("backend.app.SECRET_KEY", ...)`)
continue to resolve. The auth decorator in `backend/utils/auth.py` does a lazy
import of this module at request time specifically to honour those patches.
"""

import logging
import os

from flask import Flask
from flask_cors import CORS

from backend.config import SECRET_KEY  # re-exported for test patch compatibility
from backend.db import get_db  # re-exported for test patch compatibility

logger = logging.getLogger(__name__)


def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    # ---------------------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------------------
    CORS(
        app,
        resources={r"/*": {"origins": [
            "http://localhost:3000",
            os.getenv("FRONTEND_URL", "https://your-app.vercel.app")
        ]}},
        supports_credentials=True,
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"]
    )

    # ---------------------------------------------------------------------------
    # Logging
    # ---------------------------------------------------------------------------
    logging.basicConfig(level=logging.INFO)

    # ---------------------------------------------------------------------------
    # Blueprints
    # ---------------------------------------------------------------------------
    from backend.auth import auth
    from backend.routes.accept_routes import accept_bp
    from backend.routes.bets_routes import bets_bp
    from backend.routes.lines_routes import lines_bp
    from backend.routes.main_routes import main_bp
    from backend.routes.submit_routes import submit_bp

    app.register_blueprint(auth)
    app.register_blueprint(bets_bp)
    app.register_blueprint(accept_bp)
    app.register_blueprint(submit_bp)
    app.register_blueprint(lines_bp)
    app.register_blueprint(main_bp)

    return app


# Module-level app instance — required by `flask --app backend/app run` CLI.
app = create_app()
