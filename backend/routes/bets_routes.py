import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

import psycopg2.extras
from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json

from backend.routes._db import get_db
from backend.utils.auth import token_required

logger = logging.getLogger(__name__)

bets_bp = Blueprint('bets', __name__)


@bets_bp.route("/create_bet", methods=["POST"])
@token_required
def create_bet():
    player_id = g.player_id
    bet = request.json
    amount = bet.get('amount', 0)
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"error": "Invalid or missing amount"}), 400

    conn = get_db()
    cur = conn.cursor()

    try:
        # Derive poster identity from the authenticated player — never trust the request body.
        # JWT carries only `id`; fetch username from DB.
        cur.execute("SELECT username FROM players WHERE id = %s", (player_id,))
        player_row = cur.fetchone()
        if not player_row:
            return jsonify({"error": "Player not found"}), 404
        poster_username = player_row[0]

        # Server-side bet metadata — never trust client-supplied id, poster, posterId,
        # timePosted, or status for these fields.
        bet_id = str(uuid4())
        time_posted = datetime.now(timezone.utc)

        # Atomic caps debit — prevents TOCTOU race between balance check and update.
        # The WHERE caps_balance >= %s guard makes the check and debit a single atomic step.
        cur.execute(
            "UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s",
            (amount, player_id, amount)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Insufficient caps"}), 400

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
            bet_id, poster_username, player_id, time_posted,
            bet.get('matchup'), bet.get('amount'), bet.get('lineType'), bet.get('lineNumber'),
            bet.get('gameType'), bet.get('gamePlayed'), bet.get('gameSize'),
            Json(bet.get('yourTeamA')), Json(bet.get('yourTeamB')),
            Json(bet.get('oppTeamA')), Json(bet.get('oppTeamB')),
            bet.get('yourScoreA'), bet.get('yourScoreB'),
            bet.get('oppScoreA'), bet.get('oppScoreB'),
            bet.get('yourPlayer'), bet.get('yourShots'),
            bet.get('oppPlayer'), bet.get('oppShots'),
            bet.get('yourOutcome'), bet.get('oppOutcome'),
            'posted'
        ))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except Exception as e:
        logger.exception("Bet insert failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@bets_bp.route("/pvp_bets", methods=["GET"])
@token_required
def get_pvp_bets():
    player_id = g.player_id
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT id, poster, "posterId" AS posterid, "accepterId" AS accepterid,
                   "timePosted" AS timeposted, matchup, amount,
                   "lineType" AS linetype, "lineNumber" AS linenumber,
                   "gameType" AS gametype, "gamePlayed" AS gameplayed,
                   "gameSize" AS gamesize, status
            FROM bets
            WHERE status = 'posted' AND "posterId" != %s
            ORDER BY "timePosted" DESC
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

@bets_bp.route("/cpu_bets", methods=["GET"])
@token_required
def get_cpu_bets():
    player_id = g.player_id
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, poster, "posterId" AS posterid, "accepterId" AS accepterid,
                   "timePosted" AS timeposted, matchup, amount,
                   "lineType" AS linetype, "lineNumber" AS linenumber,
                   "gameType" AS gametype, "gamePlayed" AS gameplayed,
                   "gameSize" AS gamesize, status
            FROM bets
            WHERE status = 'CPU'
            AND id NOT IN (
                SELECT id FROM cpu_acceptances WHERE accepter_id = %s
            )
            ORDER BY "timePosted" DESC
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

@bets_bp.route("/ongoing_bets", methods=["GET"])
@token_required
def get_ongoing_bets():
    player_id = g.player_id
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, poster, "posterId" AS posterid, "accepterId" AS accepterid,
                   "timePosted" AS timeposted, matchup, amount,
                   "lineType" AS linetype, "lineNumber" AS linenumber,
                   "gameType" AS gametype, "gamePlayed" AS gameplayed,
                   "gameSize" AS gamesize, status,
                   yourteama, yourteamb, oppteama, oppteamb,
                   yourscorea, yourscoreb, oppscorea, oppscoreb,
                   yourplayer, yourshots, oppplayer, oppshots,
                   youroutcome, oppoutcome
            FROM bets
            WHERE status = 'accepted' AND ("posterId" = %s OR "accepterId" = %s)
            UNION
            SELECT b.id, b.poster, b."posterId" AS posterid, b."accepterId" AS accepterid,
                   b."timePosted" AS timeposted, b.matchup, b.amount,
                   b."lineType" AS linetype, b."lineNumber" AS linenumber,
                   b."gameType" AS gametype, b."gamePlayed" AS gameplayed,
                   b."gameSize" AS gamesize, b.status,
                   b.yourteama, b.yourteamb, b.oppteama, b.oppteamb,
                   b.yourscorea, b.yourscoreb, b.oppscorea, b.oppscoreb,
                   b.yourplayer, b.yourshots, b.oppplayer, b.oppshots,
                   b.youroutcome, b.oppoutcome
            FROM bets b
            INNER JOIN cpu_acceptances c ON b.id = c.id
            WHERE c.accepter_id = %s AND c.match_confirmed = FALSE
            UNION
            SELECT id, poster, "posterId" AS posterid, "accepterId" AS accepterid,
                   "timePosted" AS timeposted, matchup, amount,
                   "lineType" AS linetype, "lineNumber" AS linenumber,
                   "gameType" AS gametype, "gamePlayed" AS gameplayed,
                   "gameSize" AS gamesize, status,
                   yourteama, yourteamb, oppteama, oppteamb,
                   yourscorea, yourscoreb, oppscorea, oppscoreb,
                   yourplayer, yourshots, oppplayer, oppshots,
                   youroutcome, oppoutcome
            FROM bets
            WHERE status = 'CPU' AND "posterId" = 0 AND %s = 0
        """, (player_id, player_id, player_id, player_id))
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]

        result = []
        for row in rows:
            bet = dict(zip(colnames, row))
            bet["status_message"] = compute_status_message(bet, player_id, conn)
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

    logger.warning("Unknown game type: %s", game_type)
    return False


def compute_status_message(bet, player_id, conn):
    if bet["status"] == "CPU" and player_id != 0:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("""
                SELECT match_confirmed, attempted FROM cpu_acceptances
                WHERE id = %s AND accepter_id = %s
            """, (bet["id"], player_id))
            row = cur.fetchone()
        finally:
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

    if not is_poster and not is_accepter:
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

@bets_bp.route("/bets", methods=["GET"])
@token_required
def get_all_bets():
    player_id = g.player_id
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    offset = (page - 1) * per_page

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT id, poster, "posterId" AS posterid, "accepterId" AS accepterid,
                      "timePosted" AS timeposted, matchup, amount,
                      "lineType" AS linetype, "lineNumber" AS linenumber,
                      "gameType" AS gametype, "gamePlayed" AS gameplayed,
                      "gameSize" AS gamesize, status
               FROM bets
               WHERE "posterId" = %s OR "accepterId" = %s
               ORDER BY "timePosted" DESC
               LIMIT %s OFFSET %s""",
            (player_id, player_id, per_page, offset)
        )
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
        return jsonify(result), 200
    except Exception as e:
        logger.exception("Failed to fetch bets")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
