"""Tests for P–Q curve helpers (no Docker)."""

from __future__ import annotations

import pytest

from fansim.analyze.fan_curve import (
    curve_report,
    free_delivery_cfm,
    point_row,
    shut_off_pa,
)
from fansim.cfd.metrics import FanMetrics


def test_free_delivery_interp():
    points = [
        {"cfm": 40.0, "static_pa": 10.0},
        {"cfm": 70.0, "static_pa": -5.0},
    ]
    assert free_delivery_cfm(points) == pytest.approx(60.0)


def test_shut_off_interp_to_q0():
    points = [
        {"cfm": 2.0, "static_pa": 20.0},
        {"cfm": 8.0, "static_pa": 15.0},
        {"cfm": 50.0, "static_pa": 2.0},
    ]
    # Line through (2,20) and (8,15): p = 20 + (15-20)/(8-2)*(0-2) = 21.666...
    assert shut_off_pa(points) == pytest.approx(21.666666, rel=1e-5)


def test_shut_off_none_when_sweep_stays_open():
    points = [
        {"cfm": 40.0, "static_pa": 12.0},
        {"cfm": 55.0, "static_pa": 4.0},
        {"cfm": 70.0, "static_pa": -1.0},
    ]
    assert shut_off_pa(points) is None
    report = curve_report(points)
    assert report["shut_off_pa"] is None
    assert report["peak_static_pa"] == pytest.approx(12.0)
    assert report["shut_off_pa"] != report["peak_static_pa"]


def test_point_row_eta_total():
    m = FanMetrics(
        flow_m3s=0.02, cfm=42.0, static_pressure_rise_pa=5.0,
        thrust_n=0.1, torque_nm=0.01, shaft_power_w=2.0,
        air_power_w=0.1, efficiency=0.05, p_inlet_kin=1.0, p_outlet_kin=2.0,
        eta_total=0.22,
    )
    row = point_row(m, inlet_v=1.5)
    assert row["eta_total"] == pytest.approx(0.22)
    assert row["efficiency_pct"] == pytest.approx(5.0)
    m2 = FanMetrics(
        flow_m3s=0.02, cfm=42.0, static_pressure_rise_pa=5.0,
        thrust_n=0.1, torque_nm=0.01, shaft_power_w=2.0,
        air_power_w=0.1, efficiency=0.05, p_inlet_kin=1.0, p_outlet_kin=2.0,
    )
    assert point_row(m2, inlet_v=1.5)["eta_total"] is None
