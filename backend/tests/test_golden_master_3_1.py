"""Golden-master parity check for item 3.1.

The three sport bet-generation modules (caps/pong/beerball_bet_generation.py) were
collapsed into the single parameterized backend/bet_generation.py. This test pins the
float outputs of all six line-generation functions against fixed representative inputs,
captured from the ORIGINAL modules before the collapse (see golden_master_3_1.json).

The consolidated module must reproduce every output byte-for-byte per sport and line type.

Line generation is exercised through the SportConfig strategy seam
(CAPS/PONG/BEERBALL .predict_shots / .predict_score), which is the sole
line-gen entry point the routes now use. Pinning the golden master to the
config callables means a future ML swap (rebinding predict_shots/predict_score
on a config) is caught here if it changes any frozen output.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock

from backend.bet_generation import BEERBALL, CAPS, PONG

GOLDEN = json.loads((Path(__file__).parent / "golden_master_3_1.json").read_text())

# ---------------------------------------------------------------------------
# Fixed representative inputs (identical to those used to capture the golden master)
# ---------------------------------------------------------------------------
SUBJ = {"mean": 5.0, "std": 2.0, "mean_last_5": 6.0}
MATE = {"mean": 4.0, "std": 1.5, "mean_last_5": 3.5}
OPP1 = {"mean": 4.5, "std": 1.8, "mean_last_5": 4.0}
OPP2 = {"mean": 3.0, "std": 1.2, "mean_last_5": 2.5}

SP = {"mean": 5.0, "std": 2.0, "mean_last_5": 6.0, "win_rate": 0.6, "defensive_value": 0.55}
SP2 = {"mean": 4.0, "std": 1.5, "mean_last_5": 3.5, "win_rate": 0.5, "defensive_value": 0.45}
OP = {"mean": 4.5, "std": 1.8, "mean_last_5": 4.0, "win_rate": 0.55, "defensive_value": 0.6}
OP2 = {"mean": 3.0, "std": 1.2, "mean_last_5": 2.5, "win_rate": 0.4, "defensive_value": 0.5}

YOUR_SHOTS = [5.0, 4.0]
OPP_SHOTS = [4.5, 3.0]
GLOBAL_AVG_STRENGTH = 0.5


def _pong_cur():
    cur = MagicMock()
    cur.fetchone.return_value = {"avg_mean": 4.2}
    return cur


def _beerball_cur():
    cur = MagicMock()
    cur.fetchone.return_value = {"avg_dv": 0.52}
    return cur


def test_caps_shots_over():
    assert CAPS.predict_shots(SUBJ, [MATE], [OPP1, OPP2], "Over") == GOLDEN["caps_shots_over"]


def test_caps_shots_under():
    assert CAPS.predict_shots(SUBJ, [MATE], [OPP1, OPP2], "Under") == GOLDEN["caps_shots_under"]


def test_caps_score_over():
    result = CAPS.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Over")
    assert list(result) == GOLDEN["caps_score_over"]


def test_caps_score_under():
    result = CAPS.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Under")
    assert list(result) == GOLDEN["caps_score_under"]


def test_pong_shots_over():
    assert PONG.predict_shots(SUBJ, [MATE], [OPP1, OPP2], "Over", 2, _pong_cur()) == GOLDEN["pong_shots_over"]


def test_pong_shots_under():
    assert PONG.predict_shots(SUBJ, [MATE], [OPP1, OPP2], "Under", 2, _pong_cur()) == GOLDEN["pong_shots_under"]


def test_pong_score_over():
    result = PONG.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Over")
    assert list(result) == GOLDEN["pong_score_over"]


def test_pong_score_under():
    result = PONG.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Under")
    assert list(result) == GOLDEN["pong_score_under"]


def test_beerball_shots_over():
    assert BEERBALL.predict_shots(_beerball_cur(), 2, SUBJ, 0.6, 0.5, 0.55, "Over") == GOLDEN["beerball_shots_over"]


def test_beerball_shots_under():
    assert BEERBALL.predict_shots(_beerball_cur(), 2, SUBJ, 0.6, 0.5, 0.55, "Under") == GOLDEN["beerball_shots_under"]


def test_beerball_score_over():
    result = BEERBALL.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Over")
    assert list(result) == GOLDEN["beerball_score_over"]


def test_beerball_score_under():
    result = BEERBALL.predict_score([SP, SP2], [OP, OP2], YOUR_SHOTS, OPP_SHOTS, GLOBAL_AVG_STRENGTH, "Under")
    assert list(result) == GOLDEN["beerball_score_under"]
