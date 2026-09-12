"""Cylindrical tip trim: clamp section points to tip_radius OD."""

from __future__ import annotations

import math

from fansim.geometry.blade import (
    BladeParams,
    RadialStation,
    apply_tip_shape,
    build_blade_solid,
    open_tip_rmax_mm,
    tip_section_points,
)


def _bulgy() -> BladeParams:
    return BladeParams(
        cylindrical_tip=False,
        tip_radius=50.0,
        stations=[
            RadialStation(0.0, 18.0, 40.0, thickness=0.10, lean_deg=0.0),
            RadialStation(0.5, 30.0, 40.0, thickness=0.08, lean_deg=25.0),
            RadialStation(1.0, 40.0, 40.0, thickness=0.06, lean_deg=45.0),
        ],
    )


def test_default_cylindrical_tip_on():
    assert BladeParams().cylindrical_tip is True


def test_trim_off_allows_tip_bulge():
    p = _bulgy()
    assert open_tip_rmax_mm(p) > p.tip_radius + 0.5


def test_trim_on_caps_tip_hypot():
    p = _bulgy()
    p.cylindrical_tip = True
    assert open_tip_rmax_mm(p) <= p.tip_radius + 1e-6
    for v in tip_section_points(p):
        assert math.hypot(v.x, v.y) <= p.tip_radius + 1e-6
    # Solid tip face must also stay inside the cylinder (boolean cut).
    solid = build_blade_solid(p)
    bb = solid.BoundingBox()
    assert max(abs(bb.xmin), abs(bb.xmax), abs(bb.ymin), abs(bb.ymax)) <= p.tip_radius + 0.05


def test_tip_round_plus_trim_still_capped():
    p = _bulgy()
    p.cylindrical_tip = True
    apply_tip_shape(p, tip_round=0.7, start_frac=0.80)
    assert open_tip_rmax_mm(p) <= p.tip_radius + 1e-6
    solid = build_blade_solid(p)
    assert solid is not None
    assert abs(float(solid.Volume())) > 1.0
    bb = solid.BoundingBox()
    assert max(abs(bb.xmin), abs(bb.xmax), abs(bb.ymin), abs(bb.ymax)) <= p.tip_radius + 0.05


def test_blade_from_flat_cylindrical_tip_roundtrip():
    from fansim.optimize.search_space import blade_from_flat, blade_to_flat

    base = blade_to_flat(BladeParams())
    assert blade_from_flat(base).cylindrical_tip is True
    assert blade_from_flat(dict(base, cylindrical_tip=False)).cylindrical_tip is False
    slim = {k: v for k, v in base.items() if k != "cylindrical_tip"}
    assert blade_from_flat(slim).cylindrical_tip is True
