"""Cheap BEM/geometry near-stall flag (roadmap 25.10).

Thresholds are frozen in ``docs/qa/notes/near-stall-flag-prereg.md``. This never
changes CFM / η / optimizer scores — it is a warning only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fansim.cfd.metrics import CFM_PER_M3S
from fansim.fan_bem import N_ITER_MAX, _interp_geometry, _table_polar
from fansim.geometry.blade import BladeParams
from fansim.optimize.meanline import DF_LIMIT, lieblein_df, solidity
from fansim.optimize.system_curve import SystemCurveError, bem_screen_cfm
from fansim.physics.air import NU_AIR
from fansim.physics.air import RHO_AMCA as RHO_AIR

# Polar-edge stall. A 2° pre-stall band flagged Stock on the case hose (prereg ruling B).
STALL_MARGIN_DEG = 0.0
N_ELEM = 20


def stall_aoa_deg(re: float) -> float:
    """Polar-edge stall used by ``fan_bem._cl_cd_post_stall`` (degrees)."""
    return max(8.0, min(15.0, 10.0 + 3.0 * math.log10(max(re, 5000.0) / 20000.0)))


@dataclass(frozen=True)
class NearStallReport:
    flagged: bool
    rule: str  # "" | "incidence" | "no_intersect" | "lieblein"
    reason: str
    max_incidence_deg: float = 0.0
    stall_aoa_deg: float = 0.0
    max_df: float = 0.0
    free_cfm: float = 0.0
    load_cfm: float = 0.0


def near_stall_caption(report: NearStallReport) -> str:
    if not report.flagged:
        return ""
    return f"⚠ near stall on this hose ({report.reason})"


def near_stall_report(
    params: BladeParams,
    rpm: float = 2000.0,
    load_pa: float = 8.0,
    tip_gap_mm: float | None = None,
) -> NearStallReport:
    """Flag if the BEM case-hose operating point is near stall (N1/N2/N3)."""
    try:
        q0, q_op = bem_screen_cfm(params, float(rpm), float(load_pa), tip_gap_mm)
    except (SystemCurveError, ValueError, ArithmeticError):
        return NearStallReport(
            flagged=True,
            rule="no_intersect",
            reason="BEM has no operating point on this hose",
        )
    if q0 <= 0.0 or q_op <= 0.0:
        return NearStallReport(
            flagged=True,
            rule="no_intersect",
            reason="BEM has no operating point on this hose",
            free_cfm=float(q0),
            load_cfm=float(q_op),
        )

    flow_m3s = float(q_op) / CFM_PER_M3S
    max_inc = 0.0
    stall_at_max = 0.0
    max_df = 0.0
    n1 = False
    n3 = False
    for alpha_deg, stall_deg, df in _span_loading(params, float(rpm), flow_m3s):
        if alpha_deg > max_inc:
            max_inc = alpha_deg
            stall_at_max = stall_deg
        max_df = max(max_df, df)
        if alpha_deg >= stall_deg - STALL_MARGIN_DEG:
            n1 = True
        if df > DF_LIMIT:
            n3 = True

    if n1:
        if STALL_MARGIN_DEG:
            reason = (
                f"incidence {max_inc:.1f} deg >= stall {stall_at_max:.1f} deg "
                f"- {STALL_MARGIN_DEG:g} deg"
            )
        else:
            reason = f"incidence {max_inc:.1f} deg >= stall {stall_at_max:.1f} deg"
        rule = "incidence"
    elif n3:
        reason = f"Lieblein DF {max_df:.3f} > {DF_LIMIT:g}"
        rule = "lieblein"
    else:
        return NearStallReport(
            flagged=False,
            rule="",
            reason="",
            max_incidence_deg=max_inc,
            stall_aoa_deg=stall_at_max,
            max_df=max_df,
            free_cfm=float(q0),
            load_cfm=float(q_op),
        )
    return NearStallReport(
        flagged=True,
        rule=rule,
        reason=reason,
        max_incidence_deg=max_inc,
        stall_aoa_deg=stall_at_max,
        max_df=max_df,
        free_cfm=float(q0),
        load_cfm=float(q_op),
    )


def _span_loading(
    params: BladeParams,
    rpm: float,
    flow_m3s: float,
) -> list[tuple[float, float, float]]:
    """Per-element (incidence deg, stall deg, Lieblein DF) at ``flow_m3s``.

    Swirl iteration matches ``operating_point`` (euler / table polar) so the flag
    sees the same triangles the ranking BEM uses.
    """
    hub_r = params.hub_radius / 1000.0
    tip_r = params.tip_radius / 1000.0
    b = int(params.n_blades)
    omega = rpm * 2.0 * math.pi / 60.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    vx = flow_m3s / area if area > 0 else 0.0
    chord_fn, stag_fn, camb_fn = _interp_geometry(params)
    from fansim.geometry.blade import station_root_radius

    r_root = station_root_radius(params) / 1000.0
    span_cad = tip_r - r_root
    edges = np.linspace(hub_r, tip_r, N_ELEM + 1)
    out: list[tuple[float, float, float]] = []
    for i in range(N_ELEM):
        r = 0.5 * (edges[i] + edges[i + 1])
        u = omega * r
        rf = min(max((r - r_root) / span_cad, 0.0), 1.0) if span_cad > 0.0 else 0.0
        c = chord_fn(rf) / 1000.0
        beta = math.radians(stag_fn(rf))
        camb = camb_fn(rf)
        vth = 0.0
        alpha = 0.0
        re = 0.0
        for _ in range(N_ITER_MAX):
            vth_m = 0.5 * vth
            phi = math.atan2(vx, max(u - vth_m, 0.05))
            w = math.hypot(vx, u - vth_m)
            re = w * c / NU_AIR
            alpha = beta - phi
            cl, cd = _table_polar(alpha, camb, re)
            f_theta = 0.5 * RHO_AIR * w * w * c * b * (cl * math.sin(phi) + cd * math.cos(phi))
            denom = RHO_AIR * max(vx, 0.05) * 2.0 * math.pi * r
            vth_new = f_theta / denom if denom > 0 else vth
            vth_new = max(0.0, min(vth_new, 0.95 * u))
            if abs(vth_new - vth) < 1e-3:
                vth = vth_new
                break
            vth = 0.5 * vth + 0.5 * vth_new
        w1 = math.hypot(vx, u)
        w2 = math.hypot(vx, u - vth)
        sol = solidity(b, c, r) if r > 0.0 and b > 0 else 1e-9
        df = lieblein_df(w1, w2, vth, sol)
        stall = stall_aoa_deg(re)
        out.append((math.degrees(alpha), stall, df))
    return out
