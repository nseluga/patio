from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import auth
from db import get_db
import jwt
from config import SECRET_KEY

app = Flask(__name__)
CORS(app)
app.register_blueprint(auth)

@app.route('/me', methods=['GET'])
def me():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing'}), 401
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        player_id = decoded['id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, email, profile_pic_url, caps_balance FROM players WHERE id = %s", (player_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({
        'username': player[0],
        'email': player[1],
        'profile_pic_url': player[2],
        'caps_balance': player[3]
    })

@app.route('/leaderboard', methods=['GET'])
def public_leaderboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, caps FROM players ORDER BY caps DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{'name': row[0], 'caps': row[1]} for row in rows])

@app.route('/')
def hello():
    return 'Flask is working!'
