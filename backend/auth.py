from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from backend.db import get_db
import jwt
import datetime
from backend.config import SECRET_KEY

# Create a Flask blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Route to register a new player
@auth.route('/register', methods=['POST'])
def register():
    # Get JSON data from the request and hash the password
    data = request.json
    hashed_pw = generate_password_hash(data['password'], method='pbkdf2:sha256')

    # Insert the new player into the database
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO players (username, email, password_hash) VALUES (%s, %s, %s)",
                (data['username'], data['email'], hashed_pw))
    conn.commit()
    cur.close()
    conn.close()

    # Return success response
    return jsonify({'message': 'Player registered'}), 201

# Route to log in an existing player
@auth.route('/login', methods=['POST'])
def login():
    data = request.json

    # Fetch the user's full info using their email
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, password_hash, caps_balance FROM players WHERE email = %s", (data['email'],))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if not result or not check_password_hash(result[3], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    user_id, username, email, _, caps_balance = result

    # Create JWT token
    token = jwt.encode(
        {'id': user_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        SECRET_KEY, algorithm='HS256'
    )

    return jsonify({
        'token': token,
        'user': {
            'id': user_id,
            'username': username,
            'email': email,
            'caps_balance': caps_balance
        }
    })

@auth.route('/me', methods=['GET'])
def get_current_user():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Missing token'}), 401

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload['id']
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
        'bets_won': bets_won,
        'bets_played': bets_played,
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

