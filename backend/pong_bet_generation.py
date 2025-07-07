# Functions for pong generation cpu bets
from scipy.stats import norm
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

def generate_biased_pong_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, team_size, cur, recency_weight=0.1):
    def adjust(stats):
        return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight

    subj_adj = adjust(subject_stats)
    team_adj = [adjust(p) for p in teammates_stats]
    opp_adj = [adjust(p) for p in opp_team_stats]

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