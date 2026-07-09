import logging
from datetime import datetime
from random import choice, randint
from uuid import uuid4

import numpy as np
import psycopg2.extras
from flask import Blueprint, g, jsonify, request
from psycopg2.extras import Json

from backend.bet_generation import (
    BEERBALL,
    CAPS,
    PONG,
    assemble_matchup,
    get_global_beerball_score_strength_average,
    get_global_caps_score_strength_average,
    get_global_pong_score_strength_average,
    get_player_beerball_score_profile,
    get_player_caps_score_profile,
    get_player_pong_score_profile,
)
from backend.routes._db import get_db
from backend.utils.auth import token_required
from backend.validation import require_fields

logger = logging.getLogger(__name__)

lines_bp = Blueprint('lines', __name__)


@lines_bp.route("/cpu/create_caps_shots_bet", methods=["POST"])
@token_required
def create_cpu_caps_shots_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "1v1")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])  # "1v1" -> 1
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Fetch eligible players
        players = CAPS.get_shots_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        # Assemble teams and matchup
        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        playerA = matchup_info["line_subject"]
        matchup = matchup_info["matchup"]

        # Get player stats
        playerA_stats = CAPS.get_shots_profile(cur, playerA, team_size)
        teammate_stats = [CAPS.get_shots_profile(cur, p, team_size) for p in your_team if p != playerA]
        opp_stats = [CAPS.get_shots_profile(cur, p, team_size) for p in opp_team]

        line_type = choice(["Over", "Under"])

        # Generate line based on team size (dispatched through the sport's config seam)
        line = CAPS.predict_shots(
            playerA_stats,
            teammate_stats,
            opp_stats,
            line_type
        )

        # Insert the bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourplayer, oppplayer, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            bet_id,
            "CPU", 0,
            time_posted,
            matchup,
            amount,
            line_type,
            line,
            "Shots Made",
            "Caps",
            game_size,
            playerA,
            None,
            "CPU"
        ))

        conn.commit()
        return jsonify({"message": "CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Caps shots bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@lines_bp.route("/cpu/create_pong_shots_bet", methods=["POST"])
@token_required
def create_cpu_pong_shots_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "1v1")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])  # "1v1" -> 1
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get players
        players = PONG.get_shots_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        # Assemble matchup
        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        playerA = matchup_info["line_subject"]
        matchup = matchup_info["matchup"]

        # Get stat profiles
        playerA_stats = PONG.get_shots_profile(cur, playerA, team_size)
        teammate_stats = [PONG.get_shots_profile(cur, p, team_size) for p in your_team if p != playerA]
        opp_stats = [PONG.get_shots_profile(cur, p, team_size) for p in opp_team]

        line_type = choice(["Over", "Under"])

        # Generate biased line (dispatched through the sport's config seam)
        line = PONG.predict_shots(
            playerA_stats,
            teammate_stats,
            opp_stats,
            line_type,
            team_size,
            cur
        )

        # Insert bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourplayer, oppplayer, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            bet_id,
            "CPU", 0,
            time_posted,
            matchup,
            amount,
            line_type,
            line,
            "Shots Made",
            "Pong",
            game_size,
            playerA,
            None,
            "CPU"
        ))

        conn.commit()
        return jsonify({"message": "CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Pong shots bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@lines_bp.route("/cpu/create_beerball_shots_bet", methods=["POST"])
@token_required
def create_cpu_beerball_shots_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "1v1")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])  # "1v1" → 1
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Fetch players with Beerball shots made data
        players = BEERBALL.get_shots_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        # Build teams and matchup string
        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        playerA = matchup_info["line_subject"]
        matchup = matchup_info["matchup"]

        # Get subject player stats
        playerA_stats = BEERBALL.get_shots_profile(cur, playerA, team_size)
        if not playerA_stats:
            return jsonify({"error": "Missing stats for line subject"}), 400

        logger.debug("Line subject stats (Shots Made): %s", playerA_stats)

        # Get win_rate + DV from score profile for both teams
        teammate_profiles = [get_player_beerball_score_profile(cur, p, team_size) for p in your_team]
        opp_profiles = [get_player_beerball_score_profile(cur, p, team_size) for p in opp_team]

        if not all(teammate_profiles) or not all(opp_profiles):
            return jsonify({"error": "Missing win_rate or DV for one or more players"}), 400

        logger.debug("Teammate score profiles:")
        for p in teammate_profiles:
            logger.debug("  %s", p)

        logger.debug("Opponent score profiles:")
        for p in opp_profiles:
            logger.debug("  %s", p)

        # Calculate win_rate and defensive_value aggregates
        your_win_rate = np.mean([p["win_rate"] for p in teammate_profiles])
        opp_win_rate = np.mean([p["win_rate"] for p in opp_profiles])
        avg_opp_dv = np.mean([p["defensive_value"] for p in opp_profiles])

        line_type = choice(["Over", "Under"])

        # Generate opportunity-adjusted line (dispatched through the sport's config seam)
        line = BEERBALL.predict_shots(
            cur,
            team_size,
            playerA_stats,
            your_win_rate,
            opp_win_rate,
            avg_opp_dv,
            line_type
        )

        logger.debug("Aggregates: your_win_rate=%s, opp_win_rate=%s, avg_opp_dv=%s",
                     your_win_rate, opp_win_rate, avg_opp_dv)

        # Insert the bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourplayer, oppplayer, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            bet_id,
            "CPU", 0,
            time_posted,
            matchup,
            amount,
            line_type,
            line,
            "Shots Made",
            "Beerball",
            game_size,
            playerA,
            None,
            "CPU"
        ))

        conn.commit()
        return jsonify({"message": "Beerball CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Beerball shots bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@lines_bp.route("/cpu/create_beerball_score_bet", methods=["POST"])
@token_required
def create_cpu_beerball_score_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "2v2")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        players = BEERBALL.get_score_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        matchup = matchup_info["matchup"]

        # Get stats for score profile
        your_profiles = [get_player_beerball_score_profile(cur, p, team_size) for p in your_team]
        opp_profiles  = [get_player_beerball_score_profile(cur, p, team_size) for p in opp_team]

        # Get shots made profile (default 0 if missing)
        def safe_shots(p):
            row = BEERBALL.get_shots_profile(cur, p, team_size)
            return row["mean"] if row else 0.0

        your_shots = [safe_shots(p) for p in your_team]
        opp_shots  = [safe_shots(p) for p in opp_team]

        # Get global strength average
        global_avg_strength = get_global_beerball_score_strength_average(cur, team_size)

        line_type = choice(["Over", "Under"])

        line, line_type = BEERBALL.predict_score(
            your_profiles,
            opp_profiles,
            your_shots,
            opp_shots,
            global_avg_strength,
            line_type
        )

        # Insert bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourteama, yourteamb, oppteama, oppteamb, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s)
        """, (
            bet_id, "CPU", 0, time_posted, matchup, amount,
            line_type, line, "Score", "Beerball", game_size,
            Json(your_team), Json([]), None, None, "CPU"
        ))

        conn.commit()
        return jsonify({"message": "Beerball Score CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Beerball score bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@lines_bp.route("/cpu/create_caps_score_bet", methods=["POST"])
@token_required
def create_cpu_caps_score_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "2v2")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get eligible players
        players = CAPS.get_score_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        matchup = matchup_info["matchup"]

        # Get score profiles
        your_profiles = [get_player_caps_score_profile(cur, p, team_size) for p in your_team]
        opp_profiles  = [get_player_caps_score_profile(cur, p, team_size) for p in opp_team]

        if any(p is None for p in your_profiles + opp_profiles):
            return jsonify({"error": "Missing score profile"}), 400

        # Get shots made profiles (default to 0 if missing)
        def safe_shots(p):
            cur.execute("""
                SELECT mean FROM player_stat_aggregates
                WHERE player_name = %s AND game_played = 'Caps'
                  AND game_type = 'Shots Made' AND stat_name = 'shots_made'
                  AND team_size = %s
            """, (p, team_size))
            row = cur.fetchone()
            return row["mean"] if row else 0.0

        your_shots = [safe_shots(p) for p in your_team]
        opp_shots  = [safe_shots(p) for p in opp_team]

        # Global strength average
        global_avg_strength = get_global_caps_score_strength_average(cur, team_size)

        line_type = choice(["Over", "Under"])

        line, line_type = CAPS.predict_score(
            your_profiles, opp_profiles,
            your_shots, opp_shots,
            global_avg_strength,
            line_type
        )

        # Insert bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourteama, yourteamb, oppteama, oppteamb, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s)
        """, (
            bet_id, "CPU", 0, time_posted, matchup, amount,
            line_type, line, "Score", "Caps", game_size,
            Json(your_team), Json([]), None, None, "CPU"
        ))

        conn.commit()
        return jsonify({"message": "Caps Score CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Caps score bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

@lines_bp.route("/cpu/create_pong_score_bet", methods=["POST"])
@token_required
def create_cpu_pong_score_bet():
    if g.player_id != 0:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    game_size = data.get("gameSize", "2v2")
    if not game_size or not game_size[0:1].isdigit():
        return jsonify({"error": "Invalid gameSize"}), 400
    team_size = int(game_size[0])
    if team_size < 1:
        return jsonify({"error": "Invalid gameSize"}), 400

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # 1. Get players
        players = PONG.get_score_players(cur, team_size)
        if len(players) < 2 * team_size:
            return jsonify({"error": "Not enough players with stats"}), 400

        matchup_info = assemble_matchup(players, team_size)
        your_team = matchup_info["your_team"]
        opp_team = matchup_info["opp_team"]
        matchup = matchup_info["matchup"]

        # 2. Score profiles
        your_profiles = [get_player_pong_score_profile(cur, p, team_size) for p in your_team]
        opp_profiles  = [get_player_pong_score_profile(cur, p, team_size) for p in opp_team]
        if any(p is None for p in your_profiles + opp_profiles):
            return jsonify({"error": "Missing score profiles"}), 400

        # 3. Shots made profiles (default 0 if missing)
        def safe_shots(p):
            row = PONG.get_shots_profile(cur, p, team_size)
            return row["mean"] if row else 0.0

        your_shots = [safe_shots(p) for p in your_team]
        opp_shots  = [safe_shots(p) for p in opp_team]

        # 4. Global avg strength
        global_avg = get_global_pong_score_strength_average(cur, team_size)

        # 5. Line generation
        line_type = choice(["Over", "Under"])
        line, line_type = PONG.predict_score(
            your_profiles, opp_profiles,
            your_shots, opp_shots,
            global_avg,
            line_type
        )

        # 6. Insert bet
        bet_id = str(uuid4())
        time_posted = datetime.utcnow()
        amount = randint(10, 100)

        cur.execute("""
            INSERT INTO bets (
                id, poster, "posterId", "timePosted", matchup, amount,
                "lineType", "lineNumber", "gameType", "gamePlayed", "gameSize",
                yourteama, yourteamb, oppteama, oppteamb, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s)
        """, (
            bet_id, "CPU", 0, time_posted, matchup, amount,
            line_type, line, "Score", "Pong", game_size,
            Json(your_team), Json([]), None, None, "CPU"
        ))

        conn.commit()
        return jsonify({"message": "Pong Score CPU bet created"}), 201

    except Exception as e:
        logger.exception("CPU Pong score bet creation failed")
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()
