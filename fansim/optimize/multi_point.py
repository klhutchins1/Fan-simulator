"""Weighted multi-point duty scoring + CFM at matched relative noise (roadmap §20.6).

PC-fan reviewers compare airflow at a *matched noise* level across PWM duties. This module
scores a blade across a small duty×hose cycle (BEM, ranking-only) and interpolates free-air
CFM at a target relative noise. Uses the relative loading proxy only — no absolute dB(A).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise

from fansim.acoustics.farfield import blade_pass_frequency
from fansim.acoustics.loading import loading_proxy_from_rans
from fansim.cfd.metrics import CFM_PER_M3S
from fansim.fan_bem import operating_point, pq_curve
from fansim.geometry.blade import BladeParams
from fansim.optimize.presets import resolve_load
from fansim.optimize.pwm_table import A12X25_PWM, PwmRpmTable
from fansim.optimize.system_curve import SystemCurveError, bem_screen_cfm
from fansim.physics.air import C0_AIR


@dataclass(frozen=True)
class DutyWeight:
    """One operating slice: PWM duty, time weight, and hose preset (or explicit Pa)."""

    duty_pct: float
    weight: float
    hose: str = "case"
    load_pa: float | None = None  # overrides hose default when set


# Typical desktop idle / mid / load mix (weights sum to 1).
DEFAULT_PC_CYCLE: tuple[DutyWeight, ...] = (
    DutyWeight(25.0, 0.40, "case"),
    DutyWeight(50.0, 0.35, "case"),
    DutyWeight(100.0, 0.25, "heatsink"),
)


@dataclass
class PointScore:
    duty_pct: float
    rpm: float
    load_pa: float
    weight: float
    cfm_free: float
    cfm_load: float
    rel_noise_db: float
    tip_mach: float
    bpf_hz: float


@dataclass
class MultiPointScore:
    points: list[PointScore]
    weighted_cfm_load: float
    weighted_cfm_free: float
    weighted_rel_noise_db: float
    note: str = "BEM ranking-only (§20.6); not absolute CFM or calibrated dB(A)"


def relative_fan_noise(
    params: BladeParams,
    rpm: float,
    *,
    thrust_n: float | None = None,
    shaft_power_w: float | None = None,
) -> tuple[float, float, float]:
    """Relative ranking noise (dB-ish). Returns ``(rel_db, tip_mach, bpf_hz)``.

    Tip-Mach broadband + loading proxy (when thrust known) + weak shaft-power term.
    Same role as prop ``estimate_prop_noise`` — compare designs, not claim mic dB(A).
    """
    tip_r_m = float(params.tip_radius) / 1000.0
    tip_speed = (float(rpm) * 2.0 * math.pi / 60.0) * tip_r_m
    tip_mach = tip_speed / max(C0_AIR, 1.0)
    bpf = blade_pass_frequency(int(params.n_blades), float(rpm))
    broadband = 20.0 * math.log10(max(tip_mach, 1e-3) / 0.15 + 1e-9)
    loading = 0.0
    if thrust_n is not None and float(thrust_n) > 0.0:
        loading = float(loading_proxy_from_rans(int(params.n_blades), float(thrust_n))) - 60.0
    power_term = 0.0
    if shaft_power_w is not None and float(shaft_power_w) > 0.0:
        power_term = 5.0 * math.log10(max(float(shaft_power_w), 1e-3) / 5.0)
    return broadband + 0.35 * loading + power_term, tip_mach, bpf


def _thrust_n_from_bem(params: BladeParams, rpm: float, tip_gap_mm: float) -> float:
    """Crude axial force proxy from free-delivery BEM ΔP × annulus area (ranking only)."""
    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm, n_points=12)
    tip = params.tip_radius / 1000.0
    hub = params.hub_radius / 1000.0
    area = math.pi * (tip * tip - hub * hub)
    # Free-delivery static rise ≈ 0; use mid-curve ΔP as a stand-in for loading.
    mid = curve.points[len(curve.points) // 2]
    return max(float(mid.dp_static_pa), 0.0) * area


def score_multi_point(
    params: BladeParams,
    cycle: tuple[DutyWeight, ...] | list[DutyWeight] = DEFAULT_PC_CYCLE,
    *,
    tip_gap_mm: float = 0.5,
    pwm: PwmRpmTable | None = None,
) -> MultiPointScore:
    """Weighted BEM CFM across a duty×hose cycle."""
    tab = pwm or A12X25_PWM
    pts: list[PointScore] = []
    w_sum = 0.0
    cfm_load_acc = 0.0
    cfm_free_acc = 0.0
    # Intensity-weighted noise: Σ w · 10^(L/10) then back to dB.
    intensity = 0.0
    for dw in cycle:
        w = max(float(dw.weight), 0.0)
        if w <= 0.0:
            continue
        rpm = tab.rpm_at_duty(dw.duty_pct)
        if dw.load_pa is not None:
            load_pa = float(dw.load_pa)
        else:
            load_pa, _ = resolve_load(preset=dw.hose)
        try:
            free, load = bem_screen_cfm(params, rpm, load_pa, tip_gap_mm)
        except SystemCurveError:
            # Low-PWM shut-off can sit below the hose Pa — treat as zero load CFM.
            curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm, n_points=12)
            free, load = float(curve.free_delivery_cfm), 0.0
        thrust = _thrust_n_from_bem(params, rpm, tip_gap_mm)
        # Shaft power from free-delivery BEM point near peak flow.
        op = operating_point(params, rpm, flow_m3s=max(free, 1.0) / CFM_PER_M3S,
                             tip_gap_mm=tip_gap_mm)
        rel, tip_mach, bpf = relative_fan_noise(
            params, rpm, thrust_n=thrust, shaft_power_w=op.power_w,
        )
        pts.append(PointScore(
            duty_pct=float(dw.duty_pct), rpm=rpm, load_pa=load_pa, weight=w,
            cfm_free=float(free), cfm_load=float(load), rel_noise_db=float(rel),
            tip_mach=float(tip_mach), bpf_hz=float(bpf),
        ))
        w_sum += w
        cfm_load_acc += w * float(load)
        cfm_free_acc += w * float(free)
        intensity += w * (10.0 ** (float(rel) / 10.0))
    if w_sum <= 0.0:
        raise ValueError("duty cycle weights must sum to a positive value")
    noise = 10.0 * math.log10(max(intensity / w_sum, 1e-30))
    return MultiPointScore(
        points=pts,
        weighted_cfm_load=cfm_load_acc / w_sum,
        weighted_cfm_free=cfm_free_acc / w_sum,
        weighted_rel_noise_db=noise,
    )


def cfm_at_matched_noise(
    params: BladeParams,
    noise_ref_db: float,
    *,
    tip_gap_mm: float = 0.5,
    pwm: PwmRpmTable | None = None,
    duties: tuple[float, ...] = (20.0, 40.0, 60.0, 80.0, 100.0),
) -> dict[str, float | None]:
    """Free-delivery CFM at a target relative noise by PWM sweep + linear interp.

    Returns ``cfm_free``, ``duty_pct``, ``rpm`` at the match, or None CFM if ``noise_ref``
    is outside the swept band (reviewers usually pick a mid-band target).
    """
    tab = pwm or A12X25_PWM
    rows: list[tuple[float, float, float, float]] = []  # noise, cfm, duty, rpm
    for duty in duties:
        rpm = tab.rpm_at_duty(duty)
        curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm, n_points=12)
        thrust = _thrust_n_from_bem(params, rpm, tip_gap_mm)
        peak = max(curve.points, key=lambda p: p.power_w)
        rel, _, _ = relative_fan_noise(
            params, rpm, thrust_n=thrust, shaft_power_w=peak.power_w,
        )
        rows.append((rel, float(curve.free_delivery_cfm), float(duty), rpm))
    rows.sort(key=lambda r: r[0])
    target = float(noise_ref_db)
    if target < rows[0][0] or target > rows[-1][0]:
        return {
            "cfm_free": None,
            "duty_pct": None,
            "rpm": None,
            "noise_lo": rows[0][0],
            "noise_hi": rows[-1][0],
        }
    for (n0, c0, d0, r0), (n1, c1, d1, r1) in pairwise(rows):
        if n0 <= target <= n1:
            t = 0.0 if n1 <= n0 else (target - n0) / (n1 - n0)
            return {
                "cfm_free": c0 + t * (c1 - c0),
                "duty_pct": d0 + t * (d1 - d0),
                "rpm": r0 + t * (r1 - r0),
                "noise_lo": rows[0][0],
                "noise_hi": rows[-1][0],
            }
    return {"cfm_free": None, "duty_pct": None, "rpm": None,
            "noise_lo": rows[0][0], "noise_hi": rows[-1][0]}


def format_multi_point(score: MultiPointScore) -> list[str]:
    """Cockpit readout lines for a multi-point BEM score."""
    lines = [
        (
            f"Multi-point BEM (§20.6): weighted load {score.weighted_cfm_load:.0f} CFM · "
            f"free {score.weighted_cfm_free:.0f} CFM · rel noise {score.weighted_rel_noise_db:.0f}"
        ),
        score.note,
    ]
    for p in score.points:
        lines.append(
            f"  {p.duty_pct:.0f}% PWM → {p.rpm:.0f} RPM @ {p.load_pa:g} Pa: "
            f"load {p.cfm_load:.0f} / free {p.cfm_free:.0f} CFM · rel {p.rel_noise_db:.0f}"
        )
    return lines
