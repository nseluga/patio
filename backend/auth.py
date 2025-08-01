from flask import Blueprint, request, jsonify
from psycopg2.extras import RealDictCursor
import jwt
from backend.db import get_db
from backend.config import SECRET_KEY
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta, timezone

# Create a Flask blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Route to register a new player
@auth.route('/register', methods=['POST'])
def register():
    data = request.json
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
def login():
    data = request.json

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
        print(f"✅ Refreshed caps for {username} on login")

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
def get_current_user():
    print("📌 /me route in auth.py triggered")
    token = request.headers.get('Authorization')
    print("🔐 Authorization header:", token)
    if not token:
        return jsonify({'error': 'Missing token'}), 401

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']
        print("✅ Token decoded. user_id =", user_id)
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    conn = get_db()
    cur = conn.cursor()

    # Get player info
    cur.execute("SELECT username, email, caps_balance FROM players WHERE id = %s", (user_id,))
    player = cur.fetchone()

    if not player:
        cur.close()
        conn.close()
        return jsonify({'error': 'User not found'}), 404

    # Get stats
    cur.execute("SELECT COUNT(*) FROM bets WHERE winner_id = %s", (user_id,))
    bets_won = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM bets WHERE poster_id = %s OR accepter_id = %s", (user_id, user_id))
    bets_played = cur.fetchone()[0]

    # Get recent bets
    cur.execute("""
        SELECT subject, player, line, game_type, posted_at
        FROM bets
        WHERE poster_id = %s OR accepter_id = %s
        ORDER BY posted_at DESC LIMIT 5
    """, (user_id, user_id))
    recent_bets = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        'username': player[0],
        'email': player[1],
        'caps_balance': player[2],
        'pvp_bets_won': bets_won,
        'pvp_bets_played': bets_played,
        'recent_bets': [
            {
                'subject': r[0],
                'player': r[1],
                'line': r[2],
                'gameType': r[3],
                'timePosted': r[4].isoformat()
            } for r in recent_bets
        ]
    })

bets = Blueprint('bets', __name__)

@bets.route('/bets', methods=['POST'])
def create_bet():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        player_id = payload['id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.json
    amount = data.get('amount')  # amount of caps being wagered
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({'error': 'Invalid or missing amount'}), 400

    conn = get_db()
    cur = conn.cursor()

    # ✅ Check if player has enough caps
    cur.execute('SELECT caps_balance FROM players WHERE id = %s', (player_id,))
    result = cur.fetchone()
    if result is None:
        return jsonify({'error': 'Player not found'}), 404

    current_caps = result[0]
    if current_caps < amount:
        return jsonify({'error': 'Insufficient cap balance'}), 400

    # ✅ Deduct caps temporarily (optional: "lock" them instead of removing)
    cur.execute('UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s', (amount, player_id))

    # ✅ Insert the new bet
    cur.execute('''
        INSERT INTO bets (poster_id, game_type, subject, line, amount)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    ''', (player_id, data['game_type'], data['subject'], data['line'], amount))
    bet_id = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'Bet created', 'bet_id': bet_id})
