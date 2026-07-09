import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify

from backend.routes._db import get_db
from backend.utils.auth import token_required

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/leaderboard', methods=['GET'])
def public_leaderboard():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT username, caps_balance FROM players ORDER BY caps_balance DESC LIMIT 5")
        rows = cur.fetchall()
        return jsonify([{'username': row[0], 'caps_balance': row[1]} for row in rows])
    finally:
        cur.close()
        conn.close()

@main_bp.route("/cleanup_bets", methods=["POST"])
@token_required
def cleanup_bets():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    conn = get_db()
    cur = conn.cursor()

    try:
        # 🧼 Delete PvP bets that were never accepted
        cur.execute("""
            DELETE FROM bets
            WHERE status = 'posted' AND "accepterId" IS NULL AND "timePosted" < %s
        """, (cutoff,))
        logger.info("Deleted unaccepted PvP bets older than 1 week")

        # 🧼 Delete resolved bets (already submitted by both players)
        cur.execute("""
            DELETE FROM bets
            WHERE status = 'submitted' AND "timePosted" < %s
        """, (cutoff,))
        logger.info("Deleted submitted bets older than 1 week")

        # 🧼 Delete CPU bets after 30s no matter what
        cur.execute("""
            DELETE FROM bets
            WHERE status = 'CPU' AND "timePosted" < %s
        """, (cutoff,))
        logger.info("Deleted expired CPU bets older than 1 week")

        conn.commit()
        return jsonify({"message": "Cleanup completed"}), 200

    except Exception as e:
        conn.rollback()
        logger.exception("Cleanup failed")
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()
