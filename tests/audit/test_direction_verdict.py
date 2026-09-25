"""CFD-matrix verdict: judge each rotation sense only where it pumps +Z through proper BCs."""

from __future__ import annotations

import math

from fansim.audit.direction_verdict import MatrixRow, body_sense, matrix_verdict


def R(o, s, cfm, conv=True, p=0.5, mz=None):
    om = s * 209.44
    return MatrixRow(o, s, cfm, conv, p, -0.002 * (1 if om > 0 else -1) if mz is None else mz, om)


def test_body_sense():
    assert body_sense(R("as_built", -1, 1)) == -1 and body_sense(R("flipped", -1, 1)) == 1


def test_body_sense_rejects_invalid_orientation():
    """Invalid orientation strings must raise ValueError."""
    try:
        body_sense(R("invalid", -1, 1))
        assert False, "should have raised ValueError"
    except ValueError:
        pass


# Hypothesis-shaped data: body sense +1 is designed (strong, pumps -Z as built, so its proper run
# is the flipped one), and sense -1 is the reversed rotation (weak, pumps +Z as built).
ROWS = [R("as_built", -1, 42.0), R("as_built", +1, -70.0),
        R("flipped", -1, 60.0), R("flipped", +1, -30.0)]


def test_designed_sense_wins_and_matches_geometry():
    v = matrix_verdict(ROWS, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "PASS" and v["designed_sense"] == +1
    assert v["proper"] == {"+1": 60.0, "-1": 42.0}
    assert v["bc_bias_cfm"] == {"+1": 10.0, "-1": -12.0}   # |improper| - proper
    assert v["recommended"] == {"orientation": "flipped", "spin": -1}


def test_geometry_disagreement_on_orientation_fails():
    """Winner's orientation must match geometry prediction. Sense +1 wins but as_built, should be flipped."""
    rows = [R("as_built", -1, -42.0), R("as_built", +1, 60.0),  # sense -1 improper, sense +1 proper on as_built
            R("flipped", -1, -50.0), R("flipped", +1, 30.0)]   # sense +1 improper, sense -1 proper on flipped
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "FAIL" and any("orientation" in r for r in v["reasons"])


def test_geometry_disagreement_fails():
    assert matrix_verdict(ROWS, geometry_omega=-1, geometry_pump=-1)["verdict"] == "FAIL"


def test_unconverged_proper_run_is_inconclusive():
    rows = ROWS[:2] + [R("flipped", -1, 60.0, conv=False), ROWS[3]]
    assert matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)["verdict"] == "INCONCLUSIVE"


def test_small_margin_is_inconclusive():
    rows = [R("as_built", -1, 55.0), R("as_built", +1, -70.0),
            R("flipped", -1, 60.0), R("flipped", +1, -58.0)]
    assert matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)["verdict"] == "INCONCLUSIVE"


def test_must_also_win_cfm_per_watt():
    rows = [R("as_built", -1, 42.0, p=0.2), R("as_built", +1, -70.0),
            R("flipped", -1, 60.0, p=2.0), R("flipped", +1, -30.0)]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "INCONCLUSIVE" and any("per watt" in r for r in v["reasons"])


def test_power_sign_violation_is_reported():
    rows = ROWS[:2] + [R("flipped", -1, 60.0, mz=-0.002), ROWS[3]]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["power_sign_ok"] is False and v["verdict"] == "INCONCLUSIVE"


def test_non_finite_power_is_inconclusive():
    """Non-finite values in proper runs make verdict INCONCLUSIVE."""
    rows = [R("as_built", -1, 42.0, p=math.nan), R("as_built", +1, -70.0),
            R("flipped", -1, 60.0), R("flipped", +1, -30.0)]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "INCONCLUSIVE"


def test_incomplete_matrix_is_inconclusive():
    """Only 3 rows instead of 4 → INCONCLUSIVE."""
    rows = ROWS[:3]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "INCONCLUSIVE"


def test_no_geometry_is_inconclusive():
    """geometry_omega=None → INCONCLUSIVE."""
    v = matrix_verdict(ROWS, geometry_omega=None, geometry_pump=-1)
    assert v["verdict"] == "INCONCLUSIVE"


def test_power_sign_ok_false_when_no_proper_runs():
    """No proper runs → power_sign_ok is False, not True."""
    rows = [R("as_built", -1, -42.0), R("as_built", +1, -70.0),
            R("flipped", -1, -60.0), R("flipped", +1, -30.0)]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["power_sign_ok"] is False
