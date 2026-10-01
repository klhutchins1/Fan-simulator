"""Optimizer tip-radius cap: trimmed (cylindrical) tips only need the frame clearance."""

from __future__ import annotations

import pytest

from fansim.fan_spec import get_fan_spec
from fansim.geometry.blade import SHROUD_DEFAULT_MM
from fansim.optimize.study import optimizer_max_tip_radius


def test_a12x25_cap_reaches_stock_tip():
    # Stock tip radius is 54.5 mm; the old "- 4 mm bulge" cap (51 mm) made every design ~15% smaller
    # in swept annulus than Stock.
    assert optimizer_max_tip_radius(get_fan_spec("a12x25")) == pytest.approx(54.5)


def test_shroud_comes_off_the_cap():
    spec = get_fan_spec("a12x25")
    assert optimizer_max_tip_radius(spec, with_shroud=True) == pytest.approx(54.5 - SHROUD_DEFAULT_MM)
