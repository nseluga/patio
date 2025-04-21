from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db
import jwt
import datetime
from config import SECRET_KEY

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_pw = generate_password_hash(data['password'], method='sha256')

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO players (username, email, password_hash) VALUES (%s, %s, %s)",
                (data['username'], data['email'], hashed_pw))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'Player registered'}), 201

@auth.route('/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash FROM players WHERE email = %s", (data['email'],))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if not result or not check_password_hash(result[1], data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = jwt.encode(
        {'id': result[0], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        SECRET_KEY, algorithm='HS256'
    )
    return jsonify({'token': token})
