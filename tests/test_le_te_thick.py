"""LE / TE chordwise thickness scale + uniform absolute wall helpers."""

from __future__ import annotations

import numpy as np

from fansim.geometry.airfoil import naca4
from fansim.geometry.blade import (
    BladeParams,
    TE_BLUNT_FRAC,
    apply_le_te_thickness,
    le_te_thick_factors,
    uniform_thickness_tc,
)
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, blade_to_flat


def test_factors_unity_when_scales_one():
    x = np.linspace(0.0, 1.0, 21)
    assert np.allclose(le_te_thick_factors(x, 1.0, 1.0), 1.0)


def test_factors_ends_and_mid_stay_near_stock():
    """LE/TE=1.5 must hit ends but not inflate mid-chord like the old blend."""
    x = np.linspace(0.0, 1.0, 101)
    f = le_te_thick_factors(x, 1.5, 1.5)
    assert abs(float(f[0]) - 1.5) < 1e-9
    assert abs(float(f[-1]) - 1.5) < 1e-9
    # Mid-chord: cubic end weights → ~1.125, not the old ~1.5 everywhere.
    mid = float(f[50])
    assert 1.05 < mid < 1.20


def test_stock_both_one_is_noop():
    loop, x = naca4(0.0, 0.4, 0.08, 40, return_chord_param=True)
    if np.allclose(loop[0], loop[-1]):
        loop, x = loop[:-1], x[:-1]
    b0 = loop[:, 1] * 40.0
    assert np.allclose(b0, apply_le_te_thickness(x, b0, 40.0, 1.0, 1.0))


def _profile(le: float, te: float, chord: float = 38.0, t: float = 0.06, camber: float = 0.0):
    loop, x = naca4(camber, 0.4, t, 60, return_chord_param=True)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
        x = x[:-1]
    b = apply_le_te_thickness(x, loop[:, 1] * chord, chord, le, te)
    return x, np.abs(b)


def test_le_te_uses_parametric_x_not_cambered_surface():
    """High camber: surface X ≠ generator x; scales must follow the parameter (§12.13)."""
    loop, x_param = naca4(0.08, 0.4, 0.08, 80, return_chord_param=True)
    if np.allclose(loop[0], loop[-1]):
        loop, x_param = loop[:-1], x_param[:-1]
    x_surf = loop[:, 0]
    assert float(np.max(np.abs(x_surf - x_param))) > 0.005
    chord = 40.0
    b0 = loop[:, 1] * chord
    b_param = apply_le_te_thickness(x_param, b0.copy(), chord, 1.5, 1.0)
    b_surf = apply_le_te_thickness(x_surf, b0.copy(), chord, 1.5, 1.0)
    # Nose fattening under parametric x should differ from (wrong) surface-X weighting.
    assert float(np.max(np.abs(b_param - b_surf))) > 1e-4


def test_te_blunt_no_tip_sign_spike():
    """Cambered NACA TE tip is ~-0.0; blunt must not drive that vertex alone to -te_half (flap)."""
    loop, x = naca4(0.06, 0.4, 0.03, 60, return_chord_param=True)
    if np.allclose(loop[0], loop[-1]):
        loop, x = loop[:-1], x[:-1]
    b0 = loop[:, 1] * 40.0
    b = apply_le_te_thickness(x, b0.copy(), 40.0, 1.0, 2.0)
    i_le = int(np.argmin(x))
    abs0 = np.abs(b0)
    assert b[0] > 0.0
    assert b[-1] < 0.0
    lifted_upper = (np.arange(len(x)) <= i_le) & (x > 0.97) & (np.abs(b) > abs0 + 1e-9)
    lifted_lower = (np.arange(len(x)) > i_le) & (x > 0.97) & (np.abs(b) > abs0 + 1e-9)
    assert lifted_upper.any() and lifted_lower.any()
    assert float(np.min(b[lifted_upper])) > 0.0
    assert float(np.max(b[lifted_lower])) < 0.0


def test_te_blunt_under_stagger_is_documented_experimental():
    """Stagger≠0: blunt stays chord-normal (pre-pitch); regression that TE>1 still fattens aft."""
    from fansim.geometry.blade import _section_loop
    from fansim.geometry.features import Features

    _, pts_stock = _section_loop(
        r=40.0, r_frac=0.5, chord=38.0, stagger_deg=30.0, thickness=0.06,
        max_camber=0.04, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=48, features=Features(), te_thick_scale=1.0,
    )
    x_fat, pts_fat = _section_loop(
        r=40.0, r_frac=0.5, chord=38.0, stagger_deg=30.0, thickness=0.06,
        max_camber=0.04, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
        lean_deg=0.0, n_chord=48, features=Features(), te_thick_scale=1.5,
    )
    # TE region (high parametric x): fat section should extend further from mid-chord plane.
    assert len(pts_fat) == len(pts_stock)
    # At least some aft points move when TE scale rises under stagger.
    moved = sum(
        1 for a, b in zip(pts_stock, pts_fat)
        if abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z) > 1e-4
    )
    assert moved > 5
    assert float(np.max(x_fat)) > 0.9


