"""Compute-free AXIAL-FAN performance — blade-element + Euler (the fan analog of the prop BEMT).

Predicts a ducted axial fan's P-Q curve (static-pressure rise vs flow), free-delivery CFM, shut-off
pressure, peak efficiency and shaft power ANALYTICALLY — no CFD — so the optimizer can screen thousands
of fan designs in milliseconds and reserve CFD for finalists (roadmap §7.1). This is the fan side of
what made the propeller side instant.

Physics: slice the annulus hub->tip into elements; at each one balance the blade-element lift/drag
against the momentum imparted to the annular stream tube, solve for the swirl the rotor adds, and apply
the Euler turbomachinery relation (ΔP0 = ρ·U·ΔVθ; Dixon & Hall 2014, Wallis 1983). Integrate over
radius -> total pressure rise, shaft power, efficiency (AMCA 210 / ISO 5801 static definitions).
Losses: the default ``"euler"`` model relies on empirical SLIP / K_FRICTION / K_TIP_LEAK buckets
(it does NOT subtract airfoil profile-drag loss Δp0,prof = D/(2πr sin φ); see RV-3 findings). The
opt-in ``"axial_force"`` model subtracts blade drag via f_x = L cos φ1 − D sin φ1 with Viterna–Corrigan
(1982) post-stall continuation.

HONEST SCOPE: RANKING-ONLY screening. Do not quote BEM CFM as absolute or beside CFD as
equivalent — BEM ignores thickness/lean/wrap/LE-TE scales/plate sections; ranking only,
coarse, can't separate close designs. Absolute free-air needs CFD + print/measure (P–Q report: CFD Stock
~−26% vs published 60.1 CFM; the old “+2%” claim is retired).

Audit #4 (docs/validation/audits/2026-09-29-audit-04-fan-bem.md): the loss buckets SLIP / K_FRICTION /
K_TIP_LEAK are EMPIRICAL, tuned to the a12x25 Stock recipe, not derived. No Prandtl tip loss is applied
(ducted; only the gap-leakage knockdown). Momentum bound: static air power <= shaft power by construction.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

import numpy as np

from fansim.cfd.metrics import CFM_PER_M3S
from fansim.geometry.blade import BladeParams
from fansim.physics.air import MU_AIR, NU_AIR
from fansim.physics.air import RHO_AMCA as RHO_AIR
from fansim.propeller.bemt import _cl_cd  # thin cambered-airfoil polar (shared with the prop BEMT)

# --- first-order aggregate loss calibration (roadmap §7.3; refine with Kröger-Venter + low-Re polars) ---
# Inviscid blade-element+Euler over-predicts ~1.6-2x: the real fan loses work to cascade interference /
# flow deviation, tip-clearance leakage (Venter & Kröger 1992; Denton 1993), and endwall/secondary flows.
# Three empirical buckets calibrated so the a12x25 Stock recipe matches ~60 CFM free delivery (Audit #4
# notes shut-off ~39 Pa and peak η ~53% do not match datasheet 22.9 Pa / 25–35%):
SLIP = 0.71                   # empirical hydraulic/swirl delivery factor (acts on Δp0, not shaft power)
K_FRICTION = 1.7              # exit dynamic head (1.0) + endwall/duct/inlet friction (~0.7) × ½ρVx²
K_TIP_LEAK = 9.0             # tip-clearance leakage knockdown in the outer span ~ K * gap/chord (§7.3)
N_ITER_MAX = 50               # cap on the per-element swirl fixed-point iteration
DEFAULT_TIP_GAP_MM = 0.5      # blade-to-shroud gap (leakage grows the loss near the tip)

# --- Opt-in "axial_force" pressure model (QA-4, roadmap §23.5; proposed and tested by the QA bot,
# re-implemented here). Static rise = the blades' AXIAL force per annulus area,
# B·½ρW1²c·(cl·cosφ1 − cd·sinφ1), referenced to the INLET relative velocity W1 (cascade practice),
# with the polar continued past stall (Viterna–Corrigan). Blade drag and negative lift now LOWER the
# pressure, so a paddle or a wrong-hand blade no longer scores as a fan (in the Euler model the swirl
# that drag drives counted as useful work). Two empirical buckets, fitted on the Stock 7-station
# recipe's free CFM and shut-off only (datasheet 60.1 CFM / 22.9 Pa; 2 knobs, 2 targets = a fit):
# Stock 59.8 CFM / 22.1 Pa. Held-out checks (QA rules b, b2, c): paddle 14 CFM at η 0.9 %, reversed
# blades no rise, ranking vs 16 CFD designs ρ 0.809 (Euler 0.827). It is NOT a better ranker; it is
# the model that cannot be exploited — used as the pre-CFD exploit guard (system_curve).
PRESSURE_MODELS = ("euler", "axial_force")
AX_SLIP = 0.65                # deviation / under-turning on the axial force (cf. SLIP)
AX_K_FRICTION = 1.9           # friction / secondary static loss ~ K × axial dynamic head (cf. K_FRICTION)
CD_90 = 1.8                   # flat-plate drag at 90° incidence (literature 1.2–2.0; fixed, not tuned)


def _viterna(cl_s: float, cd_s: float, a_s: float, a: float) -> tuple[float, float]:
    """Viterna–Corrigan (1982, NASA TM-82944) post-stall cl/cd at ``a`` (rad) from stall ``a_s``.

    Valid on ``|a| <= pi/2``. Beyond ``+-pi/2`` the ``a2*cos^2(a)/sin(a)`` stall-matching term
    has already vanished at ``cos(+-pi/2) = 0`` and has a ``1/sin(a)`` pole at ``+-pi``, so it is
    dropped there, leaving the continuous flat-plate relation ``0.5*B1*sin(2a)``.
    """
    b1 = CD_90
    s_s, c_s = math.sin(a_s), math.cos(a_s)
    a2 = (cl_s - b1 * s_s * c_s) * s_s / max(c_s * c_s, 1e-6)
    b2 = (cd_s - b1 * s_s * s_s) / max(c_s, 1e-6)
    sa, ca = math.sin(a), abs(math.cos(a))
    if abs(a) <= 0.5 * math.pi:
        ca_eff = max(ca, 1e-3)
        cl = 0.5 * b1 * math.sin(2.0 * a) + a2 * ca_eff * ca_eff / max(abs(sa), 1e-3) * math.copysign(1.0, sa)
        cd = b1 * sa * sa + b2 * ca_eff
    else:
        cl = 0.5 * b1 * math.sin(2.0 * a)
        cd = b1 * sa * sa + b2 * ca
    return cl, max(cd, cd_s)


def _cl_cd_post_stall(alpha: float, camber: float, re: float) -> tuple[float, float]:
    """The shared low-Re polar inside its stall band, Viterna–Corrigan beyond it (the table polar
    clamps cl/cd at its edges, so a 60–90° paddle would otherwise keep cl ≈ 0.77, cd ≈ 0.10)."""
    stall = math.radians(max(8.0, min(15.0, 10.0 + 3.0 * math.log10(max(re, 5000.0) / 20000.0))))
    if -stall <= alpha <= stall:
        return _cl_cd(alpha, camber, re=re)
    edge = stall if alpha > stall else -stall
    cl_s, cd_s = _cl_cd(edge, camber, re=re)
    return _viterna(cl_s, cd_s, edge, alpha)


def _table_polar(alpha: float, camber: float, re: float) -> tuple[float, float]:
    return _cl_cd(alpha, camber, re=re)


@dataclass
class FanPoint:
    flow_cfm: float
    flow_m3s: float
    dp_static_pa: float          # useful static-pressure rise (swirl dynamic head not recovered)
    dp_total_pa: float           # Euler total-pressure rise
    efficiency: float            # static air power / shaft power
    power_w: float               # shaft power
    converged: bool = True       # False if any element's swirl iteration hit its cap (N_ITER_MAX)


@dataclass
class FanCurve:
    points: list[FanPoint]       # low flow -> high flow
    free_delivery_cfm: float     # flow where static rise crosses 0
    shutoff_dp_pa: float         # static rise at the lowest (near-zero) flow
    peak_efficiency: float
    peak_eff_cfm: float
    converged: bool = True       # False if any point up to free delivery failed to converge (post-free-delivery windmill region ignored)
    # "crossed": static rise crosses 0 inside the sweep (normal). "beyond_sweep": still positive at
    # the last point (free delivery reported at the sweep end, a lower bound). "no_rise": static
    # rise never positive (no blades, reversed/stalled blades, hub >= tip) -> free delivery 0, so a
    # dead design ranks last instead of at the sweep's max flow (roadmap §23.4).
    free_status: str = "crossed"
    # True when shutoff_dp_pa came from the Q->0 linear intercept (_shut_off_pa); False when the
    # sweep had no near-zero points and fell back to max(dp_static_pa) (or on a degenerate curve).
    shutoff_extrapolated: bool = True


def _interp_geometry(params: BladeParams):
    """chord(mm), stagger(deg), camber as callables of r_frac (0=hub .. 1=tip)."""
    if not params.stations:
        raise ValueError("params.stations must not be empty")
    st = sorted(params.stations, key=lambda s: s.r_frac)
    rs = np.array([s.r_frac for s in st])
    ch = np.array([s.chord for s in st])
    sg = np.array([s.stagger_deg for s in st])
    cb = np.array([s.max_camber for s in st])
    return (lambda rf: float(np.interp(rf, rs, ch)),
            lambda rf: float(np.interp(rf, rs, sg)),
            lambda rf: float(np.interp(rf, rs, cb)))


def _effective_tip_gap_mm(params: BladeParams, tip_gap_mm: float | None) -> float:
    """Full tip ring seals the leak path; partial / open tip keeps the screening gap."""
    from fansim.geometry.blade import shroud_is_full

    if tip_gap_mm is not None:
        return float(tip_gap_mm)
    return 0.0 if shroud_is_full(params) else DEFAULT_TIP_GAP_MM


def _validate_common(
    params: BladeParams,
    rpm: float,
    n_elem: int,
    rho: float,
    tip_gap_mm: float,
    *,
    stator: bool,
    pressure_model: str,
) -> None:
    if pressure_model not in PRESSURE_MODELS:
        raise ValueError(f"pressure_model must be one of {PRESSURE_MODELS}, got {pressure_model!r}")
    if stator and pressure_model == "axial_force":
        raise ValueError("stator=True is not supported with pressure_model='axial_force'")
    if not math.isfinite(rpm) or rpm < 0.0:
        raise ValueError(f"rpm must be finite and >= 0, got {rpm!r}")
    if not math.isfinite(rho) or rho <= 0.0:
        raise ValueError(f"rho must be finite and > 0, got {rho!r}")
    if int(n_elem) < 1:
        raise ValueError(f"n_elem must be >= 1, got {n_elem!r}")
    if not math.isfinite(tip_gap_mm) or tip_gap_mm < 0.0:
        raise ValueError(f"tip_gap_mm must be finite and >= 0, got {tip_gap_mm!r}")
    if params.hub_radius < 0.0:
        raise ValueError(f"hub_radius must be >= 0, got {params.hub_radius!r}")


_GeomFns = tuple[
    Callable[[float], float],
    Callable[[float], float],
    Callable[[float], float],
]


def operating_point(params: BladeParams, rpm: float, flow_m3s: float,
                    n_elem: int = 20, rho: float = RHO_AIR,
                    tip_gap_mm: float | None = None, *, stator: bool = False,
                    geom: _GeomFns | None = None,
                    pressure_model: str = "euler") -> FanPoint:
    """Blade-element + Euler performance at one flow rate. Angles are measured from the TANGENTIAL
    (rotation) plane, matching the geometry's stagger convention (chord axial component = sin(stagger)).

    ``stator=True`` recovers exit swirl into static pressure (ideal OGV); default loses it as KE.
    ``pressure_model="axial_force"`` (opt-in) takes the static rise from the blades' axial force with
    a post-stall polar; ``stator=True`` is rejected there. The default ``"euler"`` is unchanged.
    """
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    _validate_common(params, rpm, n_elem, rho, tip_gap_mm,
                     stator=stator, pressure_model=pressure_model)
    if not math.isfinite(flow_m3s) or flow_m3s < 0.0:
        raise ValueError(f"flow_m3s must be finite and >= 0, got {flow_m3s!r}")
    axial = pressure_model == "axial_force"
    polar = _cl_cd_post_stall if axial else _table_polar
    hub_r = params.hub_radius / 1000.0
    tip_r = params.tip_radius / 1000.0
    B = int(params.n_blades)
    omega = rpm * 2.0 * math.pi / 60.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    if area <= 0.0:
        return FanPoint(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, False)
    Vx = flow_m3s / area                                  # mean axial velocity
    nu = NU_AIR if rho == RHO_AIR else MU_AIR / rho       # kinematic viscosity scales as mu / rho
    chord_fn, stag_fn, camb_fn = geom if geom is not None else _interp_geometry(params)
    from fansim.geometry.blade import station_root_radius

    r_root = station_root_radius(params) / 1000.0
    span_cad = tip_r - r_root
    edges = np.linspace(hub_r, tip_r, n_elem + 1)

    dp0_num = 0.0        # mass-weighted Euler total-pressure rise
    swirl_ke = 0.0       # mass-weighted swirl dynamic head (lost without a stator)
    ax_force = 0.0       # useful blade axial force over the span [N] (axial_force model)
    power = 0.0
    mass = 0.0
    converged = True
    for i in range(n_elem):
        r = float(0.5 * (edges[i] + edges[i + 1]))
        dr = float(edges[i + 1] - edges[i])
        # #117: query station geometry at the CAD builder's r_frac for physical radius r.
        rf = min(max((r - r_root) / span_cad, 0.0), 1.0) if span_cad > 0.0 else 0.0
        U = omega * r
        c = chord_fn(rf) / 1000.0
        beta = math.radians(stag_fn(rf))                  # blade angle from tangential
        camb = camb_fn(rf)
        dm = rho * max(Vx, 0.0) * 2.0 * math.pi * r * dr  # element mass flow

        vth = 0.0                                         # swirl added by the rotor (absolute, +rotation)
        elem_ok = False
        for _ in range(N_ITER_MAX):
            vth_m = 0.5 * vth                             # mean swirl through the row
            phi = math.atan2(Vx, max(U - vth_m, 0.05))    # mean relative flow angle from tangential
            W = math.hypot(Vx, U - vth_m)
            re = W * c / nu                               # local blade Reynolds number
            alpha = beta - phi                            # incidence
            cl, cd = polar(alpha, camb, re)               # Re-aware low-Re polar (§7.2)
            # tangential (rotation-direction) blade force per unit span, all blades (prop-BEMT decomposition)
            f_theta = 0.5 * rho * W * W * c * B * (cl * math.sin(phi) + cd * math.cos(phi))
            # angular-momentum balance: B-blade tangential force = rate of swirl momentum
            denom = rho * max(Vx, 0.05) * 2.0 * math.pi * r
            vth_new = f_theta / denom if denom > 0 else vth
            vth_new = max(0.0, min(vth_new, 0.95 * U))
            if abs(vth_new - vth) < 1e-3:
                vth = vth_new
                elem_ok = True
                break
            vth = 0.5 * vth + 0.5 * vth_new
        converged = converged and elem_ok

        # Ducted fan screening model: do NOT apply Prandtl finite-blade tip loss (shroud suppresses the
        # free-tip vortex roll-up). Only model gap leakage in the outer span (screening approximation).
        leak = 1.0
        if rf > 0.65:                                     # outer span leaks across the blade-to-shroud gap
            leak *= max(0.2, 1.0 - K_TIP_LEAK * (tip_gap_mm / 1000.0) / max(c, 1e-3))
        vth_eff = SLIP * leak * vth                       # deviation + leakage -> useful swirl
        dp0_num += rho * U * vth_eff * dm                 # useful Euler total-pressure rise
        swirl_ke += 0.5 * rho * vth_eff * vth_eff * dm    # swirl dynamic head (lost, no stator)
        power += dm * U * vth                             # shaft work (full blade force; deviation = loss)
        if axial and B > 0:
            phi1 = math.atan2(Vx, U)                      # inlet relative flow angle (no swirl yet)
            w1 = math.hypot(Vx, U)
            cl1, cd1 = polar(beta - phi1, camb, w1 * c / nu)
            f_x = 0.5 * rho * w1 * w1 * c * B * (cl1 * math.cos(phi1) - cd1 * math.sin(phi1))
            ax_force += AX_SLIP * leak * f_x * dr         # deviation + gap leakage, as for the swirl
        mass += dm

    if mass <= 0:
        return FanPoint(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, converged)
    dp_total = dp0_num / mass
    swirl_loss = 0.0 if stator else (swirl_ke / mass)
    if axial:
        dp_static = (ax_force / area if B > 0 and area > 0 else 0.0) \
            - AX_K_FRICTION * 0.5 * rho * Vx * Vx        # axial force per annulus area minus friction
        if flow_m3s > 0.0 and power > 0.0:
            # Energy bound: the static rise cannot exceed the shaft work per unit volume (air power
            # <= shaft power). Without it dense 11-blade designs read peak η up to 115 % (QA r4).
            dp_static = min(dp_static, power / flow_m3s)
    else:
        dp_static = dp_total - swirl_loss \
            - K_FRICTION * 0.5 * rho * Vx * Vx           # endwall/duct/blade friction (grows with flow)
    flow_cfm = float(flow_m3s * CFM_PER_M3S)
    air_power = flow_m3s * max(dp_static, 0.0)
    eff = air_power / power if power > 1e-6 else 0.0
    # Full precision here (#50); cockpit/export format for display.
    return FanPoint(flow_cfm, float(flow_m3s), float(dp_static), float(dp_total),
                    float(eff), float(power), converged)


def pq_curve(params: BladeParams, rpm: float, n_points: int = 22, n_elem: int = 20,
             rho: float = RHO_AIR, tip_gap_mm: float | None = None, *,
             stator: bool = False, pressure_model: str = "euler") -> FanCurve:
    """Sweep flow from near-shutoff to past free-delivery -> the fan's P-Q curve + key points."""
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    _validate_common(params, rpm, n_elem, rho, tip_gap_mm,
                     stator=stator, pressure_model=pressure_model)
    if int(n_points) < 2:
        raise ValueError(f"n_points must be >= 2, got {n_points!r}")
    tip_r = params.tip_radius / 1000.0
    hub_r = params.hub_radius / 1000.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    if area <= 0.0 or int(params.n_blades) <= 0 or rpm == 0.0:
        return FanCurve(points=[], free_delivery_cfm=0.0, shutoff_dp_pa=0.0, peak_efficiency=0.0,
                        peak_eff_cfm=0.0, converged=False, free_status="no_rise",
                        shutoff_extrapolated=False)
    v_tip = (rpm * 2.0 * math.pi / 60.0) * tip_r
    q_max = 0.6 * v_tip * area                            # generous upper bound on flow
    flows = np.linspace(0.02 * q_max, q_max, n_points)
    geom = _interp_geometry(params)
    pts = [operating_point(params, rpm, float(q), n_elem=n_elem, rho=rho,
                           tip_gap_mm=tip_gap_mm, stator=stator, geom=geom,
                           pressure_model=pressure_model)
           for q in flows]

    # free delivery: interpolate where static rise crosses 0 (high-flow end; scan from the
    # high-flow tail so a low-flow stall dip below 0 Pa does not mask the true free-delivery point)
    if not any(p.dp_static_pa > 0.0 for p in pts):
        free_cfm, free_status = 0.0, "no_rise"
    elif pts[-1].dp_static_pa > 0.0:
        free_cfm, free_status = pts[-1].flow_cfm, "beyond_sweep"
    else:
        free_cfm, free_status = pts[-1].flow_cfm, "beyond_sweep"
        for a, b in reversed(list(pairwise(pts))):
            if a.dp_static_pa > 0.0 >= b.dp_static_pa:
                t = a.dp_static_pa / (a.dp_static_pa - b.dp_static_pa)
                free_cfm = a.flow_cfm + t * (b.flow_cfm - a.flow_cfm)
                free_status = "crossed"
                break
    # Shut-off: Q→0 linear intercept from the lowest-flow points (§10.7), not max(ΔP)
    # which can sit off the loading branch on a coarse sweep.
    from fansim.analyze.fan_curve import shut_off_pa as _shut_off_pa
    shut_proxy = _shut_off_pa(
        [{"cfm": p.flow_cfm, "static_pa": p.dp_static_pa} for p in pts],
        q_near_zero=max(5.0, 0.15 * free_cfm),
    )
    shutoff_extrapolated = shut_proxy is not None
    shutoff = float(shut_proxy) if shut_proxy is not None else max(
        p.dp_static_pa for p in pts)
    peak = max(pts, key=lambda p: p.efficiency)
    return FanCurve(points=pts, free_delivery_cfm=free_cfm, shutoff_dp_pa=shutoff,
                    peak_efficiency=peak.efficiency, peak_eff_cfm=peak.flow_cfm,
                    converged=all(p.converged for p in pts if p.flow_cfm <= free_cfm + 1e-9
                                  or p.dp_static_pa > 0.0),
                    free_status=free_status,
                    shutoff_extrapolated=shutoff_extrapolated)
