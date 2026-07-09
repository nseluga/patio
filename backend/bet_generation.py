# Unified CPU bet-line generation for all sports (Caps, Pong, Beerball).
#
# Consolidates the former caps_bet_generation.py / pong_bet_generation.py /
# beerball_bet_generation.py into one parameterized module. Behavior is
# preserved byte-for-byte per sport and line type (see tests/test_golden_master_3_1.py).
#
# Architecture:
#   Shared pipeline    -> fetch_players / build_profiles (DB reads), assemble_matchup,
#                         adjust, team_strength_multiplier, apply_house_bias, snap_to_half_point.
#   Per-sport strategy -> injected via a SportConfig holding sport-specific constants and
#                         the predict_shots / predict_score callables. DV, teammate
#                         suppression and the differing opportunity_factor signatures stay
#                         explicit per sport rather than force-fit into one path.
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import random
from scipy.stats import norm

logger = logging.getLogger(__name__)

RECENCY_WEIGHT = 0.1
SCORE_MARGIN_STD = 1.5


# ---------------------------------------------------------------------------
# Shared pipeline primitives (identical across all three original modules)
# ---------------------------------------------------------------------------

def adjust(stats, recency_weight):
    """Blend season mean with recent (last-5) mean at the given recency weight."""
    return stats["mean"] + (stats["mean_last_5"] - stats["mean"]) * recency_weight


def harmonic_mean(values):
    values = [v for v in values if v > 0]
    return len(values) / sum(1 / v for v in values) if values else 0


def team_strength_multiplier(strength, avg_strength):
    deviation = strength - avg_strength
    return 1.0 + max(min(deviation * 0.75, 0.3), -0.3)


def snap_to_half_point(raw_line, line_type):
    """Round to nearest integer then shift by half a point in the house's favor."""
    base = round(raw_line)
    return base - 0.5 if line_type == "Over" else base + 0.5


# ---------------------------------------------------------------------------
# Sport-specific opportunity factors (kept explicit — different signatures)
# ---------------------------------------------------------------------------

# --- Caps: discrete balance-ratio thresholds ---
def caps_opportunity_factor(balance_ratio):
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


# --- Pong: team advantage × teammate suppression ---
def pong_team_advantage_factor(balance_ratio):
    # Cap range to avoid extreme values
    balance_ratio = max(0.4, min(balance_ratio, 2.5))

    # Raise ratio to a power to exaggerate advantage or disadvantage
    exponent = 0.5  # √ratio for smoothing
    return balance_ratio ** exponent


def pong_teammate_suppression_factor(teammates_adj, global_avg):
    avg_teammate_score = sum(teammates_adj) / len(teammates_adj) if teammates_adj else 0
    diff = avg_teammate_score - global_avg  # + = strong teammates, - = weak teammates

    suppression = 1.0 - 0.04 * diff  # Steeper scaling: 1 cup above avg → -0.04
    return max(0.8, min(suppression, 1.1))  # Clamp to avoid extreme blowups


def pong_opportunity_factor(balance_ratio, teammates_adj, global_avg):
    return pong_team_advantage_factor(balance_ratio) * pong_teammate_suppression_factor(
        teammates_adj, global_avg
    )


# --- Beerball: skill ratio × defensive-value sigmoid ---
def beerball_opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv_center):
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


# ---------------------------------------------------------------------------
# Sport-specific shots-line generators (the predict_shots seam)
# ---------------------------------------------------------------------------

