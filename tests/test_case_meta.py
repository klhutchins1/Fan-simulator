"""`constant/case_meta.json` sidecar: duct shape, patch areas, casing/plenum flags."""

from __future__ import annotations

import json
import math

import pytest
import trimesh

from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.metrics import CFD_VERSION
from fansim.cfd.openfoam_case import BOX_SCALE, build_case


def _rig() -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=-0.0085, impeller_z_max=0.0085, mrf_z_min=-0.0105, mrf_z_max=0.0105,
                rpm=2000.0, inlet_velocity=2.0)


def _impeller_stl(tmp_path):
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    return stl


def _load_meta(case_dir):
    return json.loads((case_dir / "constant/case_meta.json").read_text(encoding="utf-8"))


def test_case_meta_no_casing_is_square(tmp_path):
    rig = _rig()
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig, back_pressure_pa=0.0)
    meta = _load_meta(case)

    H = rig.duct_radius
    assert meta["duct_shape"] == "square"
    assert meta["casing"] is False
    assert meta["plenum"] is False
    assert meta["box_half_width_m"] == pytest.approx(H)
    assert meta["inlet_area_m2"] == pytest.approx((2.0 * H) ** 2)
    assert meta["outlet_area_m2"] == pytest.approx((2.0 * H) ** 2)
    assert meta["duct_radius_m"] == pytest.approx(rig.duct_radius)
    assert meta["tip_radius_m"] == pytest.approx(rig.duct_radius - rig.tip_gap)
    assert meta["hub_radius_m"] == pytest.approx(rig.hub_radius)
    assert meta["rpm"] == pytest.approx(rig.rpm)
    assert meta["spin"] == rig.spin
    assert meta["cfd_version"] == CFD_VERSION


def test_case_meta_casing_is_round_no_plenum(tmp_path):
    rig = _rig()
    casing = export_casing_stl(rig, tmp_path / "c.stl")
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig,
                      casing_stl_mm=casing, back_pressure_pa=0.0)
    meta = _load_meta(case)

    H = BOX_SCALE * rig.duct_radius
    assert meta["duct_shape"] == "round"
    assert meta["casing"] is True
    assert meta["plenum"] is False
    assert meta["box_half_width_m"] == pytest.approx(H)
    assert meta["inlet_area_m2"] == pytest.approx(math.pi * rig.duct_radius ** 2)
    assert meta["outlet_area_m2"] == pytest.approx((2.0 * H) ** 2)


def test_case_meta_plenum_casing_sets_plenum_true(tmp_path):
    rig = _rig()
    zp = 60.0
    R_mm = rig.duct_radius / MM_TO_M
    box_scale = 3.0
    fill_radius_mm = box_scale * R_mm * (2 ** 0.5) + 5.0
    casing = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=zp,
                               fill_radius_mm=fill_radius_mm)
    case = build_case(tmp_path / "case", _impeller_stl(tmp_path), rig,
                      casing_stl_mm=casing, box_scale=box_scale, back_pressure_pa=0.0)
    meta = _load_meta(case)

    assert meta["casing"] is True
    assert meta["plenum"] is True
    assert meta["duct_shape"] == "round"
