"""Statistical/property tests for item 7.2 — line-generation.

The golden-master test (test_golden_master_3_1.py) pins exact byte-for-byte
output against fixed inputs, guarding the 3.1 refactor against accidental
drift. This file is complementary, not a duplicate: it tests the *properties*
the line-generation math is supposed to have (bias direction, monotonicity,
clamping bounds) using pytest.approx, independent of any specific pinned
constant. If someone tunes a coefficient in bet_generation.py, the golden
master will (correctly) fail; these tests should keep passing as long as the
underlying behavior is still sound.

No DB/live data needed — every function under test here takes plain stat
dicts as arguments. Where a function needs a cursor (Pong/Beerball's global
averages), a MagicMock stands in, matching the pattern already established
in test_golden_master_3_1.py.
"""
import math
from unittest.mock import MagicMock

import pytest

from backend.bet_generation import (
    BEERBALL,
    CAPS,
    PONG,
    beerball_opportunity_factor,
    caps_opportunity_factor,
    generate_biased_beerball_shots_line,
    generate_biased_caps_shots_line,
    generate_biased_pong_shots_line,
    harmonic_mean,
    pong_team_advantage_factor,
    pong_teammate_suppression_factor,
    snap_to_half_point,
    team_strength_multiplier,
)

SUBJ = {"mean": 5.0, "std": 2.0, "mean_last_5": 6.0}
MATE = {"mean": 4.0, "std": 1.5, "mean_last_5": 3.5}
OPP1 = {"mean": 4.5, "std": 1.8, "mean_last_5": 4.0}
OPP2 = {"mean": 3.0, "std": 1.2, "mean_last_5": 2.5}


def _pong_cur(avg_mean=4.2):
    cur = MagicMock()
    cur.fetchone.return_value = {"avg_mean": avg_mean}
    return cur


def _beerball_cur(avg_dv=0.52):
    cur = MagicMock()
    cur.fetchone.return_value = {"avg_dv": avg_dv}
    return cur


# ---------------------------------------------------------------------------
# snap_to_half_point — every generated line must land on a half-point so no
# push (exact tie) is ever possible.
# ---------------------------------------------------------------------------

class TestSnapToHalfPoint:
    @pytest.mark.parametrize("raw", [0.0, 1.2, 4.9, 5.5, 10.0, 23.999, -3.4])
    @pytest.mark.parametrize("line_type", ["Over", "Under"])
    def test_always_lands_on_a_half_point(self, raw, line_type):
        result = snap_to_half_point(raw, line_type)
        assert result % 1 == pytest.approx(0.5)

    def test_over_biases_down_from_rounded_base(self):
        # Over: base - 0.5 — the poster's Over line sits half a point below
        # the nearest integer, biasing toward the house (the Over side loses
        # ties that would otherwise round up).
        assert snap_to_half_point(5.0, "Over") == pytest.approx(4.5)

    def test_under_biases_up_from_rounded_base(self):
        assert snap_to_half_point(5.0, "Under") == pytest.approx(5.5)

    def test_over_always_strictly_less_than_under_for_same_raw_line(self):
        for raw in [0.0, 2.3, 7.8, 15.5, 100.1]:
            over = snap_to_half_point(raw, "Over")
            under = snap_to_half_point(raw, "Under")
            assert over < under


# ---------------------------------------------------------------------------
# harmonic_mean
# ---------------------------------------------------------------------------

class TestHarmonicMean:
    def test_uniform_values_returns_the_value_itself(self):
        assert harmonic_mean([2.0, 2.0, 2.0]) == pytest.approx(2.0)

    def test_known_two_value_case(self):
        # HM(1, 3) = 2 / (1/1 + 1/3) = 1.5
        assert harmonic_mean([1.0, 3.0]) == pytest.approx(1.5)

    def test_empty_list_returns_zero(self):
        assert harmonic_mean([]) == 0

    def test_all_zero_values_returns_zero(self):
        assert harmonic_mean([0.0, 0.0]) == 0

    @pytest.mark.parametrize(
        "values", [[1.0, 2.0, 3.0], [5.0, 5.0, 1.0], [10.0, 2.0, 8.0, 4.0]]
    )
    def test_never_exceeds_arithmetic_mean(self, values):
        # AM-HM inequality: harmonic mean <= arithmetic mean for positive reals,
        # with equality only when all values are identical.
        hm = harmonic_mean(values)
        am = sum(values) / len(values)
        assert hm <= am + 1e-9


# ---------------------------------------------------------------------------
# team_strength_multiplier — symmetric clamp around 1.0
# ---------------------------------------------------------------------------

