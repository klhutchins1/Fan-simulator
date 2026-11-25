"""R1.3: guided Optimize bounds cover Stock under wrap (prereg 2026-11-25)."""

from __future__ import annotations

from fansim.optimize.search_space import GUIDED, GUIDED_LC, OPEN, stock_blade_flat


def test_guided_p0_bounds_match_prereg_numbers():
    assert GUIDED["stagger_root"] == (19.5, 48.0)
    assert GUIDED["stagger_mid"] == (27.2, 48.0)
    assert GUIDED["stagger_tip"] == (18.0, 38.0)
    assert GUIDED["max_camber"] == (0.015, 0.06)


def test_stock_v3_lies_inside_guided():
    p = stock_blade_flat("a12x25")
    for key in ("stagger_root", "stagger_mid", "stagger_tip", "max_camber"):
        lo, hi = GUIDED[key]
        val = float(p[key])
        assert lo <= val <= hi, f"{key}={val} outside GUIDED {(lo, hi)}"


def test_open_and_guided_lc_unchanged_by_r13():
    # Freeze the pre-R1.3 numbers so this task cannot silently widen other spaces.
    assert OPEN["stagger_root"] == (20.0, 48.0)
    assert OPEN["stagger_mid"] == (18.0, 42.0)
    assert OPEN["max_camber"] == (0.0, 0.06)
    assert GUIDED_LC["stagger_root"] == (22.0, 44.0)
    assert GUIDED_LC["stagger_mid"] == (28.0, 44.0)
    assert GUIDED_LC["max_camber"] == (0.0, 0.06)
