"""Prop CFD 2-D section runner (release R2.2a / R2.2a′ rung A0).

Defaults are rung A: NACA 4406 at Re 8e4, α 0–8°, SST and SST-LM.
Rung A0: ``--section 0012 --re 6e6 --alphas 0 5 10 --models kOmegaSST --tu 0.001``.

Pre-registered: docs/validation/audits/2026-10-17-prop-cfd-fix-prereg.md (rung A),
amended in docs/validation/audits/2026-10-19-prereg-amendments-r17.md section 4,
and docs/validation/audits/2026-10-20-rulings-r18-r19-rungA.md §1 (A0 vs Ladson).

The fast suite only builds the case (no Docker, no solve). The runner writes
summary.json after every α/model unit and will not start a new unit after 15:30 local.

    python scripts/prop_section_2d.py --build-only
    python scripts/prop_section_2d.py
    python scripts/prop_section_2d.py --section 0012 --re 6e6 --alphas 0 5 10 --models kOmegaSST --tu 0.001
    python scripts/prop_section_2d.py --analyze

A0c gate grid (defaults stay 48/60/32, far field 8c). Iteration count is not tuning:

    python scripts/prop_section_2d.py --build-only --mesh cgrid --section 0012 --re 6e6 --iters 10000 --cgrid-tangent 128 --cgrid-normal 120 --cgrid-wake 64 --cgrid-far 50 --cgrid-wake-len 50 --cgrid-end-cell 0.001 --cgrid-max-ratio 1.2 --cgrid-normal-growth 1.15
"""
from __future__ import annotations

import argparse
import json
import math
import re as _re
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.geometry.airfoil import naca4
from fansim.physics.air import NU_AIR, RHO_ISA

RE = 8.0e4
DEFAULT_SECTION = "4406"
CHORD = 0.10  # m
SPAN = 0.002  # m (spanwise empty)
ALPHAS = (0.0, 2.0, 4.0, 6.0, 8.0)
MODELS = ("kOmegaSST", "kOmegaSSTLM")
# Ladson TM-4074 tripped NACA 0012, Re 6e6 (grok r20 B / rulings §1).
A0_CD_0 = 0.00808
A0_CL_5 = 0.537
A0_CL_10 = 1.063
A0_CL_TOL = 0.05
A0_CD_TOL = 0.20
A0_TU = 0.001  # ~0.1 % freestream Tu; not the Ncrit-9 value.
N_THETA = 96
N_ITERS = 2000
# grok r17 A / amendment §4, α = 4°, Re 8e4 (CERTAIN).
REF_CL_4 = 0.855
REF_CL_4_LO = 0.847
REF_CL_4_HI = 0.863
REF_CD_4 = 0.0201
OUT = ROOT / "runs" / "prop_section_2d"
# Freestream Tu matching XFOIL Ncrit 9 (Mack): Ncrit = -8.43 - 2.4 ln(Tu).
TU_NCRIT9 = math.exp(-(9.0 + 8.43) / 2.4)
CMU = 0.09
CUTOFF_HOUR = 15
CUTOFF_MINUTE = 30


def section_xy() -> np.ndarray:
    """Builder section: naca4(0.04, 0.4, 0.06, n_chord=60), closed TE."""
    return naca4(0.04, 0.4, 0.06, 60)


CGRID_U = 1.0  # incompressible; Re is set by nu = U·c/Re (avoids U≈900 m/s at Re 6e6)


def u_inf(re: float = RE, chord: float = CHORD) -> float:
    return float(re) * NU_AIR / float(chord)


def solve_u_nu(re: float, *, mesh: str) -> tuple[float, float]:
    """Velocity and viscosity that realise `re` on chord `CHORD`.

    Snappy keeps physical air. The C-grid uses U = 1 m/s so SIMPLE is not
    Mach-2 incompressible; Cl/Cd are unchanged.
    """
    if mesh == "cgrid":
        u = CGRID_U
        return u, u * CHORD / float(re)
    return u_inf(re), NU_AIR


def _cf_turb(re: float) -> float:
    return 0.026 * float(re) ** (-1.0 / 7.0)


def _u_tau(re: float, u: float) -> float:
    return float(u) * math.sqrt(_cf_turb(re) / 2.0)


def wall_spacing_m(re: float = RE, chord: float = CHORD, yplus_target: float = 0.8) -> float:
    u = u_inf(re, chord)
    return float(yplus_target) * NU_AIR / _u_tau(re, u)


def first_cell_yplus(re: float = RE, chord: float = CHORD) -> float:
    """y+ of the first cell the case actually requests (target 0.8, always ≤ 1)."""
    ds = wall_spacing_m(re, chord, yplus_target=0.8)
    return ds * _u_tau(re, u_inf(re, chord)) / NU_AIR


def parse_naca4_code(code: str) -> tuple[float, float, float]:
    """NACA MPXX → (m, p, t) as fractions of chord. '0012' and 'NACA0012' both work."""
    s = str(code).strip().upper().replace(" ", "").replace("-", "")
    if s.startswith("NACA"):
        s = s[4:]
    if len(s) != 4 or not s.isdigit():
        raise ValueError(f"need a NACA 4-digit code, got {code!r}")
    return int(s[0]) / 100.0, int(s[1]) / 10.0, int(s[2:]) / 100.0


def _foam(cls: str, obj: str) -> str:
    return (
        "FoamFile\n{\n    version     2.0;\n    format      ascii;\n"
        f"    class       {cls};\n    object      {obj};\n}}\n"
    )


N_CGRID_TANGENT = 48
N_CGRID_NORMAL = 60
N_CGRID_WAKE = 32
R_OUTER = 8.0 * CHORD
WAKE_LEN = 16.0 * CHORD


def _grading_last_over_first(first: float, length: float, n: int) -> float:
    """simpleGrading ratio (last cell / first cell) for a geometric edge of n cells."""
    if n < 2 or first <= 0 or length <= first * n:
        return 1.0
    r = 1.15
    for _ in range(50):
        if abs(r - 1.0) < 1e-9:
            r = 1.15
        s = (r ** n - 1.0) / (r - 1.0)
        ds = (n * r ** (n - 1) * (r - 1.0) - (r ** n - 1.0)) / (r - 1.0) ** 2
        err = first * s - length
        if abs(first * ds) < 1e-18:
            break
        r -= err / (first * ds)
        r = min(max(r, 1.0001), 5.0)
    return float(r ** (n - 1))


def _pt(p: np.ndarray, z: float) -> str:
    return f"({float(p[0]):.8g} {float(p[1]):.8g} {z:.8g})"


