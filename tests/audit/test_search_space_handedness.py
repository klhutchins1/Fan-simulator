"""Every optimizer search space keeps the Stock handedness (stagger > 0, camber >= 0).

The CFD orientation (flip about X, spin −1) is fixed for all axial designs. That is only valid
while no design can be a mirror image, which would need a negative stagger or camber.
"""

from __future__ import annotations

from fansim.optimize import search_space


def _spaces():
    for name in dir(search_space):
        val = getattr(search_space, name)
        if isinstance(val, dict) and any("stagger" in str(k) for k in val):
            yield name, val


def test_found_spaces():
    assert list(_spaces()), "no search-space dicts found"


def test_stator_bounds_is_discovered():
    assert "STATOR_BOUNDS" in dict(_spaces()), "STATOR_BOUNDS (stator_stagger_deg) was not discovered"


def test_stagger_and_camber_bounds_keep_handedness():
    for name, space in _spaces():
        for key, bounds in space.items():
            if "stagger" in str(key):
                assert bounds[0] > 0.0, f"{name}.{key} lower bound {bounds[0]} allows mirrored blades"
            if str(key) == "max_camber":
                assert bounds[0] >= 0.0, f"{name}.{key} lower bound {bounds[0]} allows reversed camber"
