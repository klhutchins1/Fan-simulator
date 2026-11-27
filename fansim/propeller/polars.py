"""Vendored low-Re airfoil polars for BEM / BEMT (UIUC LSATs–style tables).

CSV files live under ``fansim/data/polars/``. Lookup interpolates α linearly and Re in
log10 between neighboring tables of the camber+thickness-mapped family. Returns None when
tables are missing so callers can fall back to the analytic ``_cl_cd``.
"""

from __future__ import annotations

import itertools
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

POLAR_DIR = Path(__file__).resolve().parent.parent / "data" / "polars"

# (family name, design camber, design thickness) — nearest by
# abs(c − c*) + 0.5 * abs(t − t*) (thickness weight 0.5 so camber dominates mild mismatches)
_FAMILIES = (
    ("naca0012", 0.0, 0.12),
    ("naca2412", 0.02, 0.12),
    ("naca4412", 0.04, 0.12),
    ("e387", 0.037, 0.09),
    ("sd7032", 0.025, 0.10),
    ("s1223", 0.085, 0.12),
)

_RE_TAG = {
    40000.0: "4e4",
    80000.0: "8e4",
    160000.0: "1.6e5",
}

_DEFAULT_THICKNESS = 0.12


@lru_cache(maxsize=128)
def family_for_camber(camber: float, thickness: float = _DEFAULT_THICKNESS) -> str:
    """Nearest vendored polar family for section camber and thickness fractions."""
    c = float(camber)
    t = float(thickness) if thickness is not None else _DEFAULT_THICKNESS
    if not (math.isfinite(c) and math.isfinite(t)):
        raise ValueError(f"camber and thickness must be finite, got camber={camber!r}, thickness={thickness!r}")
    return min(
        _FAMILIES,
        key=lambda fct: abs(c - fct[1]) + 0.5 * abs(t - fct[2]),
    )[0]


@lru_cache(maxsize=32)
def _polar_re_levels(family: str) -> tuple[float, ...]:
    """Sorted Reynolds keys for a loaded polar family (avoids per-call sort in BEM hot loop)."""
    tables = load_polar_family(family)
    return tuple(sorted(tables.keys()))


def _parse_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.genfromtxt(path, delimiter=",", names=True)
    if data.size == 0:
        raise ValueError(f"polar CSV is empty: {path}")
    alpha = np.atleast_1d(np.asarray(data["alpha_deg"], float))
    cl = np.atleast_1d(np.asarray(data["cl"], float))
    cd = np.atleast_1d(np.asarray(data["cd"], float))
    if not (np.all(np.isfinite(alpha)) and np.all(np.isfinite(cl)) and np.all(np.isfinite(cd))):
        raise ValueError(f"polar CSV contains non-finite values: {path}")
    if alpha.size > 1 and not bool(np.all(np.diff(alpha) > 0.0)):
        raise ValueError(f"polar CSV alpha_deg must be strictly increasing: {path}")
    return alpha, cl, cd