def generate_biased_caps_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, recency_weight=RECENCY_WEIGHT):
    subj_adj = adjust(subject_stats, recency_weight)
    team_adj = [adjust(p, recency_weight) for p in teammates_stats]
    opp_adj = [adjust(p, recency_weight) for p in opp_team_stats]

    # Step 1: Harmonic means
    your_team_vals = [subj_adj] + team_adj
    team_strength = harmonic_mean(your_team_vals)
    opp_strength = harmonic_mean(opp_adj)

    # Step 2: Balance → opportunity
    balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1
    opportunity = caps_opportunity_factor(balance_ratio)

    # Step 3: Expected value
    expected = subj_adj * opportunity

    # Step 4: Bias line slightly in CPU's favor
    percentile = 0.47 if line_type == "Over" else 0.53
    subj_std = subject_stats["std"]
    line = norm(expected, subj_std).ppf(percentile)

    final_line = snap_to_half_point(line, line_type)

    logger.debug("Expected: %.2f, Line type: %s, Final line: %.2f", expected, line_type, final_line)

    return final_line


def generate_biased_pong_shots_line(subject_stats, teammates_stats, opp_team_stats, line_type, team_size, cur, recency_weight=RECENCY_WEIGHT):
    subj_adj = adjust(subject_stats, recency_weight)
    team_adj = [adjust(p, recency_weight) for p in teammates_stats]
    opp_adj = [adjust(p, recency_weight) for p in opp_team_stats]

    your_team_vals = [subj_adj] + team_adj
    opp_team_vals = opp_adj

    team_strength = sum(your_team_vals) / len(your_team_vals)
    opp_strength = sum(opp_team_vals) / len(opp_team_vals)

    global_avg = get_global_pong_shots_average(cur, team_size)
    balance_ratio = team_strength / opp_strength if opp_strength > 0 else 1.0
    opportunity = pong_opportunity_factor(balance_ratio, team_adj, global_avg)

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

    logger.debug("Subject: %.2f, Teammates: %s, Opponents: %s", subj_adj, team_adj, opp_adj)
    logger.debug("Balance ratio: %.2f, Opportunity: %.2f", balance_ratio, opportunity)
    logger.debug("Expected: %.2f, Final line: %.2f", expected, final_line)
    return final_line


def generate_biased_beerball_shots_line(cur, team_size, subject_stats, your_win_rate, opp_win_rate, avg_opp_dv, line_type, recency_weight=RECENCY_WEIGHT):
    subj_adj = adjust(subject_stats, recency_weight)

    avg_dv = get_global_beerball_dv_average(cur, team_size)
    opportunity = beerball_opportunity_factor(your_win_rate, opp_win_rate, avg_opp_dv, avg_dv)

    expected = subj_adj * opportunity

    percentile = 0.47 if line_type == "Over" else 0.53
    subj_std = subject_stats["std"]
    line = norm(expected, subj_std).ppf(percentile)

    final_line = snap_to_half_point(line, line_type)

    logger.debug("Generated line: adjusted_mean=%s, opportunity=%s, expected=%s, raw_line=%s",
                 subj_adj, opportunity, expected, line)
    logger.debug("Expected: %.2f, Line type: %s, Final line: %.2f", expected, line_type, final_line)
    return final_line


# ---------------------------------------------------------------------------
# Sport-specific score-line generators (the predict_score seam)
# ---------------------------------------------------------------------------

def generate_biased_caps_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots,
    global_avg_strength,
    line_type,
    recency_weight=RECENCY_WEIGHT,
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
    opp_score = opp_team_strength * team_strength_multiplier(opp_team_strength, global_avg_strength)

    expected_margin = your_score - opp_score

    # Bias the margin slightly
    std = SCORE_MARGIN_STD
    percentile = 0.47 if line_type == "Over" else 0.53
    line = norm(expected_margin, std).ppf(percentile)

    if line < 0:
        line = abs(line)
        line_type = "Under"

    final_line = snap_to_half_point(line, line_type)

    logger.debug(
        "Caps Score biasing: your_strengths=%s, opp_strengths=%s, "
        "your_team_strength(harmonic)=%s, opp_team_strength(harmonic)=%s, "
        "expected_margin=%s, final_line=%.2f (%s)",
        your_strengths, opp_strengths,
        your_team_strength, opp_team_strength,
        expected_margin, final_line, line_type,
    )

    return final_line, line_type


