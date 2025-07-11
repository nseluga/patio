# Stats utility functions for handling player statistics tracking
import math

def insert_stat(cur, bet_id, subject_id, game_played, game_type, stat_name, stat_value, team=None, team_size=None, winning_team=None):
        cur.execute("""
            INSERT INTO bettable_player_stats (bet_id, subject_player, gamePlayed, gameType, stat_name, stat_value, team, team_size, winning_team)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (bet_id, subject_id, game_played, game_type, stat_name, stat_value, team, team_size, winning_team))

def calculate_defensive_value_for_game(cur, bet_id, team, team_players, opponent_team, opponent_players, opponent_score):
    placeholders = ",".join(["%s"] * len(opponent_players))
    cur.execute(f"""
        SELECT id, name
        FROM bettable_players
        WHERE id IN ({placeholders})
    """, opponent_players)
    id_to_name = {str(row["id"]): row["name"] for row in cur.fetchall()}
    opponent_names = [id_to_name.get(pid) for pid in opponent_players]

    print(f"\n🔍 Opponent Player IDs → Names: {opponent_players} → {opponent_names}")

    cur.execute(f"""
        SELECT player_name, mean
        FROM player_stat_aggregates
        WHERE player_name IN ({','.join(['%s'] * len(opponent_names))})
        AND game_played = 'Beerball'
        AND game_type = 'Shots Made'
        AND stat_name = 'shots_made'
    """, opponent_names)
    shot_map = {r["player_name"]: r["mean"] for r in cur.fetchall()}

    print(f"📊 Opponent Shots Map: {shot_map}")

    opponent_estimated_shots = sum(shot_map.get(name, 0) for name in opponent_names)
    print(f"📈 Opponent estimated shots: {opponent_estimated_shots}")
    print(f"📉 Opponent actual score: {opponent_score}")

    if opponent_estimated_shots == 0:
        print("⚠️ No shot data found for opponents! DV set to 0.0")
        dv = 0.0
    else:
        MAX_TPP = 15

        if opponent_score == 0:
            dv = opponent_estimated_shots / MAX_TPP
        else:
            throws_per_point = opponent_estimated_shots / opponent_score
            dv = (throws_per_point - 1) / (MAX_TPP - 1)

        # Clamp and shift
        dv = max(0.0, min(1.0, dv))
        print(f"🛡️ Team {team} vs {opponent_team} → DV: {dv:.3f}")

    return {int(player_id): dv for player_id in team_players}

def update_player_aggregate(cur, player_name, game_played, game_type, stat_name, stat_value, team_size=None):
    cur.execute("""
        SELECT * FROM player_stat_aggregates
        WHERE player_name = %s
        AND game_played = %s
        AND game_type = %s
        AND stat_name = %s
        AND team_size IS NOT DISTINCT FROM %s
    """, (player_name, game_played, game_type, stat_name, team_size))

    existing = cur.fetchone()

    if not existing:
        cur.execute("""
            INSERT INTO player_stat_aggregates (
                player_name, game_played, game_type, team_size, stat_name,
                mean, std, mean_last_5, n_games, win_rate, defensive_value
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            player_name, game_played, game_type, team_size, stat_name,
            stat_value, 0.0, stat_value, 1, None, None
        ))
        return
    
    else:
        old_mean = existing['mean']
        old_std = existing['std']
        old_n = existing['n_games']

        new_n = old_n + 1
        delta = stat_value - old_mean
        new_mean = old_mean + delta / new_n
        new_var = ((old_std ** 2) * (old_n - 1) + delta * (stat_value - new_mean)) / new_n
        new_std = new_var ** 0.5 if new_var > 0 else 0.0

        cur.execute("""
            SELECT stat_value
            FROM bettable_player_stats
            WHERE subject_player = %s
            AND gamePlayed = %s
            AND gameType = %s
            AND stat_name = %s
            AND team_size IS NOT DISTINCT FROM %s
            ORDER BY timestamp DESC
            LIMIT 4
        """, (player_name, game_played, game_type, stat_name, team_size))

        recent_stats = [row['stat_value'] for row in cur.fetchall()]

        # Add the new value to the front of the list
        recent_stats.insert(0, stat_value)

        # Trim to 5 max
        recent_stats = recent_stats[:5]

        # Compute mean of last 5
        mean_last_5 = sum(recent_stats) / len(recent_stats)

        # Update win rate if applicable
        win_rate = None
        subject_id = get_or_create_bettable_player(cur, player_name)
        if stat_name == "score":
            cur.execute("""
                SELECT COUNT(*) AS total_games
                FROM bettable_player_stats
                WHERE subject_player = %s::text
                AND gamePlayed = %s
                AND gameType = %s
                AND stat_name = %s
                AND team_size IS NOT DISTINCT FROM %s
            """, (subject_id, game_played, game_type, stat_name, team_size))
            row = cur.fetchone()
            total_games = row["total_games"] if row else 0

            cur.execute("""
                SELECT COUNT(*) AS wins
                FROM bettable_player_stats
                WHERE subject_player = %s::text
                AND gamePlayed = %s
                AND gameType = %s
                AND stat_name = %s
                AND team_size IS NOT DISTINCT FROM %s
                AND team = winning_team
            """, (subject_id, game_played, game_type, stat_name, team_size))
            row = cur.fetchone()
            wins = row["wins"] if row else 0

            win_rate = wins / total_games if total_games > 0 else None

        if stat_name == "score" and game_type == "Score" and game_played == "Beerball":
            cur.execute("""
                SELECT team, bet_id
                FROM bettable_player_stats
                WHERE subject_player = %s::text
                AND stat_name = 'score'
                ORDER BY timestamp DESC
                LIMIT 1
            """, (subject_id,))
            row = cur.fetchone()
            if not row:
                print("❌ No team or bet_id found for player — exiting DV")
                return
            if row:
                team = row["team"]
                bet_id = row["bet_id"]
                print(f"✅ Using team: {team}, bet_id: {bet_id}")
                cur.execute("""
                    SELECT DISTINCT ON (subject_player) subject_player, team, stat_value
                    FROM bettable_player_stats
                    WHERE bet_id = %s AND stat_name = 'score'
                    ORDER BY subject_player, timestamp DESC
                """, (bet_id,))
                results = cur.fetchall()

                print(f"📊 Full bet stats: {results}")
                team_players = [r["subject_player"] for r in results if r["team"] == team]
                opponent_players = [r["subject_player"] for r in results if r["team"] != team]
                opponent_team = [r["team"] for r in results if r["team"] != team][0]

                print(f"🧩 Team players: {team_players}")
                print(f"🛡️ Opponent players: {opponent_players}")
                print(f"📌 Opponent teams found: {opponent_team}")
                opponent_score = max([r["stat_value"] for r in results if r["team"] != team])

                print(f"\n🔧 Computing DV for {player_name} (Team {team}) vs Team {opponent_team}")
                print(f"🧩 Team players: {team_players}, Opponents: {opponent_players}, Opponent Score: {opponent_score}")

                dvs = calculate_defensive_value_for_game(
                    cur, bet_id, team, team_players, opponent_team, opponent_players, opponent_score
                )

                print(f"📦 All DVs for this game: {dvs}")
                print(f"🔍 player_name: {player_name}, subject_id: {subject_id}")
                print(f"🧬 Looking for subject_id {subject_id} in DV keys: {list(dvs.keys())}")
                defensive_value = dvs.get(subject_id)
            else:
                print(f"⚠️ No matching row for player {player_name} to calculate DV")
                defensive_value = None

        # Compute new rolling average DV
        old_dv = existing["defensive_value"] or 0.0
        delta_dv = (defensive_value or 0.0) - old_dv
        new_dv = old_dv + delta_dv / new_n

        print(f"🛠️ Final defensive_value to update: {defensive_value} for {player_name}")
        cur.execute("""
            UPDATE player_stat_aggregates
            SET mean = %s,
                std = %s,
                mean_last_5 = %s,
                n_games = %s,
                win_rate = %s,
                defensive_value = %s
            WHERE player_name = %s
            AND game_played = %s
            AND game_type = %s
            AND stat_name = %s
            AND team_size IS NOT DISTINCT FROM %s
        """, (
            new_mean, new_std, mean_last_5, new_n, win_rate, new_dv,
            player_name, game_played, game_type, stat_name, team_size
        ))

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
