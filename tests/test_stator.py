"""Tests for stator vanes (geometry + wiring). No Docker mesh."""

from __future__ import annotations

import math

import cadquery as cq
import numpy as np
import pytest

from fansim.cfd.domain import MM_TO_M, rig_for_impeller
from fansim.cfd.stator import (
    AFTER_MRF_MM,
    BARREL_WALL_MM,
    CHORD_MM,
    STATOR_CAMBER,
    STATOR_CAMBER_POS,
    STATOR_THICKNESS,
    WALL_INSET_MM,
    build_stator_solid,
    export_stator_stl,
    n_stator_vanes,
    stationary_downstream,
)
from fansim.geometry.airfoil import naca4
from fansim.geometry.blade import BladeParams


def _solid_contains_point(solid, x: float, y: float, z: float) -> bool:
    v = cq.Vector(x, y, z)
    if hasattr(solid, "isInside"):
        try:
            return bool(solid.isInside(v))
        except Exception:  # noqa: BLE001, S110
            pass
    probe = cq.Solid.makeSphere(0.05, v)
    try:
        return solid.intersect(probe).Volume() > 1e-8
    except Exception:  # noqa: BLE001
        return False


def _naca_area_mm2() -> float:
    loop = naca4(STATOR_CAMBER, STATOR_CAMBER_POS, STATOR_THICKNESS, n_points=40) * CHORD_MM
    x, y = loop[:, 0], loop[:, 1]
    return 0.5 * float(np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def test_n_vanes_is_blades_plus_two():
    p = BladeParams()
    assert p.n_blades == 7
    assert n_stator_vanes(p) == 9


def test_n_vanes_respects_n_extra():
    p = BladeParams()
    assert n_stator_vanes(p, n_extra=3) == p.n_blades + 3
    assert n_stator_vanes(p, n_extra=1) == p.n_blades + 1


def test_build_stator_honors_stagger_and_n_extra():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    n_extra = 3
    solid = build_stator_solid(params, rig, stagger_deg=40.0, n_extra=n_extra)
    assert len(solid.Solids()) == 1
    n = n_stator_vanes(params, n_extra=n_extra)
    assert n == params.n_blades + n_extra
    outer_r = rig.duct_radius / MM_TO_M - WALL_INSET_MM
    hub_r = params.hub_radius
    span = outer_r - (hub_r - BARREL_WALL_MM)
    v_expected = (
        n * _naca_area_mm2() * span
        + math.pi * (hub_r**2 - (hub_r - BARREL_WALL_MM) ** 2) * CHORD_MM
    )
    v_actual = float(solid.Volume())
    assert abs(v_actual - v_expected) / v_expected < 0.25


def test_stationary_downstream_flag():
    assert stationary_downstream(stator=False) == "frame"
    assert stationary_downstream(stator=True) == "stator"
    assert stationary_downstream(stator_stack=True) == "stack"
    with pytest.raises(ValueError, match="cannot combine"):
        stationary_downstream(stator=True, stator_stack=True)


def test_stator_naca_constants():
    assert STATOR_CAMBER == pytest.approx(0.04)
    assert STATOR_CAMBER_POS == pytest.approx(0.4)
    assert STATOR_THICKNESS == pytest.approx(0.12)


def test_stator_vane_profile_is_cambered_naca_not_flat_box():
    """Stator vane cross-section is a cambered NACA 4-digit foil, not a symmetric box."""
    from fansim.cfd.stator import _vane_yz_profile

    pts = _vane_yz_profile(z_start=10.0)
    ys = [y for y, _ in pts]
    zs = [z for _, z in pts]
    # Exact chord span along +Z from z_start.
    assert min(zs) == pytest.approx(10.0, abs=1e-6)
    assert max(zs) == pytest.approx(10.0 + CHORD_MM, abs=1e-6)
    # Positive camber bows asymmetrically toward +Y (a flat rectangular box is symmetric).
    assert max(ys) > abs(min(ys)) + 0.02 * CHORD_MM
    # Total thickness matches STATOR_THICKNESS * CHORD_MM (rounded foil, not constant wall).
    assert (max(ys) - min(ys)) == pytest.approx(STATOR_THICKNESS * CHORD_MM, rel=0.15)
    # Leading/trailing edges taper to near zero thickness (unlike a rectangular box).
    te_ys = [abs(y) for y, z in pts if z > 10.0 + 0.98 * CHORD_MM]
    assert te_ys and max(te_ys) < 0.02 * CHORD_MM


@pytest.fixture(scope="module")
def _default_stator():
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    return params, rig, build_stator_solid(params, rig)


def test_stator_is_one_solid_after_mrf(_default_stator):
    params, rig, solid = _default_stator
    assert len(solid.Solids()) == 1
    bb = solid.BoundingBox()
    assert bb.zmin >= rig.mrf_z_max / MM_TO_M + AFTER_MRF_MM - 0.05
    n = n_stator_vanes(params)
    outer_r = rig.duct_radius / MM_TO_M - WALL_INSET_MM
    hub_r = params.hub_radius
    span = outer_r - (hub_r - BARREL_WALL_MM)
    v_expected = (
        n * _naca_area_mm2() * span
        + math.pi * (hub_r**2 - (hub_r - BARREL_WALL_MM) ** 2) * CHORD_MM
    )
    v_actual = float(solid.Volume())
    # Stagger + fuse + TE bluntness — allow generous relative error
    assert abs(v_actual - v_expected) / v_expected < 0.25

    r_mid = 0.5 * (hub_r + outer_r)
    z = 0.5 * (bb.zmin + bb.zmax)
    assert _solid_contains_point(solid, r_mid, 0.0, z) is True
    pitch = 360.0 / n
    half = math.radians(pitch / 2.0)
    assert _solid_contains_point(
        solid, r_mid * math.cos(half), r_mid * math.sin(half), z) is False


def test_stator_does_not_start_inside_mrf(_default_stator):
    _params, rig, solid = _default_stator
    bb = solid.BoundingBox()
    assert bb.zmin > rig.mrf_z_max / MM_TO_M


def test_stack_frame_sits_behind_stator(_default_stator):
    from fansim.cfd.frame import (
        STACK_GAP_MM,
        STRUT_DEPTH_MM,
        build_frame_solid,
        stack_frame_z_start_mm,
    )
    params, rig, solid = _default_stator
    stator_bb = solid.BoundingBox()
    z_frame = stack_frame_z_start_mm(rig)
    assert z_frame >= stator_bb.zmax + STACK_GAP_MM - 0.05
    frame_bb = build_frame_solid(params, rig, z_start_mm=z_frame).BoundingBox()
    assert frame_bb.zmin >= stator_bb.zmax + STACK_GAP_MM - 0.15
    assert frame_bb.zmax - frame_bb.zmin == pytest.approx(STRUT_DEPTH_MM, abs=0.2)


def test_export_stator_stl_writes_file(tmp_path):
    params = BladeParams()
    rig = rig_for_impeller(params, tip_gap_mm=0.5)
    out = tmp_path / "stator.stl"
    export_stator_stl(params, rig, out)
    assert out.exists() and out.stat().st_size > 1000


def test_templates_have_stator_placeholders():
    from fansim.cfd.templates import MRF_PROPERTIES, SNAPPY, SURFACE_FEATURES

    assert "@STATOR_GEOM@" in SNAPPY
    assert "@STATOR_FEAT@" in SNAPPY
    assert "@STATOR_SURF@" in SNAPPY
    assert "@STATOR_EXTRACT@" in SURFACE_FEATURES
    assert "@STATOR_PATCH@" in MRF_PROPERTIES


def test_run_optimization_declares_stator_flag():
    from tests._cli_parsers import load_build_parser

    ap = load_build_parser("run_optimization.py")()
    args = ap.parse_args(["--stator"])
    assert args.stator is True
    assert "★" not in ap.format_help()
