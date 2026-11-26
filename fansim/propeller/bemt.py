"""Blade Element Momentum Theory (BEMT) — fast, physics-based propeller performance.

The standard way props are analysed/designed (QProp/JavaProp-class): slice the blade into radial
elements, and at each one balance the LIFT/DRAG the element makes against the MOMENTUM it imparts to
the air, solving for the induced inflow. Integrate the elements -> total thrust, torque, power, and
efficiency. No CFD/mesh — deterministic and quick, so it screens propeller designs the way the RANS
proxy screens fans. analyze applies _compressibility_cl_cd (Prandtl-Glauert on attached Cl, capped at
the polar peak; stalled Cl unchanged; wave drag past Mach 0.7) using local
relative speed over C_AIR. A compressible CFD tier can still refine finalists.

Loss model (what is and is NOT modelled): a Prandtl finite-blade TIP-LOSS factor F (Prandtl 1919, in
Betz/Glauert form; floored at 0.15) multiplies the momentum term only; there is NO ROOT-loss factor
and NO Glauert high-induction (turbulent-wake) correction, so heavily loaded roots/hover are
approximate. Swirl is included. The inner (vi, v_theta) fixed-point iteration is capped at 60 steps;
``PropPerf.converged`` is False if any element hit the cap (results then unreliable).
References: Prandtl (1919), Glauert (1935), Drela QPROP (2006); see docs/bibliography.md.

Static thrust (V=0) is the headline drone number: thrust in grams + hover efficiency in grams-per-watt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fansim.geometry.blade import BladeParams
from fansim.physics.air import C0_AIR as C_AIR
from fansim.physics.air import NU_AIR
from fansim.physics.air import RHO_ISA as RHO_AIR

G = 9.80665

# Polar backend for `_section_aero`: "table" (default UIUC CSVs → analytic) or "neuralfoil"
# (§19.15 / §20.2). Override with ``set_polar_backend`` or env ``FANSIM_POLAR_BACKEND``.
_POLAR_BACKEND = "table"


def get_polar_backend() -> str:
    import os

    env = (os.environ.get("FANSIM_POLAR_BACKEND") or "").strip().lower()
    if env in ("table", "neuralfoil"):
        return env
    return _POLAR_BACKEND


def set_polar_backend(name: str) -> str:
    """Set process-wide polar backend: ``table`` or ``neuralfoil``. Returns the active name."""
    global _POLAR_BACKEND
    key = str(name or "table").strip().lower()
    if key not in ("table", "neuralfoil"):
        raise ValueError(f"polar backend must be 'table' or 'neuralfoil', got {name!r}")
    _POLAR_BACKEND = key
    return _POLAR_BACKEND


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
    figure_of_merit_raw: float = 0.0        # UNCLIPPED FM; > 1 would violate momentum theory (a bug flag)
    converged: bool = True                  # False if any element hit the 60-iteration inflow cap


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
    cl, cd, _stalled, _cap = _section_aero(alpha_rad, camber, re=re, thickness=thickness)
    return cl, cd


def _section_aero(
    alpha_rad: float,
    camber: float,
    re: float | None = None,
    thickness: float = 0.12,
) -> tuple[float, float, bool, float]:
    """Incompressible `(cl, cd, stalled, cl_cap)` from the same branch as `_cl_cd`."""
    if re is not None and get_polar_backend() == "neuralfoil":
        from fansim.propeller.neuralfoil_polars import section_neuralfoil

        nf = section_neuralfoil(alpha_rad, camber, re, thickness=thickness)
        if nf is not None:
            return nf
    if re is not None:
        from fansim.propeller.polars import section_table

        tab = section_table(alpha_rad, camber, re, thickness=thickness)
        if tab is not None:
            return tab
    return _analytic_section(alpha_rad, camber, re)


def _interp_geom(params: BladeParams):
    """Return callables chord(r_mm), twist_deg(r_mm) over the actual radius, from the blade stations."""
    st = sorted(params.stations, key=lambda s: s.r_frac)
    r_root = params.hub_radius
    r_tip = params.tip_radius
    rs = np.array([r_root + (r_tip - r_root) * s.r_frac for s in st])
    chords = np.array([s.chord for s in st])
    twists = np.array([s.stagger_deg for s in st])
    camber = float(np.mean([s.max_camber for s in st]))
    thickness = float(np.mean([s.thickness for s in st]))
    return (lambda r: float(np.interp(r, rs, chords)),
            lambda r: float(np.interp(r, rs, twists)), camber, thickness, r_root, r_tip)


def _validate_analyze_inputs(
    params: BladeParams,
    rpm: float,
    v_forward: float,
    rho: float,
    n_elem: int,
) -> None:
    if not math.isfinite(rpm) or rpm < 0.0:
        raise ValueError(f"rpm must be finite and >= 0, got {rpm!r}")
    if not math.isfinite(v_forward) or v_forward < 0.0:
        raise ValueError(f"v_forward must be finite and >= 0, got {v_forward!r}")
    if not math.isfinite(rho) or rho <= 0.0:
        raise ValueError(f"rho must be finite and > 0, got {rho!r}")
    if int(n_elem) < 1:
        raise ValueError(f"n_elem must be >= 1, got {n_elem!r}")
    if params.n_blades < 0:
        raise ValueError(f"n_blades must be >= 0, got {params.n_blades!r}")
    if not params.stations:
        raise ValueError("BladeParams.stations must not be empty")
    if not math.isfinite(params.hub_radius) or params.hub_radius < 0.0:
        raise ValueError(f"hub_radius must be finite and >= 0, got {params.hub_radius!r}")
    if not math.isfinite(params.tip_radius) or params.tip_radius <= params.hub_radius:
        raise ValueError(
            f"tip_radius ({params.tip_radius!r}) must be finite and > hub_radius ({params.hub_radius!r})"
        )


def analyze(params: BladeParams, rpm: float, v_forward: float = 0.0, rho: float = RHO_AIR,
            n_elem: int = 24) -> PropPerf:
    """BEMT performance of a propeller ``params`` at ``rpm`` (static if v_forward=0). Distances mm->m."""
    rpm_f = float(rpm)
    vf_f = float(v_forward)
    rho_f = float(rho)
    _validate_analyze_inputs(params, rpm_f, vf_f, rho_f, n_elem)
    if params.n_blades == 0 or (rpm_f == 0.0 and vf_f == 0.0):
        return PropPerf(
            thrust_n=0.0, torque_nm=0.0, power_w=0.0, rpm=rpm_f, v_forward=vf_f,
            thrust_g=0.0, efficiency_g_per_w=0.0, figure_of_merit=0.0,
            prop_efficiency=None, figure_of_merit_raw=0.0, converged=True,
        )
    chord_fn, twist_fn, camber, thickness, r_root_mm, r_tip_mm = _interp_geom(params)
    B = params.n_blades
    omega = rpm_f * 2.0 * math.pi / 60.0
    R = float(r_tip_mm) / 1000.0
    # Kinematic viscosity scales inversely with density at constant T (nu = mu/rho).
    # Keep bit-for-bit NU_AIR at default rho == RHO_AIR.
    nu = NU_AIR if rho_f == RHO_AIR else NU_AIR * (RHO_AIR / rho_f)
    edges = np.linspace(r_root_mm, r_tip_mm, n_elem + 1) / 1000.0   # element boundaries [m]
    T = 0.0
    Q = 0.0
    converged = True
    for i in range(n_elem):
        r = float(0.5 * (edges[i] + edges[i + 1]))
        dr = float(edges[i + 1] - edges[i])
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
        elem_converged = False
        for _ in range(60):                                 # BEM fixed-point iteration (a, a')
            Vax = vf_f + vi
            vth_m = 0.5 * vth                               # mean swirl through the disk
            Vt = max(U - vth_m, 0.05)                       # Vt = Ωr(1 − a′)
            phi = math.atan2(Vax, Vt)
            W2 = Vax * Vax + Vt * Vt
            alpha = beta - phi
            cl, cd, stalled, cl_cap = _section_aero(
                alpha, camber, re=math.sqrt(W2) * c / nu, thickness=thickness,
            )
            mach = math.sqrt(W2) / C_AIR
            cl, cd = _compressibility_cl_cd(
                cl, cd, mach, stalled=stalled, cl_cap=cl_cap
            )
            # Prandtl tip-loss factor (open propeller only; no root loss modelled)
            f = (B / 2.0) * (R - r) / max(r * math.sin(phi), 1e-4)
            F = max(0.15, (2.0 / math.pi) * math.acos(math.exp(-min(f, 20.0))))

            dT = 0.5 * rho_f * W2 * c * B * (cl * math.cos(phi) - cd * math.sin(phi))   # per unit span
            f_theta = 0.5 * rho_f * W2 * c * B * (cl * math.sin(phi) + cd * math.cos(phi))

            # Momentum: dT = 4π r ρ |Vax| vi F  (per unit span) -> update vi
            # abs(Vax) keeps the fixed-point stable when windmilling (Vax may change sign).
            denom_t = 4.0 * math.pi * r * rho_f * max(abs(Vax), 0.1) * F
            vi_new = dT / denom_t if denom_t > 0 else vi
            # Negative induced velocity is physical in the braking / windmill regime (§20.2).
            vi_new = max(-30.0, min(vi_new, 60.0))

            # Angular momentum: fθ = (ρ |Vax| 2π r) ΔVθ (per unit span), with ΔVθ ≈ vth (0 → far wake)
            denom_th = rho_f * max(abs(Vax), 0.1) * 2.0 * math.pi * r
            vth_new = f_theta / denom_th if denom_th > 0 else vth
            vth_new = max(0.0, min(vth_new, 1.9 * U))       # a′ < 0.95 (since vth ≈ 2 a′ Ωr)

            if abs(vi_new - vi) < 1e-3 and abs(vth_new - vth) < 1e-3:
                elem_converged = True
                break
            vi = 0.5 * vi + 0.5 * vi_new                    # relax
            vth = 0.5 * vth + 0.5 * vth_new

        converged = converged and elem_converged
        dQ = f_theta * r                                    # per unit span
        T += dT * dr
        Q += dQ * dr
    # Do not clamp T≥0: UIUC advance-ratio sweeps include windmill (CT_meas < 0). Clamping
    # zeroed those points and inflated C_T(J) RMS (§20.2 / Audit #3).
    P = float(Q * omega)
    A = math.pi * R * R
    fm = float((T ** 1.5 / math.sqrt(2.0 * rho_f * A)) / P) if (P > 0 and T > 0) else 0.0
    prop_eff = float(T * vf_f / P) if (vf_f > 0 and P > 0) else None
    # Full precision here (#50); cockpit/export format for display.
    thrust_g = float(T / G * 1000.0)
    return PropPerf(
        thrust_n=float(T), torque_nm=float(Q), power_w=P, rpm=rpm_f, v_forward=vf_f,
        thrust_g=thrust_g,
        efficiency_g_per_w=float(thrust_g / P) if P > 0 else 0.0,
        figure_of_merit=float(min(fm, 1.0)), prop_efficiency=prop_eff,
        figure_of_merit_raw=fm, converged=bool(converged),
    )


# --- spliced from transcript edit-history (recovery 2026-09-12) ---
def _compressibility_cl_cd(
    cl: float,
    cd: float,
    mach: float,
    *,
    stalled: bool = False,
    cl_cap: float | None = None,
) -> tuple[float, float]:
    """Prandtl–Glauert on attached Cl, capped at the polar peak; stalled Cl unchanged.

    Soft wave-drag rise past M≈0.7 applies either way. Mach is clamped to [0, 0.95].
    """
    m = max(0.0, min(float(mach), 0.95))
    beta = math.sqrt(max(1e-6, 1.0 - m * m))
    if stalled:
        cl_c = float(cl)
    else:
        cl_c = float(cl) / beta
        if cl_cap is not None:
            limit = abs(float(cl_cap))
            cl_c = math.copysign(min(abs(cl_c), limit), cl_c)
    cd_c = float(cd)
    if m > 0.70:
        cd_c = cd_c + 0.02 * ((m - 0.70) / 0.25) ** 2
    return cl_c, cd_c


def _cl_cd_analytic(alpha_rad: float, camber: float, re: float | None = None):
    """Analytic cambered-airfoil polar (high-Re or Re-aware trends)."""
    cl, cd, _stalled, _cap = _analytic_section(alpha_rad, camber, re)
    return cl, cd


def _analytic_section(
    alpha_rad: float, camber: float, re: float | None = None
) -> tuple[float, float, bool, float]:
    a_deg = math.degrees(alpha_rad)
    cl_max, cd0, stall_deg, slope = 1.4, 0.012, 14.0, 2.0 * math.pi
    if re is not None:
        r = max(float(re), 5000.0)
        f = math.log10(r / 20000.0)
        cl_max = max(0.80, min(1.5, 0.95 + 0.30 * f))
        stall_deg = max(8.0, min(15.0, 10.0 + 3.0 * f))
        cd0 = max(0.010, 0.008 + 5.0 / math.sqrt(r))
        slope = 2.0 * math.pi * max(0.75, min(1.0, 0.88 + 0.12 * f))
    cl_lin = slope * camber + slope * alpha_rad
    cl = max(-cl_max, min(cl_max, cl_lin))
    if a_deg > stall_deg:
        cl *= max(0.55, 1.0 - (a_deg - stall_deg) * 0.03)
    stalled = a_deg > stall_deg or abs(cl_lin) >= cl_max
    return cl, cd0, stalled, cl_max
