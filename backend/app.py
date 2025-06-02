from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import auth
from db import get_db
import jwt
from config import SECRET_KEY

# Initialize the Flask app and enable CORS
app = Flask(__name__)
CORS(app)

# Register authentication-related routes from a separate blueprint
app.register_blueprint(auth)

# Endpoint to return the current user's information based on the JWT token
@app.route('/me', methods=['GET'])
def me():
    # Get the token from the Authorization header
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token missing'}), 401

    try:
        # Decode the token using the secret key
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        player_id = decoded['id']
    except:
        return jsonify({'error': 'Invalid token'}), 401

    # Connect to the database and retrieve user info
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, email, profile_pic_url, caps_balance FROM players WHERE id = %s", (player_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()

    # Return the user info as JSON
    return jsonify({
        'username': player[0],
        'email': player[1],
        'profile_pic_url': player[2],
        'caps_balance': player[3]
    })

# Public endpoint to return the leaderboard sorted by caps
@app.route('/leaderboard', methods=['GET'])
def public_leaderboard():
    # Connect to the database and fetch leaderboard data
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, caps FROM players ORDER BY caps DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Return the leaderboard as a JSON list
    return jsonify([{'name': row[0], 'caps': row[1]} for row in rows])

# Simple root endpoint to test if the server is running
@app.route('/')
def hello():
    return 'Flask is working!'
