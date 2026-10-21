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
