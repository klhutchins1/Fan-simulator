"""Prop spin/sign + datasheet thrust comparison (roadmap §4.3).

Drone convention: report **positive** static thrust in grams. Fan CFD uses ``spin=-1``
so MRF pumps +z; props historically defaulted to ``spin=+1``, which can flip the force
sign. Calibration picks the spin that yields +Fz and compares magnitude to
``PropSpec.ref_thrust_g`` with RPM² affinity scaling.
"""

from __future__ import annotations

import math
from typing import Any


def affinity_thrust_g(ref_thrust_g: float, ref_rpm: float, rpm: float) -> float:
    """Scale datasheet static thrust to ``rpm`` via T ∝ n²."""
    ref = float(ref_rpm)
    if ref <= 0.0:
        return float(ref_thrust_g)
    return float(ref_thrust_g) * (float(rpm) / ref) ** 2


def affinity_power_w(ref_power_w: float, ref_rpm: float, rpm: float) -> float:
    """Scale datasheet shaft power via P ∝ n³."""
    ref = float(ref_rpm)
    if ref <= 0.0:
        return float(ref_power_w)
    return float(ref_power_w) * (float(rpm) / ref) ** 3


def preferred_spin_for_positive_thrust(thrust_n: float, spin: int) -> tuple[int, bool]:
    """If Fz is negative, recommend flipping ``spin``. Returns (spin_to_use, flipped)."""
    s = int(spin)
    if float(thrust_n) >= 0.0:
        return s, False
    return -s, True


def normalize_metrics_sign(metrics: dict[str, Any], *, spin: int) -> dict[str, Any]:
    """Stamp sign honesty and report positive thrust_g for drone tables.

    Keeps ``thrust_n_raw``; sets ``thrust_n`` / ``thrust_g`` to the positive magnitude
    used for datasheet compares. Does **not** change torque (already abs in parser).
    """
    out = dict(metrics)
    raw = float(out.get("thrust_n", 0.0))
    out["thrust_n_raw"] = raw
    out["spin"] = int(spin)
    spin_use, flipped = preferred_spin_for_positive_thrust(raw, spin)
    out["spin_flipped"] = flipped
    out["spin_recommended"] = spin_use
    mag = abs(raw)
    out["thrust_n"] = mag
    out["thrust_g"] = mag / 9.80665 * 1000.0
    return out


def datasheet_compare(
    *,
    thrust_g: float,
    power_w: float | None = None,
    rpm: float,
    spec,
) -> dict[str, Any]:
    """Compare a result to ``spec.ref_*`` at affinity-scaled RPM. Honest ratios only."""
    ref_t = getattr(spec, "ref_thrust_g", None)
    ref_rpm = getattr(spec, "ref_rpm", None) or getattr(spec, "rpm_max", None)
    ref_p = getattr(spec, "ref_power_w", None)
    out: dict[str, Any] = {
        "rpm": float(rpm),
        "thrust_g": float(thrust_g),
        "ref_thrust_g": None if ref_t is None else float(ref_t),
        "ref_rpm": None if ref_rpm is None else float(ref_rpm),
        "thrust_ref_scaled_g": None,
        "thrust_ratio": None,
        "power_w": None if power_w is None else float(power_w),
        "power_ref_scaled_w": None,
        "power_ratio": None,
        "within_2x": None,
    }
    if ref_t is not None and ref_rpm is not None:
        scaled = affinity_thrust_g(float(ref_t), float(ref_rpm), float(rpm))
        out["thrust_ref_scaled_g"] = scaled
        ratio = float(thrust_g) / scaled if scaled > 0 else None
        out["thrust_ratio"] = ratio
        out["within_2x"] = bool(ratio is not None and 0.5 <= ratio <= 2.0)
    if power_w is not None and ref_p is not None and ref_rpm is not None:
        p_scaled = affinity_power_w(float(ref_p), float(ref_rpm), float(rpm))
        out["power_ref_scaled_w"] = p_scaled
        out["power_ratio"] = float(power_w) / p_scaled if p_scaled > 0 else None
    return out


def bemt_datasheet_report(spec, *, rpm: float | None = None) -> dict[str, Any]:
    """Instant BEMT vs datasheet at ``rpm`` (default ``ref_rpm`` or ``rpm_max``)."""
    from fansim.propeller.geometry import prop_blade_params
    from fansim.propeller.bemt import analyze

    rpm_f = float(
        rpm
        if rpm is not None
        else (getattr(spec, "ref_rpm", None) or spec.rpm_max)
    )
    perf = analyze(prop_blade_params(spec), rpm=rpm_f)
    cmp_ = datasheet_compare(
        thrust_g=perf.thrust_g, power_w=perf.power_w, rpm=rpm_f, spec=spec,
    )
    return {
        "source": "bemt",
        "rpm": rpm_f,
        "thrust_g": perf.thrust_g,
        "power_w": perf.power_w,
        "figure_of_merit": perf.figure_of_merit,
        "datasheet": cmp_,
    }
