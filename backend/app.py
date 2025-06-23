from flask import Flask, request, jsonify
from flask_cors import CORS
from auth import auth
from db import get_db
import jwt
from config import SECRET_KEY
import psycopg2.extras
from psycopg2.extras import Json

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
        # Strip "Bearer " if present
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded['id']
    except Exception as e:
        print("❌ Token decode failed:", e)
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
        'id': player_id,
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
                yourOutcome, oppOutcome, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s)
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
            bet.get('yourOutcome'), bet.get('oppOutcome'),
            bet.get('status', 'posted')
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
    try:
        cur.execute('''
            SELECT *
            FROM bets
            WHERE status = 'posted' AND posterid != %s
            ORDER BY timePosted DESC
        ''', (player_id,))
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        result = []
        for row in rows:
            bet = dict(zip(colnames, row))
            result.append({
                "id": bet["id"],
                "poster": bet["poster"],
                "posterId": bet["posterid"],
                "timePosted": bet["timeposted"],
                "matchup": bet["matchup"],
                "amount": bet["amount"],
                "lineType": bet["linetype"],
                "lineNumber": bet["linenumber"],
                "gameType": bet["gametype"],
                "gamePlayed": bet["gameplayed"],
                "gameSize": bet["gamesize"],
                "status": bet["status"],
            })

        return jsonify(result)

    finally:
        cur.close()
        conn.close()
    
