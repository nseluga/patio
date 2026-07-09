import json
import logging

import psycopg2.extras
from flask import Blueprint, g, jsonify, request

from backend.routes._db import get_db
from backend.routes.bets_routes import check_stats_match, compute_status_message
from backend.stats_utils import (
    get_or_create_bettable_player,
    insert_stat,
    update_player_aggregate,
)
from backend.utils.auth import token_required

logger = logging.getLogger(__name__)

submit_bp = Blueprint('submit', __name__)


@submit_bp.route('/submit_stats/<bet_id>', methods=['POST'])
@token_required
def submit_stats(bet_id):
    data = request.json

    # Identity comes from JWT via @token_required — do not trust playerId from the request body
    player_id = g.player_id

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Fetch the current bet — explicit aliases map camelCase columns to lowercase keys
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
            FROM bets WHERE id = %s
        """, (bet_id,))
        bet = cur.fetchone()
        if not bet:
            return jsonify({"error": "Bet not found"}), 404

        is_poster = player_id == bet['posterid']
        is_accepter = player_id == bet['accepterid']
        is_cpu_bet = bet['status'] == 'CPU'
        is_admin = player_id == 0

        # Authorization: for PvP bets, only the poster or accepter may submit stats.
        # CPU bets are open to any authenticated user who accepted them (enforced via
        # cpu_acceptances row-match further in this handler).
        if not is_cpu_bet and not is_poster and not is_accepter:
            return jsonify({"error": "Forbidden"}), 403

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

                # ✅ CPU match confirmed: award or deduct caps
                line = float(bet['linenumber'])
                line_type = bet['linetype']
                game_type = bet['gametype']

                if game_type == "Shots Made":
                    user_stat = int(data["yourShots"])
                elif game_type == "Score":
                    user_stat = int(data["yourScoreA"]) + int(data["yourScoreB"])
                elif game_type == "Other":
                    user_stat = int(data["yourOutcome"])
                else:
                    user_stat = None

                if user_stat is not None:
                    outcome = "Over" if user_stat > line else "Under"
                    amount = bet["amount"]

                    if outcome == line_type:
                        # ✅ Player won against CPU
                        cur.execute("""
                            UPDATE players
                            SET caps_balance = caps_balance + %s
                            WHERE id = %s
                        """, (amount * 2, player_id))

            else:
                cur.execute("""
                    UPDATE cpu_acceptances
                    SET attempted = TRUE
                    WHERE id = %s AND accepter_id = %s
                """, (bet_id, player_id))

            # 🔄 Re-fetch the bet for fresh data (optional, since bet itself didn't change, just cpu_acceptances)
            updated_bet = bet  # can reuse bet if no need to refetch from `bets`
            status_message = compute_status_message(updated_bet, player_id, conn)

        else:
            # Prepare stat update fields
            update_fields = []
            update_values = []

            if bet['gametype'] == "Score":
                if is_poster:
                    update_fields += ['"yourTeamA"', '"yourTeamB"', '"yourScoreA"', '"yourScoreB"']
                    update_values += [data["yourTeamA"], data["yourTeamB"], data["yourScoreA"], data["yourScoreB"]]
                else:
                    update_fields += ['"oppTeamA"', '"oppTeamB"', '"oppScoreA"', '"oppScoreB"']
                    update_values += [data["yourTeamA"], data["yourTeamB"], data["yourScoreA"], data["yourScoreB"]]

            elif bet['gametype'] == "Shots Made":
                update_fields += ['"yourPlayer"' if is_poster else '"oppPlayer"',
                                '"yourShots"' if is_poster else '"oppShots"']
                update_values += [data["yourPlayer"], data["yourShots"]]

            elif bet['gametype'] == "Other":
                update_fields += ['"yourOutcome"' if is_poster else '"oppOutcome"']
                update_values += [data["yourOutcome"]]

            # Execute update
            set_clause = ", ".join(f"{field} = %s" for field in update_fields)

            # Cast any list values to JSON strings for jsonb fields
            update_values = [json.dumps(v) if isinstance(v, list) else v for v in update_values]

            # Now run the update
            cur.execute(f"UPDATE bets SET {set_clause} WHERE id = %s", (*update_values, bet_id))
            conn.commit()

            # Re-fetch updated bet — explicit aliases map camelCase columns to lowercase keys
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
                FROM bets WHERE id = %s
            """, (bet_id,))
            updated_bet = cur.fetchone()
            match = check_stats_match(updated_bet)
            status_message = compute_status_message(updated_bet, player_id, conn)

            if match:
                # ✅ Update bet status
                cur.execute("UPDATE bets SET status = 'submitted' WHERE id = %s", (bet_id,))

                # ✅ Determine cap payout
                poster_id = updated_bet['posterid']
                accepter_id = updated_bet['accepterid']
                amount = updated_bet['amount']

                # Determine the winner based on stat vs line
                line = float(updated_bet['linenumber'])
                line_type = updated_bet['linetype']  # what the poster picked

                # Figure out which stat to use for judgment
                if updated_bet['gametype'] == "Shots Made":
                    # Use the poster's player's stat
                    poster_stat = updated_bet.get('yourshots')
                    accepter_stat = updated_bet.get('oppshots')

                    if poster_stat is None or accepter_stat is None:
                        winner_id = None  # Incomplete
                    else:
                        outcome = "Over" if poster_stat > line else "Under"
                        winner_id = poster_id if outcome == line_type else accepter_id

                elif updated_bet['gametype'] == "Other":
                    # Use outcome as int directly
                    poster_stat = updated_bet.get('youroutcome')
                    accepter_stat = updated_bet.get('oppoutcome')

                    if poster_stat is None or accepter_stat is None:
                        winner_id = None
                    else:
                        outcome = "Over" if poster_stat > line else "Under"
                        winner_id = poster_id if outcome == line_type else accepter_id

                elif updated_bet['gametype'] == "Score":
                    # Use total score of Team A + B
                    your_score = updated_bet.get('yourscorea') + updated_bet.get('yourscoreb')
                    opp_score = updated_bet.get('oppscorea') + updated_bet.get('oppscoreb')

                    if your_score is None or opp_score is None:
                        winner_id = None
                    else:
                        outcome = "Over" if your_score > line else "Under"
                        winner_id = poster_id if outcome == line_type else accepter_id

                    # ✅ Use poster's scores (both players inputted the same)
                    your_score_a = updated_bet.get("yourscorea")
                    your_score_b = updated_bet.get("yourscoreb")

                    if your_score_a is not None and your_score_b is not None:
                        if your_score_a > your_score_b:
                            winning_team_label = "A"
                        elif your_score_b > your_score_a:
                            winning_team_label = "B"
                        else:
                            winning_team_label = None  # Tie
                    else:
                        winning_team_label = None  # Incomplete input

                # ✅ Award winner with total pot (2x amount)
                cur.execute("""
                    UPDATE players
                    SET caps_balance = caps_balance + %s
                    WHERE id = %s
                """, (2 * amount, winner_id))

                # ✅ Increment pvp_bets_won for the winner
                cur.execute("""
                    UPDATE players
                    SET pvp_bets_won = pvp_bets_won + 1
                    WHERE id = %s
                """, (winner_id,))


                # ✅ Log all players to bettable_player_stats (creating them if needed)
                if updated_bet['gametype'] == "Shots Made":
                    names_stats = [
                        (updated_bet.get('yourplayer'), updated_bet['yourshots']),
                        (updated_bet.get('oppplayer'), updated_bet['oppshots']),
                    ]

                    team_size = int(updated_bet['gamesize'][0]) if updated_bet.get('gamesize') else 1

                    seen = set()
                    for name, stat in names_stats:
                        if name:
                            cleaned_name = name.strip().lower()
                            if cleaned_name in seen:
                                continue
                            seen.add(cleaned_name)
                            subject_id = get_or_create_bettable_player(cur, name.strip())

                            insert_stat(
                                cur,
                                bet_id,
                                subject_id,
                                updated_bet['gameplayed'],
                                updated_bet['gametype'],
                                "shots_made",
                                stat,
                                team=None,
                                team_size=team_size,  # ✅ now passed correctly
                                winning_team=None
                            )

                            update_player_aggregate(
                                cur,
                                player_name=name.strip(),
                                game_played=updated_bet['gameplayed'],
                                game_type=updated_bet['gametype'],
                                stat_name="shots_made",
                                stat_value=stat,
                                team_size=team_size  # ✅ now passed correctly
                            )

                elif updated_bet['gametype'] == "Score":
                    team_size = int(updated_bet['gamesize'][0]) if updated_bet.get('gamesize') else 2

                    team_inputs = [
                        ("yourteama", "yourscorea", "A"),
                        ("yourteamb", "yourscoreb", "B"),
                        ("oppteama", "oppscorea", "A"),
                        ("oppteamb", "oppscoreb", "B"),
                    ]

                    seen = set()
                    inserted = []

                    for player_field, score_field, team in team_inputs:
                        players = updated_bet.get(player_field) or []
                        score = updated_bet.get(score_field)

                        if players and score is not None:
                            for player_name in players:
                                cleaned_name = player_name.strip().lower()
                                if cleaned_name in seen:
                                    continue
                                seen.add(cleaned_name)

                                subject_id = get_or_create_bettable_player(cur, player_name.strip())

                                insert_stat(
                                    cur,
                                    bet_id,
                                    subject_id,
                                    updated_bet['gameplayed'],
                                    updated_bet['gametype'],
                                    "score",
                                    score,
                                    team=team,
                                    team_size=team_size,
                                    winning_team=winning_team_label
                                )

                                inserted.append((player_name.strip(), score))
                    for player_name, score in inserted:
                        update_player_aggregate(
                            cur,
                            player_name=player_name,
                            game_played=updated_bet['gameplayed'],
                            game_type=updated_bet['gametype'],
                            stat_name="score",
                            stat_value=score,
                            team_size=team_size
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
                                cur,
                                bet_id,
                                subject_id,
                                updated_bet['gameplayed'],
                                updated_bet['gametype'],
                                "other",
                                stat,
                                team=None,            # ← add this now
                                team_size=None        # ← leave empty for now
                            )
                            update_player_aggregate(
                                cur,
                                player_name=name.strip(),
                                game_played=updated_bet['gameplayed'],
                                game_type=updated_bet['gametype'],
                                stat_name="other",
                                stat_value=stat,
                                team_size=None
                            )

        conn.commit()
        return jsonify({
            "message": "Stats processed",
            "match": match,
            "status_message": status_message
        })
    finally:
        cur.close()
        conn.close()
