"""Linear motor T–ω vs quadratic fan torque (no Docker)."""

from __future__ import annotations

import math

import pytest

from fansim.fan_spec import A12X25
from fansim.optimize.motor_curve import (
    NL_OVER_RATED,
    motor_operating_rpm,
    motor_torque_nm,
    stall_torque_nm,
)


def _omega(rpm: float) -> float:
    return rpm * 2.0 * math.pi / 60.0


def test_stall_matches_budget_at_rated():
    spec = A12X25
    t_rated = motor_torque_nm(spec.rpm, spec)
    assert t_rated * _omega(spec.rpm) == pytest.approx(spec.max_shaft_power_w_leeway)
    assert stall_torque_nm(spec) == pytest.approx(
        spec.max_shaft_power_w_leeway / (_omega(spec.rpm) * (1.0 - 1.0 / NL_OVER_RATED)))


def test_under_budget_stays_at_rated():
    spec = A12X25
    t_avail = motor_torque_nm(spec.rpm, spec)
    assert motor_operating_rpm(t_avail, spec) == pytest.approx(spec.rpm)
    assert motor_operating_rpm(0.5 * t_avail, spec) == pytest.approx(spec.rpm)


def test_over_torque_slows_and_intersects():
    spec = A12X25
    t_cfd = 2.0 * motor_torque_nm(spec.rpm, spec)
    n = motor_operating_rpm(t_cfd, spec)
    assert 0.5 * spec.rpm < n < spec.rpm
    t_fan = t_cfd * (n / spec.rpm) ** 2
    assert motor_torque_nm(n, spec) == pytest.approx(t_fan, rel=1e-6)