def generate_biased_pong_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots,
    global_avg_strength,
    line_type,
    recency_weight=RECENCY_WEIGHT,
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
    opp_adj_scores = [adjust(p, recency_weight) for p in opp_team_profiles]

    # Normalized team strength (independent of score)
    your_strengths = [player_strength(p, s) for p, s in zip(your_team_profiles, your_team_shots)]
    opp_strengths = [player_strength(p, s) for p, s in zip(opp_team_profiles, opp_team_shots)]

    your_avg_score = sum(your_adj_scores) / len(your_adj_scores)
    opp_avg_score = sum(opp_adj_scores) / len(opp_adj_scores)

    your_strength = sum(your_strengths) / len(your_strengths)
    opp_strength = sum(opp_strengths) / len(opp_strengths)

    your_score = your_avg_score * team_strength_multiplier(your_strength, global_avg_strength)
    opp_score = opp_avg_score * team_strength_multiplier(opp_strength, global_avg_strength)

    expected_margin = your_score - opp_score
    std = SCORE_MARGIN_STD
    percentile = 0.47 if line_type == "Over" else 0.53
    line = norm(expected_margin, std).ppf(percentile)

    if line < 0:
        line = abs(line)
        line_type = "Under"

    final_line = snap_to_half_point(line, line_type)

    logger.debug("[Pong Score] Expected margin: %.2f, Line: %s (%s)", expected_margin, final_line, line_type)
    return final_line, line_type


def generate_biased_beerball_score_line(
    your_team_profiles, opp_team_profiles,
    your_team_shots, opp_team_shots, global_avg_strength,
    line_type, recency_weight=RECENCY_WEIGHT,
):
    # Weights for the composite score
    w1, w2, w3, w4 = 0.25, 0.25, 0.25, 0.25

    def player_strength(profile, shots_made):
        adj_score = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)
        dv = profile.get("defensive_value", 0.5)
        # Manual normalization
        norm_score = adj_score / 3
        norm_shots = shots_made / 10
        return (
            w1 * norm_score +
            w2 * norm_shots +
            w3 * win_rate +
            w4 * dv
        )

    your_adj_scores = [adjust(p, recency_weight) for p in your_team_profiles]
    opp_adj_scores = [adjust(p, recency_weight) for p in opp_team_profiles]

    your_strengths = [player_strength(p, s) for p, s in zip(your_team_profiles, your_team_shots)]
    opp_strengths = [player_strength(p, s) for p, s in zip(opp_team_profiles, opp_team_shots)]

    logger.debug("Your strengths: %s, Opponent strengths: %s", your_strengths, opp_strengths)

    your_avg_score = sum(your_adj_scores) / len(your_adj_scores)
    opp_avg_score = sum(opp_adj_scores) / len(opp_adj_scores)

    your_strength = sum(your_strengths) / len(your_strengths)
    opp_strength = sum(opp_strengths) / len(opp_strengths)

    your_score = your_avg_score * team_strength_multiplier(your_strength, global_avg_strength)
    opp_score = opp_avg_score * team_strength_multiplier(opp_strength, global_avg_strength)

    expected_margin = your_score - opp_score

    # Simulate margin line (bias slightly in CPU's favor)
    percentile = 0.47 if line_type == "Over" else 0.53
    std = SCORE_MARGIN_STD  # assumed margin volatility
    line = norm(expected_margin, std).ppf(percentile)

    logger.debug("Line: %s, Line type: %s", line, line_type)

    # Ensure all lines are non-negative
    if line < 0:
        line = abs(line)
        line_type = "Under"

    final_line = snap_to_half_point(line, line_type)

    logger.debug(
        "Composite Score: global_avg=%s, your_mult=%s, opp_mult=%s, "
        "your_avg_score=%s, your_strength=%s, your_score=%s, "
        "opp_avg_score=%s, opp_strength=%s, opp_score=%s, "
        "expected_margin=%s, line_type=%s, final_line=%.2f",
        global_avg_strength,
        team_strength_multiplier(your_strength, global_avg_strength),
        team_strength_multiplier(opp_strength, global_avg_strength),
        your_avg_score, your_strength, your_score,
        opp_avg_score, opp_strength, opp_score,
        expected_margin, line_type, final_line,
    )

    return final_line, line_type


