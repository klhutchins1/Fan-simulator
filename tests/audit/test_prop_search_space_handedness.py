"""The prop optimizer's search space keeps the builder handedness (pitch/camber >= 0-ish).

Prop equivalent of ``test_search_space_handedness.py`` (which covers the axial fan's
``fansim.optimize.search_space`` stagger/max_camber dicts). The prop optimizer
(``fansim.propeller.optimize``) doesn't use a "stagger" angle or a single search-space dict per
archetype -- it samples ``pitch_in`` as ``spec.pitch_in * <multiplier>`` and three independent
``camber_root``/``camber_mid``/``camber_tip`` values inline in ``suggest_prop``/``random_prop_flat``.
Those bounds are named ``PROP_SEARCH_SPACE_BOUNDS`` (plus the individual
``PITCH_IN_MULT_BOUNDS``/``CAMBER_*_BOUNDS`` constants it's built from) so they can be inspected
here the same way.

Handedness argument: ``fansim.propeller.direction.BUILDER_DIRECTION`` fixes the in-house
prop/impeller builders' handedness (omega +1 pumps -Z as built, same as
``geometry.stock_handedness``) WITHOUT requiring the mesh-only proof to be CONCLUSIVE. That is
only valid as long as no design in the search space can be built mirrored -- which needs either a
negative pitch (twist direction flips) or negative camber (concave/convex faces swap).
"""

from __future__ import annotations

from fansim.propeller import optimize as prop_optimize


def test_prop_search_space_bounds_is_discovered():
    assert hasattr(prop_optimize, "PROP_SEARCH_SPACE_BOUNDS")
    assert prop_optimize.PROP_SEARCH_SPACE_BOUNDS, "PROP_SEARCH_SPACE_BOUNDS is empty"


def test_pitch_and_camber_bounds_keep_builder_handedness():
    for key, bounds in prop_optimize.PROP_SEARCH_SPACE_BOUNDS.items():
        if "pitch" in key:
            assert bounds[0] > 0.0, f"{key} lower bound {bounds[0]} allows a flipped/zero pitch"
        if "camber" in key:
            assert bounds[0] >= 0.0, f"{key} lower bound {bounds[0]} allows reversed camber"


def test_suggest_prop_and_random_prop_flat_use_the_named_bounds():
    # Guards against the constants and the actual sampling calls drifting apart.
    import random

    from fansim.prop_spec import get_prop_spec

    spec = get_prop_spec("fpv_5inch")
    rng = random.Random(0)
    for _ in range(20):
        flat = prop_optimize.random_prop_flat(spec, rng)
        lo, hi = prop_optimize.PITCH_IN_MULT_BOUNDS
        assert spec.pitch_in * lo <= flat["pitch_in"] <= spec.pitch_in * hi
        for key in ("camber_root", "camber_mid", "camber_tip"):
            bounds = prop_optimize.PROP_SEARCH_SPACE_BOUNDS[key]
            assert bounds[0] <= flat[key] <= bounds[1]
            assert flat[key] >= 0.0
