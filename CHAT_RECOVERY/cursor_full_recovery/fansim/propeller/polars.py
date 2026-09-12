"""Vendored low-Re airfoil polars for BEM / BEMT (UIUC LSATs–style tables).

CSV files live under ``fansim/data/polars/``. Lookup interpolates α linearly and Re in
log10 between neighboring tables of the camber+thickness-mapped family. Returns None when
tables are missing so callers can fall back to the analytic ``_cl_cd``.
"""

from __future__ import annotations

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


def family_for_camber(camber: float, thickness: float = _DEFAULT_THICKNESS) -> str:
    """Nearest vendored polar family for section camber and thickness fractions."""
    c = float(camber)
    t = float(thickness) if thickness is not None else _DEFAULT_THICKNESS
    return min(
        _FAMILIES,
        key=lambda fct: abs(c - fct[1]) + 0.5 * abs(t - fct[2]),
    )[0]


def _parse_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.genfromtxt(path, delimiter=",", names=True)
    return (
        np.asarray(data["alpha_deg"], float),
        np.asarray(data["cl"], float),
        np.asarray(data["cd"], float),
    )


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


def cl_cd_table(
    alpha_rad: float,
    camber: float,
    re: float,
    thickness: float = _DEFAULT_THICKNESS,
) -> tuple[float, float] | None:
    """Table Cl, Cd at (α, Re) for the camber+thickness-mapped family, or None if unavailable."""
    if re is None or not math.isfinite(float(re)):
        return None
    fam = family_for_camber(camber, thickness)
    tables = load_polar_family(fam)
    if not tables:
        return None
    a_deg = math.degrees(float(alpha_rad))
    res = sorted(tables.keys())
    r = float(re)
    # Below the lowest table Re: do NOT clamp up (fan chord Re is often ~1–3e4). Caller falls back.
    if r < res[0]:
        return None
    if r <= res[0]:
        a, cl, cd = tables[res[0]]
        return _interp_alpha(a_deg, a, cl, cd)
    if r >= res[-1]:
        a, cl, cd = tables[res[-1]]
        return _interp_alpha(a_deg, a, cl, cd)
    # log10 Re blend between neighbors
    for lo, hi in zip(res[:-1], res[1:]):
        if lo <= r <= hi:
            w = (math.log10(r) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
            a0, cl0, cd0 = tables[lo]
            a1, cl1, cd1 = tables[hi]
            c0, d0 = _interp_alpha(a_deg, a0, cl0, cd0)
            c1, d1 = _interp_alpha(a_deg, a1, cl1, cd1)
            return c0 * (1.0 - w) + c1 * w, d0 * (1.0 - w) + d1 * w
    return None


def clear_polar_cache() -> None:
    load_polar_family.cache_clear()
