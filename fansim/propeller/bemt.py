"""Blade Element Momentum Theory (BEMT) — fast, physics-based propeller performance.

The standard way props are analysed/designed (QProp/JavaProp-class): slice the blade into radial
elements, and at each one balance the LIFT/DRAG the element makes against the MOMENTUM it imparts to
the air, solving for the induced inflow. Integrate the elements -> total thrust, torque, power, and
efficiency. No CFD/mesh — deterministic and quick, so it screens propeller designs the way the RANS
proxy screens fans. analyze applies _compressibility_cl_cd (Prandtl-Glauert on Cl,
wave drag past Mach 0.7) using local relative speed over C_AIR. A compressible CFD tier
can still refine finalists.

Static thrust (V=0) is the headline drone number: thrust in grams + hover efficiency in grams-per-watt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fansim.geometry.blade import BladeParams
from fansim.prop_spec import C_AIR

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


def _cl_cd(
    alpha_rad: float,
    camber: float,
    re: float | None = None,
    thickness: float = 0.12,
):
    """Cambered-airfoil polar: vendored UIUC-style table when Re is set, else analytic.

    REYNOLDS-AWARE (roadmap §7.2 / §1.6): with ``re`` given, prefer ``fansim.data.polars``
    tables (NACA *12 + Selig e387/sd7032/s1223), matched on camber + thickness. If the
    table path is unavailable, use the analytic low-Re trends. ``re=None`` keeps the
    original high-Re analytic (back-compat).
    """
    if re is not None:
        from fansim.propeller.polars import cl_cd_table
        tab = cl_cd_table(alpha_rad, camber, re, thickness=thickness)
        if tab is not None:
            return tab
    return _cl_cd_analytic(alpha_rad, camber, re)


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
        U = omega * r
        vi = 2.0                                            # induced axial velocity guess [m/s]
        vth = 0.0                                           # far-wake swirl velocity (≈ 2 a' Ωr), +rotation
        dT = 0.0
        f_theta = 0.0
        phi = 0.0
        W2 = 0.0
        cl = cd = 0.0
        for _ in range(60):                                 # BEM fixed-point iteration (a, a')
            Vax = v_forward + vi
            vth_m = 0.5 * vth                               # mean swirl through the disk
            Vt = max(U - vth_m, 0.05)                       # Vt = Ωr(1 − a′)
            phi = math.atan2(Vax, Vt)
            W2 = Vax * Vax + Vt * Vt
            alpha = beta - phi
            cl, cd = _cl_cd(alpha, camber, re=math.sqrt(W2) * c / NU_AIR)   # Re-aware polar (§7.2)
            mach = math.sqrt(W2) / C_AIR
            cl, cd = _compressibility_cl_cd(cl, cd, mach)
            # Prandtl tip-loss factor (open propeller only)
            f = (B / 2.0) * (R - r) / max(r * math.sin(phi), 1e-4)
            F = max(0.15, (2.0 / math.pi) * math.acos(math.exp(-min(f, 20.0))))

            dT = 0.5 * rho * W2 * c * B * (cl * math.cos(phi) - cd * math.sin(phi))   # per unit span
            f_theta = 0.5 * rho * W2 * c * B * (cl * math.sin(phi) + cd * math.cos(phi))

            # Momentum: dT = 4π r ρ Vax vi F  (per unit span) -> update vi
            denom_t = 4.0 * math.pi * r * rho * max(Vax, 0.1) * F
            vi_new = dT / denom_t if denom_t > 0 else vi
            vi_new = max(0.0, min(vi_new, 60.0))

            # Angular momentum: fθ = (ρ Vax 2π r) ΔVθ (per unit span), with ΔVθ ≈ vth (0 → far wake)
            denom_th = rho * max(Vax, 0.1) * 2.0 * math.pi * r
            vth_new = f_theta / denom_th if denom_th > 0 else vth
            vth_new = max(0.0, min(vth_new, 1.9 * U))       # a′ < 0.95 (since vth ≈ 2 a′ Ωr)

            if abs(vi_new - vi) < 1e-3 and abs(vth_new - vth) < 1e-3:
                vi = vi_new
                vth = vth_new
                break
            vi = 0.5 * vi + 0.5 * vi_new                    # relax
            vth = 0.5 * vth + 0.5 * vth_new

        dQ = f_theta * r                                    # per unit span
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


# --- spliced from transcript edit-history (recovery 2026-09-12) ---
def _compressibility_cl_cd(cl: float, cd: float, mach: float) -> tuple[float, float]:
    """Stage-1 compressibility: Prandtl–Glauert on Cl; soft wave-drag rise past M≈0.7."""
    m = max(0.0, min(float(mach), 0.95))
    beta = math.sqrt(max(1e-6, 1.0 - m * m))
    cl_c = float(cl) / beta
    cd_c = float(cd)
    if m > 0.70:
        cd_c = cd_c + 0.02 * ((m - 0.70) / 0.25) ** 2
    return cl_c, cd_c


def _cl_cd_analytic(alpha_rad: float, camber: float, re: float | None = None):
    """Analytic cambered-airfoil polar (high-Re or Re-aware trends)."""
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
    # Analytic polar: use only profile drag (cd0). Do not include an induced-drag term here;
    # BEM/BEMT already accounts for induced power via momentum coupling.
    cd = cd0
    return cl, cd
