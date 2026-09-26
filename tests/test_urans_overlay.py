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
