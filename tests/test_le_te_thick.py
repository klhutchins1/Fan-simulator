"""LE / TE chordwise thickness scale."""

from __future__ import annotations

import numpy as np

from fansim.geometry.airfoil import naca4
from fansim.geometry.blade import (
    BladeParams,
    TE_BLUNT_FRAC,
    apply_le_te_thickness,
    le_te_thick_factors,
)
from fansim.optimize.search_space import blade_from_flat, blade_to_flat


def test_factors_unity_when_scales_one():
    x = np.linspace(0.0, 1.0, 21)
    assert np.allclose(le_te_thick_factors(x, 1.0, 1.0), 1.0)


def test_stock_both_one_is_noop():
    loop = naca4(0.0, 0.4, 0.08, 40)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    x = loop[:, 0]
    b0 = loop[:, 1] * 40.0
    assert np.allclose(b0, apply_le_te_thickness(x, b0, 40.0, 1.0, 1.0))


def _profile(le: float, te: float, chord: float = 38.0, t: float = 0.06):
    loop = naca4(0.0, 0.4, t, 60)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    x = loop[:, 0]
    b = apply_le_te_thickness(x, loop[:, 1] * chord, chord, le, te)
    return x, np.abs(b)


def test_te_blunt_is_capped_below_le_nose():
    """TE must stay a short edge — not matched to full LE half-thickness (paddle)."""
    x, b = _profile(1.5, 1.5)
    x1, b_sharp = _profile(1.5, 1.0)
    le_half = float(np.max(b[x < 0.15]))
    # Very near the TE tip (where NACA → 0) the blunt floor should raise thickness.
    tip = x > 0.97
    te_blunt = float(np.max(b[tip]))
    te_sharp = float(np.max(b_sharp[x1 > 0.97]))
    t_peak = float(np.max(b))
    assert te_blunt > te_sharp + 0.01
    assert te_blunt <= TE_BLUNT_FRAC * t_peak + 1e-6
    assert te_blunt < 0.55 * le_half
    # Blunt must not inflate the forward aft region (old long face lip started ~x=0.78).
    mid_aft = (x > 0.80) & (x < 0.90)
    assert float(np.max(b[mid_aft])) <= float(np.max(b_sharp[(x1 > 0.80) & (x1 < 0.90)])) + 0.05


def test_te_blunt_no_tip_sign_spike():
    """Cambered NACA TE tip is ~-0.0; blunt must not drive that vertex alone to -te_half (flap)."""
    loop = naca4(0.06, 0.4, 0.03, 60)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    x = loop[:, 0]
    b0 = loop[:, 1] * 40.0
    b = apply_le_te_thickness(x, b0.copy(), 40.0, 1.0, 2.0)
    i_le = int(np.argmin(x))
    # Points the blunt floor actually lifts (|b0| was below the floor).
    abs0 = np.abs(b0)
    t_peak = float(np.max(np.abs(b)))
    # Closing edge between last (lower) and first (upper TE) should be a short flat, not a midplane cross.
    assert b[0] > 0.0
    assert b[-1] < 0.0
    lifted_upper = (np.arange(len(x)) <= i_le) & (x > 0.97) & (np.abs(b) > abs0 + 1e-9)
    lifted_lower = (np.arange(len(x)) > i_le) & (x > 0.97) & (np.abs(b) > abs0 + 1e-9)
    assert lifted_upper.any() and lifted_lower.any()
    assert float(np.min(b[lifted_upper])) > 0.0
    assert float(np.max(b[lifted_lower])) < 0.0


def test_te_scale_below_one_thins_aft():
    x, b_thin = _profile(1.0, 0.5)
    _, b_stock = _profile(1.0, 1.0)
    aft = x > 0.85
    assert float(np.max(b_thin[aft])) < float(np.max(b_stock[aft])) * 0.85
    nose = x < 0.15
    assert abs(float(np.max(b_thin[nose])) - float(np.max(b_stock[nose]))) < 0.05 * float(np.max(b_stock[nose])) + 1e-6


def test_defaults_and_flat_roundtrip():
    p = BladeParams()
    flat = blade_to_flat(p)
    q = blade_from_flat(dict(flat, le_thick_scale=1.3, te_thick_scale=1.4))
    assert abs(q.le_thick_scale - 1.3) < 1e-9
    assert abs(q.te_thick_scale - 1.4) < 1e-9
