# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller optimizer (fansim/propeller/optimize.py) — BEMT-driven, so fast + deterministic."""

from __future__ import annotations

import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import run_prop_study


def test_pareto_is_populated_and_ordered():
    spec = get_prop_spec("fpv_5inch")
    study, pareto = run_prop_study(spec, n_trials=60, seed=0)
    assert len(pareto) >= 3
    # front sorted by descending thrust; efficiency should trade the other way
    thrusts = [r["thrust_g"] for r in pareto]
    assert thrusts == sorted(thrusts, reverse=True)
    assert pareto[0]["thrust_g"] > pareto[-1]["thrust_g"]
    assert pareto[0]["eff_g_per_w"] < pareto[-1]["eff_g_per_w"]   # thrust<->efficiency tradeoff


def test_power_cap_is_respected():
    spec = get_prop_spec("fpv_5inch")
    _, pareto = run_prop_study(spec, n_trials=120, seed=1, max_power_w=600)
    assert pareto, "cap should still yield a front"
    assert all(r["power_w"] <= 600 + 1e-6 for r in pareto)


def test_designs_are_physically_sane():
    spec = get_prop_spec("fpv_5inch")
    _, pareto = run_prop_study(spec, n_trials=60, seed=2)
    for r in pareto:
        assert 2 <= r["n_blades"] <= 4
        assert 0.4 < r["fm"] <= 1.0
        assert r["thrust_g"] > 0


def test_unknown_mission_names_the_legal_four():
    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="quiet_thrust") as exc:
        run_prop_study(spec, n_trials=1, seed=0, mission="louder")
    text = str(exc.value)
    for name in ("thrust_efficiency", "hover_endurance", "range"):
        assert name in text


def test_unknown_mission_wins_over_minutes_flag():
    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError, match="thrust_efficiency") as exc:
        run_prop_study(spec, n_trials=1, seed=0, mission="louder", min_hover_minutes=1.0)
    text = str(exc.value)
    assert "quiet_thrust" in text and "hover_endurance" in text and "range" in text
    assert "min_hover_minutes" not in text


def test_endurance_and_range_require_vehicle_inputs():
    spec = get_prop_spec("fpv_5inch")
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="hover_endurance")
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="range",
                       all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0)
    with pytest.raises(ValueError):
        run_prop_study(spec, n_trials=1, seed=0, mission="thrust_efficiency",
                       min_hover_minutes=1.0)


def test_quiet_floor_can_empty_the_front():
    spec = get_prop_spec("fpv_5inch")
    _, pareto = run_prop_study(
        spec, n_trials=20, seed=0, mission="quiet_thrust",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0,
        min_hover_minutes=1.0e9,
    )
    assert pareto == []


def test_endurance_and_range_fronts_lift_the_weight():
    spec = get_prop_spec("fpv_5inch")
    _, endurance = run_prop_study(
        spec, n_trials=30, seed=0, mission="hover_endurance",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0,
    )
    assert endurance
    assert all(r["hover_minutes"] > 0 for r in endurance)
    assert all(r["mission"] == "hover_endurance" for r in endurance)
    _, ranged = run_prop_study(
        spec, n_trials=30, seed=1, mission="range",
        all_up_weight_n=2.0, n_rotors=1, battery_wh=50.0, cruise_mps=15.0,
    )
    assert ranged
    assert all(r["range_km"] > 0 for r in ranged)
    assert all(r["thrust_g"] * 9.80665 / 1000.0 >= 2.0 - 0.01 for r in ranged)
    thrusts = [r["thrust_g"] for r in ranged]
    assert thrusts == sorted(thrusts, reverse=True)
