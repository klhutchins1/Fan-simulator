"""Outlet-chamber (plenum) domain: duct ends downstream of the rotor, box is 3x duct radius."""

from __future__ import annotations

import re

import pytest
import trimesh

from fansim.cfd.casing import export_casing_stl
from fansim.cfd.domain import MM_TO_M, TestRig as _Rig
from fansim.cfd.openfoam_case import build_case


def _rig() -> _Rig:
    return _Rig(duct_radius=0.056, tip_gap=0.0005, inlet_length=0.224, outlet_length=0.448,
                impeller_z_min=-0.0085, impeller_z_max=0.0085, mrf_z_min=-0.0105, mrf_z_max=0.0105,
                rpm=2000.0, inlet_velocity=2.0)


def test_plenum_casing_ends_at_plenum_z(tmp_path):
    rig = _rig()
    zp = 60.0
    p = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=zp, fill_radius_mm=200.0)
    m = trimesh.load(str(p))
    assert m.bounds[0, 2] == pytest.approx(rig.domain_z_min / MM_TO_M, abs=0.05)
    assert m.bounds[1, 2] == pytest.approx(zp, abs=0.05)


def test_default_casing_unchanged(tmp_path):
    rig = _rig()
    m = trimesh.load(str(export_casing_stl(rig, tmp_path / "c.stl")))
    assert m.bounds[1, 2] == pytest.approx(rig.domain_z_max / MM_TO_M, abs=0.05)


def test_plenum_must_be_downstream_of_rotor(tmp_path):
    with pytest.raises(ValueError, match="plenum"):
        export_casing_stl(_rig(), tmp_path / "c.stl", plenum_z_mm=5.0,
                          fill_radius_mm=200.0)


def test_plenum_requires_fill_radius(tmp_path):
    with pytest.raises(ValueError, match="fill_radius_mm"):
        export_casing_stl(_rig(), tmp_path / "c.stl", plenum_z_mm=60.0)


def test_fill_radius_covers_box_corners(tmp_path):
    rig = _rig()
    R_mm = rig.duct_radius / MM_TO_M
    box_scale = 3.0
    fill_radius_mm = box_scale * R_mm * (2 ** 0.5) + 5.0
    p = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=64.0,
                          fill_radius_mm=fill_radius_mm)
    m = trimesh.load(str(p))
    assert max(abs(m.bounds[0, 0]), abs(m.bounds[1, 0])) >= box_scale * R_mm * (2 ** 0.5)


def test_box_scale_sets_block_half_width(tmp_path):
    rig = _rig()
    stl = tmp_path / "r.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 10.0)).export(str(stl))
    R_mm = rig.duct_radius / MM_TO_M
    fill_radius_mm = 3.0 * R_mm * (2 ** 0.5) + 5.0
    casing = export_casing_stl(rig, tmp_path / "c.stl", plenum_z_mm=64.0,
                               fill_radius_mm=fill_radius_mm)
    case = build_case(tmp_path / "case", stl, rig, casing_stl_mm=casing, box_scale=3.0,
                      back_pressure_pa=0.0)
    text = (case / "system/blockMeshDict").read_text(encoding="utf-8")
    xs = [float(v) for v in re.findall(r"\(\s*([-\d.eE+]+)\s+[-\d.eE+]+\s+[-\d.eE+]+\s*\)",
                                        text.split("blocks")[0])[:8]]
    assert max(xs) == pytest.approx(3.0 * rig.duct_radius)