@lru_cache(maxsize=32)
def load_polar_family(name: str) -> dict[float, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Map Reynolds number → (alpha_deg, cl, cd) arrays for one family."""
    out: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for re, tag in _RE_TAG.items():
        path = POLAR_DIR / f"{name}_re{tag}.csv"
        if path.is_file():
            out[re] = _parse_csv(path)
    return out


def _interp_alpha(alpha_deg: float, a: np.ndarray, cl: np.ndarray, cd: np.ndarray):
    """Linear α interp; clamp to table edges."""
    a_deg = float(alpha_deg)
    if a_deg <= a[0]:
        return float(cl[0]), float(cd[0])
    if a_deg >= a[-1]:
        return float(cl[-1]), float(cd[-1])
    return (
        float(np.interp(a_deg, a, cl)),
        float(np.interp(a_deg, a, cd)),
    )


_STALL_TOL = 1e-4


def _curve_limits(alphas: np.ndarray, cls: np.ndarray) -> tuple[float, float | None, float, float]:
    """Positive stall angle, negative stall angle or None, peak Cl, trough Cl."""
    cl_peak = float(np.max(cls))
    cl_trough = float(np.min(cls))
    pos = np.flatnonzero(cls >= cl_peak - _STALL_TOL)
    a_pos = float(alphas[int(pos[0])])
    a_neg: float | None = None
    if cl_trough < 0.0:
        neg = np.flatnonzero(cls <= cl_trough + _STALL_TOL)
        a_neg = float(alphas[int(neg[-1])])
    return a_pos, a_neg, cl_peak, cl_trough


def _blend_limits(
    lo: tuple[float, float | None, float, float],
    hi: tuple[float, float | None, float, float],
    w: float,
) -> tuple[float, float | None, float, float]:
    a_pos = (1.0 - w) * lo[0] + w * hi[0]
    if lo[1] is None or hi[1] is None:
        a_neg = None
    else:
        a_neg = (1.0 - w) * lo[1] + w * hi[1]
    cl_peak = (1.0 - w) * lo[2] + w * hi[2]
    cl_trough = (1.0 - w) * lo[3] + w * hi[3]
    return a_pos, a_neg, cl_peak, cl_trough


def _stall_from_limits(
    alpha_deg: float,
    cl: float,
    a_pos: float,
    a_neg: float | None,
    cl_peak: float,
    cl_trough: float,
) -> tuple[bool, float]:
    stalled = float(alpha_deg) >= a_pos or (
        a_neg is not None and float(alpha_deg) <= a_neg
    )
    cap = abs(cl_trough) if cl < 0.0 else cl_peak
    return stalled, float(cap)


@lru_cache(maxsize=64)
def _polar_curve_limits(family: str, re_key: float) -> tuple[float, float | None, float, float]:
    """Cached stall-angle and Cl-bound summary for one `(family, Re)` table."""
    alphas, cls, _cds = load_polar_family(family)[re_key]
    return _curve_limits(alphas, cls)


def section_table(
    alpha_rad: float,
    camber: float,
    re: float,
    thickness: float = _DEFAULT_THICKNESS,
) -> tuple[float, float, bool, float] | None:
    """Table `(cl, cd, stalled, cl_cap)` or None when `cl_cd_table` would miss."""
    if re is None:
        return None
    r = float(re)
    a_rad = float(alpha_rad)
    c_val = float(camber)
    t_val = float(thickness) if thickness is not None else _DEFAULT_THICKNESS
    if not (math.isfinite(r) and math.isfinite(a_rad) and math.isfinite(c_val) and math.isfinite(t_val)):
        return None
    fam = family_for_camber(c_val, t_val)
    tables = load_polar_family(fam)
    if not tables:
        return None
    a_deg = math.degrees(a_rad)
    res = _polar_re_levels(fam)
    if r < res[0]:
        return None
    if r == res[0] or r >= res[-1]:
        key = res[0] if r == res[0] else res[-1]
        alphas, cls, cds = tables[key]
        cl, cd = _interp_alpha(a_deg, alphas, cls, cds)
        a_pos, a_neg, cl_peak, cl_trough = _polar_curve_limits(fam, key)
        stalled, cap = _stall_from_limits(a_deg, cl, a_pos, a_neg, cl_peak, cl_trough)
        return cl, cd, stalled, cap
    for lo, hi in itertools.pairwise(res):
        if lo <= r <= hi:
            w = (math.log10(r) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
            a0, cl0, cd0 = tables[lo]
            a1, cl1, cd1 = tables[hi]
            c0, d0 = _interp_alpha(a_deg, a0, cl0, cd0)
            c1, d1 = _interp_alpha(a_deg, a1, cl1, cd1)
            cl = c0 * (1.0 - w) + c1 * w
            cd = d0 * (1.0 - w) + d1 * w
            limits = _blend_limits(_polar_curve_limits(fam, lo), _polar_curve_limits(fam, hi), w)
            stalled, cap = _stall_from_limits(a_deg, cl, *limits)
            return cl, cd, stalled, cap
    return None


def cl_cd_table(
    alpha_rad: float,
    camber: float,
    re: float,
    thickness: float = _DEFAULT_THICKNESS,
) -> tuple[float, float] | None:
    """Table Cl, Cd at (α, Re) for the camber+thickness-mapped family, or None if unavailable."""
    row = section_table(alpha_rad, camber, re, thickness=thickness)
    if row is None:
        return None
    return row[0], row[1]


def clear_polar_cache() -> None:
    load_polar_family.cache_clear()
    family_for_camber.cache_clear()
    _polar_re_levels.cache_clear()
    _polar_curve_limits.cache_clear()
