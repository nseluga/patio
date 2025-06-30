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
    if player_id is None:
        return jsonify({"error": "Unauthorized"}), 401

    bet = request.json
    amount = bet.get('amount', 0)
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"error": "Invalid or missing amount"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        # Check if player has enough caps
        cur.execute("SELECT caps_balance FROM players WHERE id = %s", (player_id,))
        caps = cur.fetchone()
        if not caps or caps[0] < amount:
            return jsonify({"error": "Insufficient caps"}), 400

        # Deduct caps from poster
        cur.execute("UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s", (amount, player_id))

        # Insert bet
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
    if player_id is None:
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
    if player_id is None:
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
    if player_id is None:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    cur = conn.cursor()

    try:
        # Get amount and poster ID
        cur.execute("SELECT amount, posterId FROM bets WHERE id = %s AND status = 'posted'", (bet_id,))
        bet = cur.fetchone()
        if not bet:
            return jsonify({"error": "Bet not found or already accepted"}), 404

        amount, poster_id = bet

        # Check caps of accepter
        cur.execute("SELECT caps_balance FROM players WHERE id = %s", (player_id,))
        caps = cur.fetchone()
        if not caps or caps[0] < amount:
            return jsonify({"error": "Insufficient caps"}), 400

        # Deduct caps from accepter
        cur.execute("UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s", (amount, player_id))

        # Accept the bet
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


@app.route("/ongoing_bets", methods=["GET"])
def get_ongoing_bets():
    player_id = get_player_id()
    if player_id is None:
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
            WHERE c.accepter_id = %s AND c.match_confirmed = FALSE
            UNION
            SELECT * FROM bets
            WHERE status = 'CPU' AND posterid = 0 AND %s = 0
        """, (player_id, player_id, player_id, player_id))
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
    if bet["status"] == "CPU" and player_id != 0:
        cur = get_db().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT match_confirmed, attempted FROM cpu_acceptances
            WHERE id = %s AND accepter_id = %s
        """, (bet["id"], player_id))
        row = cur.fetchone()
        cur.close()

        if not row:
            return "You have not submitted stats yet"
        if row["match_confirmed"]:
            return "✅ Match confirmed"
        if row["attempted"]:
            return "❌ Stats do not match"
        return "You have not submitted stats yet"
    
    game_type = bet["gametype"]
    is_poster = player_id == bet.get("posterid")
    is_accepter = player_id == bet.get("accepterid")

    if (is_poster or is_accepter) is None:
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

