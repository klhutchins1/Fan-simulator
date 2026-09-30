"""Optional NeuralFoil polar backend for BEM / BEMT (§19.15 / §20.2).

Maps station (camber, thickness) to a NACA 4-digit section and evaluates Cl/Cd via
NeuralFoil. Requires ``uv sync --extra neuralfoil``. Default BEMT path stays on the
vendored UIUC tables; call :func:`set_polar_backend` or set ``FANSIM_POLAR_BACKEND=neuralfoil``.

Supported geometric α band is documented as ``ALPHA_DEG_MIN``…``ALPHA_DEG_MAX`` (not a
proven 360° claim). Outside that band α is clamped; stall / ``cl_cap`` mirror the table
path so compressibility capping in ``_compressibility_cl_cd`` still applies.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

_MODEL_SIZE = "medium"
# Documented NeuralFoil evaluation band for this backend (widen from the old −15…20).
# Not a 360° coverage claim — see roadmap §20.2.
ALPHA_DEG_MIN = -25.0
ALPHA_DEG_MAX = 25.0
# Soft thin-airfoil stall onset used for stalled / cl_cap parity with the table path.
STALL_ALPHA_DEG = 12.0


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
    a_deg = max(ALPHA_DEG_MIN, min(ALPHA_DEG_MAX, math.degrees(float(alpha_rad))))
    re_c = max(1.0e4, min(1.0e6, float(re)))
    naca = naca4_name(camber, thickness)
    re_key = round(math.log10(re_c), 3)
    try:
        cl, cd = _nf_cl_cd(naca, round(a_deg, 2), re_key, model_size)
        # cl_cap at stall-onset α so Prandtl–Glauert in bemt stays bounded like the table path.
        stall_a = math.copysign(STALL_ALPHA_DEG, a_deg if a_deg != 0.0 else 1.0)
        cl_stall, _cd_stall = _nf_cl_cd(naca, round(stall_a, 2), re_key, model_size)
    except Exception:  # noqa: BLE001 - polar miss must fall through to tables/analytic
        return None
    stalled = abs(a_deg) >= STALL_ALPHA_DEG
    cl_cap = abs(cl_stall)
    return cl, cd, stalled, cl_cap
