# Stats utility functions for handling player statistics tracking
import psycopg2

def insert_stat(cur, bet_id, subject_id, game_played, game_type, stat_name, stat_value, team=None, team_size=None, winning_team=None):
        cur.execute("""
            INSERT INTO bettable_player_stats (bet_id, subject_player, gamePlayed, gameType, stat_name, stat_value, team, team_size, winning_team)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (bet_id, subject_id, game_played, game_type, stat_name, stat_value, team, team_size, winning_team))

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

        # Compute win_rate if applicable
        win_rate = None
        if game_type == "Score":
            cur.execute("""
                SELECT COUNT(*) FROM bettable_player_stats
                WHERE subject_player = %s
                AND gamePlayed = %s
                AND gameType = %s
                AND team_size IS NOT DISTINCT FROM %s
            """, (player_name, game_played, game_type, team_size))
            total_games = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM bettable_player_stats
                WHERE subject_player = %s
                AND gamePlayed = %s
                AND gameType = %s
                AND team_size IS NOT DISTINCT FROM %s
                AND team = winning_team
            """, (player_name, game_played, game_type, team_size))
            wins = cur.fetchone()[0]

            win_rate = wins / total_games if total_games > 0 else None

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
            new_mean, new_std, mean_last_5, new_n, win_rate, None,
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
