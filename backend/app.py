from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import auth
from db import get_db
import jwt
from config import SECRET_KEY

# Initialize the Flask app and enable CORS
app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "http://localhost:3000"}},
    supports_credentials=True,
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# Register authentication-related routes
app.register_blueprint(auth)

# Helper function to get player ID from JWT
def get_player_id():
    token = request.headers.get('Authorization')
    if not token:
        return None
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded['id']
    except:
        return None

# ---------------- Existing Endpoints ---------------- #

@app.route('/me', methods=['GET'])
def me():
    player_id = get_player_id()
    if not player_id:
        return jsonify({'error': 'Unauthorized'}), 401

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, email, profile_pic_url, caps_balance FROM players WHERE id = %s", (player_id,))
    player = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({
        'playerId': player_id,
        'username': player[0],
        'email': player[1],
        'profile_pic_url': player[2],
        'caps_balance': player[3]
    })

@app.route('/leaderboard', methods=['GET'])
def public_leaderboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, caps_balance FROM players ORDER BY caps_balance DESC LIMIT 5")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{'username': row[0], 'caps_balance': row[1]} for row in rows])

# ---------------- New Bets Endpoints ---------------- #

@app.route("/create_bet", methods=["POST"])
def create_bet():
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    bet = request.json
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('''
            INSERT INTO bets (
                id, poster, posterId, timePosted, matchup, amount,
                lineType, lineNumber, gameType, gamePlayed, gameSize,
                yourTeamA, yourTeamB, oppTeamA, oppTeamB,
                yourScoreA, yourScoreB, oppScoreA, oppScoreB,
                yourPlayer, yourShots, oppPlayer, oppShots,
                yourOutcome, oppOutcome
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s)
        ''', (
            bet.get('id'), bet.get('poster'), bet.get('posterId'), bet.get('timePosted'),
            bet.get('matchup'), bet.get('amount'), bet.get('lineType'), bet.get('lineNumber'),
            bet.get('gameType'), bet.get('gamePlayed'), bet.get('gameSize'),
            Json(bet.get('yourTeamA')), Json(bet.get('yourTeamB')),
            Json(bet.get('oppTeamA')), Json(bet.get('oppTeamB')),
            bet.get('yourScoreA'), bet.get('yourScoreB'),
            bet.get('oppScoreA'), bet.get('oppScoreB'),
            bet.get('yourPlayer'), bet.get('yourShots'),
            bet.get('oppPlayer'), bet.get('oppShots'),
            bet.get('yourOutcome'), bet.get('oppOutcome')
        ))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except Exception as e:
        print("❌ Bet insert failed:", e)
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route("/pvp_bets", methods=["GET"])
def get_pvp_bets():
    player_id = request.args.get("playerId")
    if not player_id:
        return jsonify({"error": "Missing playerId"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM bets
        WHERE accepterId IS NULL AND posterId != %s
        ORDER BY timePosted DESC
    ''', (player_id,))
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]
    bets = [dict(zip(colnames, row)) for row in rows]
    cur.close()
    conn.close()
    return jsonify(bets)

@app.route("/accept_bet/<bet_id>", methods=["POST"])
def accept_bet(bet_id):
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("UPDATE bets SET accepterId = %s WHERE id = %s", (player_id, bet_id))
        conn.commit()
        return jsonify({"status": "accepted"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
