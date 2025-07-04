# Functions for generation cpu bets
from scipy.stats import norm
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

def assemble_caps_shots_matchup(players, team_size):
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

# Generate a biased line for Caps Shots Made bets
# lines make theoretical sense but may need to be adjusted depending on actual player stats and actual games
def generate_biased_caps_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, recency_weight=0.1):
    def adjust(stats):
        return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight

    subj_adj = adjust(subject_stats)
    team_adj = [adjust(p) for p in teammates_stats]
    opp_adj = [adjust(p) for p in opp_team_stats]

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