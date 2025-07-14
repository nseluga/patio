# Functions for pong generation cpu bets
from scipy.stats import norm
import numpy as np
import random

def get_pong_shots_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Pong'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]

def get_player_pong_shots_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Pong'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_name, team_size))
    
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_global_pong_shots_average(cur, team_size):
    cur.execute("""
        SELECT AVG(mean) AS avg_mean
        FROM player_stat_aggregates
        WHERE game_played = 'Pong'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (team_size,))
    row = cur.fetchone()
    return row["avg_mean"] if row and row["avg_mean"] is not None else 4.0  # default fallback

def get_pong_score_players(cur, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = 'Pong'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]

def get_player_pong_score_profile(cur, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5, win_rate
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = 'Pong'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (player_name, team_size))
    
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row

def get_global_pong_score_strength_average(cur, team_size, recency_weight=0.1):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate
        FROM player_stat_aggregates
        WHERE game_played = 'Pong'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()

    strengths = []
    for row in rows:
        profile = dict(row)
        name = profile["player_name"]

        cur.execute("""
            SELECT mean FROM player_stat_aggregates
            WHERE player_name = %s AND game_played = 'Pong'
              AND game_type = 'Shots Made' AND stat_name = 'shots_made'
              AND team_size = %s
        """, (name, team_size))
        shot_row = cur.fetchone()
        if not shot_row:
            continue

        shots = shot_row["mean"]
        score_adj = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)

        # Normalized composite
        strength = 0.25 * (score_adj / 10) + 0.25 * (shots / 10) + 0.25 * win_rate
        strengths.append(strength)

    return np.mean(strengths) if strengths else 1.0

def assemble_pong_shots_matchup(players, team_size):
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

def adjust(stats, recency_weight):
        return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight

def team_advantage_factor(balance_ratio):
    # Cap range to avoid extreme values
    balance_ratio = max(0.4, min(balance_ratio, 2.5))

    # Raise ratio to a power to exaggerate advantage or disadvantage
    exponent = 0.5  # √ratio for smoothing
    return balance_ratio ** exponent

def teammate_suppression_factor(teammates_adj, global_avg):
    avg_teammate_score = sum(teammates_adj) / len(teammates_adj) if teammates_adj else 0
    diff = avg_teammate_score - global_avg  # + = strong teammates, - = weak teammates

    suppression = 1.0 - 0.04 * diff  # Steeper scaling: 1 cup above avg → -0.04
    return max(0.8, min(suppression, 1.1))  # Clamp to avoid extreme blowups

def opportunity_factor(balance_ratio, teammates_adj, global_avg):
    return team_advantage_factor(balance_ratio) * teammate_suppression_factor(teammates_adj, global_avg)

def team_strength_multiplier(strength, avg_strength):
    deviation = strength - avg_strength
    return 1.0 + max(min(deviation * 0.75, 0.3), -0.3)

def generate_biased_pong_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, team_size, cur, recency_weight=0.1):
    subj_adj = adjust(subject_stats, recency_weight)
    team_adj = [adjust(p, recency_weight) for p in teammates_stats]
    opp_adj = [adjust(p, recency_weight) for p in opp_team_stats]

    your_team_vals = [subj_adj] + team_adj
    opp_team_vals = opp_adj

    team_strength = sum(your_team_vals) / len(your_team_vals)
    opp_strength = sum(opp_team_vals) / len(opp_team_vals)

    global_avg = get_global_pong_shots_average(cur, team_size)
    balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1.0
    opportunity = opportunity_factor(balance_ratio, team_adj, global_avg)

    expected = subj_adj * opportunity

    # Bias line in CPU's favor
    subj_std = subject_stats["std"]
    percentile = 0.48 if line_type == "Over" else 0.52
    line = norm(expected, subj_std).ppf(percentile)

    base = round(line)
    if line_type == "Over":
        final_line = min(base - 0.5, 9.5)
    else:  # "Under"
        final_line = min(base + 0.5, 9.5)

    print(f"Subject: {subj_adj:.2f}, Teammates: {team_adj}, Opponents: {opp_adj}")
    print(f"Balance ratio: {balance_ratio:.2f}, Opportunity: {opportunity:.2f}")
    print(f"Expected: {expected:.2f}, Final line: {final_line:.2f}")
    return final_line

def generate_biased_pong_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots,
    global_avg_strength,
    line_type,
    recency_weight=0.1
):
    # Weights for the composite score
    w1, w2, w3 = 0.25, 0.25, 0.25

    def player_strength(profile, shots):
        adj_score = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)
        norm_score = adj_score / 10
        norm_shots = shots / 10
        return (
            w1 * norm_score +
            w2 * norm_shots +
            w3 * win_rate
        )

    # Adjusted average scores
    your_adj_scores = [adjust(p, recency_weight) for p in your_team_profiles]
    opp_adj_scores  = [adjust(p, recency_weight) for p in opp_team_profiles]

    # Normalized team strength (independent of score)
    your_strengths = [player_strength(p, s) for p, s in zip(your_team_profiles, your_team_shots)]
    opp_strengths  = [player_strength(p, s) for p, s in zip(opp_team_profiles, opp_team_shots)]

    your_avg_score = sum(your_adj_scores) / len(your_adj_scores)
    opp_avg_score  = sum(opp_adj_scores) / len(opp_adj_scores)

    your_strength = sum(your_strengths) / len(your_strengths)
    opp_strength  = sum(opp_strengths) / len(opp_strengths)

    your_score = your_avg_score * team_strength_multiplier(your_strength, global_avg_strength)
    opp_score  = opp_avg_score  * team_strength_multiplier(opp_strength, global_avg_strength)

    expected_margin = your_score - opp_score
    std = 1.5
    percentile = 0.47 if line_type == "Over" else 0.53
    line = norm(expected_margin, std).ppf(percentile)

    if line < 0:
        line = abs(line)
        line_type = "Under"

    base = round(line)
    final_line = base - 0.5 if line_type == "Over" else base + 0.5

    print(f"[PONG Score] Expected margin: {expected_margin:.2f}, Line: {final_line} ({line_type})")
    return final_line, line_type
