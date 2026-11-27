"""Cheap LOADING-noise proxy, calibrated against LBM dipole scores.

The Proudman broadband proxy (proxies.py) ranks fan noise POORLY vs the higher-fidelity LBM
control-volume dipole (measured Spearman rho ~ 0.21 on the opt_noise finalists) because it captures
turbulent-broadband noise, not the unsteady-force DIPOLE (loading) noise that dominates a low-speed
fan. Empirically, the LBM band dB(A) is predicted far better by cheap quantities already in every
RANS result: blade count and per-blade thrust. This module packages a linear proxy calibrated to
those -- computed from RANS scalars alone (no field reconstruction), so it is even cheaper than
Proudman and a better stand-in for the objective.

HONESTY: calibrated on only 7 LBM points (opt_noise Pareto). In-sample rho 0.82 / R2 0.81, but
leave-one-out rho ~ 0.54 -- a real improvement over Proudman (0.21) yet clearly overfit-limited by n.
The robust signal is blade count (rho 0.86); the per-blade term is weaker and partly confounded.
Recalibrate with `calibrate(...)` as more designs are LBM-scored. Output is an LBM-band-dB-equivalent
(relative ranking metric), not calibrated dB(A).
"""

from __future__ import annotations

import math

import numpy as np

# Physically signed default coefficients (#122, prereg 2026-11-26-loading-proxy-positive-slope):
# LBM_band ~ c0*n_blades + c1*thrust_per_blade + c2.
# Keeps the empirical blade-count slope c0 = 2.263 dB/blade from the 7 opt_noise finalists
# (Spearman rho = 0.86), replaces the confounded small-n c1 = -74.4 with a physically positive
# loading sensitivity c1 = +100.0 dB/N so higher blade thrust increases predicted noise and
# motor derating strictly reduces it, and anchors nominal (7 blades, 0.01 N/blade) near 50.8 dB.
DEFAULT_COEFFS = (2.263, 100.0, 34.0)


def loading_noise_proxy(n_blades: int, thrust_per_blade_n: float, coeffs=DEFAULT_COEFFS) -> float:
    """LBM-band-dB-equivalent loading-noise estimate from cheap RANS scalars (lower = quieter).

    n_blades: blade count. thrust_per_blade_n: RANS thrust / n_blades (N). Relative metric for
    ranking designs; use as a MINIMIZE objective. Cheaper than Proudman (no field reconstruction).
    """
    nb = int(n_blades)
    tpb = float(thrust_per_blade_n)
    if nb < 1:
        raise ValueError(f"n_blades must be >= 1, got {n_blades!r}")
    if not math.isfinite(tpb):
        raise ValueError(f"thrust_per_blade_n must be finite, got {thrust_per_blade_n!r}")
    c0, c1, c2 = coeffs
    return float(c0 * float(nb) + c1 * tpb + c2)


def loading_proxy_from_rans(n_blades: int, thrust_n: float, coeffs=DEFAULT_COEFFS) -> float:
    """Convenience: proxy from total RANS thrust (divides by n_blades internally)."""
    nb = int(n_blades)
    thrust = float(thrust_n)
    if nb < 1:
        raise ValueError(f"n_blades must be >= 1, got {n_blades!r}")
    if not math.isfinite(thrust):
        raise ValueError(f"thrust_n must be finite, got {thrust_n!r}")
    return loading_noise_proxy(nb, thrust / nb, coeffs)


def loading_proxy_operating(
    n_blades: int,
    thrust_n_at_rated: float,
    derate: float,
    coeffs=DEFAULT_COEFFS,
) -> float:
    """Loading proxy at the RPM the motor actually holds (O7 / #53).

    RANS free-air thrust is at rated/target RPM. Fan affinity: thrust ∝ λ² with
    λ = actual_rpm / rated_rpm (``derate`` ≤ 1). Scale thrust before the proxy so
    motor-limited designs are not ranked on rated-RPM thrust.
    """
    d = float(derate)
    if not (math.isfinite(d) and d >= 0.0):
        raise ValueError(f"derate must be finite and >= 0, got {derate!r}")
    lam2 = d * d
    return loading_proxy_from_rans(n_blades, float(thrust_n_at_rated) * lam2, coeffs)


def calibrate(
    n_blades,
    thrust_per_blade,
    lbm_band,
    *,
    non_negative: bool = False,
) -> tuple[float, float, float]:
    """Refit the (c0, c1, c2) coefficients to new (n_blades, thrust_per_blade) -> LBM_band data.

    Pass arrays of equal length (more LBM-scored designs = a more robust proxy). Returns the fitted
    coefficients; feed them back via the ``coeffs`` argument. Needs >= 3 points. Pass
    ``non_negative=True`` to constrain ``c0 >= 0, c1 >= 0`` (free intercept ``c2``) so small-n
    collinearity cannot invert the physical blade-count or thrust-loading sign (#122).
    """
    nb = np.asarray(n_blades, float)
    tpb = np.asarray(thrust_per_blade, float)
    y = np.asarray(lbm_band, float)
    if nb.ndim != 1 or tpb.ndim != 1 or y.ndim != 1 or not (len(nb) == len(tpb) == len(y)):
        raise ValueError("n_blades, thrust_per_blade, and lbm_band must be 1-D arrays of equal length")
    if len(nb) < 3:
        raise ValueError("need >= 3 calibration points")
    if not (np.all(np.isfinite(nb)) and np.all(np.isfinite(tpb)) and np.all(np.isfinite(y))):
        raise ValueError("calibration inputs must be finite")
    A = np.column_stack([nb, tpb, np.ones(len(nb))])
    if non_negative:
        from scipy.optimize import lsq_linear

        res = lsq_linear(A, y, bounds=([0.0, 0.0, -np.inf], [np.inf, np.inf, np.inf]))
        coef = res.x
    else:
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[0]), float(coef[1]), float(coef[2])
