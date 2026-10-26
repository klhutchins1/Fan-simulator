"""Rung A runner pieces that need no CFD: section, y+, case files, verdict rules."""
from __future__ import annotations

import importlib.util
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
        [ln for ln in (quiet / "0" / "k").read_text(encoding="utf-8").splitlines()
         if "internalField" in ln][0].split()[-1].rstrip(";"))
    k_n = float(
        [ln for ln in (noisy / "0" / "k").read_text(encoding="utf-8").splitlines()
         if "internalField" in ln][0].split()[-1].rstrip(";"))
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
