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


def u_inf(re: float = RE, chord: float = CHORD) -> float:
    return float(re) * NU_AIR / float(chord)


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


N_CGRID_TANGENT = 40
N_CGRID_NORMAL = 80
R_OUTER = 12.0 * CHORD


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


def _cgrid_inner_outer(section: str):
    """Four airfoil arcs (TE→top→LE→bot→TE) and matching outer-circle arcs."""
    m, p, t = parse_naca4_code(section)
    pts = naca4(m, p, t, N_THETA)[:-1] * CHORD
    i_le = int(np.argmin(pts[:, 0]))
    i_top = int(np.argmax(pts[:, 1]))
    i_bot = int(np.argmin(pts[:, 1]))
    inner_corners = [pts[0], pts[i_top], pts[i_le], pts[i_bot]]
    arcs = [
        pts[0:i_top + 1],
        pts[i_top:i_le + 1],
        pts[i_le:i_bot + 1],
        np.vstack([pts[i_bot:], pts[0:1]]),
    ]
    centre = np.array([0.25 * CHORD, 0.0])

    def _outer(p: np.ndarray) -> np.ndarray:
        v = p - centre
        nrm = float(np.linalg.norm(v))
        if nrm < 1e-16:
            v = np.array([0.0, 1.0])
            nrm = 1.0
        return centre + R_OUTER * v / nrm

    outer_arcs = [np.vstack([_outer(p) for p in arc]) for arc in arcs]
    return arcs, outer_arcs, inner_corners, [_outer(c) for c in inner_corners]


def _pt(p: np.ndarray, z: float) -> str:
    return f"({float(p[0]):.8g} {float(p[1]):.8g} {z:.8g})"