def _cgrid_geometry(section: str, r_outer: float | None = None, wake_len: float | None = None):
    """Corners and splines for a 4-block C-grid (cut in the wake, not at the TE).

    Trailing-edge and outlet vertices are duplicated (same coordinates, different
    indices) so the upper and lower surfaces are distinct edges. The wake slit is
    stitched with mergePatchPairs.
    """
    r_outer = R_OUTER if r_outer is None else float(r_outer)
    wake_len = WAKE_LEN if wake_len is None else float(wake_len)
    m, p, t = parse_naca4_code(section)
    foil = naca4(m, p, t, N_THETA) * CHORD  # closed: TE → upper → LE → lower → TE
    te = foil[0].copy()
    i_le = int(np.argmin(foil[:-1, 0]))
    le = foil[i_le].copy()
    lower = np.vstack([te, foil[-2:i_le - 1:-1]])  # TE → LE along lower
    upper = foil[i_le::-1]  # LE → TE along upper
    xmax = float(te[0] + wake_len)
    outlet = np.array([xmax, 0.0])
    centre = np.array([0.25 * CHORD, 0.0])
    dx = float(te[0] - centre[0])
    y_arc = math.sqrt(max(r_outer ** 2 - dx ** 2, 1e-18))
    te_lo = np.array([float(te[0]), -y_arc])
    te_hi = np.array([float(te[0]), y_arc])
    le_out = centre + np.array([-r_outer, 0.0])
    out_lo = np.array([xmax, -y_arc])
    out_hi = np.array([xmax, y_arc])
    n_arc = max(len(lower), 16)
    ang_te = math.atan2(-y_arc, dx)
    th_lo = np.linspace(ang_te, -math.pi, n_arc)
    outer_lower = centre + r_outer * np.column_stack((np.cos(th_lo), np.sin(th_lo)))
    th_hi = np.linspace(math.pi, -ang_te, n_arc)
    outer_upper = centre + r_outer * np.column_stack((np.cos(th_hi), np.sin(th_hi)))
    # 0 TE_lo, 1 LE, 2 outlet_lo, 3 LE_out, 4 TE_out_lo, 5 out_lo,
    # 6 TE_out_hi, 7 out_hi, 8 TE_hi, 9 outlet_hi
    corners = [te, le, outlet, le_out, te_lo, out_lo, te_hi, out_hi, te.copy(), outlet.copy()]
    splines = {
        (0, 1): lower[1:-1],
        (1, 8): upper[1:-1],
        (4, 3): outer_lower[1:-1],
        (3, 6): outer_upper[1:-1],
    }
    return corners, splines


def _edge_length(corners, splines, a: int, b: int) -> float:
    if (a, b) in splines:
        pts = np.vstack([corners[a], splines[(a, b)], corners[b]])
    elif (b, a) in splines:
        pts = np.vstack([corners[a], splines[(b, a)][::-1], corners[b]])
    else:
        pts = np.vstack([corners[a], corners[b]])
    return float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def _geom_cell_sizes(length: float, n: int, expansion: float) -> list[float]:
    """Cell lengths for OpenFOAM simpleGrading (expansion = last/first)."""
    if n <= 0:
        return []
    if n == 1 or abs(expansion - 1.0) <= 1e-12:
        return [length / n] * n
    r = expansion ** (1.0 / (n - 1))
    if abs(r - 1.0) <= 1e-14:
        return [length / n] * n
    first = length * (r - 1.0) / (r ** n - 1.0)
    return [first * (r ** i) for i in range(n)]


def _sizes_from_sections(length: float, n: int, sections: list[tuple[float, float, float]]) -> list[float]:
    block_sum = sum(s[0] for s in sections)
    div_sum = sum(s[1] for s in sections)
    norm = [(s[0] / block_sum, s[1] / div_sum, s[2]) for s in sections]
    counts = [int(s[1] * n + 0.5) for s in norm]
    drift = n - sum(counts)
    if counts and drift:
        biggest = max(range(len(counts)), key=lambda i: counts[i])
        counts[biggest] += drift
    sizes: list[float] = []
    for (block_frac, _div_frac, expansion), n_cells in zip(norm, counts):
        sizes.extend(_geom_cell_sizes(block_frac * length, n_cells, expansion))
    return sizes


def _max_step_ratio(sizes: list[float]) -> float:
    if len(sizes) < 2:
        return 1.0
    worst = 1.0
    for a, b in zip(sizes, sizes[1:]):
        lo = min(abs(a), abs(b))
        if lo <= 0.0:
            return float("inf")
        worst = max(worst, max(abs(a), abs(b)) / lo)
    return worst


