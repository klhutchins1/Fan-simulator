"""RANS aeroacoustic noise proxies: Proudman (broadband, volumetric) and Curle (surface).

These reduce a steady RANS field (turbulent kinetic energy k, specific dissipation rate omega or
epsilon, wall pressure fluctuations) to a single sound-power level in dB. They are approximate and
best used for RELATIVE ranking of designs -- the same role the LBM relative noise metric plays, but
free per candidate. Absolute levels carry model-constant and turbulence-model uncertainty.

References (docs/bibliography.md):
- Proudman, I. (1952). Proc. R. Soc. Lond. A 214, 119-132.  (isotropic-turbulence acoustic power)
- Sarkar, S. & Hussaini, M. Y. (1993).  (rescaled Proudman constant alpha ~ 0.1)
- Curle, N. (1955). Proc. R. Soc. Lond. A 231, 505-514.     (surface-dipole radiated power)
"""

from __future__ import annotations

import math

import numpy as np

# physical constants / model constants
# Use the same default air density as the CFD/AMCA metrics (screening-level consistency).
from fansim.physics.air import C0_AIR
from fansim.physics.air import RHO_AMCA as RHO_AIR

CMU = 0.09             # k-omega/k-epsilon Cmu
ALPHA_PROUDMAN = 0.1   # rescaled Proudman constant (Sarkar & Hussaini 1993)
W_REF = 1e-12          # reference acoustic power, W (=> dB re 1 pW)


def _positive_finite(val: float, name: str) -> float:
    v = float(val)
    if not (math.isfinite(v) and v > 0.0):
        raise ValueError(f"{name} must be finite and > 0, got {val!r}")
    return v


def epsilon_from_komega(k, omega, cmu: float = CMU):
    """Turbulent dissipation rate epsilon [m^2/s^3] from k and specific rate omega (k-omega SST).

    epsilon = Cmu * max(k, 0) * max(omega, 0). Clamps numerical undershoot so acoustic
    power density stays non-negative (matching :func:`turbulent_mach`).
    """
    cmu_f = float(cmu)
    if not (math.isfinite(cmu_f) and cmu_f >= 0.0):
        raise ValueError(f"cmu must be finite and >= 0, got {cmu!r}")
    return cmu_f * np.maximum(np.asarray(k, float), 0.0) * np.maximum(np.asarray(omega, float), 0.0)


def turbulent_mach(k, c0: float = C0_AIR):
    """Turbulent Mach number M_t = sqrt(2k)/c0 (k = turbulent kinetic energy, m^2/s^2)."""
    c0_f = _positive_finite(c0, "c0")
    return np.sqrt(2.0 * np.maximum(np.asarray(k, float), 0.0)) / c0_f


def proudman_power_density(k, epsilon, rho: float = RHO_AIR, c0: float = C0_AIR,
                           alpha: float = ALPHA_PROUDMAN):
    """Proudman acoustic power per unit volume [W/m^3] from isotropic turbulence.

        P_A = alpha * rho * max(epsilon, 0) * M_t^5,   M_t = sqrt(2k)/c0

    The 5th-power Mach dependence makes this a steep function of turbulence intensity -- it flags
    where broadband noise is generated (blade wakes, tip vortices). Pointwise; integrate over cell
    volumes for total power (see proudman_swl). Negative ``epsilon`` numerical undershoot is
    clamped to 0 so power density stays non-negative (#124).
    """
    rho_f = _positive_finite(rho, "rho")
    c0_f = _positive_finite(c0, "c0")
    alpha_f = float(alpha)
    if not (math.isfinite(alpha_f) and alpha_f >= 0.0):
        raise ValueError(f"alpha must be finite and >= 0, got {alpha!r}")
    mt = turbulent_mach(k, c0_f)
    eps = np.maximum(np.asarray(epsilon, float), 0.0)
    return alpha_f * rho_f * eps * mt**5


