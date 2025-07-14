# Functions for caps generation cpu bets
from scipy.stats import norm
import numpy as np
import random

def get_caps_shots_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Caps'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]

def get_player_caps_shots_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Caps'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_name, team_size))
    
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_caps_score_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Caps'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    return [row["player_name"] for row in cur.fetchall()]

def get_player_caps_score_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Caps'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (player_name, team_size))
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_global_caps_score_strength_average(cur, team_size, recency_weight=0.1):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate
        FROM player_stat_aggregates
        WHERE game_played = 'Caps'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    score_rows = cur.fetchall()

    strengths = []
    for row in score_rows:
        profile = dict(row)
        name = profile["player_name"]

        # Get shots profile
        cur.execute("""
            SELECT mean
            FROM player_stat_aggregates
            WHERE player_name = %s
              AND game_played = 'Caps'
              AND game_type = 'Shots Made'
              AND stat_name = 'shots_made'
              AND team_size = %s
        """, (name, team_size))
        shots_row = cur.fetchone()
        if not shots_row:
            continue  # skip if missing shots

        shots = shots_row["mean"]

        score_adj = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)

        strength = 0.25 * score_adj + 0.25 * shots + 0.25 * win_rate
        strengths.append(strength)
        print(f"✔️ Included {name}: {strength:.2f}")

    if not strengths:
        print("⚠️ No players had both Score and Shots data")
        return 1.0

    avg = np.mean(strengths)
    print(f"✅ Global avg Caps strength: {avg:.4f}")
    return avg

def assemble_caps_matchup(players, team_size):
    assert len(players) >= 2 * team_size, "Not enough players for matchup"

    selected = random.sample(players, 2 * team_size)
    your_team = selected[:team_size]
    opp_team = selected[team_size:]

    playerA = your_team[0]  # line subject

    if team_size == 1:
        matchup = f"{playerA} vs {opp_team[0]}"
    elif team_size == 2:
        matchup = f"{playerA} with {your_team[1]} vs {opp_team[0]} and {opp_team[1]}"
    elif team_size == 3:
        matchup = f"{playerA} with {your_team[1]}, {your_team[2]} vs {', '.join(opp_team)}"
    else:
        raise ValueError("Unsupported team size")

    return {
        "your_team": your_team,
        "opp_team": opp_team,
        "line_subject": playerA,
        "matchup": matchup
    }

def opportunity_factor(balance_ratio):
    deviation = abs(balance_ratio - 1.0)

    if deviation < 0.05:
        return 1.4  # Perfectly balanced → max opportunity
    elif balance_ratio > 1.0:
        # You are better
        if deviation < 0.15:
            return 1.3  # Slight edge
        elif deviation < 0.35:
            return 1.1  # Moderate advantage
        else:
            return 0.9  # Blowout win = shorter game
    else:
        # You are worse
        if deviation < 0.15:
            return 1.1  # Slightly worse = still close
        elif deviation < 0.35:
            return 0.9  # Moderate disadvantage
        else:
            return 0.7  # Likely quick loss

def harmonic_mean(values):
    values = [v for v in values if v > 0]
    return len(values) / sum(1/v for v in values) if values else 0

def adjust(stats, recency_weight):
        return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight

def team_strength_multiplier(strength, avg_strength):
    deviation = strength - avg_strength
    return 1.0 + max(min(deviation * 0.75, 0.3), -0.3)

# Generate a biased line for Caps Shots Made bets
# lines make theoretical sense but may need to be adjusted depending on actual player stats and actual games
def generate_biased_caps_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, recency_weight=0.1):
    subj_adj = adjust(subject_stats, recency_weight)
    team_adj = [adjust(p, recency_weight) for p in teammates_stats]
    opp_adj = [adjust(p, recency_weight) for p in opp_team_stats]

    # Step 1: Harmonic means
    your_team_vals = [subj_adj] + team_adj
    team_strength = harmonic_mean(your_team_vals)
    opp_strength = harmonic_mean(opp_adj)

    # Step 2: Balance → opportunity
    balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1
    opportunity = opportunity_factor(balance_ratio)

    # Step 3: Expected value
    expected = subj_adj * opportunity

    # Step 4: Bias line slightly in CPU's favor
    percentile = 0.47 if line_type == "Over" else 0.53
    subj_std = subject_stats["std"]
    line = norm(expected, subj_std).ppf(percentile)

    base = round(line)
    final_line = base - 0.5 if line_type == "Over" else base + 0.5

    # Debug
    print(f"Expected: {expected:.2f}, Line type: {line_type}, Final line: {final_line:.2f}")

    return final_line

def generate_biased_caps_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots,
    global_avg_strength,
    line_type,
    recency_weight=0.1,
):
    # Weights for the composite score
    w1, w2, w3 = 0.25, 0.25, 0.25

    def player_strength(profile, shots):
        adj_score = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)
        # Manual normalization
        norm_score = adj_score / 8
        norm_shots = shots / 16
        return (
            w1 * norm_score +
            w2 * norm_shots +
            w3 * win_rate
        )

    your_strengths = [player_strength(p, s) for p, s in zip(your_team_profiles, your_team_shots)]
    opp_strengths = [player_strength(p, s) for p, s in zip(opp_team_profiles, opp_team_shots)]

    your_team_strength = harmonic_mean(your_strengths)
    opp_team_strength = harmonic_mean(opp_strengths)

    # Team scores adjusted by strength vs global avg
    your_score = your_team_strength * team_strength_multiplier(your_team_strength, global_avg_strength)
    opp_score  = opp_team_strength * team_strength_multiplier(opp_team_strength, global_avg_strength)

    expected_margin = your_score - opp_score

    # Bias the margin slightly
    std = 1.5
    percentile = 0.47 if line_type == "Over" else 0.53
    line = norm(expected_margin, std).ppf(percentile)

    if line < 0:
        line = abs(line)
        line_type = "Under"

    base = round(line)
    final_line = base - 0.5 if line_type == "Over" else base + 0.5

    # Debug
    print("🧠 CAPS Score Biasing")
    print("  Your team strengths:", your_strengths)
    print("  Opp team strengths:", opp_strengths)
    print("  Your team strength (harmonic):", your_team_strength)
    print("  Opp team strength (harmonic):", opp_team_strength)
    print("  Expected margin:", expected_margin)
    print(f"  Final line: {final_line:.2f} ({line_type})")

    return final_line, line_type
