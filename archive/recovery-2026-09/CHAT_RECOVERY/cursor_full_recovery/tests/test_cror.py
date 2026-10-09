"""CROR geometry + dual-MRF wiring tests. No Docker."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.cror.geometry import CrorParams, build_cror, cror_axial_layout_mm, export_cror_stl
from fansim.problem.archetypes import get_archetype


def test_cror_builds_one_solid():
    solid = build_cror(CrorParams()).val()
    assert len(solid.Solids()) == 1


def test_cror_rear_stagger_is_opposite():
    p = CrorParams()
    assert all(s.stagger_deg > 0 for s in p.front.stations)
    assert all(s.stagger_deg < 0 for s in p.rear.stations)


def test_cror_axial_layout_rear_downstream():
    lay = cror_axial_layout_mm(CrorParams())
    assert lay["rear_z_min_mm"] > lay["front_z_max_mm"]
    assert lay["gap_mm"] == pytest.approx(8.0)


def test_export_cror_stl(tmp_path):
    out = tmp_path / "cror.stl"
    export_cror_stl(CrorParams(), out)
    assert out.exists() and out.stat().st_size > 1000


def test_dual_mrf_dict_opposite_omega():
    from fansim.cror.evaluate import dual_mrf_dict
    d = dual_mrf_dict(CrorParams(), omega_front=-200.0)
    assert d["omega_front"] == pytest.approx(-200.0)
    assert d["omega_rear"] == pytest.approx(200.0)
    assert d["rear_z_min"] > d["front_z_max"]


def test_build_case_dual_mrf_writes_two_zones(tmp_path):
    from fansim.cror.evaluate import dual_mrf_dict, rig_for_cror
    from fansim.cror.geometry import export_cror_stl
    from fansim.cfd.openfoam_case import MeshResolution, build_case

    stl = export_cror_stl(CrorParams(), tmp_path / "impeller.stl")
    rig = rig_for_cror(CrorParams(), tip_gap_mm=0.5, casing_id_mm=120.0, rpm=2000.0)
    dmrf = dual_mrf_dict(CrorParams(), rig.omega_signed)
    case = tmp_path / "case"
    build_case(case, stl, rig, mesh=MeshResolution(base_cell=0.01),
               n_iters=10, n_subdomains=2, back_pressure_pa=0.0, dual_mrf=dmrf)
    topo = (case / "system/topoSetDict").read_text(encoding="utf-8")
    mrf = (case / "constant/MRFProperties").read_text(encoding="utf-8")
    assert "rotorFront" in topo and "rotorRear" in topo
    assert "MRF1" in mrf and "MRF2" in mrf
    assert "rotorFront" in mrf and "rotorRear" in mrf


def test_cror_archetype_evaluate_wired():
    a = get_archetype("cror")
    assert a.name == "cror"
    p = a.suggest_design(None)
    assert isinstance(p, CrorParams)
    import inspect
    src = inspect.getsource(type(a).evaluate)
    assert "NotImplementedError" not in src


def test_cli_export_cror_no_star():
    text = Path("scripts/export_cror.py").read_text(encoding="utf-8")
    assert "cror" in text.lower()
    assert "★" not in text


def test_cli_evaluate_cror_declares_dry_run():
    text = Path("scripts/evaluate_cror.py").read_text(encoding="utf-8")
    assert "--dry-run" in text
    assert "dual" in text.lower()
    assert "--spec" in text
    assert "delta_afc1212de" in text


def test_default_cror_fits_delta_not_a12x25(tmp_path):
    """Dual stack ~33 mm deep: A12x25 (25 mm) rejects; Delta 38 mm envelope accepts tip gap."""
    from fansim.cror.evaluate import remaining_cror_tip_gap_mm
    from fansim.fan_spec import A12X25, get_fan_spec
    from fansim.geometry import watertight_report

    p = CrorParams()
    stl = export_cror_stl(p, tmp_path / "cror.stl")
    rep = watertight_report(stl)
    (_, _, zmin), (_, _, zmax) = rep.bounds_mm
    depth = zmax - zmin
    assert depth > A12X25.depth_mm[1]
    delta = get_fan_spec("delta_afc1212de")
    assert depth <= delta.depth_mm[1]
    assert remaining_cror_tip_gap_mm(p, delta.tip_dia_mm[1]) >= 0.5
