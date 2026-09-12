# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller optimizer (fansim/propeller/optimize.py) — BEMT-driven, so fast + deterministic."""

from __future__ import annotations

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