@app.route("/cpu_bets", methods=["GET"])
def get_cpu_bets():
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT * FROM bets
            WHERE status = 'CPU'
            AND id NOT IN (
                SELECT id FROM cpu_acceptances WHERE accepter_id = %s
            )
            ORDER BY timePosted DESC
        """, (player_id,))

        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        result = []
        for row in rows:
            bet = dict(zip(colnames, row))
            result.append({
                "id": bet["id"],
                "poster": bet["poster"],
                "posterId": bet["posterid"],
                "timePosted": bet["timeposted"],
                "matchup": bet["matchup"],
                "amount": bet["amount"],
                "lineType": bet["linetype"],
                "lineNumber": bet["linenumber"],
                "gameType": bet["gametype"],
                "gamePlayed": bet["gameplayed"],
                "gameSize": bet["gamesize"],
                "status": bet["status"],
            })

        return jsonify(result)

    finally:
        cur.close()
        conn.close()

@app.route("/accept_bet/<bet_id>", methods=["POST"])
def accept_bet(bet_id):
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE bets
            SET accepterId = %s, status = 'accepted'
            WHERE id = %s
        """, (player_id, bet_id))
        conn.commit()
        return jsonify({"status": "accepted"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/accept_cpu_bet/<bet_id>", methods=["POST"])
def accept_cpu_bet(bet_id):
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()

    try:
        # Check if this player already accepted this CPU bet
        cur.execute("""
            SELECT 1 FROM cpu_acceptances WHERE id = %s AND accepter_id = %s
        """, (bet_id, player_id))
        if cur.fetchone():
            return jsonify({"error": "Bet already accepted"}), 400

        # Record the acceptance
        cur.execute("""
            INSERT INTO cpu_acceptances (id, accepter_id)
            VALUES (%s, %s)
        """, (bet_id, player_id))

        conn.commit()
        return jsonify({"status": "accepted"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@app.route("/ongoing_bets", methods=["GET"])
def get_ongoing_bets():
    player_id = get_player_id()
    if not player_id:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM bets
            WHERE status = 'accepted' AND (posterid = %s OR accepterid = %s)
            UNION
            SELECT b.* FROM bets b
            INNER JOIN cpu_acceptances c ON b.id = c.id
            WHERE c.accepter_id = %s
        """, (player_id, player_id, player_id))
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        result = []
        for row in rows:
            bet = dict(zip(colnames, row))
            result.append({
                "id": bet["id"],
                "poster": bet["poster"],
                "posterId": bet["posterid"],
                "accepterId": bet.get("accepterid"),
                "timePosted": bet["timeposted"],
                "matchup": bet["matchup"],
                "amount": bet["amount"],
                "lineType": bet["linetype"],
                "lineNumber": bet["linenumber"],
                "gameType": bet["gametype"],
                "gamePlayed": bet["gameplayed"],
                "gameSize": bet["gamesize"],
                "status": bet["status"],
            })

        return jsonify(result)
    finally:
        cur.close()
        conn.close()

def check_stats_match(bet):
    game_type = bet['gametype']

    if game_type == "Score":
        if not all([
            bet['yourteama'], bet['oppteama'],
            bet['yourteamb'], bet['oppteamb'],
            bet['yourscorea'], bet['oppscorea'],
            bet['yourscoreb'], bet['oppscoreb']
        ]):
            return False

        return (
            bet['yourteama'] == bet['oppteama'] and
            bet['yourteamb'] == bet['oppteamb'] and
            bet['yourscorea'] == bet['oppscorea'] and
            bet['yourscoreb'] == bet['oppscoreb']
        )

    elif game_type == "Shots Made":
        your_player = bet.get('yourplayer', '').strip().lower()
        opp_player = bet.get('oppplayer', '').strip().lower()
        your_shots = bet.get('yourshots')
        opp_shots = bet.get('oppshots')

        return (
            your_player and opp_player and
            your_player == opp_player and
            your_shots is not None and
            opp_shots is not None and
            your_shots == opp_shots
        )

    elif game_type == "Other":
        return (
            bet.get('youroutcome') is not None and
            bet.get('oppoutcome') is not None and
            bet['youroutcome'] == bet['oppoutcome']
        )

    else:
        print("⚠️ Unknown game type:", game_type)

    return False

@app.route('/submit_stats/<bet_id>', methods=['POST'])
def submit_stats(bet_id):
    data = request.json
    player_id = data['playerId']

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get current bet
    cur.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
    bet = cur.fetchone()

    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    # Determine if this is poster or accepter
    is_poster = player_id == bet['posterid']
    is_accepter = player_id == bet['accepterid']

    if not (is_poster or is_accepter):
        return jsonify({"error": "Unauthorized"}), 403

    # Update the corresponding side (poster or accepter)
    update_fields = []
    update_values = []

    if bet['gametype'] == "Score":
        if is_poster:
            update_fields += ["yourTeamA", "yourTeamB", "yourScoreA", "yourScoreB"]
            update_values += [data["yourTeamA"], data["yourTeamB"], data["yourScoreA"], data["yourScoreB"]]
        else:
            update_fields += ["oppTeamA", "oppTeamB", "oppScoreA", "oppScoreB"]
            update_values += [data["yourTeamA"], data["yourTeamB"], data["yourScoreA"], data["yourScoreB"]]

    elif bet['gametype'] == "Shots Made":
        update_fields += ["yourPlayer" if is_poster else "oppPlayer",
                          "yourShots" if is_poster else "oppShots"]
        update_values += [data["yourPlayer"], data["yourShots"]]

    elif bet['gametype'] == "Other":
        update_fields += ["yourOutcome" if is_poster else "oppOutcome"]
        update_values += [data["yourOutcome"]]

    # Build query
    set_clause = ", ".join(f"{field} = %s" for field in update_fields)
    cur.execute(f"UPDATE bets SET {set_clause} WHERE id = %s", (*update_values, bet_id))

    conn.commit()
    
    # Check if stats match → if yes, mark as submitted
    cur.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
    updated_bet = cur.fetchone()
    
    match = check_stats_match(updated_bet)

    # Only mark as submitted if BOTH sides entered AND match
    if match:
        cur.execute("UPDATE bets SET status = 'submitted' WHERE id = %s", (bet_id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Stats submitted successfully", "match": match})

@app.route("/bets", methods=["GET"])
def get_all_bets():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM bets")
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        bets = [dict(zip(colnames, row)) for row in rows]
        return jsonify(bets), 200
    except Exception as e:
        print("❌ Failed to fetch bets:", e)
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()