class TestTeamStrengthMultiplier:
    def test_equal_strength_gives_neutral_multiplier(self):
        assert team_strength_multiplier(5.0, 5.0) == pytest.approx(1.0)

    def test_clamped_to_upper_bound(self):
        # deviation * 0.75 clamped to +0.3 -> multiplier caps at 1.3
        assert team_strength_multiplier(100.0, 1.0) == pytest.approx(1.3)

    def test_clamped_to_lower_bound(self):
        assert team_strength_multiplier(1.0, 100.0) == pytest.approx(0.7)

    def test_monotonic_increasing_in_strength(self):
        lo = team_strength_multiplier(3.0, 5.0)
        mid = team_strength_multiplier(5.0, 5.0)
        hi = team_strength_multiplier(7.0, 5.0)
        assert lo < mid < hi


# ---------------------------------------------------------------------------
# Per-sport opportunity factors
# ---------------------------------------------------------------------------

class TestCapsOpportunityFactor:
    def test_perfect_balance_gives_max_opportunity(self):
        assert caps_opportunity_factor(1.0) == pytest.approx(1.4)

    @pytest.mark.parametrize("ratio", [0.1, 0.5, 0.9, 1.0, 1.1, 1.5, 3.0])
    def test_always_within_documented_bounds(self, ratio):
        assert 0.7 <= caps_opportunity_factor(ratio) <= 1.4


class TestPongOpportunityFactor:
    def test_advantage_factor_is_sqrt_of_ratio_within_cap_range(self):
        # 2.25 sits inside the [0.4, 2.5] clamp range, so the exponent applies
        # to the raw ratio unmodified: sqrt(2.25) == 1.5.
        assert pong_team_advantage_factor(2.25) == pytest.approx(1.5)
        assert pong_team_advantage_factor(1.0) == pytest.approx(1.0)

    def test_advantage_factor_clamps_extreme_ratios(self):
        uncapped_high = pong_team_advantage_factor(999.0)
        uncapped_low = pong_team_advantage_factor(0.0001)
        assert uncapped_high == pytest.approx(2.5 ** 0.5)
        assert uncapped_low == pytest.approx(0.4 ** 0.5)

    def test_suppression_is_neutral_when_teammates_match_global_avg(self):
        assert pong_teammate_suppression_factor([4.2, 4.2], 4.2) == pytest.approx(1.0)

    def test_suppression_clamped_to_bounds(self):
        strong_teammates = pong_teammate_suppression_factor([50.0, 50.0], 1.0)
        weak_teammates = pong_teammate_suppression_factor([-50.0, -50.0], 1.0)
        assert strong_teammates == pytest.approx(0.8)
        assert weak_teammates == pytest.approx(1.1)


class TestBeerballOpportunityFactor:
    def test_equal_skill_and_center_defense_gives_neutral_skill_bonus(self):
        # your_win_rate == opp_win_rate -> skill_ratio == 1 -> skill_bonus == 1.0
        result = beerball_opportunity_factor(0.5, 0.5, avg_opp_dv=0.5, avg_dv_center=0.5)
        # At dv == center, the sigmoid defensive_adjustment sits exactly at its
        # midpoint: scale + (max_boost - scale) * 0.5.
        expected_defense = 0.7 + (1.4 - 0.7) * 0.5
        assert result == pytest.approx(1.0 * expected_defense)

    def test_better_skill_ratio_increases_opportunity(self):
        weaker = beerball_opportunity_factor(0.4, 0.6, avg_opp_dv=0.5, avg_dv_center=0.5)
        stronger = beerball_opportunity_factor(0.6, 0.4, avg_opp_dv=0.5, avg_dv_center=0.5)
        assert stronger > weaker


# ---------------------------------------------------------------------------
# Cross-sport shots-line invariants
# ---------------------------------------------------------------------------

class TestShotsLineBiasDirection:
    """Every sport's Over line must sit strictly below its Under line for
    identical inputs — the house-favor percentile split (0.47/0.53 or
    0.48/0.52) plus the snap_to_half_point shift both push in that direction.
    A regression here means a bet could push or the bias could invert."""

    def test_caps_over_below_under(self):
        over = generate_biased_caps_shots_line(SUBJ, [MATE], [OPP1, OPP2], "Over")
        under = generate_biased_caps_shots_line(SUBJ, [MATE], [OPP1, OPP2], "Under")
        assert over < under

    def test_pong_over_below_under(self):
        over = generate_biased_pong_shots_line(SUBJ, [MATE], [OPP1, OPP2], "Over", 2, _pong_cur())
        under = generate_biased_pong_shots_line(SUBJ, [MATE], [OPP1, OPP2], "Under", 2, _pong_cur())
        assert over < under

    def test_beerball_over_below_under(self):
        over = generate_biased_beerball_shots_line(
            _beerball_cur(), 2, SUBJ, 0.6, 0.5, 0.55, "Over"
        )
        under = generate_biased_beerball_shots_line(
            _beerball_cur(), 2, SUBJ, 0.6, 0.5, 0.55, "Under"
        )
        assert over < under