def test_le_scale_fattens_nose_not_midchord():
    """LE=1.5 must thicken the nose without ballooning mid-chord (old multiply+puff)."""
    x, b_le = _profile(1.5, 1.0)
    _, b_stock = _profile(1.0, 1.0)
    nose = x < 0.08
    mid = (x > 0.40) & (x < 0.60)
    assert float(np.max(b_le[nose])) > float(np.max(b_stock[nose])) * 1.25
    assert float(np.max(b_le[mid])) < float(np.max(b_stock[mid])) * 1.15


def test_te_scale_above_one_fattens_aft():
    """TE>1 must multiply the aft section — not only a near-invisible tip blunt."""
    x, b_fat = _profile(1.0, 1.5)
    _, b_stock = _profile(1.0, 1.0)
    aft = (x > 0.85) & (x < 0.95)
    assert float(np.max(b_fat[aft])) > float(np.max(b_stock[aft])) * 1.15
    nose = x < 0.15
    assert abs(float(np.max(b_fat[nose])) - float(np.max(b_stock[nose]))) < 0.05 * float(
        np.max(b_stock[nose])
    ) + 1e-6


def test_te_blunt_is_capped_below_le_nose():
    """TE must stay a short edge — not matched to full LE half-thickness (paddle)."""
    x, b = _profile(1.5, 1.5)
    x1, b_sharp = _profile(1.5, 1.0)
    le_half = float(np.max(b[x < 0.15]))
    tip = x > 0.99
    te_blunt = float(np.max(b[tip]))
    te_sharp = float(np.max(b_sharp[x1 > 0.99]))
    t_peak = float(np.max(b))
    assert te_blunt > te_sharp + 0.005
    assert te_blunt <= TE_BLUNT_FRAC * t_peak + 1e-6
    assert te_blunt < 0.55 * le_half
    mid_aft = (x > 0.80) & (x < 0.90)
    # TE multiplicative fattening is allowed in mid-aft; just keep it below LE nose.
    assert float(np.max(b[mid_aft])) < 0.85 * le_half


def test_te_scale_below_one_thins_aft():
    x, b_thin = _profile(1.0, 0.5)
    _, b_stock = _profile(1.0, 1.0)
    aft = x > 0.85
    assert float(np.max(b_thin[aft])) < float(np.max(b_stock[aft])) * 0.85
    nose = x < 0.15
    assert abs(float(np.max(b_thin[nose])) - float(np.max(b_stock[nose]))) < 0.05 * float(
        np.max(b_stock[nose])
    ) + 1e-6


def test_uniform_thickness_tc_keeps_abs_mm():
    th_r, th_m, th_t = uniform_thickness_tc(2.0, 18.0, 25.0, 38.0)
    assert abs(th_r * 18.0 - 2.0) < 1e-9
    assert abs(th_m * 25.0 - 2.0) < 1e-9
    assert abs(th_t * 38.0 - 2.0) < 1e-9
    # Equal mm ⇒ falling t/c as chord grows
    assert th_r > th_m > th_t


def test_blade_from_flat_uniform_mm_stations():
    th_r, th_m, th_t = uniform_thickness_tc(2.0, 18.0, 25.0, 38.0)
    flat = dict(
        n_blades=9,
        chord_root=18,
        chord_mid=25,
        chord_tip=38,
        stagger_root=40,
        stagger_mid=30,
        stagger_tip=22,
        max_camber=0.05,
        camber_pos=0.4,
        sweep_mid=0,
        sweep_tip=0,
        skew_mid=0,
        skew_tip=0,
        lean_mid=0,
        lean_tip=0,
        thickness_root=th_r,
        thickness_mid=th_m,
        thickness_tip=th_t,
        le_thick_scale=1.0,
        te_thick_scale=1.0,
    )
    bp = blade_from_flat(flat, Features())
    abs_mm = [s.thickness * s.chord for s in sorted(bp.stations, key=lambda s: s.r_frac)]
    assert all(abs(a - 2.0) < 1e-9 for a in abs_mm)


def test_defaults_and_flat_roundtrip():
    p = BladeParams()
    flat = blade_to_flat(p)
    q = blade_from_flat(dict(flat, le_thick_scale=1.3, te_thick_scale=1.4))
    assert abs(q.le_thick_scale - 1.3) < 1e-9
    assert abs(q.te_thick_scale - 1.4) < 1e-9


def test_tip_le_te_z_honors_te_thick_scale():
    """Shroud/hub helpers must not silently omit LE/TE scales (GEO-05)."""
    from fansim.geometry.blade import tip_le_te_z

    stock = BladeParams()
    fat = BladeParams()
    fat.te_thick_scale = 2.0
    _le0, te0 = tip_le_te_z(stock)
    _le1, te1 = tip_le_te_z(fat)
    assert abs(te1 - te0) > 0.05
