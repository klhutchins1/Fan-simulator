# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Blade Element Momentum Theory (BEMT) — fast, physics-based propeller performance.

The standard way props are analysed/designed (QProp/JavaProp-class): slice the blade into radial
elements, and at each one balance the LIFT/DRAG the element makes against the MOMENTUM it imparts to
the air, solving for the induced inflow. Integrate the elements -> total thrust, torque, power, and
efficiency. No CFD/mesh — deterministic and quick, so it screens propeller designs the way the RANS
proxy screens fans. (A compressible open-air CFD tier can refine finalists later; tips run ~Mach 0.5.)

Static thrust (V=0) is the headline drone number: thrust in grams + hover efficiency in grams-per-watt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fansim.geometry.blade import BladeParams

RHO_AIR = 1.225   # kg/m^3
NU_AIR = 1.5e-5   # kinematic viscosity (m^2/s) -> local blade Reynolds number
G = 9.80665


@dataclass
class PropPerf:
    thrust_n: float
    torque_nm: float
    power_w: float
    rpm: float
    v_forward: float
    thrust_g: float                 # thrust in grams (drone convention)
    efficiency_g_per_w: float        # static hover efficiency = thrust/power
    figure_of_merit: float           # ideal/actual hover power ratio (0..1; ~0.6-0.8 good)
    prop_efficiency: float | None = None   # propulsive eff (forward flight); None in hover


def _cl_cd(alpha_rad: float, camber: float, re: float | None = None):
    """Cambered-airfoil polar: linear lift to stall, soft drop past it, quadratic drag.

    REYNOLDS-AWARE (roadmap §7.2): fan blades run Re ~20-80k and small props even lower, where lift/drag
    depart sharply from high-Re thin-airfoil theory. Pass the local Re = W*c/nu to apply low-Re trends
    from the UIUC/Selig low-Reynolds data: max-lift drops and stall comes earlier as Re falls, profile
    drag rises steeply (thick laminar boundary layer / separation bubble), and the lift slope softens.
    re=None keeps the original high-Re polar (back-compat)."""
    a_deg = math.degrees(alpha_rad)
    cl_max, cd0, stall_deg, slope = 1.4, 0.012, 14.0, 2.0 * math.pi
    if re is not None:
        r = max(float(re), 5000.0)
        f = math.log10(r / 20000.0)               # 0 at Re 20k, 1 at 200k, 2 at 2M
        cl_max = max(0.80, min(1.5, 0.95 + 0.30 * f))     # low Re -> lower max lift
        stall_deg = max(8.0, min(15.0, 10.0 + 3.0 * f))   # low Re -> earlier stall
        cd0 = max(0.010, 0.008 + 5.0 / math.sqrt(r))      # low Re -> much higher profile drag
        slope = 2.0 * math.pi * max(0.75, min(1.0, 0.88 + 0.12 * f))
    cl0 = slope * camber                          # zero-alpha lift from camber (thin-airfoil approx)
    cl = cl0 + slope * alpha_rad
    cl = max(-cl_max, min(cl_max, cl))            # clamp near max lift
    if a_deg > stall_deg:                         # post-stall soft drop
        cl *= max(0.55, 1.0 - (a_deg - stall_deg) * 0.03)
    cd = cd0 + 0.020 * cl * cl                    # profile + induced-ish drag polar
    return cl, cd


def _interp_geom(params: BladeParams):
    """Return callables chord(r_mm), twist_deg(r_mm) over the actual radius, from the blade stations."""
    st = sorted(params.stations, key=lambda s: s.r_frac)
    r_root = params.hub_radius
    r_tip = params.tip_radius
    rs = np.array([r_root + (r_tip - r_root) * s.r_frac for s in st])
    chords = np.array([s.chord for s in st])
    twists = np.array([s.stagger_deg for s in st])
    camber = float(np.mean([s.max_camber for s in st]))
    return (lambda r: float(np.interp(r, rs, chords)),
            lambda r: float(np.interp(r, rs, twists)), camber, r_root, r_tip)


def analyze(params: BladeParams, rpm: float, v_forward: float = 0.0, rho: float = RHO_AIR,
            n_elem: int = 24) -> PropPerf:
    """BEMT performance of a propeller ``params`` at ``rpm`` (static if v_forward=0). Distances mm->m."""
    chord_fn, twist_fn, camber, r_root_mm, r_tip_mm = _interp_geom(params)
    B = params.n_blades
    omega = rpm * 2.0 * math.pi / 60.0
    R = r_tip_mm / 1000.0
    edges = np.linspace(r_root_mm, r_tip_mm, n_elem + 1) / 1000.0   # element boundaries [m]
    T = Q = 0.0
    for i in range(n_elem):
        r = 0.5 * (edges[i] + edges[i + 1])
        dr = edges[i + 1] - edges[i]
        c = chord_fn(r * 1000.0) / 1000.0
        beta = math.radians(twist_fn(r * 1000.0))
        sigma = B * c / (2.0 * math.pi * r)                 # local solidity
        vi = 2.0                                            # induced axial velocity guess [m/s]
        for _ in range(60):                                # BEM fixed-point iteration
            Vax = v_forward + vi
            phi = math.atan2(Vax, omega * r)
            W2 = Vax * Vax + (omega * r) ** 2
            alpha = beta - phi
            cl, cd = _cl_cd(alpha, camber, re=math.sqrt(W2) * c / NU_AIR)   # Re-aware polar (§7.2)
            # Prandtl tip-loss factor
            f = (B / 2.0) * (R - r) / max(r * math.sin(phi), 1e-4)
            F = max(0.15, (2.0 / math.pi) * math.acos(math.exp(-min(f, 20.0))))
            dT = 0.5 * rho * W2 * c * B * (cl * math.cos(phi) - cd * math.sin(phi))   # per unit span
            # momentum: dT = 4*pi*r*rho*(V+vi)*vi*F  -> update vi
            denom = 4.0 * math.pi * r * rho * max(Vax, 0.1) * F
            vi_new = dT / denom if denom > 0 else vi
            vi_new = max(0.0, min(vi_new, 60.0))
            if abs(vi_new - vi) < 1e-3:
                vi = vi_new
                break
            vi = 0.5 * vi + 0.5 * vi_new                    # relax
        dQ = 0.5 * rho * W2 * c * B * (cl * math.sin(phi) + cd * math.cos(phi)) * r    # per unit span
        T += dT * dr
        Q += dQ * dr
    T = max(T, 0.0)
    P = Q * omega
    A = math.pi * R * R
    fm = (T ** 1.5 / math.sqrt(2.0 * rho * A)) / P if (P > 0 and T > 0) else 0.0
    prop_eff = (T * v_forward / P) if (v_forward > 0 and P > 0) else None
    return PropPerf(thrust_n=round(T, 3), torque_nm=round(Q, 4), power_w=round(P, 1), rpm=rpm,
                    v_forward=v_forward, thrust_g=round(T / G * 1000.0, 0),
                    efficiency_g_per_w=round(T / G * 1000.0 / P, 2) if P > 0 else 0.0,
                    figure_of_merit=round(min(fm, 1.0), 3), prop_efficiency=prop_eff)
