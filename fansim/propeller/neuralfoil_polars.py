"""Optional NeuralFoil polar backend for BEM / BEMT (§19.15 / §20.2).

Maps station (camber, thickness) to a NACA 4-digit section and evaluates Cl/Cd via
NeuralFoil. Requires ``uv sync --extra neuralfoil``. Default BEMT path stays on the
vendored UIUC tables; call :func:`set_polar_backend` or set ``FANSIM_POLAR_BACKEND=neuralfoil``.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

_MODEL_SIZE = "medium"


def neuralfoil_available() -> bool:
    try:
        import neuralfoil  # noqa: F401
        import aerosandbox  # noqa: F401
        return True
    except ImportError:
        return False


def naca4_name(camber: float, thickness: float, *, camber_pos: float = 0.4) -> str:
    """NACA 4-digit name from max-camber / thickness fractions (camber_pos fixed at 0.4)."""
    m = int(round(max(0.0, min(0.09, float(camber))) * 100.0))
    p = int(round(max(0.1, min(0.9, float(camber_pos))) * 10.0))
    tt = int(round(max(0.01, min(0.40, float(thickness))) * 100.0))
    return f"naca{m}{p}{tt:02d}"


@lru_cache(maxsize=8192)
def _nf_cl_cd(naca: str, alpha_deg: float, re_log10: float, model_size: str) -> tuple[float, float]:
    import aerosandbox as asb
    import neuralfoil as nf

    af = asb.Airfoil(naca)
    out = nf.get_aero_from_airfoil(
        af, alpha=float(alpha_deg), Re=10.0 ** float(re_log10), model_size=model_size,
    )
    cl = float(np.asarray(out["CL"]).ravel()[0])
    cd = float(np.asarray(out["CD"]).ravel()[0])
    return cl, max(cd, 1e-4)


def section_neuralfoil(
    alpha_rad: float,
    camber: float,
    re: float | None,
    thickness: float = 0.12,
    *,
    model_size: str = _MODEL_SIZE,
) -> tuple[float, float, bool, float] | None:
    """Return `(cl, cd, stalled, cl_cap)` or ``None`` if NeuralFoil is unavailable / fails."""
    if re is None or float(re) <= 0.0 or not neuralfoil_available():
        return None
    a_deg = max(-15.0, min(20.0, math.degrees(float(alpha_rad))))
    re_c = max(1.0e4, min(1.0e6, float(re)))
    try:
        cl, cd = _nf_cl_cd(
            naca4_name(camber, thickness),
            round(a_deg, 2),
            round(math.log10(re_c), 3),
            model_size,
        )
    except Exception:  # noqa: BLE001 - polar miss must fall through to tables/analytic
        return None
    return cl, cd, False, abs(cl) + 0.5
