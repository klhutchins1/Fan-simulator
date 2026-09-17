import math

import cadquery as cq
import pytest

from fansim.cfd.domain import MM_TO_M, rig_for_impeller
from fansim.cfd.frame import (
    BARREL_WALL_MM,
    STRUT_AFTER_MRF_MM,
    STRUT_DEPTH_MM,
    STRUT_THICK_MM,
    STRUT_WALL_INSET_MM,
    build_frame_solid,
    export_frame_stl,
)
from fansim.geometry.blade import BladeParams


def _solid_contains_point(solid, x: float, y: float, z: float) -> bool:
    """Robust point-in-solid check: use OCC if present, else boolean-probe."""
    v = cq.Vector(x, y, z)
    if hasattr(solid, "isInside"):
        try:
            return bool(solid.isInside(v))
        except Exception:  # noqa: BLE001 - fall back to boolean probe
            pass
    # Fallback: intersect with a tiny sphere around the point.
    probe = cq.Solid.makeSphere(0.05, v)
    try:
        return solid.intersect(probe).Volume() > 1e-8
    except Exception:  # noqa: BLE001 - if intersect fails, assume not inside
        return False


def test_frame_is_one_solid_after_mrf():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    solid = build_frame_solid(params, rig)
    assert len(solid.Solids()) == 1
    bb = solid.BoundingBox()
    assert bb.zmin >= rig.mrf_z_max / MM_TO_M + STRUT_AFTER_MRF_MM - 0.05
    assert bb.zmax <= bb.zmin + STRUT_DEPTH_MM + 0.2
    # Volume bound: 4 bars + hub-shadow barrel, within a few percent (overlap makes the union smaller).
    outer_r = rig.duct_radius / MM_TO_M - STRUT_WALL_INSET_MM
    hub_r = params.hub_radius
    bar_r0 = hub_r - BARREL_WALL_MM
    bar_len = outer_r - bar_r0
    v_expected = (
        4.0 * bar_len * STRUT_THICK_MM * STRUT_DEPTH_MM
        + math.pi * (hub_r**2 - (hub_r - BARREL_WALL_MM) ** 2) * STRUT_DEPTH_MM
    )
    v_actual = float(solid.Volume())
    assert abs(v_actual - v_expected) / v_expected < 0.06

    # Distinguish four bars from a closed disk: mid-span at 45° must be outside.
    r_mid = 0.5 * (hub_r + outer_r)
    x = r_mid / math.sqrt(2.0)
    y = r_mid / math.sqrt(2.0)
    z = 0.5 * (bb.zmin + bb.zmax)
    assert _solid_contains_point(solid, x, y, z) is False


def test_frame_does_not_start_inside_mrf():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    bb = build_frame_solid(params, rig).BoundingBox()
    assert bb.zmin > rig.mrf_z_max / MM_TO_M


def test_export_frame_stl_writes_file(tmp_path):
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    out = tmp_path / "frame.stl"
    export_frame_stl(params, rig, out)
    assert out.exists() and out.stat().st_size > 1000
