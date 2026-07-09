"""
Flask decorator for JWT authentication.

All protected routes apply @token_required. On success, flask.g.player_id is
set to the authenticated player's id (int). On failure, a 401 JSON response is
returned before the route handler runs.

SECRET_KEY is looked up at request time from backend.app so that test patches
on `backend.app.SECRET_KEY` are respected without requiring changes to the
existing test suite.
"""

import logging
from functools import wraps

import jwt
from flask import g, jsonify, request

logger = logging.getLogger(__name__)


def token_required(f):
    """Decorator that validates the JWT in the Authorization header.

    Populates flask.g.player_id (int) on success.
    Returns a 401 JSON response on any auth failure.
    Does not perform role/ownership checks — those remain in route handlers.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Lazy import at request time so test patches on backend.app.SECRET_KEY
        # are in effect when the token is decoded.
        import backend.app as _app_module
        secret_key = _app_module.SECRET_KEY

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        token = auth_header.split(' ', 1)[1]
        try:
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            g.player_id = int(payload['id'])
        except (jwt.exceptions.DecodeError, jwt.exceptions.InvalidTokenError, KeyError) as e:
            logger.warning("JWT decode failed: %s", e)
            return jsonify({'error': 'Unauthorized'}), 401
        except Exception as e:
            logger.exception("Unexpected error during JWT decode")
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated
