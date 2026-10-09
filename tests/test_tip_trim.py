"""The tip trim never leaves a blade sticking out past tip_radius (roadmap §23.32)."""

from __future__ import annotations

import random

import cadquery as cq
import pytest

import fansim.geometry.blade as gb
from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import blade_params_from_trial_params, random_prop_flat


def _hard_prop_blade():
    """The random_prop_flat blade (seed 12345, 2nd draw) whose plain trim comes back empty."""
    spec = get_prop_spec("fpv_5inch")
    rng = random.Random(12345)
    random_prop_flat(spec, rng)
    params = blade_params_from_trial_params(spec, random_prop_flat(spec, rng))
    caught = []

    def grab(blade, radius):
        caught.append((blade, radius))
        raise StopIteration

    real = gb._trim_blade_to_tip_cylinder
    gb._trim_blade_to_tip_cylinder = grab
    try:
        with pytest.raises(StopIteration):
            gb.build_blade_solid(params)
    finally:
        gb._trim_blade_to_tip_cylinder = real
    return caught[0]


@pytest.mark.slow
def test_many_faced_prop_blade_is_trimmed_to_the_tip_radius():
    blade, radius = _hard_prop_blade()
    assert gb._max_radius(blade) > radius + 1.0          # it really crosses the tip cylinder
    out = gb._trim_blade_to_tip_cylinder(blade, radius)
    assert gb._max_radius(out) <= radius + gb.TIP_TRIM_TOL_MM
    assert out.isValid()
    assert 0.98 < out.Volume() / blade.Volume() < 1.0


def test_fallback_that_returns_the_untrimmed_blade_is_rejected(monkeypatch):
    # A blade crossing R where every boolean "succeeds" by handing back the whole blade must
    # fail loudly, not pass through untrimmed.
    blade = cq.Solid.makeBox(10, 4, 2, cq.Vector(45, -2, 0))           # reaches r ≈ 55
    monkeypatch.setattr(cq.Solid, "intersect", lambda self, *o: self)
    monkeypatch.setattr(cq.Solid, "cut", lambda self, *o: self)
    monkeypatch.setattr(gb, "_fuzzy_common", lambda a, b, f: a)
    with pytest.raises(RuntimeError, match="tip trim failed"):
        gb._trim_blade_to_tip_cylinder(blade, 50.0)


def test_blade_inside_the_cylinder_is_kept_when_the_boolean_is_empty(monkeypatch):
    blade = cq.Solid.makeBox(5, 4, 2, cq.Vector(40, -2, 0))            # r ≤ 45.2 < 50
    monkeypatch.setattr(cq.Solid, "intersect", lambda self, *o: cq.Compound.makeCompound([]))
    assert gb._trim_blade_to_tip_cylinder(blade, 50.0) is blade
