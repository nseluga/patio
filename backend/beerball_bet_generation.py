# Functions for beerball generation cpu bets
import numpy as np
from scipy.stats import norm
import random

def get_beerball_shots_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Beerball'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]

def get_player_beerball_shots_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Beerball'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_name, team_size))
    
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_beerball_score_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Beerball'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]

def get_player_beerball_score_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, mean_last_5, win_rate, defensive_value
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Beerball'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (player_name, team_size))
    
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_global_beerball_dv_average(cur, team_size):
    cur.execute("""
        SELECT AVG(defensive_value) AS avg_dv
        FROM player_stat_aggregates
        WHERE game_played = 'Beerball'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
          AND defensive_value IS NOT NULL
    """, (team_size,))
    row = cur.fetchone()
    return row["avg_dv"] if row and row["avg_dv"] is not None else 0.7  # safe fallback

def get_global_beerball_score_strength_average(cur, team_size, recency_weight=0.1):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate, defensive_value
        FROM player_stat_aggregates
        WHERE game_played = 'Beerball'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    score_rows = cur.fetchall()

    strengths = []
    for row in score_rows:
        profile = dict(row)
        name = profile["player_name"]

        # 🔄 Use helper to get shots profile
        shots_profile = get_player_beerball_shots_profile(cur, name, team_size)
        if not shots_profile:
            continue  # ❌ Skip if missing

        shots = shots_profile["mean"]

        strength = (
            0.25 * adjust(profile, recency_weight) +
            0.25 * shots +
            0.25 * profile.get("win_rate", 0.5) +
            0.25 * profile.get("defensive_value", 0.5)
        )
        strengths.append(strength)
        print(f"  ✔️ Included strength for {name}: {strength:.2f}")

    if not strengths:
        print("⚠️ No players had both Score and Shots Made data")
        return 1.0

    avg_strength = np.mean(strengths)
    print(f"  ✅ Global average strength (from {len(strengths)} players): {avg_strength:.4f}")
    return avg_strength


def assemble_beerball_matchup(players, team_size):
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
    
    print("🏗️ Matchup generated:")
    print("  Your team:", your_team)
    print("  Opponent team:", opp_team)
    print("  Line subject:", playerA)
    print("  Matchup string:", matchup)

    return {
        "your_team": your_team,
        "opp_team": opp_team,
        "line_subject": playerA,
        "matchup": matchup
    }

def adjust(stats, recency_weight):
    return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight

def opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv_center):
    skill_ratio = your_win_rate / opp_win_rate if opp_win_rate > 0 else 1.0

    if skill_ratio >= 1:
        skill_bonus = min(1.0 + 0.4 * (skill_ratio - 1.0), 1.4)
    else:
        skill_bonus = max(1.0 - 0.6 * (1.0 - skill_ratio), 0.7)

    def defensive_adjustment(dv, center):
        steepness = np.log(81) / 0.45  # Very gentle slope
        scale = 0.7
        max_boost = 1.4
        return scale + (max_boost - scale) * (1 / (1 + np.exp(steepness * (center - dv))))
    
    defense_penalty = defensive_adjustment(avg_opp_dv, avg_dv_center)

    return skill_bonus * defense_penalty

def team_strength_multiplier(strength, avg_strength):
    deviation = strength - avg_strength
    return 1.0 + max(min(deviation * 0.75, 0.3), -0.3)

def generate_biased_beerball_shots_line(cur, team_size, subject_stats, your_win_rate, opp_win_rate, avg_opp_dv, line_type, recency_weight=0.1):
    subj_adj = adjust(subject_stats, recency_weight)

    avg_dv = get_global_beerball_dv_average(cur, team_size)
    opportunity = opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv)

    expected = subj_adj * opportunity

    percentile = 0.47 if line_type == "Over" else 0.53
    subj_std = subject_stats["std"]
    line = norm(expected, subj_std).ppf(percentile)

    base = round(line)
    final_line = base - 0.5 if line_type == "Over" else base + 0.5

    print("📏 Generated line details:")
    print("  Adjusted mean:", subj_adj)
    print("  Opportunity multiplier:", opportunity)
    print("  Expected value:", expected)
    print("  Final line:", line)

    print(f"Expected: {expected:.2f}, Line type: {line_type}, Final line: {final_line:.2f}")
    return final_line

def generate_biased_beerball_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots, global_avg_strength,
    line_type, recency_weight=0.1,
):
    # Weights for the composite score
    w1, w2, w3, w4 = 0.25, 0.25, 0.25, 0.25

    def player_strength(profile, shots_made):
        score_adj = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)
        dv = profile.get("defensive_value", 0.5)
        return (
            w1 * score_adj +
            w2 * shots_made +
            w3 * win_rate +
            w4 * dv
        )

    your_adj_scores = [adjust(p, recency_weight) for p in your_team_profiles]
    opp_adj_scores  = [adjust(p, recency_weight) for p in opp_team_profiles]

    your_strengths = [player_strength(p, s) for p, s in zip(your_team_profiles, your_team_shots)]
    opp_strengths  = [player_strength(p, s) for p, s in zip(opp_team_profiles, opp_team_shots)]

    print("  Your strengths:", your_strengths)
    print("  Opponent strengths:", opp_strengths)

    your_avg_score = sum(your_adj_scores) / len(your_adj_scores)
    opp_avg_score  = sum(opp_adj_scores) / len(opp_adj_scores)

    your_strength = sum(your_strengths) / len(your_strengths)
    opp_strength  = sum(opp_strengths) / len(opp_strengths)

    your_score = your_avg_score * team_strength_multiplier(your_strength, global_avg_strength)
    opp_score  = opp_avg_score  * team_strength_multiplier(opp_strength, global_avg_strength)

    expected_margin = your_score - opp_score

    # Simulate margin line (bias slightly in CPU's favor)
    percentile = 0.47 if line_type == "Over" else 0.53
    std = 1.5  # assumed margin volatility
    line = norm(expected_margin, std).ppf(percentile)

    print(" Line:", line)
    print(" Line type:", line_type)

    # Ensure all lines are non-negative
    if line < 0:
        line = abs(line)
        line_type = "Under"

    base = round(line)
    final_line = base - 0.5 if line_type == "Over" else base + 0.5

    print("📊 Composite Score Prediction")
    print("  Global average strength:", global_avg_strength)
    print("  Your team multiplier:", team_strength_multiplier(your_strength, global_avg_strength))
    print("  Opponent team multiplier:", team_strength_multiplier(opp_strength, global_avg_strength))
    print("  Your avg score:", your_avg_score)
    print("  Your team strength:", your_strength)
    print("  Your team score:", your_score)
    print("  Opponent avg score:", opp_avg_score)
    print("  Opponent team strength:", opp_strength)
    print("  Opponent team score:", opp_score)
    print("  Expected margin:", expected_margin)
    print(f"  Line type: {line_type}, Final line: {final_line:.2f}")

    return final_line, line_type
