"""Re-derating saved scores for a new motor budget (docs/validation/audits/2026-10-10-motor-efficiency.md)."""

from __future__ import annotations

import pytest

from fansim.optimize.rederate import derate_factor, rederate_scale, rescore_from_raw


def _raw(shaft_free=0.9, shaft_load=0.95, **kw):
    raw = {
        "free": {"cfm": 60.0, "shaft_power_w": shaft_free, "efficiency": 0.30,
                 "static_pressure_rise_pa": 2.0},
        "load": {"cfm": 45.0, "shaft_power_w": shaft_load, "efficiency": 0.35,
                 "static_pressure_rise_pa": 8.0},
        "print_k_cfm": 0.95, "print_k_eta": 0.93,
    }
    raw.update(kw)
    return raw


def test_derate_factor_caps_at_one():
    assert derate_factor(1.0, 0.5) == 1.0
    assert derate_factor(0.672, 0.775) == pytest.approx(0.9536, abs=1e-4)  # Stock at 0.40


def test_stock_not_derated_at_half_efficiency():
    assert derate_factor(12.0 * 0.14 * 0.50, 0.775) == 1.0  # M1


def test_rederate_scale_matches_formula():
    # lambda_old 0.9 at budget 0.672; at 0.84 the motor can deliver (0.84/0.672)^(1/3) more speed
    s = rederate_scale(1800.0, 2000.0, 0.672, 0.84)
    assert s == pytest.approx(min(1.0, 0.9 * (0.84 / 0.672) ** (1 / 3)) / 0.9)
    assert rederate_scale(2000.0, 2000.0, 0.672, 0.84) == 1.0       # was not limited: unchanged
    assert rederate_scale(1990.0, 2000.0, 0.672, 0.84) == pytest.approx(2000.0 / 1990.0)


def test_rescore_scaling_shortcut_is_exact():
    raw = _raw()
    old = rescore_from_raw(raw, budget_w=0.672, target_rpm=2000.0, load_pa=8.0)
    new = rescore_from_raw(raw, budget_w=0.84, target_rpm=2000.0, load_pa=8.0)
    s = rederate_scale(old["actual_rpm"], 2000.0, 0.672, 0.84)
    assert old["derate"] < 1.0
    assert new["cfm_free"] == pytest.approx(old["cfm_free"] * s, rel=1e-9)
    assert new["cfm_load"] == pytest.approx(old["cfm_load"] * s, rel=1e-9)
    assert new["efficiency"] == pytest.approx(old["efficiency"], rel=1e-9)


def test_rescore_applies_print_knockdown_and_missing_k():
    r = rescore_from_raw(_raw(shaft_free=0.1, shaft_load=0.1), budget_w=0.84,
                         target_rpm=2000.0, load_pa=8.0)
    assert r["derate"] == 1.0
    assert r["cfm_free"] == pytest.approx(60.0 * 0.95)
    r2 = rescore_from_raw(_raw(shaft_free=0.1, shaft_load=0.1, print_k_cfm=None, print_k_eta=None),
                          budget_w=0.84, target_rpm=2000.0, load_pa=8.0)
    assert r2["cfm_free"] == pytest.approx(60.0)


def test_rescore_refuses_refined_or_incomplete():
    assert rescore_from_raw(_raw(op_cfd={"x": 1}), budget_w=0.84, target_rpm=2000.0, load_pa=8.0) is None
    assert rescore_from_raw({"free": {}}, budget_w=0.84, target_rpm=2000.0, load_pa=8.0) is None
