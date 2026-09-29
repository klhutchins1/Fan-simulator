"""Compute-free AXIAL-FAN performance — blade-element + Euler (the fan analog of the prop BEMT).

Predicts a ducted axial fan's P-Q curve (static-pressure rise vs flow), free-delivery CFM, shut-off
pressure, peak efficiency and shaft power ANALYTICALLY — no CFD — so the optimizer can screen thousands
of fan designs in milliseconds and reserve CFD for finalists (roadmap §7.1). This is the fan side of
what made the propeller side instant.

Physics: slice the annulus hub->tip into elements; at each one balance the blade-element lift/drag
against the momentum imparted to the annular stream tube, solve for the swirl the rotor adds, and apply
the Euler turbomachinery relation (ΔP0 = ρ·U·ΔVθ). Integrate over radius -> total pressure rise, shaft
power, efficiency. Losses: airfoil profile drag (from the polar) now; TIP-CLEARANCE (Kröger-Venter) and
low-Reynolds airfoil polars are the next upgrades (roadmap §7.2/§7.3).

HONEST SCOPE: RANKING-ONLY screening. Do not quote BEM CFM as absolute or beside CFD as
equivalent — BEM ignores thickness/lean/wrap/LE-TE scales/plate sections and typically
under-ranks CFD (~0.6×). Absolute free-air needs CFD + print/measure (P–Q report: CFD Stock
~−26% vs published 60.1 CFM; the old “+2%” claim is retired).

Audit #4 (docs/validation/audits/2026-09-29-audit-04-fan-bem.md): the loss buckets SLIP / K_FRICTION /
K_TIP_LEAK are EMPIRICAL, tuned to the a12x25 Stock recipe, not derived. No Prandtl tip loss is applied
(ducted; only the gap-leakage knockdown). Momentum bound: static air power <= shaft power by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from fansim.cfd.metrics import CFM_PER_M3S
from fansim.geometry.blade import BladeParams
from fansim.propeller.bemt import _cl_cd   # thin cambered-airfoil polar (shared with the prop BEMT)

RHO_AIR = 1.2                 # kg/m^3
NU_AIR = 1.5e-5               # kinematic viscosity (m^2/s) -> local blade Reynolds number

# --- first-order aggregate loss calibration (roadmap §7.3; refine with Kröger-Venter + low-Re polars) ---
# Inviscid blade-element+Euler over-predicts ~1.6-2x: the real fan loses work to flow DEVIATION/slip
# (fluid under-turns vs the blade), TIP-CLEARANCE leakage, and endwall/secondary flows. Until those are
# modelled properly, three empirical buckets calibrated so the reference a12x25 geometry reproduces the
# CFD-validated P-Q (~60 CFM free, ~23 Pa shut-off, ~25-35% eff):
SLIP = 0.71                   # swirl actually delivered vs ideal (deviation) — gap leakage now explicit (§7.3)
K_FRICTION = 1.7              # endwall/duct/blade friction static-pressure loss ~ K * dynamic head
K_TIP_LEAK = 9.0             # tip-clearance leakage knockdown in the outer span ~ K * gap/chord (§7.3)
N_ITER_MAX = 50               # cap on the per-element swirl fixed-point iteration
DEFAULT_TIP_GAP_MM = 0.5      # blade-to-shroud gap (leakage grows the loss near the tip)


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
    points: list                 # list[FanPoint], low flow -> high flow
    free_delivery_cfm: float     # flow where static rise crosses 0
    shutoff_dp_pa: float         # static rise at the lowest (near-zero) flow
    peak_efficiency: float
    peak_eff_cfm: float
    converged: bool = True       # False if any point up to free delivery failed to converge (post-free-delivery windmill region ignored)


def _interp_geometry(params: BladeParams):
    """chord(mm), stagger(deg), camber as callables of r_frac (0=hub .. 1=tip)."""
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


_GeomFns = tuple[
    Callable[[float], float],
    Callable[[float], float],
    Callable[[float], float],
]


def operating_point(params: BladeParams, rpm: float, flow_m3s: float,
                    n_elem: int = 20, rho: float = RHO_AIR,
                    tip_gap_mm: float | None = None, *, stator: bool = False,
                    geom: _GeomFns | None = None) -> FanPoint:
    """Blade-element + Euler performance at one flow rate. Angles are measured from the TANGENTIAL
    (rotation) plane, matching the geometry's stagger convention (chord axial component = sin(stagger)).

    ``stator=True`` recovers exit swirl into static pressure (ideal OGV); default loses it as KE.
    """
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    hub_r = params.hub_radius / 1000.0
    tip_r = params.tip_radius / 1000.0
    B = int(params.n_blades)
    omega = rpm * 2.0 * math.pi / 60.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    Vx = flow_m3s / area if area > 0 else 0.0             # mean axial velocity
    chord_fn, stag_fn, camb_fn = geom if geom is not None else _interp_geometry(params)
    edges = np.linspace(hub_r, tip_r, n_elem + 1)

    dp0_num = 0.0        # mass-weighted Euler total-pressure rise
    swirl_ke = 0.0       # mass-weighted swirl dynamic head (lost without a stator)
    power = 0.0
    mass = 0.0
    converged = True
    for i in range(n_elem):
        r = 0.5 * (edges[i] + edges[i + 1])
        dr = edges[i + 1] - edges[i]
        rf = (r - hub_r) / (tip_r - hub_r) if tip_r > hub_r else 0.0
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
            re = W * c / NU_AIR                           # local blade Reynolds number
            alpha = beta - phi                            # incidence
            cl, cd = _cl_cd(alpha, camb, re=re)           # Re-aware low-Re polar (§7.2)
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
        r_norm = (r - hub_r) / (tip_r - hub_r) if tip_r > hub_r else 0.0
        if r_norm > 0.65:                                 # outer span leaks across the blade-to-shroud gap
            leak *= max(0.2, 1.0 - K_TIP_LEAK * (tip_gap_mm / 1000.0) / max(c, 1e-3))
        vth_eff = SLIP * leak * vth                       # deviation + leakage -> useful swirl
        dp0_num += rho * U * vth_eff * dm                 # useful Euler total-pressure rise
        swirl_ke += 0.5 * rho * vth_eff * vth_eff * dm    # swirl dynamic head (lost, no stator)
        power += dm * U * vth                             # shaft work (full blade force; deviation = loss)
        mass += dm

    if mass <= 0:
        return FanPoint(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, converged)
    dp_total = dp0_num / mass
    swirl_loss = 0.0 if stator else (swirl_ke / mass)
    dp_static = dp_total - swirl_loss \
        - K_FRICTION * 0.5 * rho * Vx * Vx               # endwall/duct/blade friction (grows with flow)
    flow_cfm = flow_m3s * CFM_PER_M3S
    air_power = flow_m3s * max(dp_static, 0.0)
    eff = air_power / power if power > 1e-6 else 0.0
    return FanPoint(round(flow_cfm, 1), flow_m3s, round(dp_static, 2), round(dp_total, 2),
                    round(eff, 3), round(power, 2), converged)


def pq_curve(params: BladeParams, rpm: float, n_points: int = 22, n_elem: int = 20,
             rho: float = RHO_AIR, tip_gap_mm: float | None = None, *,
             stator: bool = False) -> FanCurve:
    """Sweep flow from near-shutoff to past free-delivery -> the fan's P-Q curve + key points."""
    tip_gap_mm = _effective_tip_gap_mm(params, tip_gap_mm)
    tip_r = params.tip_radius / 1000.0
    hub_r = params.hub_radius / 1000.0
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    v_tip = (rpm * 2.0 * math.pi / 60.0) * tip_r
    q_max = 0.6 * v_tip * area                            # generous upper bound on flow
    flows = np.linspace(0.02 * q_max, q_max, n_points)
    geom = _interp_geometry(params)
    pts = [operating_point(params, rpm, float(q), n_elem=n_elem, rho=rho,
                           tip_gap_mm=tip_gap_mm, stator=stator, geom=geom)
           for q in flows]

    # free delivery: interpolate where static rise crosses 0 (high-flow end)
    free_cfm = pts[-1].flow_cfm
    for a, b in zip(pts, pts[1:]):
        if a.dp_static_pa > 0.0 >= b.dp_static_pa:
            t = a.dp_static_pa / (a.dp_static_pa - b.dp_static_pa)
            free_cfm = round(a.flow_cfm + t * (b.flow_cfm - a.flow_cfm), 1)
            break
    # Shut-off: Q→0 linear intercept from the lowest-flow points (§10.7), not max(ΔP)
    # which can sit off the loading branch on a coarse sweep.
    from fansim.analyze.fan_curve import shut_off_pa as _shut_off_pa
    shut_proxy = _shut_off_pa(
        [{"cfm": p.flow_cfm, "static_pa": p.dp_static_pa} for p in pts],
        q_near_zero=max(5.0, 0.15 * free_cfm),
    )
    shutoff = float(shut_proxy) if shut_proxy is not None else max(
        p.dp_static_pa for p in pts)
    peak = max(pts, key=lambda p: p.efficiency)
    return FanCurve(points=pts, free_delivery_cfm=free_cfm, shutoff_dp_pa=round(shutoff, 2),
                    peak_efficiency=peak.efficiency, peak_eff_cfm=peak.flow_cfm,
                    converged=all(p.converged for p in pts if p.flow_cfm <= free_cfm + 1e-9
                                  or p.dp_static_pa > 0.0))
