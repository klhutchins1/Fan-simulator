"""Optional NeuralFoil polar backend for BEM / BEMT (§19.15 / §20.2).

Maps station (camber, thickness) to a NACA 4-digit section and evaluates Cl/Cd via
NeuralFoil. Requires ``uv sync --extra neuralfoil``. Default BEMT path stays on the
vendored UIUC tables; call :func:`set_polar_backend` or set ``FANSIM_POLAR_BACKEND=neuralfoil``.

**α coverage (proven engineering 360°):**

- **NeuralFoil-native** band: ``ALPHA_NF_MIN``…``ALPHA_NF_MAX`` (±25°). Raw NeuralFoil
  values are used here (camber asymmetry preserved).
- **Outside that band** through ±180°: Viterna–Corrigan post-stall extrapolation
  (NREL / AeroDyn style) matched at the NF band edge, with reverse-flow mirroring
  near ±180° back onto the NF band. Flat-plate asymptote ``CD_MAX`` at ±90°.

Raw NeuralFoil alone returns finite numbers past ±25° but is **not** physical there
(e.g. Cd ≪ 1 at 90°) — do not treat unextended NF as a 360° claim.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

_MODEL_SIZE = "medium"
# NeuralFoil-native evaluation band (trusted attached / near-stall).
ALPHA_NF_MIN = -25.0
ALPHA_NF_MAX = 25.0
# Full-circle wrap targets after Viterna extension (§20.2 proven 360°).
ALPHA_DEG_MIN = -180.0
ALPHA_DEG_MAX = 180.0
# Soft thin-airfoil stall onset used for stalled / cl_cap parity with the table path.
STALL_ALPHA_DEG = 12.0
# Viterna aspect-ratio proxy → CD_MAX = 1.11 + 0.018·AR (NREL AirfoilPrep default form).
VITERNA_AR = 10.0
CD_MAX = 1.11 + 0.018 * VITERNA_AR


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


def _wrap_alpha_deg(alpha_deg: float) -> float:
    """Wrap to (-180, 180]."""
    x = ((float(alpha_deg) + 180.0) % 360.0) - 180.0
    return 180.0 if x == -180.0 else x


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


def _viterna_coeffs(
    alpha_match_deg: float, cl_match: float, cd_match: float, cd_max: float
) -> tuple[float, float, float, float]:
    """Viterna–Corrigan A1, A2, B1, B2 matched at ``alpha_match_deg`` (> 0)."""
    a = math.radians(float(alpha_match_deg))
    s, c = math.sin(a), math.cos(a)
    if abs(c) < 1e-9:
        raise ValueError("Viterna match angle must be away from ±90°")
    a1 = float(cd_max) / 2.0
    b1 = float(cd_max)
    a2 = (float(cl_match) - float(cd_max) * s * c) * s / (c * c)
    b2 = (float(cd_match) - float(cd_max) * s * s) / c
    return a1, a2, b1, b2


def _viterna_eval(
    alpha_deg: float, a1: float, a2: float, b1: float, b2: float
) -> tuple[float, float]:
    a = math.radians(float(alpha_deg))
    s, c = math.sin(a), math.cos(a)
    if abs(s) < 1e-12:
        return 0.0, max(b2 * c, 1e-4)
    cl = a1 * math.sin(2.0 * a) + a2 * c * c / s
    cd = b1 * s * s + b2 * c
    return float(cl), max(float(cd), 1e-4)


def _extend_positive(
    alpha_abs_deg: float,
    naca: str,
    re_key: float,
    model_size: str,
    cl_match: float,
    cd_match: float,
) -> tuple[float, float]:
    """Cl/Cd for α in (ALPHA_NF_MAX, 180] using Viterna + reverse NF mirror."""
    a = float(alpha_abs_deg)
    am = ALPHA_NF_MAX
    ah = 180.0 - am
    if a <= 90.0:
        return _viterna_eval(a, *_viterna_coeffs(am, cl_match, cd_match, CD_MAX))
    if a < ah:
        return _viterna_eval(a, *_viterna_coeffs(ah, -cl_match, cd_match, CD_MAX))
    # Reverse-flow trust mirror onto NeuralFoil band: α' = α − 180 ∈ [-AM, 0].
    ap = a - 180.0
    return _nf_cl_cd(naca, round(ap, 2), re_key, model_size)


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
    a_deg = _wrap_alpha_deg(math.degrees(float(alpha_rad)))
    re_c = max(1.0e4, min(1.0e6, float(re)))
    naca = naca4_name(camber, thickness)
    re_key = round(math.log10(re_c), 3)
    try:
        if ALPHA_NF_MIN <= a_deg <= ALPHA_NF_MAX:
            cl, cd = _nf_cl_cd(naca, round(a_deg, 2), re_key, model_size)
        else:
            cl_m, cd_m = _nf_cl_cd(naca, round(ALPHA_NF_MAX, 2), re_key, model_size)
            cl, cd = _extend_positive(abs(a_deg), naca, re_key, model_size, cl_m, cd_m)
            if a_deg < 0.0:
                cl = -cl
        # cl_cap at stall-onset α so Prandtl–Glauert in bemt stays bounded like the table path.
        stall_a = math.copysign(STALL_ALPHA_DEG, a_deg if a_deg != 0.0 else 1.0)
        cl_stall, _cd_stall = _nf_cl_cd(naca, round(stall_a, 2), re_key, model_size)
    except Exception:  # noqa: BLE001 - polar miss must fall through to tables/analytic
        return None
    stalled = abs(a_deg) >= STALL_ALPHA_DEG
    cl_cap = abs(cl_stall)
    return cl, cd, stalled, cl_cap
