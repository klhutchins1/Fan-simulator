"""Linear T–ω PC-fan motor intersected with quadratic fan torque.

No-load RPM is 1.15× rated so the motor still has torque at ``spec.rpm``. Stall torque is
set so available shaft power at rated speed equals ``max_shaft_power_w_leeway``.
"""

from __future__ import annotations

import math

from fansim.fan_spec import FanSpec

NL_OVER_RATED = 1.15
_RPM_TO_OMEGA = 2.0 * math.pi / 60.0


def _omega(rpm: float) -> float:
    return float(rpm) * _RPM_TO_OMEGA


def stall_torque_nm(spec: FanSpec) -> float:
    """Stall torque such that T(rated)·ω_rated = shaft budget."""
    drop = 1.0 - 1.0 / NL_OVER_RATED
    return spec.max_shaft_power_w_leeway / (_omega(spec.rpm) * drop)


def motor_torque_nm(rpm: float, spec: FanSpec) -> float:
    rpm_nl = spec.rpm * NL_OVER_RATED
    if rpm >= rpm_nl:
        return 0.0
    if rpm <= 0.0:
        return stall_torque_nm(spec)
    return stall_torque_nm(spec) * (1.0 - rpm / rpm_nl)


def motor_operating_rpm(torque_nm_at_rated: float, spec: FanSpec) -> float:
    """RPM ≤ rated where T_motor(n) = T_cfd · (n/n_rated)²."""
    t_cfd = max(float(torque_nm_at_rated), 0.0)
    t_avail = motor_torque_nm(spec.rpm, spec)
    if t_cfd <= t_avail:
        return float(spec.rpm)
    t_stall = stall_torque_nm(spec)
    # T_cfd x² + (T_stall/NL) x - T_stall = 0, x = n/n_rated
    a = t_cfd
    b = t_stall / NL_OVER_RATED
    c = -t_stall
    disc = b * b - 4.0 * a * c
    if a <= 0.0 or disc < 0.0:
        return float(spec.rpm)
    x = (-b + math.sqrt(disc)) / (2.0 * a)
    x = min(max(x, 1e-6), 1.0)
    return float(spec.rpm) * x


def motor_curve_stamps(spec: FanSpec) -> dict:
    """Honesty stamps for evaluate raw dicts (Kv-ish no-load slope + stall torque)."""
    rpm_nl = float(spec.rpm) * NL_OVER_RATED
    return {
        "motor_kv_rpm_per_v": rpm_nl / max(float(spec.voltage_v), 1e-9),
        "motor_nl_rpm": rpm_nl,
        "motor_stall_torque_nm": float(stall_torque_nm(spec)),
        "motor_rated_rpm": float(spec.rpm),
        "motor_max_shaft_w": float(spec.max_shaft_power_w_leeway),
    }