# ---------------------------------------------------------------------------
# Shared DB reads (fetch_players / build_profiles), parameterized by SportConfig
# ---------------------------------------------------------------------------

def get_shots_players(cur, game_name, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = %s
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (game_name, team_size))
    rows = cur.fetchall()
    return [row['player_name'] for row in rows]


def get_player_shots_profile(cur, game_name, player_name, team_size):
    cur.execute("""
        SELECT mean, std, mean_last_5
        FROM player_stat_aggregates
        WHERE player_name = %s
          AND game_played = %s
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_name, game_name, team_size))
    row = cur.fetchone()
    if row:
        row["player_name"] = player_name
    return row


def get_score_players(cur, game_name, team_size):
    cur.execute("""
        SELECT DISTINCT player_name
        FROM player_stat_aggregates
        WHERE game_played = %s
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (game_name, team_size))
    return [row["player_name"] for row in cur.fetchall()]


def assemble_matchup(players, team_size):
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


# --- Caps score profile: mean, std, mean_last_5 ---
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


def get_global_caps_score_strength_average(cur, team_size, recency_weight=RECENCY_WEIGHT):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate
        FROM player_stat_aggregates
        WHERE game_played = 'Caps'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    score_rows = cur.fetchall()

    player_names = [row["player_name"] for row in score_rows]
    cur.execute("""
        SELECT player_name, mean
        FROM player_stat_aggregates
        WHERE player_name = ANY(%s)
          AND game_played = 'Caps'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_names, team_size))
    shots_by_name = {row["player_name"]: row["mean"] for row in cur.fetchall()}

    strengths = []
    for row in score_rows:
        profile = dict(row)
        name = profile["player_name"]

        if name not in shots_by_name:
            continue  # skip if missing shots

        shots = shots_by_name[name]

        score_adj = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)

        strength = 0.25 * score_adj + 0.25 * shots + 0.25 * win_rate
        strengths.append(strength)
        logger.debug("Included %s: %.2f", name, strength)

    if not strengths:
        logger.warning("No players had both Score and Shots data")
        return 1.0

    avg = np.mean(strengths)
    logger.debug("Global avg Caps strength: %.4f", avg)
    return avg


# --- Pong shots global average + score profile ---
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


def get_global_pong_score_strength_average(cur, team_size, recency_weight=RECENCY_WEIGHT):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate
        FROM player_stat_aggregates
        WHERE game_played = 'Pong'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    rows = cur.fetchall()

    player_names = [row["player_name"] for row in rows]
    cur.execute("""
        SELECT player_name, mean FROM player_stat_aggregates
        WHERE player_name = ANY(%s) AND game_played = 'Pong'
          AND game_type = 'Shots Made' AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_names, team_size))
    shots_by_name = {row["player_name"]: row["mean"] for row in cur.fetchall()}

    strengths = []
    for row in rows:
        profile = dict(row)
        name = profile["player_name"]

        if name not in shots_by_name:
            continue

        shots = shots_by_name[name]
        score_adj = adjust(profile, recency_weight)
        win_rate = profile.get("win_rate", 0.5)

        # Normalized composite
        strength = 0.25 * (score_adj / 10) + 0.25 * (shots / 10) + 0.25 * win_rate
        strengths.append(strength)

    return np.mean(strengths) if strengths else 1.0


# --- Beerball score profile (adds win_rate + defensive_value), DV average ---
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


