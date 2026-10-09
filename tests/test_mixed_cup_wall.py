"""Mixed-flow motor-cup wall is checked at the cone's narrowest point (roadmap §23.36)."""

import pytest

from fansim.centrifugal.geometry import MixedFlowParams, cup_wall_hub_radius_mm
from fansim.fan_spec import A12X25


def test_default_cup_wall_uses_cone_radius_at_ceiling():
    p = MixedFlowParams()
    # model bottom at -10.74 mm (blades hang below the -9 mm hub face) -> ceiling at +2.26 mm
    r = cup_wall_hub_radius_mm(p, A12X25.motor_mount, -10.74)
    assert r == pytest.approx(28.0 - 12.0 * (2.26 + 9.0) / 18.0, abs=1e-6)   # ~20.49, not 28
    need = 37.25 / 2 + 0.35 + 1.2
    assert r > need                      # default design still mounts (wall ~1.5 mm >= 1.2 mm)


def test_narrow_eye_now_fails_the_mount_check():
    p = MixedFlowParams(r_eye_mm=10.0)
    r = cup_wall_hub_radius_mm(p, A12X25.motor_mount, -10.74)
    assert r < 37.25 / 2 + 0.35 + 1.2    # r_back (28) alone would have passed it