def _cgrid_block_mesh_dict(*, section: str, re: float) -> str:
    """Structured 4-block O-grid (closed TE). Inner patch is airfoil; outer is freestream."""
    arcs, outer_arcs, inner_c, outer_c = _cgrid_inner_outer(section)
    ds = wall_spacing_m(re)
    gy = _grading_last_over_first(ds, R_OUTER - 0.25 * CHORD, N_CGRID_NORMAL)
    nx, ny = N_CGRID_TANGENT, N_CGRID_NORMAL
    verts: list[str] = []
    for z in (0.0, SPAN):
        for p in inner_c:
            verts.append(f"    {_pt(p, z)}")
        for p in outer_c:
            verts.append(f"    {_pt(p, z)}")
    # z=0: 0-3 inner TE,top,LE,bot; 4-7 outer. z=SPAN: 8-11 inner, 12-15 outer.
    hexes = [
        f"    hex (0 4 5 1 8 12 13 9) ({ny} {nx} 1) simpleGrading ({gy:.8g} 1 1)",
        f"    hex (1 5 6 2 9 13 14 10) ({ny} {nx} 1) simpleGrading ({gy:.8g} 1 1)",
        f"    hex (2 6 7 3 10 14 15 11) ({ny} {nx} 1) simpleGrading ({gy:.8g} 1 1)",
        f"    hex (3 7 4 0 11 15 12 8) ({ny} {nx} 1) simpleGrading ({gy:.8g} 1 1)",
    ]
    # spline intermediates on each airfoil arc (0-1, 1-2, 2-3, 3-0) and outer (4-5, ...).
    pairs = ((0, 1), (1, 2), (2, 3), (3, 0))
    edge_lines = ["edges", "("]
    for (a, b), arc in zip(pairs, arcs):
        mid = arc[1:-1]
        if len(mid):
            body = " ".join(_pt(p, 0.0) for p in mid)
            body_z = " ".join(_pt(p, SPAN) for p in mid)
            edge_lines.append(f"    spline {a} {b} ( {body} )")
            edge_lines.append(f"    spline {a + 8} {b + 8} ( {body_z} )")
    for (a, b), arc in zip(((4, 5), (5, 6), (6, 7), (7, 4)), outer_arcs):
        mid = arc[1:-1]
        if len(mid):
            body = " ".join(_pt(p, 0.0) for p in mid)
            body_z = " ".join(_pt(p, SPAN) for p in mid)
            edge_lines.append(f"    spline {a} {b} ( {body} )")
            edge_lines.append(f"    spline {a + 8} {b + 8} ( {body_z} )")
    edge_lines.append(");")
    return "\n".join([
        _foam("dictionary", "blockMeshDict"),
        f"// cgrid firstLayer {ds:.8g} m  y+_req {first_cell_yplus(re):.3f}",
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
        "            (0 1 9 8)",
        "            (1 2 10 9)",
        "            (2 3 11 10)",
        "            (3 0 8 11)",
        "        );",
        "    }",
        "    freestream",
        "    {",
        "        type patch;",
        "        faces",
        "        (",
        "            (4 12 13 5)",
        "            (5 13 14 6)",
        "            (6 14 15 7)",
        "            (7 15 12 4)",
        "        );",
        "    }",
        "    front { type empty; faces ((8 9 13 12) (9 10 14 13) (10 11 15 14) (11 8 12 15)); }",
        "    back  { type empty; faces ((0 4 5 1) (1 5 6 2) (2 6 7 3) (3 7 4 0)); }",
        ");",
        "mergePatchPairs ();",
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


def _field_scalar(name: str, dims: str, value: float, wall: str, empty: bool = True) -> str:
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

    u = u_inf(re)
    a = math.radians(float(alpha_deg))
    ux, uy = u * math.cos(a), u * math.sin(a)
    k = 1.5 * (tu_frac * u) ** 2
    omega = math.sqrt(k) / (CMU ** 0.25 * 0.1 * CHORD)
    lift = (-math.sin(a), math.cos(a), 0.0)
    drag = (math.cos(a), math.sin(a), 0.0)
    aref = CHORD * SPAN
    lm = model == "kOmegaSSTLM"

    if mesh == "cgrid":
        (case / "system" / "blockMeshDict").write_text(
            _cgrid_block_mesh_dict(section=section, re=re), encoding="utf-8")
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
        (
            "    \"(U|k|omega)\" { solver smoothSolver; smoother symGaussSeidel; "
            "tolerance 1e-8; relTol 0.1; }"
        ),
        extra_solvers.rstrip(),
        "}",
        "SIMPLE",
        "{",
        "    nNonOrthogonalCorrectors 1;",
        "    residualControl { p 1e-4; U 1e-4; k 1e-4; omega 1e-4; "
        + extra_resid + "}",
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
        + f"transportModel Newtonian;\nnu {NU_AIR};\n",
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
        "    front       { type empty; }",
        "    back        { type empty; }",
        "}",
        "",
    ]), encoding="utf-8")
    (case / "0" / "k").write_text(
        _field_scalar("k", "[0 2 -2 0 0 0 0]", k, f"type kqRWallFunction; value uniform {k:.8g};"),
        encoding="utf-8",
    )
    (case / "0" / "omega").write_text(
        _field_scalar(
            "omega", "[0 0 -1 0 0 0 0]", omega,
            f"type omegaWallFunction; value uniform {omega:.8g};",
        ),
        encoding="utf-8",
    )
    (case / "0" / "nut").write_text(
        _field_scalar(
            "nut", "[0 2 -1 0 0 0 0]", 0.0,
            "type nutUSpaldingWallFunction; value uniform 0;",
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
            ),
            encoding="utf-8",
        )
        (case / "0" / "ReThetat").write_text(
            _field_scalar(
                "ReThetat", "[0 0 0 0 0 0 0]", re_th,
                "type zeroGradient;",
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


def parse_cl_cd(case: Path) -> tuple[float, float] | None:
    hits = sorted(case.glob("postProcessing/forceCoeffs1/*/coefficient.dat"))
    if not hits:
        hits = sorted(case.glob("postProcessing/forceCoeffs1/*/forceCoeffs.dat"))
    if not hits:
        return None
    rows = []
    for ln in hits[-1].read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        parts = ln.split()
        if len(parts) >= 5:
            rows.append((float(parts[1]), float(parts[4])))  # Cd, Cl
        elif len(parts) >= 3:
            rows.append((float(parts[1]), float(parts[2])))
    if len(rows) < 5:
        return None
    tail = rows[-max(5, len(rows) // 5):]
    cd = sum(r[0] for r in tail) / len(tail)
    cl = sum(r[1] for r in tail) / len(tail)
    return cl, cd


def parse_yplus(case: Path) -> dict | None:
    hits = sorted(Path(case).glob("postProcessing/yPlus/*/yPlus.dat"))
    if not hits:
        return None
    last = None
    for ln in hits[-1].read_text(encoding="utf-8", errors="replace").splitlines():
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
        help="snappy+layers (rung A default) or structured O-grid (A0 mesher fix)",
    )
    return ap.parse_args(argv)


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

    if a.build_only:
        write_case(
            out / "build_only", alpha_deg=alphas[0] if alphas else 4.0,
            model=models[0] if models else "kOmegaSST",
            section=section, re=re_n, tu=tu, mesh=mesh,
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

    n_iters = int(a.iters)
    points = summary.setdefault("points", {})
    mesh_dir = out / "_mesh"
    mesh_src = mesh_dir / "constant" / "polyMesh"
    if not (mesh_src / "points").is_file():
        write_case(
            mesh_dir, alpha_deg=0.0, model="kOmegaSST", n_iters=n_iters,
            section=section, re=re_n, tu=tu, mesh=mesh,
        )
        mesh_run = OpenFOAMRunner(mesh_dir)
        mesh_run.run("blockMesh")
        coverage: float | None
        if mesh == "cgrid":
            coverage = 100.0
        else:
            mesh_run.run("surfaceFeatureExtract")
            mesh_run.run("snappyHexMesh -overwrite")
            snap_log = (mesh_dir / "logs" / "snappyHexMesh.log")
            coverage = None
            if snap_log.is_file():
                coverage = parse_layer_coverage(
                    snap_log.read_text(encoding="utf-8", errors="replace"))
        summary["mesh"] = {
            "kind": mesh,
            "layer_coverage_pct": coverage,
            "surface_cells": parse_surface_cells(mesh_dir),
            "yplus_requested": first_cell_yplus(re_n),
        }
        summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for model in models:
        points.setdefault(model, {})
        for alpha in alphas:
            key = f"{alpha:.1f}"
            if points[model].get(key, {}).get("cl") is not None:
                continue
            if _past_cutoff():
                _write_progress(out, {"stopped": "cutoff", "next": [model, alpha]})
                summary["verdict"] = _judge(
                    summary, section=section, re=re_n, alphas=alphas)
                summ_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print("stopped before 15:30 local; remaining units left for another day")
                return 0
            tag = f"{model}_a{key}"
            case = out / tag
            _write_progress(out, {"current": tag, "start": time.time()})
            write_case(
                case, alpha_deg=alpha, model=model, n_iters=n_iters,
                section=section, re=re_n, tu=tu, mesh=mesh,
            )
            dest = case / "constant" / "polyMesh"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(mesh_src, dest)
            run = OpenFOAMRunner(case)
            t0 = time.time()
            run.run("simpleFoam")
            parsed = parse_cl_cd(case)
            cl, cd = (None, None) if parsed is None else parsed
            yp = parse_yplus(case)
            points[model][key] = {
                "cl": cl, "cd": cd, "wall_s": time.time() - t0,
                "yplus_first": first_cell_yplus(re_n),
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