def sound_power_level(power_watts, w_ref: float = W_REF) -> float:
    """Sound power level L_W = 10 log10(W / W_ref) in dB re 1 pW.

    Returns ``-inf`` for finite ``W <= 0``, ``nan`` for ``NaN`` input (never silently ``-inf``),
    and ``+inf`` for ``+inf`` input (#124).
    """
    w_ref_f = _positive_finite(w_ref, "w_ref")
    w = float(np.sum(power_watts))
    if math.isnan(w):
        return float("nan")
    if w <= 0.0:
        return float("-inf")
    if math.isinf(w):
        return float("inf")
    return float(10.0 * math.log10(w / w_ref_f))


def proudman_swl(k, epsilon, cell_volumes, rho: float = RHO_AIR, c0: float = C0_AIR,
                 alpha: float = ALPHA_PROUDMAN) -> float:
    """Total Proudman broadband sound power level [dB] = integral of P_A over the volume.

    k, epsilon, cell_volumes are per-cell arrays of equal length (from a RANS solution). Returns the
    domain sound-power level in dB re 1 pW. Compare designs relatively; do not read as absolute dBA.
    """
    pd = proudman_power_density(k, epsilon, rho, c0, alpha)
    total = np.asarray(pd, float) * np.asarray(cell_volumes, float)
    return sound_power_level(total)


def curle_surface_swl(
    dpdt_ms,
    areas,
    rho: float = RHO_AIR,
    c0: float = C0_AIR,
    *,
    corr_area_m2: float | None = None,
) -> float:
    """Curle surface-dipole power-like index [dB] from wall pressure time-derivative fluctuations.

    NOTE (Audit #6, #124): when ``corr_area_m2 is None`` (default), the integral omits the eddy
    correlation area ``A_c``, so the linear value is dimensionally ``W/m^2`` (use for RELATIVE
    ranking only). Pass a positive ``corr_area_m2`` [m^2] to multiply by ``A_c`` and obtain true
    radiated power in watts ``[W]``:

        W = A_c / (12 pi rho c0^3) * integral_S <(dp/dt)^2> dS

    ``dpdt_ms`` is the per-face mean-square wall-pressure time derivative <(dp/dt)^2> [Pa^2/s^2];
    ``areas`` the per-face areas [m^2]. When only RANS turbulence is available, estimate
    <(dp/dt)^2> ~ (Cp * rho * k)^2 * omega^2 via ``curle_dpdt_estimate`` below. Relative metric.
    """
    rho_f = _positive_finite(rho, "rho")
    c0_f = _positive_finite(c0, "c0")
    ac = 1.0 if corr_area_m2 is None else _positive_finite(corr_area_m2, "corr_area_m2")
    integrand = np.asarray(dpdt_ms, float) * np.asarray(areas, float)
    w = ac * float(np.sum(integrand)) / (12.0 * math.pi * rho_f * c0_f**3)
    return sound_power_level(w)


def curle_dpdt_estimate(k, omega, rho: float = RHO_AIR, cp: float = 1.0):
    """Estimate wall <(dp/dt)^2> [Pa^2/s^2] from RANS k, omega for the Curle proxy.

    Turbulent pressure fluctuation scale p' ~ cp * rho * k; characteristic frequency ~ omega
    (= epsilon/(Cmu k)). Hence <(dp/dt)^2> ~ (cp rho k)^2 * omega^2. Heuristic -- cp absorbs the
    correlation constant and is calibrated once against a measured or LBM case.

    NOTE (#124): in k-omega SST near-wall cells, wall ``omega`` scales as ``1 / y_1^2``, so
    ``omega^2 ~ y_1^-4`` carries strong first-cell ``y+`` mesh sensitivity. Only compare cases
    built with matched near-wall mesh resolution.
    """
    rho_f = _positive_finite(rho, "rho")
    cp_f = float(cp)
    if not math.isfinite(cp_f):
        raise ValueError(f"cp must be finite, got {cp!r}")
    k_arr = np.asarray(k, float)
    return (cp_f * rho_f * k_arr) ** 2 * np.asarray(omega, float) ** 2
