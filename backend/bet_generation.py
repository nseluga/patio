# Functions for generation cpu bets
from scipy.stats import norm

def get_caps_shots_players(cur):
    cur.execute("""
        SELECT player_name, mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE game_played = 'Caps'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size IS NULL
    """)
    return cur.fetchall()

def generate_biased_caps_shots_line(subject_stats, opponent_stats, line_type, recency_weight=0.1):
    subject_mean = subject_stats["mean"]
    subject_std = subject_stats["std"]
    subject_recent = subject_stats["mean_last_5"]

    opponent_mean = opponent_stats["mean"]
    opponent_recent = opponent_stats["mean_last_5"]

    # Recency-weighted accuracy
    subject_adjusted = subject_mean + (subject_recent - subject_mean) * recency_weight
    opponent_adjusted = opponent_mean + (opponent_recent - opponent_mean) * recency_weight

    # Relative skill ratio (normalized)
    ratio = subject_adjusted / opponent_adjusted if opponent_adjusted > 0 else 1

    # Opportunity factor based on ratio shape:
    # Boosts volume when evenly matched or dominant; shrinks when clearly outmatched
    opportunity_factor = (
        1.4 if ratio > 1.3 else
        1.2 if ratio > 1.1 else
        1.0 if 0.9 <= ratio <= 1.1 else
        0.85 if ratio >= 0.7 else
        0.7
    )

    # Final adjusted expected makes
    expected = subject_adjusted * opportunity_factor

    # Biased percentile based on line type
    percentile = 0.55 if line_type == "Over" else 0.45
    line = norm(expected, subject_std).ppf(percentile)

    # Round toward CPU favor
    base = round(line)
    line = base + 0.5 if line_type == "Over" else base - 0.5

    return line
