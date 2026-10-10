"""Impossible fans raise a clear ValueError before any CAD work (roadmap §23.3, §23.33)."""

import math

import numpy as np
import pytest

from fansim.centrifugal.geometry import MixedFlowParams
from fansim.geometry.blade import BladeParams, RadialStation, validate_blade_params


def _bp(**kw):
    return BladeParams(**kw)


@pytest.mark.parametrize("kw, match", [
    (dict(n_blades=0), "n_blades"),
    (dict(n_blades=1), "single blade"),
    (dict(hub_radius=60.0, tip_radius=50.0), "must be < tip_radius"),
    (dict(tip_radius=math.nan), "positive numbers"),
    (dict(hub_radius=-1.0), "positive numbers"),
])
def test_bad_blade_params_raise(kw, match):
    with pytest.raises(ValueError, match=match):
        validate_blade_params(_bp(**kw))


def test_bad_stations_raise():
    with pytest.raises(ValueError, match="chord must be > 0"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, 30), RadialStation(1.0, -5, 25)]))
    with pytest.raises(ValueError, match="not a finite number"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, math.nan), RadialStation(1.0, 30, 25)]))
    with pytest.raises(ValueError, match="r_frac"):
        validate_blade_params(_bp(stations=[RadialStation(0.0, 30, 30), RadialStation(1.4, 30, 25)]))


def test_blade_angle_count_checked_for_preview_too():
    with pytest.raises(ValueError, match="blade_angles_deg"):
        validate_blade_params(_bp(n_blades=7, blade_angles_deg=[0.0, 90.0]))


def test_valid_inputs_including_numpy_and_float_counts_pass():
    validate_blade_params(_bp())
    validate_blade_params(_bp(n_blades=np.int64(9)))
    validate_blade_params(_bp(n_blades=9.0))


def test_mixed_flow_rejects_zero_blades_and_negative_span():
    with pytest.raises(ValueError, match="n_blades"):
        MixedFlowParams(n_blades=0)
    with pytest.raises(ValueError, match="z_span_mm"):
        MixedFlowParams(z_span_mm=-5.0)
    MixedFlowParams()  # defaults stay valid


def test_root_axial_span_uses_the_innermost_station_not_list_order():
    from fansim.geometry.blade import _root_axial_span

    ordered = _bp(stations=[RadialStation(0.0, 30, 40), RadialStation(0.5, 40, 30),
                            RadialStation(1.0, 35, 20)])
    shuffled = _bp(stations=[RadialStation(1.0, 35, 20), RadialStation(0.0, 30, 40),
                             RadialStation(0.5, 40, 30)])
    assert _root_axial_span(shuffled) == _root_axial_span(ordered)


def test_tip_trim_falls_back_when_the_plain_intersect_is_empty(monkeypatch):
    import cadquery as cq

    from fansim.geometry.blade import TIP_TRIM_TOL_MM, _max_radius, _trim_blade_to_tip_cylinder

    blade = cq.Solid.makeBox(10, 10, 10, cq.Vector(40, 0, 0))   # reaches r ≈ 53.9 mm
    empty = cq.Compound.makeCompound([])
    monkeypatch.setattr(cq.Solid, "intersect", lambda self, other: empty)
    out = _trim_blade_to_tip_cylinder(blade, 45.0)               # outer-ring cut (§23.32)
    assert _max_radius(out) <= 45.0 + TIP_TRIM_TOL_MM and out.Volume() < blade.Volume()
    # already inside the cylinder (e.g. a rounded tip): nothing to trim, keep it
    inside = cq.Solid.makeBox(5, 5, 5, cq.Vector(30, 0, 0))     # r <= ~35.4 mm
    assert _trim_blade_to_tip_cylinder(inside, 45.0) is inside


def test_hub_measure_cut_follows_the_hub_not_a12x25():
    from fansim.geometry.chord_realisation import _station_measure_fracs
    from fansim.geometry.config import load_blade_params

    stock = load_blade_params("config/problems/a12x25_reference.yaml")
    fr = _station_measure_fracs(stock)
    assert fr[0] is None and all(f is not None for f in fr[1:])   # same as the old 0.47 rule
    big_hub = _bp(hub_radius=30.0, tip_radius=50.0, stations=[
        RadialStation(0.0, 30, 30), RadialStation(0.15, 30, 30), RadialStation(1.0, 30, 25)])
    fb = _station_measure_fracs(big_hub)
    assert fb[0] is None and fb[1] is None and fb[2] == 0.99     # 0.15 sits within 4.1 mm of hub


def test_blade_solidity_of_a_bladeless_rotor_is_zero():
    """QA-11: a direct call with n_blades=0 used to divide by zero."""
    from fansim.geometry.blade import blade_solidity

    assert blade_solidity(_bp(n_blades=0)) == {"hub": 0.0, "mid": 0.0, "tip": 0.0}
    seven = blade_solidity(_bp(n_blades=7))
    assert blade_solidity(_bp(n_blades=14))["mid"] == pytest.approx(2 * seven["mid"])


def test_fan_blades_never_reach_below_the_hub_face():
    """User rule 2026-10-09: the hub's motor face is the lowest point (frame struts sit there)."""
    import copy

    from fansim.geometry.blade import _hub_axial_range, build_blade_solid, clip_blade_below
    from fansim.geometry.config import load_blade_params

    p = load_blade_params("config/problems/a12x25_reference.yaml")   # hangs 0.94 mm unclipped
    z_face = _hub_axial_range(p)[0]
    blade = build_blade_solid(p)
    assert blade.BoundingBox().zmin < z_face - 0.5
    clipped = clip_blade_below(p, blade, z_face)
    assert clipped.BoundingBox().zmin >= z_face - 0.01 and clipped.isValid()
    off = copy.copy(p)
    off.clip_below_hub = False                                      # props / wind / CROR
    assert clip_blade_below(off, blade, z_face) is blade
