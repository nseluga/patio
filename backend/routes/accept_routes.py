import logging

from flask import Blueprint, g, jsonify, request

from backend.routes._db import get_db
from backend.utils.auth import token_required

logger = logging.getLogger(__name__)

accept_bp = Blueprint('accept', __name__)


@accept_bp.route("/accept_bet/<bet_id>", methods=["POST"])
@token_required
def accept_bet(bet_id):
    player_id = g.player_id
    logger.debug("PvP accept_bet triggered by player_id: %s", player_id)

    data = request.get_json()
    accepter_line_type = data.get("accepterLineType")  # Get flipped lineType from frontend

    conn = get_db()
    cur = conn.cursor()

    try:
        # Get amount and poster ID
        cur.execute('SELECT amount, "posterId" AS posterid FROM bets WHERE id = %s AND status = \'posted\'', (bet_id,))
        bet = cur.fetchone()
        if not bet:
            return jsonify({"error": "Bet not found or already accepted"}), 404

        amount, poster_id = bet

        # Atomic caps debit — prevents TOCTOU race between balance check and update.
        # The WHERE caps_balance >= %s guard makes the check and debit a single atomic step.
        cur.execute(
            "UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s",
            (amount, player_id, amount)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Insufficient caps"}), 400

        # Accept the bet and store accepter's line type
        cur.execute("""
            UPDATE bets
            SET "accepterId" = %s,
                accepter_line_type = %s,
                status = 'accepted'
            WHERE id = %s
        """, (player_id, accepter_line_type, bet_id))

        # Increment pvp_bets_played for both poster and accepter
        cur.execute("""
            UPDATE players
            SET pvp_bets_played = pvp_bets_played + 1
            WHERE id IN (%s, %s)
        """, (poster_id, player_id))


        conn.commit()
        return jsonify({"status": "accepted"}), 200

    except Exception as e:
        conn.rollback()
        logger.exception("Accept bet error")
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@accept_bp.route("/accept_cpu_bet/<bet_id>", methods=["POST"])
@token_required
def accept_cpu_bet(bet_id):
    player_id = g.player_id
    conn = get_db()
    cur = conn.cursor()

    try:
        # Check if this player already accepted this CPU bet
        cur.execute("""
            SELECT 1 FROM cpu_acceptances WHERE id = %s AND accepter_id = %s
        """, (bet_id, player_id))
        if cur.fetchone():
            return jsonify({"error": "Bet already accepted"}), 400

        # Get amount
        cur.execute("""
            SELECT amount FROM bets WHERE id = %s AND status = 'CPU'
        """, (bet_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "CPU bet not found"}), 404

        amount = row[0]

        # Atomic caps debit — prevents TOCTOU race between balance check and update.
        # The WHERE caps_balance >= %s guard makes the check and debit a single atomic step.
        cur.execute(
            "UPDATE players SET caps_balance = caps_balance - %s WHERE id = %s AND caps_balance >= %s",
            (amount, player_id, amount)
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Insufficient caps"}), 400

        # Record the acceptance
        cur.execute("""
            INSERT INTO cpu_acceptances (id, accepter_id)
            VALUES (%s, %s)
        """, (bet_id, player_id))

        # ✅ Increment CPU bet count (reuses PvP field for now)
        if player_id != 0:
            cur.execute("""
                UPDATE players
                SET pvp_bets_played = pvp_bets_played + 1
                WHERE id = %s
            """, (player_id,))

        conn.commit()
        return jsonify({"status": "accepted"}), 200

    except Exception as e:
        logger.exception("Accept CPU bet error")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()
