"""URANS overlay: pimpleFoam, adjustable dt, same RAS model, same metric function objects."""

from __future__ import annotations

import trimesh

from fansim.cfd.domain import TestRig as _Rig
from fansim.cfd.openfoam_case import apply_urans_transient, build_case


def _case(tmp_path):
    rig = _Rig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
               impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=-0.01, mrf_z_max=0.01,
               rpm=2000.0, inlet_velocity=2.0)
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    return build_case(tmp_path / "case", stl, rig, back_pressure_pa=5.0)


def test_urans_control_dict(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3, delta_t=1e-5, max_co=1.5)
    cd = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "application     pimpleFoam;" in cd
    assert "adjustTimeStep  yes;" in cd and "maxCo           1.5;" in cd
    assert "endTime         0.3;" in cd and "deltaT          1e-05;" in cd
    for fo in ("forces", "outletFlow", "inletP", "outletP"):
        assert fo in cd


def test_urans_keeps_ras_sst_and_transient_schemes(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3)
    turb = (case / "constant/turbulenceProperties").read_text(encoding="utf-8")
    assert "RAS" in turb and "kOmegaSST" in turb and "LES" not in turb
    sch = (case / "system/fvSchemes").read_text(encoding="utf-8")
    assert "backward" in sch
    sol = (case / "system/fvSolution").read_text(encoding="utf-8")
    assert "PIMPLE" in sol


def test_urans_default_n_outer_is_byte_identical_to_single_pass(tmp_path):
    """n_outer defaults to 1: fvSolution must be unchanged from before n_outer existed."""
    case = _case(tmp_path)
    apply_urans_transient(case, end_time=0.3)
    sol_default = (case / "system/fvSolution").read_text(encoding="utf-8")

    apply_urans_transient(case, end_time=0.3, n_outer=1)
    sol_explicit = (case / "system/fvSolution").read_text(encoding="utf-8")

    assert sol_default == sol_explicit
    assert "nOuterCorrectors 1;" in sol_default
    assert "outerCorrectorResidualControl" not in sol_default
    assert "relaxationFactors" not in sol_default


def test_urans_n_outer_greater_than_one_adds_outer_loop_controls(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3, max_co=5.0, n_outer=3)
    sol = (case / "system/fvSolution").read_text(encoding="utf-8")

    assert "nOuterCorrectors 3;" in sol
    assert "nCorrectors     2;" in sol
    assert "nNonOrthogonalCorrectors 1;" in sol
    assert "outerCorrectorResidualControl" in sol
    assert sol.count("tolerance 1e-3; relTol 0;") == 4  # p, U, k, omega
    assert "relaxationFactors" in sol
    assert '".*"      0.7;' in sol
    assert '".*Final" 1;' in sol
    assert "p      0.3;" in sol
    assert "pFinal 1;" in sol

    cd = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "maxCo           5.0;" in cd

    # PIMPLE block appears exactly once even after the rewrite.
    assert sol.count("PIMPLE\n{") == 1


def test_urans_n_outer_one_explicit_matches_default(tmp_path):
    case = apply_urans_transient(_case(tmp_path), end_time=0.3, n_outer=1)
    sol = (case / "system/fvSolution").read_text(encoding="utf-8")
    assert "nOuterCorrectors 1;" in sol
    assert "outerCorrectorResidualControl" not in sol
    assert "relaxationFactors" not in sol
