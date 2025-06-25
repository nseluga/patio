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
            bet["status_message"] = compute_status_message(bet, player_id)
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
                "status_message": bet["status_message"],
            })

        return jsonify(result)
    finally:
        cur.close()
        conn.close()

def check_stats_match(bet):
    game_type = bet.get('gametype')

    if game_type == "Score":
        required_fields = [
            bet.get('yourteama'), bet.get('oppteama'),
            bet.get('yourteamb'), bet.get('oppteamb'),
            bet.get('yourscorea'), bet.get('oppscorea'),
            bet.get('yourscoreb'), bet.get('oppscoreb')
        ]
        if not all(field is not None for field in required_fields):
            return False

        return (
            bet['yourteama'] == bet['oppteama'] and
            bet['yourteamb'] == bet['oppteamb'] and
            bet['yourscorea'] == bet['oppscorea'] and
            bet['yourscoreb'] == bet['oppscoreb']
        )

    elif game_type == "Shots Made":
        player_1 = (bet.get('yourplayer') or '').strip().lower()
        player_2 = (bet.get('oppplayer') or '').strip().lower()
        your_shots = bet.get('yourshots')
        opp_shots = bet.get('oppshots')

        return (
            player_1 and player_2 and
            player_1 == player_2 and
            bet.get('yourshots') is not None and
            bet.get('oppshots') is not None and
            bet['yourshots'] == bet['oppshots']
        )


    elif game_type == "Other":
        your_outcome = bet.get('youroutcome')
        opp_outcome = bet.get('oppoutcome')

        return (
            your_outcome is not None and
            opp_outcome is not None and
            your_outcome == opp_outcome
        )

    print("⚠️ Unknown game type:", game_type)
    return False


def compute_status_message(bet, player_id):
    game_type = bet["gametype"]
    is_poster = player_id == bet.get("posterid")
    is_accepter = player_id == bet.get("accepterid")

    if not (is_poster or is_accepter):
        return "Unknown user"

    # Score Game
    if game_type == "Score":
        your_teamA = bet["yourteama"] if is_poster else bet["oppteama"]
        your_teamB = bet["yourteamb"] if is_poster else bet["oppteamb"]
        your_scoreA = bet["yourscorea"] if is_poster else bet["oppscorea"]
        your_scoreB = bet["yourscoreb"] if is_poster else bet["oppscoreb"]

        opp_teamA = bet["oppteama"] if is_poster else bet["yourteama"]
        opp_teamB = bet["oppteamb"] if is_poster else bet["yourteamb"]
        opp_scoreA = bet["oppscorea"] if is_poster else bet["yourscorea"]
        opp_scoreB = bet["oppscoreb"] if is_poster else bet["yourscoreb"]

        you_submitted = all([your_teamA, your_teamB, your_scoreA is not None, your_scoreB is not None])
        opp_submitted = all([opp_teamA, opp_teamB, opp_scoreA is not None, opp_scoreB is not None])

        if you_submitted and opp_submitted:
            if your_teamA == opp_teamA and your_teamB == opp_teamB:
                if your_scoreA == opp_scoreA and your_scoreB == opp_scoreB:
                    return "✅ Match confirmed"
                return "❌ Scores not matching, please communicate"
            return "❌ Player names do not match"
        elif you_submitted:
            return "Waiting for other player to input stats"
        return "You have not submitted stats yet"

    # Shots Made Game
    elif game_type == "Shots Made":
        your_player = bet["yourplayer"] if is_poster else bet["oppplayer"]
        your_shots = bet["yourshots"] if is_poster else bet["oppshots"]
        opp_player = bet["oppplayer"] if is_poster else bet["yourplayer"]
        opp_shots = bet["oppshots"] if is_poster else bet["yourshots"]

        you_submitted = your_player and your_shots is not None
        opp_submitted = opp_player and opp_shots is not None

        if you_submitted and opp_submitted:
            if your_player == opp_player:
                if your_shots == opp_shots:
                    return "✅ Match confirmed"
                return "❌ Stats not matching, please communicate"
            return "❌ Player names do not match"
        elif you_submitted:
            return "Waiting for other player to input stats"
        return "You have not submitted stats yet"

    # Other Game
    elif game_type == "Other":
        your_outcome = bet["youroutcome"] if is_poster else bet["oppoutcome"]
        opp_outcome = bet["oppoutcome"] if is_poster else bet["youroutcome"]

        you_submitted = your_outcome not in [None, ""]
        opp_submitted = opp_outcome not in [None, ""]

        if you_submitted and opp_submitted:
            if your_outcome == opp_outcome:
                return "✅ Match confirmed"
            return "❌ Outcome not matching, please communicate"
        elif you_submitted:
            return "Waiting for other player to input stats"
        return "You have not submitted stats yet"

    return "Unknown game type"

