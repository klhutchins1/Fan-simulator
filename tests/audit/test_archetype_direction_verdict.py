"""Audit #7 proof-3 verdict rule (scripts/audit_archetype_direction_cfd.py), no CFD."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "adc", Path(__file__).resolve().parents[2] / "scripts" / "audit_archetype_direction_cfd.py")
adc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adc)


def _row(cfm, power=1.0, converged=True):
    return {"cfm": cfm, "shaft_power_w": power, "converged": converged}


def test_clear_win_passes():
    v = adc.verdict(_row(40.0, 1.0), _row(20.0, 1.2))
    assert v["verdict"] == "PASS" and v["cfm_ratio"] == pytest.approx(2.0)


def test_reversed_winning_fails():
    assert adc.verdict(_row(20.0), _row(40.0))["verdict"] == "FAIL"


def test_designed_not_delivering_fails():
    assert adc.verdict(_row(-5.0), _row(-10.0))["verdict"] == "FAIL"


def test_small_margin_is_inconclusive():
    assert adc.verdict(_row(41.0, 1.0), _row(40.0, 1.0))["verdict"] == "INCONCLUSIVE"


def test_more_cfm_but_worse_per_watt_is_inconclusive():
    # 25% more air but 60% more power: not a clean designed-direction win
    assert adc.verdict(_row(50.0, 1.6), _row(40.0, 1.0))["verdict"] == "INCONCLUSIVE"


def test_unconverged_never_passes():
    assert adc.verdict(_row(40.0, converged=False), _row(10.0))["verdict"] == "INCONCLUSIVE"


def test_reversed_pumping_backwards_counts_as_designed_win():
    v = adc.verdict(_row(40.0, 1.0), _row(-8.0, 1.0))
    assert v["verdict"] == "PASS" and v["reversed_pumps_backwards"] and v["cfm_ratio"] is None
    import json
    json.dumps(v, allow_nan=False)  # result file must serialise (the inf ratio crashed it once)


def test_missing_solve_is_inconclusive():
    assert adc.verdict(_row(40.0), None)["verdict"] == "INCONCLUSIVE"
