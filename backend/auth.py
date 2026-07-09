from flask import Blueprint, g, request, jsonify
from psycopg2.extras import RealDictCursor
import jwt
import logging
from backend.db import get_db
from backend.config import SECRET_KEY
from backend.extensions import limiter
from backend.utils.auth import token_required
from backend.validation import require_fields
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Create a Flask blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Route to register a new player
@auth.route('/register', methods=['POST'])
@limiter.limit("10 per minute")
def register():
    data, err = require_fields(request.json, 'username', 'email', 'password')
    if err:
        return err

    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')

    conn = get_db()
    cur = conn.cursor()

    # ✅ Insert with caps_balance set to 500
    cur.execute("""
        INSERT INTO players (username, email, password_hash, caps_balance)
        VALUES (%s, %s, %s, %s)
    """, (data['username'], data['email'], hashed_pw, 500))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'Player registered'}), 201


# Route to log in an existing player
@auth.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data, err = require_fields(request.json, 'email', 'password')
    if err:
        return err

    conn = get_db()
    cur = conn.cursor()

    # Fetch player record including pvp stats
    cur.execute("""
        SELECT id, username, email, password_hash, caps_balance, last_caps_refresh,
               pvp_bets_played, pvp_bets_won
        FROM players
        WHERE email = %s
    """, (data['email'],))
    result = cur.fetchone()

    if not result:
        cur.close()
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401

    # Unpack result
    (user_id, username, email, password_hash,
     caps_balance, last_refresh,
     pvp_bets_played, pvp_bets_won) = result

    if not check_password_hash(password_hash, data['password']):
        cur.close()
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401

    # Cap refresh logic
    now = datetime.now(timezone.utc)
    if last_refresh and last_refresh.tzinfo is None:
        last_refresh = last_refresh.replace(tzinfo=timezone.utc)
    if not last_refresh:
        last_refresh = now - timedelta(days=999)

    caps_refreshed = False
    if user_id != 0 and now - last_refresh > timedelta(days=7):
        caps_balance += 100
        cur.execute("""
            UPDATE players
            SET caps_balance = %s, last_caps_refresh = %s
            WHERE id = %s
        """, (caps_balance, now, user_id))
        caps_refreshed = True
        logger.info("Refreshed caps for %s on login", username)

    conn.commit()
    cur.close()
    conn.close()

    # Create JWT
    token = jwt.encode(
        {'id': user_id, 'exp': datetime.now(timezone.utc) + timedelta(hours=24)},
        SECRET_KEY, algorithm='HS256'
    )

    return jsonify({
        'token': token,
        'user': {
            'id': user_id,
            'username': username,
            'email': email,
            'caps_balance': caps_balance,
            'pvp_bets_won': pvp_bets_won,
            'pvp_bets_played': pvp_bets_played
        },
        'caps_refreshed': caps_refreshed
    })



@auth.route('/me', methods=['GET'])
@token_required
def get_current_user():
    user_id = g.player_id

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT username, email, caps_balance, pvp_bets_played, pvp_bets_won FROM players WHERE id = %s",
        (user_id,)
    )
    player = cur.fetchone()

    if not player:
        cur.close()
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    cur.execute("""
        SELECT "gameType" AS gametype, status, amount, "timePosted" AS timeposted
        FROM bets WHERE "posterId" = %s OR "accepterId" = %s
        ORDER BY "timePosted" DESC LIMIT 5
    """, (user_id, user_id))
    recent_bets = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        'username': player[0],
        'email': player[1],
        'caps_balance': player[2],
        'pvp_bets_played': player[3],
        'pvp_bets_won': player[4],
        'recent_bets': [
            {
                'gameType': r[0],
                'status': r[1],
                'amount': r[2],
                'timePosted': r[3].isoformat() if r[3] else None,
            }
            for r in recent_bets
        ],
    })