def _cluster_sections(length: float, n_req: int, end_max: float, ratio_max: float):
    """Two-ended geometric clustering. Returns (n_cells, grading sections).

    Sections are (edge-length fraction, cell fraction, last/first expansion).
    The first cell and the last cell are each <= end_max, and every adjacent
    ratio is <= ratio_max. n_cells is at least n_req.
    """
    if ratio_max <= 1.0:
        raise ValueError(f"max adjacent ratio must be > 1, got {ratio_max}")
    n = max(int(n_req), 4)
    limit = n + 512

    def attempt(n_cells: int, r: float):
        for n_ramp in range(2, n_cells // 2 + 1):
            n_mid = n_cells - 2 * n_ramp
            ramp_unit = (r ** n_ramp - 1.0) / (r - 1.0)
            plateau = r ** (n_ramp - 1)
            factor = 2.0 * ramp_unit + n_mid * plateau
            delta = length / factor
            if delta > end_max:
                continue
            length_ramp = delta * ramp_unit
            length_mid = n_mid * delta * plateau
            expand = r ** (n_ramp - 1)
            parts = [(length_ramp, n_ramp, expand)]
            if n_mid > 0:
                parts.append((length_mid, n_mid, 1.0))
            parts.append((length_ramp, n_ramp, 1.0 / expand))
            sections = [(part_l / length, nc / n_cells, exp) for part_l, nc, exp in parts]
            sizes = _sizes_from_sections(length, n_cells, sections)
            if not sizes or abs(sum(sizes) - length) / length > 1e-6:
                continue
            if sizes[0] > end_max or sizes[-1] > end_max:
                continue
            if _max_step_ratio(sizes) > ratio_max:
                continue
            return sections
        return None

    while n <= limit:
        for scale in (1.0, 1.0 - 1e-6, 0.999, 0.99, 0.98):
            r = 1.0 + (float(ratio_max) - 1.0) * scale
            if r <= 1.0:
                continue
            found = attempt(n, r)
            if found is not None:
                return n, found
        n += 1
    raise ValueError(
        f"cannot cluster length {length:.6g} m into >= {n_req} cells "
        f"with ends <= {end_max:.6g} m and ratio <= {ratio_max}"
    )


def _wake_expansion(length: float, n_req: int, te_cell: float, ratio_max: float) -> tuple[int, float]:
    """Cells and last/first expansion so the first cell equals the foil TE cell.

    The edge runs TE → outlet. The reciprocal expansion is the outlet → TE edge.
    """
    def first_of(n_cells: int, r: float) -> float:
        if abs(r - 1.0) <= 1e-15:
            return length / n_cells
        return length * (r - 1.0) / (r ** n_cells - 1.0)

    n = max(int(n_req), 2)
    while n <= n_req + 400:
        uniform = length / n
        if te_cell >= uniform:
            if uniform <= 0.0 or te_cell / uniform <= ratio_max:
                return n, 1.0
            n += 1
            continue
        if first_of(n, ratio_max) > te_cell:
            n += 1
            continue
        lo, hi = 1.0, float(ratio_max)
        for _ in range(70):
            mid = 0.5 * (lo + hi)
            if first_of(n, mid) > te_cell:
                lo = mid
            else:
                hi = mid
        r = hi
        if r <= 1.0 + 1e-15:
            return n, 1.0
        expansion = r ** (n - 1)
        sizes = _geom_cell_sizes(length, n, expansion)
        step = _max_step_ratio(sizes)
        if sizes and sizes[0] <= te_cell * (1.0 + 1e-6) and step <= ratio_max:
            return n, expansion
        n += 1
    raise ValueError(
        f"cannot match wake cell {te_cell:.6g} m over {length:.6g} m "
        f"with >= {n_req} cells and ratio <= {ratio_max}"
    )


def _normal_grading(re: float, r_outer: float, n_normal: int, yplus_target: float, growth_cap: float | None):
    """Return (n_normal, last/first, first-cell metres). Growth cap adds cells, not y+."""
    ds = wall_spacing_m(re, yplus_target=yplus_target)
    length = float(r_outer) - 0.25 * CHORD
    n = max(int(n_normal), 2)
    while True:
        gy = _grading_last_over_first(ds, length, n)
        growth = 1.0 if n < 2 else gy ** (1.0 / (n - 1))
        if growth_cap is None or growth <= float(growth_cap):
            return n, gy, ds
        n += 1
        if n > max(int(n_normal), 2) + 8000:
            raise ValueError(
                f"normal growth stays above {growth_cap} at {n} cells "
                f"(first cell {ds:.6g} m, length {length:.6g} m)"
            )


def _fmt_tangential(spec, gy: float, *, legacy: str | None = None) -> str:
    gy_s = f"{gy:.8g}" if legacy is not None else f"{gy:.12g}"
    if legacy is not None:
        return f"simpleGrading ({legacy} {gy_s} 1)"
    if isinstance(spec, (int, float)):
        return f"simpleGrading ({float(spec):.12g} {gy_s} 1)"
    rows = " ".join(f"({bf:.16g} {nf:.16g} {exp:.16g})" for bf, nf, exp in spec)
    return f"simpleGrading ( ( {rows} ) {gy_s} 1 )"


def _cgrid_block_mesh_dict(
    *,
    section: str,
    re: float,
    n_tangent: int | None = None,
    n_normal: int | None = None,
    n_wake: int | None = None,
    far_chords: float | None = None,
    wake_chords: float | None = None,
    end_cell_frac: float | None = None,
    max_ratio: float = 1.2,
    normal_growth: float | None = None,
    yplus_target: float = 0.8,
) -> str:
    """Structured 4-block C-grid: two foil blocks + two wake blocks. Inner foil is `airfoil`."""
    r_outer = R_OUTER if far_chords is None else float(far_chords) * CHORD
    wake_len = WAKE_LEN if wake_chords is None else float(wake_chords) * CHORD
    n_tangent = N_CGRID_TANGENT if n_tangent is None else int(n_tangent)
    n_normal_req = N_CGRID_NORMAL if n_normal is None else int(n_normal)
    n_wake = N_CGRID_WAKE if n_wake is None else int(n_wake)
    corners, splines = _cgrid_geometry(section, r_outer, wake_len)
    ny, gy, ds = _normal_grading(re, r_outer, n_normal_req, yplus_target, normal_growth)
    if end_cell_frac is None:
        nx_lo = nx_hi = n_tangent
        nw = n_wake
        grade_lo = _fmt_tangential(1.0, gy, legacy="1")
        grade_hi = _fmt_tangential(1.0, gy, legacy="1")
        grade_wlo = _fmt_tangential(0.05, gy, legacy="0.05")
        grade_whi = _fmt_tangential(20.0, gy, legacy="20")
    else:
        end_max = float(end_cell_frac) * CHORD
        ratio_max = float(max_ratio)
        len_lo = _edge_length(corners, splines, 0, 1)
        len_hi = _edge_length(corners, splines, 1, 8)
        nx_lo, sec_lo = _cluster_sections(len_lo, n_tangent, end_max, ratio_max)
        nx_hi, sec_hi = _cluster_sections(len_hi, n_tangent, end_max, ratio_max)
        te_lo = _sizes_from_sections(len_lo, nx_lo, sec_lo)[0]
        te_hi = _sizes_from_sections(len_hi, nx_hi, sec_hi)[-1]
        te_cell = max(te_lo, te_hi)
        nw, wake_exp = _wake_expansion(wake_len, n_wake, te_cell, ratio_max)
        grade_lo = _fmt_tangential(sec_lo, gy)
        grade_hi = _fmt_tangential(sec_hi, gy)
        grade_wlo = _fmt_tangential(1.0 / wake_exp, gy)
        grade_whi = _fmt_tangential(wake_exp, gy)
    verts: list[str] = []
    for z in (0.0, SPAN):
        for p in corners:
            verts.append(f"    {_pt(p, z)}")
    # z=0: 0..9 as in _cgrid_geometry; z=SPAN: +10
    hexes = [
        f"    hex (0 1 3 4 10 11 13 14) ({nx_lo} {ny} 1) {grade_lo}",
        f"    hex (1 8 6 3 11 18 16 13) ({nx_hi} {ny} 1) {grade_hi}",
        f"    hex (2 0 4 5 12 10 14 15) ({nw} {ny} 1) {grade_wlo}",
        f"    hex (8 9 7 6 18 19 17 16) ({nw} {ny} 1) {grade_whi}",
    ]
    edge_lines = ["edges", "("]
    for (a, b), mid in splines.items():
        if len(mid) == 0:
            continue
        body = " ".join(_pt(p, 0.0) for p in mid)
        body_z = " ".join(_pt(p, SPAN) for p in mid)
        edge_lines.append(f"    spline {a} {b} ( {body} )")
        edge_lines.append(f"    spline {a + 10} {b + 10} ( {body_z} )")
    edge_lines.append(");")
    return "\n".join([
        _foam("dictionary", "blockMeshDict"),
        (
            f"// cgrid firstLayer {ds:.8g} m  y+_req {first_cell_yplus(re):.3f}"
            if abs(float(yplus_target) - 0.8) < 1e-12
            else f"// cgrid firstLayer {ds:.8g} m  y+_req {float(yplus_target):.3f}"
        ),
        "scale 1;",
        "vertices",
        "(",
        *verts,
        ");",
        "blocks",
        "(",
        *hexes,
        ");",
        *edge_lines,
        "boundary",
        "(",
        "    airfoil",
        "    {",
        "        type wall;",
        "        faces",
        "        (",
        "            (0 1 11 10)",
        "            (1 8 18 11)",
        "        );",
        "    }",
        "    freestream",
        "    {",
        "        type patch;",
        "        faces",
        "        (",
            "            (4 14 13 3)",
            "            (3 13 16 6)",
            "            (4 5 15 14)",
            "            (6 16 17 7)",
            "        );",
            "    }",
            "    outlet",
            "    {",
            "        type patch;",
            "        faces",
            "        (",
            "            (5 2 12 15)",
            "            (9 7 17 19)",
            "        );",
            "    }",
        "    wakeLower { type patch; faces ((2 0 10 12)); }",
        "    wakeUpper { type patch; faces ((8 9 19 18)); }",
        "    front { type empty; faces ("
        "(10 11 13 14) (11 18 16 13) (12 10 14 15) (18 19 17 16)"
        "); }",
        "    back  { type empty; faces ("
        "(0 4 3 1) (1 3 6 8) (2 5 4 0) (8 6 7 9)"
        "); }",
        ");",
        "mergePatchPairs",
        "(",
        "    (wakeLower wakeUpper)",
        ");",
        "",
    ])


def _block_mesh_dict() -> str:
    """Background hex: one cell in z, empty front/back. Airfoil comes from snappy."""
    xmin, xmax = -8.0 * CHORD, 16.0 * CHORD
    ymin, ymax = -8.0 * CHORD, 8.0 * CHORD
    dx, dy = xmax - xmin, ymax - ymin
    nx, ny = 120, 80
    return "\n".join([
        _foam("dictionary", "blockMeshDict"),
        "scale 1;",
        "vertices",
        "(",
        f"    ({xmin:.8g} {ymin:.8g} 0)",
        f"    ({xmax:.8g} {ymin:.8g} 0)",
        f"    ({xmax:.8g} {ymax:.8g} 0)",
        f"    ({xmin:.8g} {ymax:.8g} 0)",
        f"    ({xmin:.8g} {ymin:.8g} {SPAN:.8g})",
        f"    ({xmax:.8g} {ymin:.8g} {SPAN:.8g})",
        f"    ({xmax:.8g} {ymax:.8g} {SPAN:.8g})",
        f"    ({xmin:.8g} {ymax:.8g} {SPAN:.8g})",
        ");",
        "blocks",
        "(",
        f"    hex (0 1 2 3 4 5 6 7) ({nx} {ny} 1) simpleGrading (1 1 1)",
        ");",
        "edges ();",
        "boundary",
        "(",
        "    freestream { type patch; faces ((0 4 7 3) (1 2 6 5) (0 1 5 4) (3 7 6 2)); }",
        "    back { type empty; faces ((0 3 2 1)); }",
        "    front { type empty; faces ((4 5 6 7)); }",
        ");",
        "mergePatchPairs ();",
        f"// domain {dx:.4g} x {dy:.4g} m, one cell in z",
        "",
    ])


def _write_airfoil_stl(path: Path, *, section: str = DEFAULT_SECTION) -> None:
    m, p, t = parse_naca4_code(section)
    loop = naca4(m, p, t, N_THETA)[:-1] * CHORD
    n = len(loop)
    facets: list[tuple[tuple[float, float, float], ...]] = []
    for i in range(n):
        j = (i + 1) % n
        p0 = (float(loop[i, 0]), float(loop[i, 1]), 0.0)
        p1 = (float(loop[j, 0]), float(loop[j, 1]), 0.0)
        p2 = (float(loop[j, 0]), float(loop[j, 1]), SPAN)
        p3 = (float(loop[i, 0]), float(loop[i, 1]), SPAN)
        facets.append((p0, p1, p2))
        facets.append((p0, p2, p3))
    for i in range(1, n - 1):
        a = (float(loop[0, 0]), float(loop[0, 1]), 0.0)
        b = (float(loop[i, 0]), float(loop[i, 1]), 0.0)
        c = (float(loop[i + 1, 0]), float(loop[i + 1, 1]), 0.0)
        facets.append((a, c, b))
        a1 = (float(loop[0, 0]), float(loop[0, 1]), SPAN)
        b1 = (float(loop[i, 0]), float(loop[i, 1]), SPAN)
        c1 = (float(loop[i + 1, 0]), float(loop[i + 1, 1]), SPAN)
        facets.append((a1, b1, c1))
    lines = ["solid airfoil"]
    for a, b, c in facets:
        lines.append("  facet normal 0 0 0")
        lines.append("    outer loop")
        for p in (a, b, c):
            lines.append(f"      vertex {p[0]:.8e} {p[1]:.8e} {p[2]:.8e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid airfoil\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _snappy_dict(*, re: float = RE) -> str:
    ds = wall_spacing_m(re)
    locx, locy, locz = -2.0 * CHORD, 0.0, 0.5 * SPAN
    return "\n".join([
        _foam("dictionary", "snappyHexMeshDict"),
        "castellatedMesh true;",
        "snap            true;",
        "addLayers       true;",
        "geometry",
        "{",
        "    airfoil.stl { type triSurfaceMesh; name airfoil; }",
        "}",
        "castellatedMeshControls",
        "{",
        "    maxLocalCells 2000000;",
        "    maxGlobalCells 4000000;",
        "    minRefinementCells 0;",
        "    maxLoadUnbalance 0.10;",
        "    nCellsBetweenLevels 2;",
        "    features ( { file \"airfoil.eMesh\"; level 4; } );",
        "    refinementSurfaces { airfoil { level (4 4); patchInfo { type wall; } } }",
        "    resolveFeatureAngle 30;",
        "    refinementRegions {};",
        f"    locationInMesh ({locx:.8g} {locy:.8g} {locz:.8g});",
        "    allowFreeStandingZoneFaces true;",
        "}",
        "snapControls",
        "{",
        "    nSmoothPatch 2; tolerance 4.0; nSolveIter 8; nRelaxIter 3;",
        "    nFeatureSnapIter 4; implicitFeatureSnap false; explicitFeatureSnap true;",
        "}",
        "addLayersControls",
        "{",
        "    relativeSizes false;",
        "    layers { airfoil { nSurfaceLayers 8; } }",
        "    expansionRatio 1.2;",
        f"    firstLayerThickness {ds:.8g};",
        f"    minThickness {0.2 * ds:.8g};",
        "    nGrow 0; featureAngle 130; nRelaxIter 5;",
        "    nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;",
        "    maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3;",
        "    minMedialAxisAngle 90; nBufferCellsNoExtrude 0; nLayerIter 50;",
        "}",
        "meshQualityControls",
        "{",
        "    maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4;",
        "    maxConcave 80; minFlatness 0.5; minVol 1e-16; minTetQuality 1e-15;",
        "    minArea -1; minTwist 0.02; minDeterminant 0.001; minFaceWeight 0.02;",
        "    minVolRatio 0.01; minTriangleTwist -1; nSmoothScale 4; errorReduction 0.75;",
        "}",
        "debug 0; mergeTolerance 1e-6;",
        "",
    ])


def _surface_feature_dict() -> str:
    return "\n".join([
        _foam("dictionary", "surfaceFeatureExtractDict"),
        "airfoil.stl",
        "{",
        "    extractionMethod extractFromSurface;",
        "    extractFromSurfaceCoeffs { includedAngle 150; }",
        "    subsetFeatures { nonManifoldEdges no; openEdges no; }",
        "    writeObj no;",
        "}",
        "",
    ])


def _field_scalar(
    name: str, dims: str, value: float, wall: str, empty: bool = True,
    *, outlet: bool = False,
) -> str:
    outlet_bc = (
        f"    outlet      {{ type inletOutlet; inletValue uniform {value:.8g}; "
        f"value uniform {value:.8g}; }}"
        if outlet else ""
    )
    return "\n".join([
        _foam("volScalarField", name),
        f"dimensions {dims};",
        f"internalField uniform {value:.8g};",
        "boundaryField",
        "{",
        f"    airfoil     {{ {wall} }}",
        (
            f"    freestream  {{ type inletOutlet; inletValue uniform {value:.8g}; "
            f"value uniform {value:.8g}; }}"
        ),
        outlet_bc,
        "    front       { type empty; }" if empty else "",
        "    back        { type empty; }" if empty else "",
        "}",
        "",
    ])


def write_case(
    case_dir: Path,
    *,
    alpha_deg: float,
    model: str,
    n_iters: int = N_ITERS,
    section: str = DEFAULT_SECTION,
    re: float = RE,
    tu: float | None = None,
    mesh: str = "snappy",
    n_tangent: int | None = None,
    n_normal: int | None = None,
    n_wake: int | None = None,
    far_chords: float | None = None,
    wake_chords: float | None = None,
    end_cell_frac: float | None = None,
    max_ratio: float = 1.2,
    normal_growth: float | None = None,
    yplus_target: float = 0.8,
) -> Path:
    """Write a 2-D simpleFoam case. Does not run blockMesh or the solver."""
    if model not in MODELS:
        raise ValueError(f"model must be one of {MODELS}, got {model!r}")
    if mesh not in ("snappy", "cgrid"):
        raise ValueError(f"mesh must be 'snappy' or 'cgrid', got {mesh!r}")
    parse_naca4_code(section)
    tu_frac = TU_NCRIT9 if tu is None else float(tu)
    case = Path(case_dir)
    (case / "0").mkdir(parents=True, exist_ok=True)
    (case / "system").mkdir(parents=True, exist_ok=True)
    (case / "constant").mkdir(parents=True, exist_ok=True)

    u, nu = solve_u_nu(re, mesh=mesh)
    a = math.radians(float(alpha_deg))
    ux, uy = u * math.cos(a), u * math.sin(a)
    k = 1.5 * (tu_frac * u) ** 2
    omega = math.sqrt(k) / (CMU ** 0.25 * 0.1 * CHORD)
    lift = (-math.sin(a), math.cos(a), 0.0)
    drag = (math.cos(a), math.sin(a), 0.0)
    aref = CHORD * SPAN
    lm = model == "kOmegaSSTLM"
    has_outlet = mesh == "cgrid"

    if mesh == "cgrid":
        (case / "system" / "blockMeshDict").write_text(
            _cgrid_block_mesh_dict(
                section=section, re=re,
                n_tangent=n_tangent, n_normal=n_normal, n_wake=n_wake,
                far_chords=far_chords, wake_chords=wake_chords,
                end_cell_frac=end_cell_frac, max_ratio=max_ratio,
                normal_growth=normal_growth, yplus_target=yplus_target,
            ),
            encoding="utf-8",
        )
    else:
        (case / "system" / "blockMeshDict").write_text(_block_mesh_dict(), encoding="utf-8")
        (case / "system" / "snappyHexMeshDict").write_text(_snappy_dict(re=re), encoding="utf-8")
        (case / "system" / "surfaceFeatureExtractDict").write_text(
            _surface_feature_dict(), encoding="utf-8")
        _write_airfoil_stl(case / "constant" / "triSurface" / "airfoil.stl", section=section)

    extra_div = ""
    extra_relax = ""
    extra_solvers = ""
    extra_resid = ""
    if lm:
        extra_div = (
            "    div(phi,gammaInt)      bounded Gauss upwind;\n"
            "    div(phi,ReThetat) bounded Gauss upwind;\n"
        )
        extra_relax = "        gammaInt 0.7; ReThetat 0.7;\n"
        extra_solvers = (
            "    \"(gammaInt|ReThetat)\"\n"
            "    {\n"
            "        solver          smoothSolver;\n"
            "        smoother        symGaussSeidel;\n"
            "        tolerance       1e-8;\n"
            "        relTol          0.1;\n"
            "    }\n"
        )
        extra_resid = "        gammaInt 1e-4; ReThetat 1e-4;\n"

    (case / "system" / "fvSchemes").write_text("\n".join([
        _foam("dictionary", "fvSchemes"),
        "ddtSchemes { default steadyState; }",
        "gradSchemes { default Gauss linear; }",
        "divSchemes",
        "{",
        "    default none;",
        "    div(phi,U) bounded Gauss linearUpwind grad(U);",
        "    div(phi,k) bounded Gauss upwind;",
        "    div(phi,omega) bounded Gauss upwind;",
        extra_div.rstrip(),
        "    div((nuEff*dev2(T(grad(U))))) Gauss linear;",
        "    div(div(phi,U)) Gauss linear;",
        "}",
        "laplacianSchemes { default Gauss linear corrected; }",
        "interpolationSchemes { default linear; }",
        "snGradSchemes { default corrected; }",
        "wallDist { method meshWave; }",
        "",
    ]), encoding="utf-8")

    (case / "system" / "fvSolution").write_text("\n".join([
        _foam("dictionary", "fvSolution"),
        "solvers",
        "{",
        "    p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }",
        "    Phi { solver PCG; preconditioner DIC; tolerance 1e-7; relTol 0.05; }",
        (
            "    \"(U|k|omega)\" { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-8; relTol 0.1; }"
        ),
        extra_solvers.rstrip(),
        "}",
        "potentialFlow { nNonOrthogonalCorrectors 3; }",
        "SIMPLE",
        "{",
        f"    nNonOrthogonalCorrectors {2 if has_outlet else 1};",
        (
            "    residualControl {};"
            if has_outlet else
            "    residualControl { p 1e-4; U 1e-4; k 1e-4; omega 1e-4; "
            + extra_resid + "}"
        ),
        "}",
        "relaxationFactors",
        "{",
        "    fields { p 0.3; }",
        "    equations { U 0.7; k 0.7; omega 0.7; " + extra_relax + "}",
        "}",
        "",
    ]), encoding="utf-8")

    (case / "system" / "controlDict").write_text("\n".join([
        _foam("dictionary", "controlDict"),
        "application     simpleFoam;",
        "startFrom       startTime;",
        "startTime       0;",
        "stopAt          endTime;",
        f"endTime         {int(n_iters)};",
        "deltaT          1;",
        "writeControl    timeStep;",
        f"writeInterval   {int(n_iters)};",
        "purgeWrite      1;",
        "writeFormat     ascii;",
        "writePrecision  8;",
        "writeCompression off;",
        "timeFormat      general;",
        "runTimeModifiable true;",
        "functions",
        "{",
        "    forceCoeffs1",
        "    {",
        "        type            forceCoeffs;",
        "        libs            (forces);",
        "        patches         (airfoil);",
        "        rho             rhoInf;",
        f"        rhoInf          {RHO_ISA};",
        f"        liftDir         ({lift[0]:.8g} {lift[1]:.8g} {lift[2]:.8g});",
        f"        dragDir         ({drag[0]:.8g} {drag[1]:.8g} {drag[2]:.8g});",
        f"        CofR            ({0.25 * CHORD:.8g} 0 0);",
        "        pitchAxis       (0 0 1);",
        f"        magUInf         {u:.8g};",
        f"        lRef            {CHORD};",
        f"        Aref            {aref:.8g};",
        "        writeControl    timeStep;",
        "        writeInterval   20;",
        "        log             true;",
        "    }",
        "    yPlus",
        "    {",
        "        type            yPlus;",
        "        libs            (fieldFunctionObjects);",
        "        writeControl    writeTime;",
        "    }",
        "}",
        "",
    ]), encoding="utf-8")

    ras = "kOmegaSSTLM" if lm else "kOmegaSST"
    (case / "constant" / "turbulenceProperties").write_text(
        _foam("dictionary", "turbulenceProperties")
        + "simulationType RAS;\n"
        + f"RAS {{ RASModel {ras}; turbulence on; printCoeffs on; }}\n",
        encoding="utf-8",
    )
    (case / "constant" / "transportProperties").write_text(
        _foam("dictionary", "transportProperties")
        + f"transportModel Newtonian;\nnu {nu:.16g};\n",
        encoding="utf-8",
    )

    (case / "0" / "U").write_text("\n".join([
        _foam("volVectorField", "U"),
        "dimensions [0 1 -1 0 0 0 0];",
        f"internalField uniform ({ux:.8g} {uy:.8g} 0);",
        "boundaryField",
        "{",
        "    airfoil     { type noSlip; }",
        (
            "    freestream  { type freestreamVelocity; "
            f"freestreamValue uniform ({ux:.8g} {uy:.8g} 0); "
            f"value uniform ({ux:.8g} {uy:.8g} 0); }}"
        ),
        (
            "    outlet      { type inletOutlet; "
            f"inletValue uniform ({ux:.8g} {uy:.8g} 0); "
            f"value uniform ({ux:.8g} {uy:.8g} 0); }}"
            if has_outlet else ""
        ),
        "    front       { type empty; }",
        "    back        { type empty; }",
        "}",
        "",
    ]), encoding="utf-8")
    (case / "0" / "p").write_text("\n".join([
        _foam("volScalarField", "p"),
        "dimensions [0 2 -2 0 0 0 0];",
        "internalField uniform 0;",
        "boundaryField",
        "{",
        "    airfoil     { type zeroGradient; }",
        "    freestream  { type freestreamPressure; freestreamValue uniform 0; value uniform 0; }",
        (
            "    outlet      { type fixedValue; value uniform 0; }"
            if has_outlet else ""
        ),
        "    front       { type empty; }",
        "    back        { type empty; }",
        "}",
        "",
    ]), encoding="utf-8")
    (case / "0" / "k").write_text(
        _field_scalar(
            "k", "[0 2 -2 0 0 0 0]", k,
            f"type kqRWallFunction; value uniform {k:.8g};",
            outlet=has_outlet,
        ),
        encoding="utf-8",
    )
    (case / "0" / "omega").write_text(
        _field_scalar(
            "omega", "[0 0 -1 0 0 0 0]", omega,
            f"type omegaWallFunction; value uniform {omega:.8g};",
            outlet=has_outlet,
        ),
        encoding="utf-8",
    )
    (case / "0" / "nut").write_text(
        _field_scalar(
            "nut", "[0 2 -1 0 0 0 0]", 0.0,
            "type nutUSpaldingWallFunction; value uniform 0;",
            outlet=has_outlet,
        ),
        encoding="utf-8",
    )
    if lm:
        # Langtry–Menter Reθt at Tu (%) < 1.3 % (Menter et al. 2006).
        tu_pct = tu_frac * 100.0
        re_th = 1173.51 - 589.428 * tu_pct + 0.2196 / (tu_pct ** 2)
        (case / "0" / "gammaInt").write_text(
            _field_scalar(
                "gammaInt", "[0 0 0 0 0 0 0]", 1.0,
                "type zeroGradient;",
                outlet=has_outlet,
            ),
            encoding="utf-8",
        )
        (case / "0" / "ReThetat").write_text(
            _field_scalar(
                "ReThetat", "[0 0 0 0 0 0 0]", re_th,
                "type zeroGradient;",
                outlet=has_outlet,
            ),
            encoding="utf-8",
        )
    return case


def verdict(*, sst_cl: float | None, lm_cl: float | None, ref: float = REF_CL_4) -> dict:
    """Rung A rules at α = 4°. A1 confirmed / A2 refuted / else report."""
    if sst_cl is None or lm_cl is None:
        return {"verdict": "INCONCLUSIVE", "why": "a Cl at α=4° is missing"}
    sst_err = float(sst_cl) / float(ref) - 1.0
    lm_err = float(lm_cl) / float(ref) - 1.0
    if sst_err <= -0.25 and abs(lm_err) <= 0.10:
        return {"verdict": "A1", "sst_err": sst_err, "lm_err": lm_err}
    if abs(sst_err) <= 0.10:
        return {"verdict": "A2", "sst_err": sst_err, "lm_err": lm_err}
    return {"verdict": "report to Claude", "sst_err": sst_err, "lm_err": lm_err}


def verdict_a0(points: dict) -> dict:
    """Rung A0: C_l ±5 % at 5° and 10°, C_d ±20 % at 0° vs Ladson TM-4074."""
    def _pt(alpha: float) -> dict | None:
        return points.get(f"{alpha:.1f}") or points.get(str(alpha))

    p0, p5, p10 = _pt(0.0), _pt(5.0), _pt(10.0)
    if not p0 or not p5 or not p10:
        return {"verdict": "INCONCLUSIVE", "why": "missing α 0/5/10"}
    cd0, cl5, cl10 = p0.get("cd"), p5.get("cl"), p10.get("cl")
    if cd0 is None or cl5 is None or cl10 is None:
        return {"verdict": "INCONCLUSIVE", "why": "missing Cl/Cd"}
    cd_err = float(cd0) / A0_CD_0 - 1.0
    cl5_err = float(cl5) / A0_CL_5 - 1.0
    cl10_err = float(cl10) / A0_CL_10 - 1.0
    ok = (
        abs(cd_err) <= A0_CD_TOL
        and abs(cl5_err) <= A0_CL_TOL
        and abs(cl10_err) <= A0_CL_TOL
    )
    return {
        "verdict": "PASS" if ok else "FAIL",
        "cd0_err": cd_err, "cl5_err": cl5_err, "cl10_err": cl10_err,
        "ref": {"cd_0": A0_CD_0, "cl_5": A0_CL_5, "cl_10": A0_CL_10},
    }


def _latest_time_file(paths: list[Path]) -> Path | None:
    """Pick the file in the highest numeric time directory (not lexicographic)."""
    if not paths:
        return None

    def _t(p: Path) -> float:
        try:
            return float(p.parent.name)
        except ValueError:
            return -1.0

    return max(paths, key=_t)


def parse_cl_cd(case: Path) -> tuple[float, float] | None:
    hits = list(case.glob("postProcessing/forceCoeffs1/*/coefficient.dat"))
    if not hits:
        hits = list(case.glob("postProcessing/forceCoeffs1/*/forceCoeffs.dat"))
    latest = _latest_time_file(hits)
    if latest is None:
        return None
    rows = []
    for ln in latest.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        parts = ln.split()
        if len(parts) >= 5:
            rows.append((float(parts[1]), float(parts[4])))  # Cd, Cl
        elif len(parts) >= 3:
            rows.append((float(parts[1]), float(parts[2])))
    if not rows:
        return None
    n_tail = max(1, min(len(rows), max(5, len(rows) // 5)))
    tail = rows[-n_tail:]
    cd = sum(r[0] for r in tail) / len(tail)
    cl = sum(r[1] for r in tail) / len(tail)
    return cl, cd


def parse_yplus(case: Path) -> dict | None:
    hits = list(Path(case).glob("postProcessing/yPlus/*/yPlus.dat"))
    latest = _latest_time_file(hits)
    if latest is None:
        return None
    last = None
    for ln in latest.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        parts = ln.split()
        if len(parts) < 5 or parts[1] != "airfoil":
            continue
        last = {
            "min": float(parts[2]),
            "max": float(parts[3]),
            "mean": float(parts[4]),
        }
    return last


def parse_layer_coverage(log: str) -> float | None:
    hits = _re.findall(r"Extruding\s+\d+\s+faces\s+\(([\d.]+)%\s+of\s+\d+\)", log)
    if not hits:
        hits = _re.findall(r"Extruding\s+\d+\s+out of\s+\d+\s+faces\s+\(([\d.]+)%\)", log)
    if not hits:
        hits = _re.findall(r"([\d.]+)%\s+of\s+\d+\s+faces", log)
    return float(hits[-1]) if hits else None


def parse_surface_cells(case: Path) -> int | None:
    path = Path(case) / "constant" / "polyMesh" / "boundary"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _re.search(r"airfoil\s*\{[^}]*nFaces\s+(\d+)", text, _re.DOTALL)
    return int(m.group(1)) if m else None


def parse_cli(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true", help="write one SST case and stop")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--iters", type=int, default=N_ITERS)
    ap.add_argument("--section", default=DEFAULT_SECTION, help="NACA 4-digit code (default 4406)")
    ap.add_argument("--re", type=float, default=RE)
    ap.add_argument("--alphas", type=float, nargs="+", default=list(ALPHAS))
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--tu", type=float, default=TU_NCRIT9, help="freestream Tu as a fraction")
    ap.add_argument(
        "--mesh", choices=("snappy", "cgrid"), default="snappy",
        help="snappy+layers (rung A default) or structured C-grid (A0 mesher fix)",
    )
    ap.add_argument("--cgrid-tangent", type=int, default=N_CGRID_TANGENT,
                    help="C-grid cells along each airfoil surface (default 48)")
    ap.add_argument("--cgrid-normal", type=int, default=N_CGRID_NORMAL,
                    help="C-grid cells from the wall to the far field (default 60)")
    ap.add_argument("--cgrid-wake", type=int, default=N_CGRID_WAKE,
                    help="C-grid cells along the wake (default 32)")
    ap.add_argument("--cgrid-far", type=float, default=R_OUTER / CHORD,
                    help="far-field radius in chords (default 8)")
    ap.add_argument("--cgrid-wake-len", type=float, default=WAKE_LEN / CHORD,
                    help="wake length downstream of the trailing edge, in chords (default 16)")
    ap.add_argument("--cgrid-end-cell", type=float, default=None,
                    help="cluster the LE and TE cells to this fraction of chord")
    ap.add_argument("--cgrid-max-ratio", type=float, default=1.2,
                    help="max adjacent tangential cell-size ratio when clustering")
    ap.add_argument("--cgrid-normal-growth", type=float, default=None,
                    help="cap on wall-normal growth; the normal count is raised if needed")
    ap.add_argument("--cgrid-refine", type=int, default=1,
                    help="after the main angles, solve one angle on a grid refined by this factor")
    ap.add_argument("--cgrid-refine-alpha", type=float, default=None,
                    help="angle for the refined grid (default: the last --alphas value)")
    return ap.parse_args(argv)


def cgrid_jobs(ns) -> list[dict]:
    """Solve campaigns. A refine factor adds one finer grid at a single angle."""
    base = {
        "alphas": [float(x) for x in ns.alphas],
        "n_tangent": int(ns.cgrid_tangent),
        "n_normal": int(ns.cgrid_normal),
        "n_wake": int(ns.cgrid_wake),
        "far_chords": float(ns.cgrid_far),
        "wake_chords": float(ns.cgrid_wake_len),
        "end_cell_frac": None if ns.cgrid_end_cell is None else float(ns.cgrid_end_cell),
        "max_ratio": float(ns.cgrid_max_ratio),
        "normal_growth": (
            None if ns.cgrid_normal_growth is None else float(ns.cgrid_normal_growth)
        ),
        "yplus_target": 0.8,
        "tag": "base",
    }
    jobs = [base]
    refine = int(ns.cgrid_refine or 1)
    if refine > 1:
        fine = dict(base)
        fine["n_tangent"] *= refine
        fine["n_normal"] *= refine
        fine["n_wake"] *= refine
        if fine["end_cell_frac"] is not None:
            fine["end_cell_frac"] = float(fine["end_cell_frac"]) / refine
        fine["yplus_target"] = 0.8 / refine
        alpha = base["alphas"][-1] if ns.cgrid_refine_alpha is None else ns.cgrid_refine_alpha
        fine["alphas"] = [float(alpha)]
        fine["tag"] = f"refine{refine}"
        jobs.append(fine)
    return jobs


def _cgrid_kwargs(job: dict | None) -> dict:
    if not job:
        return {}
    return {
        key: job[key]
        for key in (
            "n_tangent", "n_normal", "n_wake", "far_chords", "wake_chords",
            "end_cell_frac", "max_ratio", "normal_growth", "yplus_target",
        )
    }


def _past_cutoff(now: datetime | None = None) -> bool:
    t = now or datetime.now(UTC).astimezone()
    return (t.hour, t.minute) >= (CUTOFF_HOUR, CUTOFF_MINUTE)


def _write_progress(out: Path, payload: dict) -> None:
    (out / "progress.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _is_a0(section: str, re: float, alphas: list[float]) -> bool:
    return (
        parse_naca4_code(section) == (0.0, 0.0, 0.12)
        and abs(float(re) - 6.0e6) / 6.0e6 < 0.05
        and {round(float(a), 1) for a in alphas} >= {0.0, 5.0, 10.0}
    )


def _judge(summary: dict, *, section: str, re: float, alphas: list[float]) -> dict:
    points = summary.get("points") or {}
    if _is_a0(section, re, alphas):
        sst = points.get("kOmegaSST") or next(iter(points.values()), {})
        return verdict_a0(sst)
    sst = (points.get("kOmegaSST") or {}).get("4.0")
    lm = (points.get("kOmegaSSTLM") or {}).get("4.0")
    return verdict(
        sst_cl=None if not sst else sst.get("cl"),
        lm_cl=None if not lm else lm.get("cl"),
    )


def main(argv: list[str] | None = None) -> int:
    a = parse_cli(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    section = str(a.section)
    re_n = float(a.re)
    tu = float(a.tu)
    mesh = str(a.mesh)
    alphas = [float(x) for x in a.alphas]
    models = list(a.models)
    for m in models:
        if m not in MODELS:
            raise SystemExit(f"model must be one of {MODELS}, got {m!r}")

    n_iters = int(a.iters)
    campaigns = cgrid_jobs(a) if mesh == "cgrid" else [None]

    if a.build_only:
        write_case(
            out / "build_only", alpha_deg=alphas[0] if alphas else 4.0,
            model=models[0] if models else "kOmegaSST",
            n_iters=n_iters,
            section=section, re=re_n, tu=tu, mesh=mesh,
            **_cgrid_kwargs(campaigns[0]),
        )
        print(f"wrote {out / 'build_only'} y+={first_cell_yplus(re_n):.3f} section={section}")
        return 0

    summ_path = out / "summary.json"
    try:
        summary = json.loads(summ_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {
            "section": section, "re": re_n, "chord_m": CHORD, "tu": tu, "mesh": mesh,
            "ref_cl_4": REF_CL_4,
            "ref_cl_4_band": [REF_CL_4_LO, REF_CL_4_HI], "ref_cd_4": REF_CD_4,
            "yplus_first": first_cell_yplus(re_n), "points": {},
        }

    if a.analyze:
        v = _judge(summary, section=section, re=re_n, alphas=alphas)
        summary["verdict"] = v
        summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(v))
        return 0

    from fansim.cfd.runner import OpenFOAMRunner, image_available

    if not image_available():
        print("OpenFOAM image not available; wrote no solves. Use --build-only.", file=sys.stderr)
        return 2

    for campaign in campaigns:
        camp_tag = "base" if campaign is None else campaign["tag"]
        ckw = _cgrid_kwargs(campaign)
        run_alphas = alphas if campaign is None else campaign["alphas"]
        bucket = summary if camp_tag == "base" else summary.setdefault(camp_tag, {"points": {}})
        points = bucket.setdefault("points", {})
        yp_req = first_cell_yplus(re_n) if campaign is None else float(campaign["yplus_target"])
        mesh_dir = out / ("_mesh" if camp_tag == "base" else f"_mesh_{camp_tag}")
        mesh_src = mesh_dir / "constant" / "polyMesh"
        if not (mesh_src / "points").is_file():
            write_case(
                mesh_dir, alpha_deg=0.0, model="kOmegaSST", n_iters=n_iters,
                section=section, re=re_n, tu=tu, mesh=mesh, **ckw,
            )
            mesh_run = OpenFOAMRunner(mesh_dir)
            mesh_run.run("blockMesh")
            coverage: float | None
            if mesh == "cgrid":
                mesh_run.run("checkMesh")
                coverage = 100.0
            else:
                mesh_run.run("surfaceFeatureExtract")
                mesh_run.run("snappyHexMesh -overwrite")
                snap_log = (mesh_dir / "logs" / "snappyHexMesh.log")
                coverage = None
                if snap_log.is_file():
                    coverage = parse_layer_coverage(
                        snap_log.read_text(encoding="utf-8", errors="replace"))
            mesh_info = {
                "kind": mesh,
                "layer_coverage_pct": coverage,
                "surface_cells": parse_surface_cells(mesh_dir),
                "yplus_requested": yp_req,
            }
            if camp_tag == "base":
                summary["mesh"] = mesh_info
            else:
                bucket["mesh"] = mesh_info
            summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        for model in models:
            points.setdefault(model, {})
            for alpha in run_alphas:
                key = f"{alpha:.1f}"
                if points[model].get(key, {}).get("cl") is not None:
                    continue
                if _past_cutoff():
                    _write_progress(out, {
                        "stopped": "cutoff", "next": [model, alpha], "grid": camp_tag,
                    })
                    summary["verdict"] = _judge(
                        summary, section=section, re=re_n, alphas=alphas)
                    summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                    print("stopped before 15:30 local; remaining units left for another day")
                    return 0
                tag = f"{model}_a{key}" if camp_tag == "base" else f"{camp_tag}_{model}_a{key}"
                case = out / tag
                _write_progress(out, {"current": tag, "start": time.time()})
                write_case(
                    case, alpha_deg=alpha, model=model, n_iters=n_iters,
                    section=section, re=re_n, tu=tu, mesh=mesh, **ckw,
                )
                dest = case / "constant" / "polyMesh"
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(mesh_src, dest)
                run = OpenFOAMRunner(case)
                t0 = time.time()
                if mesh == "cgrid":
                    run.run("potentialFoam -writep")
                run.run("simpleFoam")
                parsed = parse_cl_cd(case)
                cl, cd = (None, None) if parsed is None else parsed
                yp = parse_yplus(case)
                points[model][key] = {
                    "cl": cl, "cd": cd, "wall_s": time.time() - t0,
                    "yplus_first": yp_req,
                    "yplus": yp,
                }
                summary["verdict"] = _judge(
                    summary, section=section, re=re_n, alphas=alphas)
                summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(f"{tag} Cl={cl} Cd={cd} y+={yp}")
    print(json.dumps(summary.get("verdict")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