@app.route('/submit_stats/<bet_id>', methods=['POST'])
def submit_stats(bet_id):
    data = request.json
    player_id = data['playerId']

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def insert_stat(subject_id, game_played, game_type, stat_name, stat_value):
        cur.execute("""
            INSERT INTO player_stats (player_id, game_played, game_type, stat_name, stat_value)
            VALUES (%s, %s, %s, %s, %s)
        """, (subject_id, game_played, game_type, stat_name, stat_value))

    # Fetch the current bet
    cur.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
    bet = cur.fetchone()
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    is_poster = player_id == bet['posterid']
    is_accepter = player_id == bet['accepterid']
    if not (is_poster or is_accepter):
        return jsonify({"error": "Unauthorized"}), 403

    # Prepare stat update fields
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

    # Execute update
    set_clause = ", ".join(f"{field} = %s" for field in update_fields)
    cur.execute(f"UPDATE bets SET {set_clause} WHERE id = %s", (*update_values, bet_id))
    conn.commit()

    # Re-fetch updated bet
    cur.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
    updated_bet = cur.fetchone()
    match = check_stats_match(updated_bet)
    status_message = compute_status_message(updated_bet, player_id)

    if match:
        cur.execute("UPDATE bets SET status = 'submitted' WHERE id = %s", (bet_id,))

        if updated_bet['gametype'] == "Shots Made":
            subject_name = (updated_bet.get('yourplayer') or updated_bet.get('oppplayer')).strip()
            stat_value = updated_bet['yourshots']  # same as oppshots after match

            # Get player ID by name
            cur.execute("SELECT id FROM players WHERE LOWER(username) = LOWER(%s)", (subject_name,))
            result = cur.fetchone()

            if result:
                subject_id = result['id']
                insert_stat(subject_id, updated_bet['gameplayed'], updated_bet['gametype'], "shots_made", stat_value)
            else:
                print(f"❌ No player found with name: {subject_name}")

        elif updated_bet['gametype'] == "Score":
            insert_stat(updated_bet['posterid'], updated_bet['gameplayed'], updated_bet['gametype'], "score_a", updated_bet['yourscorea'])
            insert_stat(updated_bet['posterid'], updated_bet['gameplayed'], updated_bet['gametype'], "score_b", updated_bet['yourscoreb'])
            insert_stat(updated_bet['accepterid'], updated_bet['gameplayed'], updated_bet['gametype'], "score_a", updated_bet['oppscorea'])
            insert_stat(updated_bet['accepterid'], updated_bet['gameplayed'], updated_bet['gametype'], "score_b", updated_bet['oppscoreb'])

        elif updated_bet['gametype'] == "Other":
            insert_stat(updated_bet['posterid'], updated_bet['gameplayed'], updated_bet['gametype'], "outcome", updated_bet['youroutcome'])
            insert_stat(updated_bet['accepterid'], updated_bet['gameplayed'], updated_bet['gametype'], "outcome", updated_bet['oppoutcome'])

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": "Stats submitted successfully",
        "match": match,
        "status_message": status_message
    })



        # # Insert stats into player_stats table
        # if bet['gametype'] == "Shots Made":
        #     insert_stat(bet['posterid'], bet['gameplayed'], bet['gametype'], "shots_made", bet['yourshots'])
        #     insert_stat(bet['accepterid'], bet['gameplayed'], bet['gametype'], "shots_made", bet['oppshots'])

        # elif bet['gametype'] == "Score":
        #     insert_stat(bet['posterid'], bet['gameplayed'], bet['gametype'], "score_a", bet['yourscorea'])
        #     insert_stat(bet['posterid'], bet['gameplayed'], bet['gametype'], "score_b", bet['yourscoreb'])
        #     insert_stat(bet['accepterid'], bet['gameplayed'], bet['gametype'], "score_a", bet['oppscorea'])
        #     insert_stat(bet['accepterid'], bet['gameplayed'], bet['gametype'], "score_b", bet['oppscoreb'])

        # elif bet['gametype'] == "Other":
        #     insert_stat(bet['posterid'], bet['gameplayed'], bet['gametype'], "outcome", bet['youroutcome'])
        #     insert_stat(bet['accepterid'], bet['gameplayed'], bet['gametype'], "outcome", bet['oppoutcome'])

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": "Stats submitted successfully",
        "match": match,
        "status_message": status_message
    })

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

# @app.route("/stats/averages/<stat_name>", methods=["GET"])
# def get_average_stats(stat_name):
#     conn = get_db()
#     cur = conn.cursor()
    
#     try:
#         cur.execute("""
#             SELECT player_id, game_played, AVG(stat_value) AS average
#             FROM player_stats
#             WHERE stat_name = %s
#             GROUP BY player_id, game_played
#         """, (stat_name,))
#         rows = cur.fetchall()
#         return jsonify([
#             {
#                 "playerId": row[0],
#                 "gamePlayed": row[1],
#                 "average": float(row[2])
#             }
#             for row in rows
#         ])

#     except Exception as e:
#         print("❌ Failed to compute averages:", e)
#         return jsonify({"error": str(e)}), 500

#     finally:
#         cur.close()
#         conn.close()