def get_or_create_bettable_player(cur, name):
    cur.execute("SELECT id FROM bettable_players WHERE LOWER(name) = LOWER(%s)", (name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    
    cur.execute(
        "INSERT INTO bettable_players (name) VALUES (%s) RETURNING id",
        (name,)
    )
    return cur.fetchone()["id"]

@app.route('/submit_stats/<bet_id>', methods=['POST'])
def submit_stats(bet_id):
    data = request.json
    player_id = data['playerId']

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def insert_stat(bet_id, subject_id, game_played, game_type, stat_name, stat_value, team=None, team_size=None):
        cur.execute("""
            INSERT INTO bettable_player_stats (bet_id, subject_player, gamePlayed, gameType, stat_name, stat_value, team, team_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (bet_id, subject_id, game_played, game_type, stat_name, stat_value, team, team_size))

    # Fetch the current bet
    cur.execute("SELECT * FROM bets WHERE id = %s", (bet_id,))
    bet = cur.fetchone()
    if not bet:
        return jsonify({"error": "Bet not found"}), 404

    is_poster = player_id == bet['posterid']
    is_accepter = player_id == bet['accepterid']
    is_cpu_bet = bet['status'] == 'CPU'
    is_admin = player_id == 0

    # ✅ If non-admin tries to submit to a CPU bet, do nothing and return success
    if is_cpu_bet and not is_admin:
        game_type = bet['gametype']
        match = False

        if game_type == "Score":
            match = (
                data["yourTeamA"] == bet["yourteama"] and
                data["yourTeamB"] == bet["yourteamb"] and
                int(data["yourScoreA"]) == bet["yourscorea"] and
                int(data["yourScoreB"]) == bet["yourscoreb"]
            )

        elif game_type == "Shots Made":
            match = (
                data["yourPlayer"].strip().lower() == bet["yourplayer"].strip().lower() and
                int(data["yourShots"]) == bet["yourshots"]
            )

        elif game_type == "Other":
            match = int(data["yourOutcome"]) == bet["youroutcome"]
        
        if match:
            cur.execute("""
                UPDATE cpu_acceptances
                SET match_confirmed = TRUE
                WHERE id = %s AND accepter_id = %s
            """, (bet_id, player_id))

        else: 
            cur.execute("""
                UPDATE cpu_acceptances
                SET attempted = TRUE
                WHERE id = %s AND accepter_id = %s
            """, (bet_id, player_id))
        
        # 🔄 Re-fetch the bet for fresh data (optional, since bet itself didn't change, just cpu_acceptances)
        updated_bet = bet  # can reuse bet if no need to refetch from `bets`
        status_message = compute_status_message(updated_bet, player_id)

    else:
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
            # ✅ Update bet status
            cur.execute("UPDATE bets SET status = 'submitted' WHERE id = %s", (bet_id,))

            # ✅ Determine cap payout
            poster_id = updated_bet['posterid']
            accepter_id = updated_bet['accepterid']
            amount = updated_bet['amount']

            if is_poster:
                winner_id = poster_id
                loser_id = accepter_id
            else:
                winner_id = accepter_id
                loser_id = poster_id

            # ✅ Award winner with total pot (2x amount)
            cur.execute("""
                UPDATE players
                SET caps_balance = caps_balance + %s
                WHERE id = %s
            """, (2 * amount, winner_id))

            # ✅ Log all players to bettable_player_stats (creating them if needed)
            if updated_bet['gametype'] == "Shots Made":
                names_stats = [
                    (updated_bet.get('yourplayer'), updated_bet['yourshots']),
                    (updated_bet.get('oppplayer'), updated_bet['oppshots']),
                ]

                seen = set()
                for name, stat in names_stats:
                    if name:
                        cleaned_name = name.strip().lower()
                        if cleaned_name in seen:
                            continue
                        seen.add(cleaned_name)
                        subject_id = get_or_create_bettable_player(cur, name.strip())
                        insert_stat(
                            bet_id,
                            subject_id,
                            updated_bet['gameplayed'],
                            updated_bet['gametype'],
                            "shots_made",
                            stat,
                            team=None,            # ← add this now
                            team_size=None        # ← leave empty for now
                        )

            elif updated_bet['gametype'] == "Score":
                names_stats = [
                    (updated_bet.get('yourplayera'), updated_bet['yourscorea']),
                    (updated_bet.get('yourplayerb'), updated_bet['yourscoreb']),
                    (updated_bet.get('oppplayera'), updated_bet['oppscorea']),
                    (updated_bet.get('oppplayerb'), updated_bet['oppscoreb']),
                ]

                team_lookup = {
                    "yourplayera": "A", "yourplayerb": "A",
                    "oppplayera": "B", "oppplayerb": "B"
                }

                seen = set()
                for key in ["yourplayera", "yourplayerb", "oppplayera", "oppplayerb"]:
                    name = updated_bet.get(key)
                    stat_key = "yourscorea" if key.endswith("a") else "yourscoreb"
                    if "opp" in key:
                        stat_key = stat_key.replace("your", "opp")

                    stat = updated_bet.get(stat_key)

                    if name and stat is not None:
                        cleaned_name = name.strip().lower()
                        if cleaned_name in seen:
                            continue
                        seen.add(cleaned_name)
                        subject_id = get_or_create_bettable_player(cur, name.strip())
                        insert_stat(
                            bet_id,
                            subject_id,
                            updated_bet['gameplayed'],
                            updated_bet['gametype'],
                            "score",
                            stat,
                            team=team_lookup[key],
                            team_size=updated_bet.get("none") # update once team size is tracked
                        )

            elif updated_bet['gametype'] == "Other":
                names_stats = [
                    (updated_bet.get('yourplayer'), updated_bet.get('youroutcome')),
                    (updated_bet.get('oppplayer'), updated_bet.get('oppoutcome')),
                ]

                seen = set()
                for name, stat in names_stats:
                    if name:
                        cleaned_name = name.strip().lower()
                        if cleaned_name in seen:
                            continue
                        seen.add(cleaned_name)
                        subject_id = get_or_create_bettable_player(cur, name.strip())
                        insert_stat(
                        bet_id,
                        subject_id,
                        updated_bet['gameplayed'],
                        updated_bet['gametype'],
                        "other",
                        stat,
                        team=None,            # ← add this now
                        team_size=None        # ← leave empty for now
                    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": "Stats processed",
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
