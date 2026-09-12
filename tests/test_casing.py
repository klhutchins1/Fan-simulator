import cadquery as cq
import pytest

from fansim.cfd.domain import MM_TO_M, rig_for_impeller
from fansim.cfd.casing import (
    CASING_WALL_MM,
    STEP_DEPTH_MM,
    STEP_LEN_MM,
    build_casing_solid,
    export_casing_stl,
)
from fansim.geometry.blade import BladeParams


def _solid_contains_point(solid, x: float, y: float, z: float) -> bool:
    v = cq.Vector(x, y, z)
    if hasattr(solid, "isInside"):
        try:
            return bool(solid.isInside(v))
        except Exception:  # noqa: BLE001 - fall back to boolean probe
            pass
    probe = cq.Solid.makeSphere(0.05, v)
    try:
        return solid.intersect(probe).Volume() > 1e-8
    except Exception:  # noqa: BLE001 - if intersect fails, assume not inside
        return False


def test_casing_is_one_tube_at_duct_radius():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    solid = build_casing_solid(rig)
    assert len(solid.Solids()) == 1
    inner_r = rig.duct_radius / MM_TO_M
    bb = solid.BoundingBox()
    zmin = rig.domain_z_min / MM_TO_M
    zmax = rig.domain_z_max / MM_TO_M
    assert bb.zmin == pytest.approx(zmin, abs=0.2)
    assert bb.zmax == pytest.approx(zmax, abs=0.2)
    assert bb.xmax == pytest.approx(inner_r + CASING_WALL_MM, abs=0.3)

    z_mid = 0.5 * (bb.zmin + bb.zmax)
    assert _solid_contains_point(solid, 0.5 * inner_r, 0.0, z_mid) is False
    assert _solid_contains_point(solid, inner_r + 1.0, 0.0, z_mid) is True


def test_export_casing_stl_writes_file(tmp_path):
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    out = tmp_path / "casing.stl"
    export_casing_stl(rig, out)
    assert out.exists() and out.stat().st_size > 1000


def test_stepped_casing_enlarges_inlet_bore_not_midspan():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    solid = build_casing_solid(rig, stepped=True)
    assert len(solid.Solids()) == 1
    inner_r = rig.duct_radius / MM_TO_M
    zmin = rig.domain_z_min / MM_TO_M
    zmax = rig.domain_z_max / MM_TO_M
    bb = solid.BoundingBox()
    assert bb.zmin == pytest.approx(zmin, abs=0.2)
    assert bb.zmax == pytest.approx(zmax, abs=0.2)
    assert bb.xmax == pytest.approx(inner_r + CASING_WALL_MM + STEP_DEPTH_MM, abs=0.3)
    assert STEP_LEN_MM == 6.0

    z_inlet = zmin + 1.0
    z_mid = 0.5 * (zmin + zmax)
    assert _solid_contains_point(solid, inner_r + 0.4, 0.0, z_inlet) is False
    assert _solid_contains_point(solid, inner_r + 0.4, 0.0, z_mid) is True
    assert _solid_contains_point(
        solid, inner_r + STEP_DEPTH_MM + 1.0, 0.0, z_inlet) is True


def test_export_stepped_casing_stl_writes_file(tmp_path):
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    out = tmp_path / "casing_stepped.stl"
    export_casing_stl(rig, out, stepped=True)
    assert out.exists() and out.stat().st_size > 1000
