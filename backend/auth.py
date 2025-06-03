from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db
import jwt
import datetime
from config import SECRET_KEY

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
            'username': username,
            'email': email,
            'caps_balance': caps_balance
        }
    })
