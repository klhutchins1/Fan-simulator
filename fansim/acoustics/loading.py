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

import numpy as np

# Calibrated on the 7 opt_noise finalists: LBM_band ~ c0*n_blades + c1*thrust_per_blade + c2.
# (thrust_per_blade in N; the negative c1 is a small-n confound with n_blades -- see module docstring.)
DEFAULT_COEFFS = (2.263, -74.4, 35.55)


def loading_noise_proxy(n_blades: int, thrust_per_blade_n: float, coeffs=DEFAULT_COEFFS) -> float:
    """LBM-band-dB-equivalent loading-noise estimate from cheap RANS scalars (lower = quieter).

    n_blades: blade count. thrust_per_blade_n: RANS thrust / n_blades (N). Relative metric for
    ranking designs; use as a MINIMIZE objective. Cheaper than Proudman (no field reconstruction).
    """
    c0, c1, c2 = coeffs
    return c0 * float(n_blades) + c1 * float(thrust_per_blade_n) + c2


def loading_proxy_from_rans(n_blades: int, thrust_n: float, coeffs=DEFAULT_COEFFS) -> float:
    """Convenience: proxy from total RANS thrust (divides by n_blades internally)."""
    return loading_noise_proxy(n_blades, thrust_n / max(n_blades, 1), coeffs)


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
    lam2 = float(derate) * float(derate)
    return loading_proxy_from_rans(n_blades, float(thrust_n_at_rated) * lam2, coeffs)


def calibrate(n_blades, thrust_per_blade, lbm_band) -> tuple[float, float, float]:
    """Refit the (c0, c1, c2) coefficients to new (n_blades, thrust_per_blade) -> LBM_band data.

    Pass arrays of equal length (more LBM-scored designs = a more robust proxy). Returns the fitted
    coefficients; feed them back via the ``coeffs`` argument. Needs >= 3 points.
    """
    nb = np.asarray(n_blades, float)
    tpb = np.asarray(thrust_per_blade, float)
    y = np.asarray(lbm_band, float)
    if len(nb) < 3:
        raise ValueError("need >= 3 calibration points")
    A = np.column_stack([nb, tpb, np.ones(len(nb))])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(coef[0]), float(coef[1]), float(coef[2])
