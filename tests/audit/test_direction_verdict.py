"""CFD-matrix verdict: judge each rotation sense only where it pumps +Z through proper BCs."""

from __future__ import annotations

import math

import pytest

from fansim.audit.direction_verdict import MatrixRow, body_sense, convention_verdict, matrix_verdict


def R(o, s, cfm, conv=True, p=0.5, mz=None):
    om = s * 209.44
    return MatrixRow(o, s, cfm, conv, p, -0.002 * (1 if om > 0 else -1) if mz is None else mz, om)


def test_body_sense():
    assert body_sense(R("as_built", -1, 1)) == -1 and body_sense(R("flipped", -1, 1)) == 1


def test_body_sense_rejects_invalid_orientation():
    """Invalid orientation strings must raise ValueError."""
    with pytest.raises(ValueError):
        body_sense(R("invalid", -1, 1))


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


def test_no_pump_direction_is_inconclusive():
    """geometry_pump=None → INCONCLUSIVE."""
    v = matrix_verdict(ROWS, geometry_omega=+1, geometry_pump=None)
    assert v["verdict"] == "INCONCLUSIVE" and any("pump" in r for r in v["reasons"])


def test_convention_verdict_fails_when_matrix_recommends_flipped_but_production_is_as_built():
    # ROWS recommends {flipped, -1}; production here solves as_built.
    v = matrix_verdict(ROWS, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "PASS" and v["recommended"] == {"orientation": "flipped", "spin": -1}
    cv = convention_verdict(v, production_spin=-1, production_orientation="as_built")
    assert cv["verdict"] == "FAIL"
    assert cv["production"] == {"orientation": "as_built", "spin": -1}
    assert "reversed" in cv["reason"] or "mis-oriented" in cv["reason"]


def test_convention_verdict_passes_when_matrix_recommends_as_built():
    rows = [R("as_built", +1, 60.0), R("as_built", -1, -30.0),
            R("flipped", -1, -70.0), R("flipped", +1, 42.0)]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=+1)
    assert v["verdict"] == "PASS" and v["recommended"] == {"orientation": "as_built", "spin": +1}
    cv = convention_verdict(v, production_spin=+1, production_orientation="as_built")
    assert cv["verdict"] == "PASS"
    assert cv["production"] == cv["recommended"] == {"orientation": "as_built", "spin": +1}


def test_convention_verdict_passes_when_production_is_flipped_matching_recommendation():
    # ROWS recommends {flipped, -1}; production is the flipped setup at spin -1: PASS.
    v = matrix_verdict(ROWS, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "PASS" and v["recommended"] == {"orientation": "flipped", "spin": -1}
    cv = convention_verdict(v, production_spin=-1, production_orientation="flipped")
    assert cv["verdict"] == "PASS"
    assert cv["production"] == cv["recommended"] == {"orientation": "flipped", "spin": -1}


def test_convention_verdict_fails_when_production_as_built_for_flipped_recommendation():
    # Same matrix, production claims as_built at spin -1: FAIL (mismatched orientation).
    v = matrix_verdict(ROWS, geometry_omega=+1, geometry_pump=-1)
    assert v["verdict"] == "PASS" and v["recommended"] == {"orientation": "flipped", "spin": -1}
    cv = convention_verdict(v, production_spin=-1, production_orientation="as_built")
    assert cv["verdict"] == "FAIL"
    assert cv["production"] == {"orientation": "as_built", "spin": -1}


def test_convention_verdict_inconclusive_when_matrix_inconclusive():
    v = matrix_verdict(ROWS, geometry_omega=None, geometry_pump=-1)
    assert v["verdict"] == "INCONCLUSIVE"
    cv = convention_verdict(v, production_spin=-1, production_orientation="as_built")
    assert cv["verdict"] == "INCONCLUSIVE"


def test_convention_verdict_inconclusive_when_matrix_status_missing():
    cv = convention_verdict({}, production_spin=-1, production_orientation="as_built")
    assert cv["verdict"] == "INCONCLUSIVE"


def test_convention_verdict_inconclusive_when_matrix_status_unrecognised():
    cv = convention_verdict({"verdict": "SKIPPED", "recommended": None}, production_spin=-1,
                            production_orientation="as_built")
    assert cv["verdict"] == "INCONCLUSIVE"
    assert "SKIPPED" in cv["reason"]


def test_convention_verdict_rejects_invalid_production_orientation():
    with pytest.raises(ValueError):
        convention_verdict({"verdict": "PASS", "recommended": None}, production_spin=-1,
                           production_orientation="backwards")


def test_convention_verdict_fail_when_matrix_fail():
    v = matrix_verdict(ROWS, geometry_omega=-1, geometry_pump=-1)
    assert v["verdict"] == "FAIL"
    cv = convention_verdict(v, production_spin=-1, production_orientation="as_built")
    assert cv["verdict"] == "FAIL"


def test_power_sign_ok_false_when_no_proper_runs():
    """No proper runs → power_sign_ok is False, not True."""
    rows = [R("as_built", -1, -42.0), R("as_built", +1, -70.0),
            R("flipped", -1, -60.0), R("flipped", +1, -30.0)]
    v = matrix_verdict(rows, geometry_omega=+1, geometry_pump=-1)
    assert v["power_sign_ok"] is False