class TestShotsLineMonotonicity:
    """A stronger subject (higher recent-weighted mean) should never produce
    a lower line than a weaker one, all else equal."""

    def test_caps_line_increases_with_subject_strength(self):
        weak_subject = {"mean": 2.0, "std": 2.0, "mean_last_5": 2.0}
        strong_subject = {"mean": 9.0, "std": 2.0, "mean_last_5": 9.0}
        low = generate_biased_caps_shots_line(weak_subject, [MATE], [OPP1, OPP2], "Over")
        high = generate_biased_caps_shots_line(strong_subject, [MATE], [OPP1, OPP2], "Over")
        assert low < high

    def test_pong_line_is_capped_at_9_5_regardless_of_line_type(self):
        # generate_biased_pong_shots_line hard-caps both Over and Under at 9.5
        # (min(base ± 0.5, 9.5)) — a real asymmetric quirk worth pinning.
        extreme_subject = {"mean": 500.0, "std": 1.0, "mean_last_5": 500.0}
        over = generate_biased_pong_shots_line(
            extreme_subject, [MATE], [OPP1, OPP2], "Over", 2, _pong_cur()
        )
        under = generate_biased_pong_shots_line(
            extreme_subject, [MATE], [OPP1, OPP2], "Under", 2, _pong_cur()
        )
        assert over == pytest.approx(9.5)
        assert under == pytest.approx(9.5)


# ---------------------------------------------------------------------------
# Score-line sanity checks (shared shape across CAPS/PONG/BEERBALL)
# ---------------------------------------------------------------------------

SP = {"mean": 5.0, "std": 2.0, "mean_last_5": 6.0, "win_rate": 0.6, "defensive_value": 0.55}
SP2 = {"mean": 4.0, "std": 1.5, "mean_last_5": 3.5, "win_rate": 0.5, "defensive_value": 0.45}
OP = {"mean": 4.5, "std": 1.8, "mean_last_5": 4.0, "win_rate": 0.55, "defensive_value": 0.6}
OP2 = {"mean": 3.0, "std": 1.2, "mean_last_5": 2.5, "win_rate": 0.4, "defensive_value": 0.5}
YOUR_SHOTS = [5.0, 4.0]
OPP_SHOTS = [4.5, 3.0]
GLOBAL_AVG_STRENGTH = 0.5


class TestScoreLineInvariants:
    @pytest.mark.parametrize("sport", [CAPS, PONG, BEERBALL])
    @pytest.mark.parametrize("line_type", ["Over", "Under"])
    def test_final_line_is_never_negative(self, sport, line_type):
        final_line, _ = sport.predict_score(
            [SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, line_type
        )
        assert final_line >= 0

    @pytest.mark.parametrize("sport", [CAPS, PONG, BEERBALL])
    @pytest.mark.parametrize("line_type", ["Over", "Under"])
    def test_final_line_lands_on_a_half_point(self, sport, line_type):
        final_line, _ = sport.predict_score(
            [SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, line_type
        )
        assert final_line % 1 == pytest.approx(0.5)

    @pytest.mark.parametrize("sport", [CAPS, PONG, BEERBALL])
    def test_returned_line_type_is_always_over_or_under(self, sport):
        for requested in ["Over", "Under"]:
            _, resolved_type = sport.predict_score(
                [SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, requested
            )
            assert resolved_type in ("Over", "Under")

    def test_much_weaker_team_flips_over_to_under(self):
        # A hugely disadvantaged "your" team produces a negative expected
        # margin; the generator flips Over -> Under rather than emitting a
        # negative line (see bet_generation.py's `if line < 0: line_type =
        # "Under"` branch in every score generator).
        weak = {"mean": 0.1, "std": 0.5, "mean_last_5": 0.1, "win_rate": 0.05, "defensive_value": 0.1}
        dominant_opp = {"mean": 9.0, "std": 0.5, "mean_last_5": 9.0, "win_rate": 0.95, "defensive_value": 0.95}
        _, resolved_type = CAPS.predict_score(
            [weak, weak], [dominant_opp, dominant_opp], [1.0, 1.0], [15.0, 15.0], 0.5, "Over"
        )
        assert resolved_type == "Under"
