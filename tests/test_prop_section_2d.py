"""Rung A runner pieces that need no CFD: section, y+, case files, verdict rules."""
from __future__ import annotations

import importlib.util
import inspect
import itertools
import re
from pathlib import Path

import numpy as np
import pytest

from fansim.geometry.airfoil import naca4

_SPEC = importlib.util.spec_from_file_location(
    "prop_section_2d", Path(__file__).resolve().parents[1] / "scripts" / "prop_section_2d.py")
ps = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ps)


def test_section_is_builder_naca4406():
    loop = ps.section_xy()
    ref = naca4(0.04, 0.4, 0.06, 60)
    assert loop.shape == ref.shape
    np.testing.assert_allclose(loop, ref, atol=1e-12)


def test_first_cell_yplus_at_most_one():
    yp = ps.first_cell_yplus(re=ps.RE, chord=ps.CHORD)
    assert yp <= 1.0 + 1e-12


def test_case_builds_sst_without_solve(tmp_path):
    case = ps.write_case(tmp_path / "sst", alpha_deg=4.0, model="kOmegaSST")
    text = (case / "constant" / "turbulenceProperties").read_text(encoding="utf-8")
    assert "kOmegaSST" in text
    assert "kOmegaSSTLM" not in text
    block = (case / "system" / "blockMeshDict").read_text(encoding="utf-8")
    assert "empty" in block
    snappy = (case / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    assert "airfoil" in snappy
    assert (case / "constant" / "triSurface" / "airfoil.stl").is_file()
    ctrl = (case / "system" / "controlDict").read_text(encoding="utf-8")
    assert "forceCoeffs" in ctrl
    assert (case / "0" / "U").is_file()
    assert (case / "0" / "omega").is_file()
    assert not (case / "0" / "gammaInt").exists()


def test_case_builds_sstlm_fields(tmp_path):
    case = ps.write_case(tmp_path / "lm", alpha_deg=4.0, model="kOmegaSSTLM")
    text = (case / "constant" / "turbulenceProperties").read_text(encoding="utf-8")
    assert "kOmegaSSTLM" in text
    assert (case / "0" / "gammaInt").is_file()
    assert (case / "0" / "ReThetat").is_file()


def test_alphas_and_models_match_prereg():
    assert ps.ALPHAS == (0.0, 2.0, 4.0, 6.0, 8.0)
    assert ps.MODELS == ("kOmegaSST", "kOmegaSSTLM")
    assert ps.RE == 8.0e4
    assert ps.REF_CL_4 == pytest.approx(0.855)


def test_parse_coefficient_dat_uses_cl_column(tmp_path):
    d = tmp_path / "postProcessing" / "forceCoeffs1" / "0"
    d.mkdir(parents=True)
    (d / "coefficient.dat").write_text(
        "# Time\tCd\tCd(f)\tCd(r)\tCl\n"
        + "".join(f"20\t0.04\t0.01\t0.03\t0.68{i}\n" for i in range(6)),
        encoding="utf-8",
    )
    cl, cd = ps.parse_cl_cd(tmp_path)
    assert cd == pytest.approx(0.04)
    assert cl == pytest.approx(0.683, abs=0.02)


def test_parse_cl_cd_prefers_numeric_latest_time(tmp_path):
    root = tmp_path / "postProcessing" / "forceCoeffs1"
    for t, cd, cl in (("80", 0.02, 0.1), ("2000", 0.008, 0.0)):
        d = root / t
        d.mkdir(parents=True)
        (d / "coefficient.dat").write_text(
            "# Time\tCd\tCd(f)\tCd(r)\tCl\n"
            + "".join(f"{t}\t{cd}\t0.01\t0.01\t{cl}\n" for _ in range(6)),
            encoding="utf-8",
        )
    cl, cd = ps.parse_cl_cd(tmp_path)
    assert cd == pytest.approx(0.008)
    assert cl == pytest.approx(0.0)


def test_verdict_rules():
    # A1: SST ≥ 25 % below reference and SST-LM within 10 %.
    assert ps.verdict(sst_cl=0.855 * 0.70, lm_cl=0.855 * 0.95)["verdict"] == "A1"
    # A2: SST within 10 % of the reference.
    assert ps.verdict(sst_cl=0.855 * 0.95, lm_cl=0.50)["verdict"] == "A2"
    assert ps.verdict(sst_cl=0.855 * 0.80, lm_cl=0.50)["verdict"] == "report to Claude"
    assert ps.verdict(sst_cl=None, lm_cl=0.85)["verdict"] == "INCONCLUSIVE"


def test_parse_naca4_code():
    assert ps.parse_naca4_code("4406") == (0.04, 0.4, 0.06)
    assert ps.parse_naca4_code("0012") == (0.0, 0.0, 0.12)
    assert ps.parse_naca4_code("NACA0012") == (0.0, 0.0, 0.12)
    with pytest.raises(ValueError):
        ps.parse_naca4_code("12")


def test_naca0012_case_is_symmetric_twelve_percent(tmp_path):
    case = ps.write_case(
        tmp_path / "n0012", alpha_deg=0.0, model="kOmegaSST", section="0012")
    stl = (case / "constant" / "triSurface" / "airfoil.stl").read_text(encoding="utf-8")
    ys = [float(ln.split()[2]) for ln in stl.splitlines() if ln.strip().startswith("vertex")]
    half_t = 0.06 * ps.CHORD
    assert max(ys) == pytest.approx(half_t, rel=0.08)
    assert min(ys) == pytest.approx(-half_t, rel=0.08)


def test_higher_re_thins_the_first_layer(tmp_path):
    lo = ps.write_case(tmp_path / "lo", alpha_deg=0.0, model="kOmegaSST", re=8.0e4)
    hi = ps.write_case(tmp_path / "hi", alpha_deg=0.0, model="kOmegaSST", re=6.0e6)

    def first_layer(case: Path) -> float:
        for ln in (case / "system" / "snappyHexMeshDict").read_text(encoding="utf-8").splitlines():
            if "firstLayerThickness" in ln:
                return float(ln.split()[1].rstrip(";"))
        raise AssertionError("no firstLayerThickness")

    assert first_layer(hi) < first_layer(lo) * 0.2


def test_tu_changes_freestream_k(tmp_path):
    quiet = ps.write_case(
        tmp_path / "q", alpha_deg=0.0, model="kOmegaSST", tu=0.001)
    noisy = ps.write_case(
        tmp_path / "n", alpha_deg=0.0, model="kOmegaSST", tu=0.05)
    k_q = float(
        next(
            ln for ln in (quiet / "0" / "k").read_text(encoding="utf-8").splitlines()
            if "internalField" in ln
        ).split()[-1].rstrip(";")
    )
    k_n = float(
        next(
            ln for ln in (noisy / "0" / "k").read_text(encoding="utf-8").splitlines()
            if "internalField" in ln
        ).split()[-1].rstrip(";")
    )
    assert k_n > k_q * 10


def test_cli_defaults_are_rung_a():
    ns = ps.parse_cli([])
    assert ns.section == "4406"
    assert ns.re == pytest.approx(8.0e4)
    assert list(ns.alphas) == [0.0, 2.0, 4.0, 6.0, 8.0]
    assert list(ns.models) == ["kOmegaSST", "kOmegaSSTLM"]
    assert ns.tu == pytest.approx(ps.TU_NCRIT9)


def test_cli_a0_flags():
    ns = ps.parse_cli(
        ["--section", "0012", "--re", "6e6", "--alphas", "0", "5", "10",
         "--models", "kOmegaSST", "--tu", "0.001", "--mesh", "cgrid"])
    assert ns.section == "0012"
    assert ns.re == pytest.approx(6.0e6)
    assert list(ns.alphas) == [0.0, 5.0, 10.0]
    assert list(ns.models) == ["kOmegaSST"]
    assert ns.tu == pytest.approx(0.001)
    assert ns.mesh == "cgrid"


def test_cli_default_mesh_is_snappy():
    assert ps.parse_cli([]).mesh == "snappy"


def test_cgrid_case_has_no_snappy_and_clusters_the_wall(tmp_path):
    case = ps.write_case(
        tmp_path / "cgrid", alpha_deg=0.0, model="kOmegaSST",
        section="0012", re=6.0e6, mesh="cgrid")
    assert not (case / "system" / "snappyHexMeshDict").exists()
    assert not (case / "constant" / "triSurface" / "airfoil.stl").exists()
    block = (case / "system" / "blockMeshDict").read_text(encoding="utf-8")
    assert "spline" in block or "polyLine" in block
    assert "airfoil" in block
    assert "empty" in block
    ds = ps.wall_spacing_m(6.0e6)
    assert f"{ds:.8g}" in block or "simpleGrading" in block


def test_cgrid_is_wake_cut_not_trailing_edge_o(tmp_path):
    """C-grid: cut in the wake, two foil wall faces, lower/upper 0012 not swapped."""
    case = ps.write_case(
        tmp_path / "cgrid_topo", alpha_deg=0.0, model="kOmegaSST",
        section="0012", re=6.0e6, mesh="cgrid")
    block = (case / "system" / "blockMeshDict").read_text(encoding="utf-8")
    assert block.count("hex ") == 4
    airfoil = block.split("airfoil", 1)[1].split("freestream", 1)[0]
    wall_faces = [
        ln for ln in airfoil.splitlines()
        if ln.strip().startswith("(") and any(c.isdigit() for c in ln)
    ]
    assert len(wall_faces) == 2
    corners, splines = ps._cgrid_geometry("0012")
    te, le, outlet, _le_out, te_lo, _out_lo, te_hi, _out_hi, te_hi_in, outlet_hi = corners
    assert outlet[0] > te[0] + 10.0 * ps.CHORD
    assert te_lo[1] < 0.0 < te_hi[1]
    assert le[0] < te[0]
    np.testing.assert_allclose(te_hi_in, te)
    np.testing.assert_allclose(outlet_hi, outlet)
    lower_mid = splines[(0, 1)]
    upper_mid = splines[(1, 8)]
    assert np.max(lower_mid[:, 1]) <= 1e-9
    assert np.min(upper_mid[:, 1]) >= -1e-9
    assert "mergePatchPairs" in block
    assert "wakeLower" in block
    assert "outlet" in block


def test_cgrid_schemes_stay_finite_on_a_50_chord_mesh(tmp_path):
    """Unlimited gradients blow up the 50-chord gate mesh around step 18.

    A limited gradient keeps the same mesh finite, and the pressure smoother
    has to be DICGaussSeidel or the stiff system never actually converges.
    """
    case = ps.write_case(
        tmp_path / "cgrid_scheme", alpha_deg=0.0, model="kOmegaSST",
        section="0012", re=6.0e6, mesh="cgrid")
    schemes = (case / "system" / "fvSchemes").read_text(encoding="utf-8")
    sol = (case / "system" / "fvSolution").read_text(encoding="utf-8")
    assert "cellLimited Gauss linear 1" in schemes
    assert "smoother DICGaussSeidel" in sol
    assert "smoother GaussSeidel;" not in sol
    assert "consistent      yes;" in sol
    assert "fields { p 0.1; }" in sol
    assert "equations { U 0.15; k 0.15; omega 0.15;" in sol


def test_cgrid_keeps_re_without_supersonic_u(tmp_path):
    """Incompressible similarity: Re 6e6 at U=1 m/s, not physical U≈900 m/s."""
    case = ps.write_case(
        tmp_path / "cgrid_re", alpha_deg=0.0, model="kOmegaSST",
        section="0012", re=6.0e6, mesh="cgrid")
    ctrl = (case / "system" / "controlDict").read_text(encoding="utf-8")
    trans = (case / "constant" / "transportProperties").read_text(encoding="utf-8")
    u = None
    nu = None
    for ln in ctrl.splitlines():
        if "magUInf" in ln:
            u = float(ln.split()[1].rstrip(";"))
    for ln in trans.splitlines():
        if ln.strip().startswith("nu "):
            nu = float(ln.split()[1].rstrip(";"))
    assert u is not None and nu is not None
    assert u == pytest.approx(ps.CGRID_U)
    assert u < 50.0
    assert u * ps.CHORD / nu == pytest.approx(6.0e6, rel=1e-8)


def test_verdict_a0_ladson_windows():
    ok = {
        "0.0": {"cl": 0.0, "cd": 0.00808},
        "5.0": {"cl": 0.537, "cd": 0.0085},
        "10.0": {"cl": 1.063, "cd": 0.012},
    }
    assert ps.verdict_a0(ok)["verdict"] == "PASS"
    low_lift = dict(ok)
    low_lift["5.0"] = {"cl": 0.40, "cd": 0.0085}
    assert ps.verdict_a0(low_lift)["verdict"] == "FAIL"
    fat_drag = dict(ok)
    fat_drag["0.0"] = {"cl": 0.0, "cd": 0.012}
    assert ps.verdict_a0(fat_drag)["verdict"] == "FAIL"
    assert ps.verdict_a0({})["verdict"] == "INCONCLUSIVE"


def test_case_writes_yplus_function_object(tmp_path):
    case = ps.write_case(tmp_path / "yp", alpha_deg=0.0, model="kOmegaSST")
    ctrl = (case / "system" / "controlDict").read_text(encoding="utf-8")
    assert "yPlus" in ctrl
    assert "fieldFunctionObjects" in ctrl


def test_parse_yplus_airfoil(tmp_path):
    d = tmp_path / "postProcessing" / "yPlus" / "2000"
    d.mkdir(parents=True)
    (d / "yPlus.dat").write_text(
        "# Time patch min max average\n2000 airfoil 0.2 1.5 0.6\n",
        encoding="utf-8",
    )
    yp = ps.parse_yplus(tmp_path)
    assert yp == {"min": 0.2, "max": 1.5, "mean": 0.6}


def test_parse_layer_coverage_and_surface_cells(tmp_path):
    log = "Extruding 800 faces (95.2% of 840).\n"
    assert ps.parse_layer_coverage(log) == pytest.approx(95.2)
    of2406 = "Extruding 0 out of 2592 faces (0%). Removed extrusion at 1483 faces.\n"
    assert ps.parse_layer_coverage(of2406) == pytest.approx(0.0)
    bound = tmp_path / "constant" / "polyMesh"
    bound.mkdir(parents=True)
    (bound / "boundary").write_text(
        "2\n(\nairfoil\n{\n    type wall;\n    nFaces 640;\n    startFace 12;\n}\n"
        "freestream\n{\n    type patch;\n    nFaces 400;\n    startFace 652;\n}\n)\n",
        encoding="utf-8",
    )
    assert ps.parse_surface_cells(tmp_path) == 640


_NUM = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?")


def _matching_paren(text: str, open_at: int) -> int:
    depth = 0
    for j in range(open_at, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("unbalanced parenthesis in blockMeshDict")


def _parse_grading_expr(text: str, i: int):
    while i < len(text) and text[i].isspace():
        i += 1
    if i >= len(text):
        return None, i
    if text[i] == "(":
        items = []
        i += 1
        while True:
            while i < len(text) and text[i].isspace():
                i += 1
            if i < len(text) and text[i] == ")":
                return items, i + 1
            item, i = _parse_grading_expr(text, i)
            items.append(item)
        return items, i
    match = _NUM.match(text, i)
    if match is None:
        raise ValueError(f"expected number in grading near {text[i:i + 24]!r}")
    return float(match.group(0)), match.end()


def _grading_directions(body: str):
    dirs = []
    i = 0
    while len(dirs) < 3:
        item, i = _parse_grading_expr(body, i)
        if item is None:
            break
        dirs.append(item)
    if len(dirs) != 3:
        raise ValueError(f"simpleGrading needs 3 directions, got {dirs!r}")
    return dirs


def _geom_cell_sizes(length: float, n: int, expansion: float) -> list[float]:
    """OpenFOAM simpleGrading: expansion is last cell / first cell along the edge."""
    if n <= 0:
        return []
    if n == 1 or abs(expansion - 1.0) <= 1e-12:
        return [length / n] * n
    r = expansion ** (1.0 / (n - 1))
    if abs(r - 1.0) <= 1e-14:
        return [length / n] * n
    first = length * (r - 1.0) / (r ** n - 1.0)
    return [first * (r ** i) for i in range(n)]


def _direction_cell_sizes(length: float, n: int, grading) -> list[float]:
    if isinstance(grading, (int, float)):
        sections = [(1.0, 1.0, float(grading))]
    else:
        sections = [(float(s[0]), float(s[1]), float(s[2])) for s in grading]
    block_sum = sum(s[0] for s in sections)
    div_sum = sum(s[1] for s in sections)
    sections = [(s[0] / block_sum, s[1] / div_sum, s[2]) for s in sections]
    counts = [int(s[1] * n + 0.5) for s in sections]
    drift = n - sum(counts)
    if counts and drift:
        biggest = max(range(len(counts)), key=lambda i: counts[i])
        counts[biggest] += drift
    sizes: list[float] = []
    for (block_frac, _div_frac, expansion), n_cells in zip(sections, counts):
        sizes.extend(_geom_cell_sizes(block_frac * length, n_cells, expansion))
    return sizes


def _polyline_length(pts: list[tuple[float, float]]) -> float:
    total = 0.0
    for a, b in itertools.pairwise(pts):
        total += float(np.hypot(b[0] - a[0], b[1] - a[1]))
    return total


def _size_ratio(a: float, b: float) -> float:
    lo = min(abs(a), abs(b))
    if lo <= 0.0:
        return float("inf")
    return max(abs(a), abs(b)) / lo


def _max_step_ratio(sizes: list[float]) -> float:
    if len(sizes) < 2:
        return 1.0
    return max(_size_ratio(a, b) for a, b in itertools.pairwise(sizes))


def measure_cgrid(block_mesh_text: str, chord: float) -> dict:
    """Cell sizes implied by a C-grid blockMeshDict (no OpenFOAM run).

    Tangential size is arc length along the wall or wake edge. simpleGrading
    matches OpenFOAM: one number is last/first, and a list of
    (length fraction, cell fraction, expansion) is multi-grading.
    """
    vsec = block_mesh_text.split("vertices", 1)[1].split("blocks", 1)[0]
    verts = []
    for raw in re.findall(r"\(([^()]*)\)", vsec):
        parts = raw.split()
        verts.append((float(parts[0]), float(parts[1]), float(parts[2])))
    xy = [(x, y) for x, y, _z in verts]

    splines: dict[tuple[int, int], list[tuple[float, float]]] = {}
    for line in block_mesh_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("spline "):
            continue
        head, rest = stripped.split("(", 1)
        ids = [int(tok) for tok in head.split()[1:3]]
        if ids[0] >= 10:
            continue
        pts = []
        for raw in re.findall(r"\(([^()]*)\)", rest):
            parts = raw.split()
            pts.append((float(parts[0]), float(parts[1])))
        splines[(ids[0], ids[1])] = pts

    def edge_length(a: int, b: int) -> float:
        if (a, b) in splines:
            pts = [xy[a], *splines[(a, b)], xy[b]]
        elif (b, a) in splines:
            pts = [xy[a], *splines[(b, a)][::-1], xy[b]]
        else:
            pts = [xy[a], xy[b]]
        return _polyline_length(pts)

    hexes = []
    cursor = 0
    while True:
        at = block_mesh_text.find("hex (", cursor)
        if at < 0:
            break
        open_v = block_mesh_text.find("(", at)
        close_v = _matching_paren(block_mesh_text, open_v)
        open_n = block_mesh_text.find("(", close_v)
        close_n = _matching_paren(block_mesh_text, open_n)
        line_end = block_mesh_text.find("\n", close_n)
        chunk = block_mesh_text[close_n: line_end if line_end > 0 else len(block_mesh_text)]
        if "edgeGrading" in chunk:
            g_at = chunk.find("edgeGrading")
            open_g = block_mesh_text.find("(", close_n + g_at)
            close_g = _matching_paren(block_mesh_text, open_g)
            body = block_mesh_text[open_g + 1:close_g]
            grading = []
            gi = 0
            while len(grading) < 12:
                item, gi = _parse_grading_expr(body, gi)
                if item is None:
                    break
                grading.append(item)
            if len(grading) != 12:
                raise ValueError(f"edgeGrading needs 12 edges, got {len(grading)}")
        else:
            g_at = block_mesh_text.find("simpleGrading", close_n)
            open_g = block_mesh_text.find("(", g_at)
            close_g = _matching_paren(block_mesh_text, open_g)
            grading = _grading_directions(block_mesh_text[open_g + 1:close_g])
        ids = [int(tok) for tok in block_mesh_text[open_v + 1:close_v].split()]
        counts = [int(tok) for tok in block_mesh_text[open_n + 1:close_n].split()]
        hexes.append({"ids": ids, "counts": counts, "grading": grading})
        cursor = close_g

    by_edge = {(h["ids"][0], h["ids"][1]): h for h in hexes}
    lower = by_edge[(0, 1)]
    upper = by_edge[(1, 8)]

    def tangential(hex_rec) -> list[float]:
        a, b = hex_rec["ids"][0], hex_rec["ids"][1]
        return _direction_cell_sizes(edge_length(a, b), hex_rec["counts"][0], hex_rec["grading"][0])

    lo = tangential(lower)
    up = tangential(upper)
    span = abs(verts[10][2] - verts[0][2]) if len(verts) > 10 else 0.0
    foil_keys = {(0, 1), (1, 8)}
    wakes = [h for h in hexes if (h["ids"][0], h["ids"][1]) not in foil_keys]
    lower_wakes = sorted(
        (h for h in wakes if xy[h["ids"][0]][0] > xy[h["ids"][1]][0]),
        key=lambda h: xy[h["ids"][1]][0],
    )
    upper_wakes = sorted(
        (h for h in wakes if xy[h["ids"][0]][0] < xy[h["ids"][1]][0]),
        key=lambda h: xy[h["ids"][0]][0],
    )

    def _end_heights(hex_rec) -> tuple[float, float]:
        """First-cell height on the local-0 side and the local-1 side."""
        grading = hex_rec["grading"]
        n_y = hex_rec["counts"][1]
        if len(grading) == 3:
            height = _direction_cell_sizes(
                edge_length(hex_rec["ids"][0], hex_rec["ids"][3]), n_y, grading[1],
            )[0]
            return height, height
        h0 = _direction_cell_sizes(
            edge_length(hex_rec["ids"][0], hex_rec["ids"][3]), n_y, grading[4],
        )[0]
        h1 = _direction_cell_sizes(
            edge_length(hex_rec["ids"][1], hex_rec["ids"][2]), n_y, grading[5],
        )[0]
        return h0, h1

    def _chain(blocks: list[dict], lower_block: bool) -> tuple[list[float], list[float]]:
        sizes: list[float] = []
        aspects: list[float] = []
        for hex_rec in blocks:
            raw = tangential(hex_rec)
            h_local0, h_local1 = _end_heights(hex_rec)
            if lower_block:
                seq = list(reversed(raw))
                h_te, h_out = h_local1, h_local0
            else:
                seq = list(raw)
                h_te, h_out = h_local0, h_local1
            n_cells = len(seq)
            for j, dx in enumerate(seq):
                xi = 0.5 if n_cells <= 1 else j / (n_cells - 1)
                height = (1.0 - xi) * h_te + xi * h_out
                edges = (abs(dx), abs(height), span)
                short = min(edges)
                aspects.append(float("inf") if short <= 0.0 else max(edges) / short)
            sizes.extend(seq)
        return sizes, aspects

    wlo, asp_lo = _chain(lower_wakes, True)
    whi, asp_hi = _chain(upper_wakes, False)
    wake_slit_aspect = max(asp_lo + asp_hi)
    # Lower wall runs TE → LE. Upper wall runs LE → TE.
    # Wake chains are TE → outlet on both sides.
    le_cell = max(lo[-1], up[0])
    te_cell = max(lo[0], up[-1])
    foil_wake = max(_size_ratio(lo[0], wlo[0]), _size_ratio(up[-1], whi[0]))
    adjacent = max(
        _max_step_ratio(lo),
        _max_step_ratio(up),
        _max_step_ratio(wlo),
        _max_step_ratio(whi),
        foil_wake,
        _size_ratio(lo[-1], up[0]),
        _size_ratio(wlo[0], whi[0]),
    )
    ny = lower["counts"][1]
    gy = float(lower["grading"][1])
    normal_growth = 1.0 if ny < 2 else gy ** (1.0 / (ny - 1))
    centre = (0.25 * chord, 0.0)
    r_outer = float(np.hypot(xy[3][0] - centre[0], xy[3][1] - centre[1]))
    wake_len = float(xy[2][0] - xy[0][0])
    wake_cell_max = max(max(wlo), max(whi))
    return {
        "n_tangent": lower["counts"][0],
        "n_normal": ny,
        "n_wake": sum(h["counts"][0] for h in lower_wakes),
        "wake_cell_max": wake_cell_max,
        "wake_slit_aspect": wake_slit_aspect,
        "n_tangent_upper": upper["counts"][0],
        "r_outer": r_outer,
        "wake_len": wake_len,
        "le_cell": le_cell,
        "te_cell": te_cell,
        "foil_edge_length": edge_length(0, 1),
        "foil_ratio_max": max(_max_step_ratio(lo), _max_step_ratio(up)),
        "adjacent_ratio": adjacent,
        "foil_wake_ratio": foil_wake,
        "normal_growth": normal_growth,
        "foil_expansion": lower["grading"][0],
        "wake_lower_expansion": lower_wakes[0]["grading"][0],
        "wake_upper_expansion": upper_wakes[0]["grading"][0],
    }


_GATE_FLAGS = [
    "--cgrid-tangent", "128",
    "--cgrid-normal", "120",
    "--cgrid-wake", "64",
    "--cgrid-far", "50",
    "--cgrid-wake-len", "50",
    "--cgrid-end-cell", "0.001",
    "--cgrid-max-ratio", "1.2",
    "--cgrid-normal-growth", "1.15",
]


def test_a0c_cgrid_flags_meet_geometric_gate_and_defaults_stay(tmp_path):
    """A0c flags build a gate mesh; omitting them keeps today's 48/60/32 C-grid.

    The production change that fails this test is the C-grid CLI
    (counts, far field, wake length, LE/TE clustering, ratio caps) leaving
    the blockMeshDict on today's uniform 48/60/32, 8c domain.
    """
    default_out = tmp_path / "default"
    assert ps.main([
        "--build-only", "--mesh", "cgrid", "--section", "0012",
        "--out", str(default_out),
    ]) == 0
    dblock = (default_out / "build_only" / "system" / "blockMeshDict").read_text(encoding="utf-8")
    default = measure_cgrid(dblock, ps.CHORD)
    assert default["n_tangent"] == 48
    assert default["n_tangent_upper"] == 48
    assert default["n_normal"] == 60
    assert default["n_wake"] == 32
    assert default["r_outer"] == pytest.approx(8 * ps.CHORD, rel=1e-6)
    assert default["wake_len"] == pytest.approx(16 * ps.CHORD, rel=1e-6)
    assert default["foil_expansion"] == pytest.approx(1.0)
    assert default["wake_lower_expansion"] == pytest.approx(0.05)
    assert default["wake_upper_expansion"] == pytest.approx(20.0)
    assert default["te_cell"] == pytest.approx(default["foil_edge_length"] / 48, rel=1e-6)
    assert default["foil_ratio_max"] == pytest.approx(1.0, abs=1e-6)

    gate_out = tmp_path / "gate"
    gate_argv = [
        "--build-only", "--mesh", "cgrid", "--section", "0012", "--re", "6e6",
        "--iters", "10000",
        *_GATE_FLAGS,
        "--out", str(gate_out),
    ]
    try:
        rc = ps.main(gate_argv)
    except SystemExit as exc:
        pytest.fail(f"A0c cgrid flags rejected: {exc}")
    assert rc == 0
    case = gate_out / "build_only"
    gate = measure_cgrid(
        (case / "system" / "blockMeshDict").read_text(encoding="utf-8"),
        ps.CHORD,
    )
    chord = ps.CHORD
    assert gate["n_tangent"] >= 128, gate
    assert gate["n_tangent_upper"] >= 128, gate
    assert gate["le_cell"] <= 0.001 * chord, gate
    assert gate["te_cell"] <= 0.001 * chord, gate
    assert gate["adjacent_ratio"] <= 1.2, gate
    assert gate["foil_wake_ratio"] <= 1.2, gate
    assert gate["normal_growth"] <= 1.15, gate
    assert gate["r_outer"] >= 50 * chord - 1e-9, gate
    assert gate["wake_len"] >= 50 * chord - 1e-9, gate
    assert gate["n_wake"] >= 64, gate
    # 64 cells over 50 chords grew a 0.66 m outlet cell (aspect 1.8e6) and
    # simpleFoam died. The outlet cell is capped at the span, so the wake
    # aspect stays in the airfoil's own band (~5.6e3 here).
    assert gate["wake_slit_aspect"] <= 8000.0, gate
    assert gate["n_wake"] <= 4000, gate
    ctrl = (case / "system" / "controlDict").read_text(encoding="utf-8")
    assert re.search(r"endTime\s+10000\s*;", ctrl)


def test_cgrid_refine_flag_doubles_the_gate_grid_at_ten_degrees(tmp_path):
    """--cgrid-refine 2 plans one extra 10° mesh with twice the cells each way."""
    if not hasattr(ps, "cgrid_jobs"):
        pytest.fail("cgrid_jobs is missing")
    argv = [
        "--mesh", "cgrid", "--section", "0012", "--re", "6e6",
        "--alphas", "0", "5", "10", "--models", "kOmegaSST", "--tu", "0.001",
        "--iters", "10000",
        *_GATE_FLAGS,
        "--cgrid-refine", "2", "--cgrid-refine-alpha", "10",
    ]
    try:
        ns = ps.parse_cli(argv)
    except SystemExit as exc:
        pytest.fail(f"A0c refine flags rejected: {exc}")
    jobs = ps.cgrid_jobs(ns)
    assert len(jobs) == 2
    assert jobs[0]["alphas"] == [0.0, 5.0, 10.0]
    assert jobs[1]["alphas"] == [10.0]
    assert jobs[1]["n_tangent"] == 2 * jobs[0]["n_tangent"]
    assert jobs[1]["n_normal"] == 2 * jobs[0]["n_normal"]
    assert jobs[1]["n_wake"] == 2 * jobs[0]["n_wake"]
    assert jobs[1]["end_cell_frac"] == pytest.approx(0.0005)
    assert jobs[1]["yplus_target"] == pytest.approx(0.4)
    if "end_cell_frac" not in inspect.signature(ps.write_case).parameters:
        pytest.fail("write_case does not take cgrid parameters")
    case = ps.write_case(
        tmp_path / "refine",
        alpha_deg=10.0,
        model="kOmegaSST",
        section="0012",
        re=6.0e6,
        mesh="cgrid",
        n_iters=10000,
        n_tangent=jobs[1]["n_tangent"],
        n_normal=jobs[1]["n_normal"],
        n_wake=jobs[1]["n_wake"],
        far_chords=jobs[1]["far_chords"],
        wake_chords=jobs[1]["wake_chords"],
        end_cell_frac=jobs[1]["end_cell_frac"],
        max_ratio=jobs[1]["max_ratio"],
        normal_growth=jobs[1]["normal_growth"],
        yplus_target=jobs[1]["yplus_target"],
    )
    gate = measure_cgrid(
        (case / "system" / "blockMeshDict").read_text(encoding="utf-8"),
        ps.CHORD,
    )
    assert gate["n_tangent"] >= 256, gate
    assert gate["n_normal"] >= 240, gate
    assert gate["le_cell"] <= 0.0005 * ps.CHORD, gate
    assert gate["te_cell"] <= 0.0005 * ps.CHORD, gate
    assert gate["adjacent_ratio"] <= 1.2, gate
    assert gate["foil_wake_ratio"] <= 1.2, gate
    assert gate["normal_growth"] <= 1.15, gate
    ctrl = (case / "system" / "controlDict").read_text(encoding="utf-8")
    assert re.search(r"endTime\s+10000\s*;", ctrl)


def test_section_2d_promoted_module_and_cli_delegation():
    """RV-4 (#74): maths and verdict logic live in fansim.propeller.section_2d."""
    from fansim.propeller import section_2d as s2d

    for name in (
        "section_xy",
        "u_inf",
        "solve_u_nu",
        "wall_spacing_m",
        "first_cell_yplus",
        "parse_naca4_code",
        "write_case",
        "verdict",
        "verdict_a0",
        "parse_cl_cd",
        "parse_yplus",
        "parse_layer_coverage",
        "parse_surface_cells",
        "is_a0_campaign",
        "judge_summary",
    ):
        assert getattr(ps, name) is getattr(s2d, name), name

    assert s2d.is_a0_campaign("0012", 6.0e6, [0.0, 5.0, 10.0]) is True
    assert s2d.is_a0_campaign("4406", 8.0e4, [0.0, 2.0, 4.0, 6.0, 8.0]) is False
    a0_summary = {
        "points": {
            "kOmegaSST": {
                "0.0": {"cd": s2d.A0_CD_0},
                "5.0": {"cl": s2d.A0_CL_5},
                "10.0": {"cl": s2d.A0_CL_10},
            }
        }
    }
    assert s2d.judge_summary(
        a0_summary, section="0012", re=6.0e6, alphas=[0.0, 5.0, 10.0]
    )["verdict"] == "PASS"
    rung_a_summary = {
        "points": {
            "kOmegaSST": {"4.0": {"cl": s2d.REF_CL_4 * 0.95}},
            "kOmegaSSTLM": {"4.0": {"cl": s2d.REF_CL_4 * 0.50}},
        }
    }
    assert s2d.judge_summary(
        rung_a_summary, section="4406", re=8.0e4, alphas=[0.0, 2.0, 4.0, 6.0, 8.0]
    )["verdict"] == "A2"