def get_global_beerball_score_strength_average(cur, team_size, recency_weight=RECENCY_WEIGHT):
    cur.execute("""
        SELECT player_name, mean, mean_last_5, win_rate, defensive_value
        FROM player_stat_aggregates
        WHERE game_played = 'Beerball'
          AND game_type = 'Score'
          AND stat_name = 'score'
          AND team_size = %s
    """, (team_size,))
    score_rows = cur.fetchall()

    player_names = [row["player_name"] for row in score_rows]
    cur.execute("""
        SELECT player_name, mean
        FROM player_stat_aggregates
        WHERE player_name = ANY(%s)
          AND game_played = 'Beerball'
          AND game_type = 'Shots Made'
          AND stat_name = 'shots_made'
          AND team_size = %s
    """, (player_names, team_size))
    shots_by_name = {row["player_name"]: row["mean"] for row in cur.fetchall()}

    strengths = []
    for row in score_rows:
        profile = dict(row)
        name = profile["player_name"]

        if name not in shots_by_name:
            continue  # skip if missing shots data

        shots = shots_by_name[name]

        strength = (
            0.25 * adjust(profile, recency_weight) +
            0.25 * shots +
            0.25 * profile.get("win_rate", 0.5) +
            0.25 * profile.get("defensive_value", 0.5)
        )
        strengths.append(strength)
        logger.debug("Included strength for %s: %.2f", name, strength)

    if not strengths:
        logger.warning("No players had both Score and Shots Made data")
        return 1.0

    avg_strength = np.mean(strengths)
    logger.debug("Global average strength (from %d players): %.4f", len(strengths), avg_strength)
    return avg_strength


# ---------------------------------------------------------------------------
# SportConfig: the per-sport strategy seam
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SportConfig:
    """Bundles a sport's name and the callables that vary per sport.

    predict_shots / predict_score are the injected strategy seam. Their
    signatures differ per sport (Pong shots needs cur+team_size for the global
    average; Beerball shots takes win-rate/DV inputs) so callers pass the
    sport's required arguments through; the shared pipeline (fetch/assemble/
    profiles) is reused across all three.
    """
    game_name: str
    get_shots_players: Callable
    get_shots_profile: Callable
    get_score_players: Callable
    get_score_profile: Callable
    get_global_score_strength_average: Callable
    predict_shots: Callable
    predict_score: Callable


CAPS = SportConfig(
    game_name="Caps",
    get_shots_players=lambda cur, team_size: get_shots_players(cur, "Caps", team_size),
    get_shots_profile=lambda cur, player_name, team_size: get_player_shots_profile(cur, "Caps", player_name, team_size),
    get_score_players=lambda cur, team_size: get_score_players(cur, "Caps", team_size),
    get_score_profile=get_player_caps_score_profile,
    get_global_score_strength_average=get_global_caps_score_strength_average,
    predict_shots=generate_biased_caps_shots_line,
    predict_score=generate_biased_caps_score_line,
)

PONG = SportConfig(
    game_name="Pong",
    get_shots_players=lambda cur, team_size: get_shots_players(cur, "Pong", team_size),
    get_shots_profile=lambda cur, player_name, team_size: get_player_shots_profile(cur, "Pong", player_name, team_size),
    get_score_players=lambda cur, team_size: get_score_players(cur, "Pong", team_size),
    get_score_profile=get_player_pong_score_profile,
    get_global_score_strength_average=get_global_pong_score_strength_average,
    predict_shots=generate_biased_pong_shots_line,
    predict_score=generate_biased_pong_score_line,
)

BEERBALL = SportConfig(
    game_name="Beerball",
    get_shots_players=lambda cur, team_size: get_shots_players(cur, "Beerball", team_size),
    get_shots_profile=lambda cur, player_name, team_size: get_player_shots_profile(cur, "Beerball", player_name, team_size),
    get_score_players=lambda cur, team_size: get_score_players(cur, "Beerball", team_size),
    get_score_profile=get_player_beerball_score_profile,
    get_global_score_strength_average=get_global_beerball_score_strength_average,
    predict_shots=generate_biased_beerball_shots_line,
    predict_score=generate_biased_beerball_score_line,
)

SPORTS = {"Caps": CAPS, "Pong": PONG, "Beerball": BEERBALL}
