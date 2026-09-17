"""Rounded-plate (bullnose / sharp-TE / cambered) section family."""

from __future__ import annotations

import numpy as np
import pytest

from fansim.geometry.airfoil import rounded_plate, section_loop_2d
from fansim.geometry.blade import BladeParams, SECTION_NACA, SECTION_PLATE
from fansim.optimize.search_space import blade_from_flat, blade_to_flat


def test_plate_ends_are_full_round():
    t = 0.10
    R = 0.5 * t
    loop = rounded_plate(t, 80)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    # LE tip at x≈0, y≈0; points near LE should lie on circle center (R,0)
    near_le = loop[:, 0] < R * 0.5
    assert near_le.any()
    d_le = np.hypot(loop[near_le, 0] - R, loop[near_le, 1])
    assert abs(float(np.mean(d_le)) - R) < 0.02 * R + 1e-3
    # TE tip near x=1
    near_te = loop[:, 0] > 1.0 - R * 0.5
    d_te = np.hypot(loop[near_te, 0] - (1.0 - R), loop[near_te, 1])
    assert abs(float(np.mean(d_te)) - R) < 0.02 * R + 1e-3
    # Flat faces at ±R
    mid = (loop[:, 0] > R + 0.05) & (loop[:, 0] < 1.0 - R - 0.05)
    assert mid.any()
    assert abs(float(np.max(np.abs(loop[mid, 1]))) - R) < 1e-6


def test_plate_sharp_te_is_smaller_than_le():
    t = 0.10
    half = 0.5 * t
    loop = rounded_plate(t, 100, te_radius_frac=0.2)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    a_te = 0.2 * half
    # Sharp TE is an ellipse (a_te, half) — chordwise short, still flush at ±half.
    near_te = loop[:, 0] >= (1.0 - a_te) - 1e-9
    assert near_te.any()
    cx = 1.0 - a_te
    resid = ((loop[near_te, 0] - cx) / a_te) ** 2 + (loop[near_te, 1] / half) ** 2
    assert float(np.max(np.abs(resid - 1.0))) < 0.05
    assert a_te < 0.35 * half


def test_plate_sharp_le_joins_flat_without_shoulder():
    """le_frac<1 must not drop from ±t/2 into a smaller circle (that ridge is the bead)."""
    t = 0.10
    half = 0.5 * t
    a_le = 0.2 * half
    loop = rounded_plate(t, 120, le_radius_frac=0.2, te_radius_frac=1.0)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    # Face/nose join at x≈a_le stays at y=±half (ellipse), not y=±a_le (old circle bug).
    band = np.abs(loop[:, 0] - a_le) < max(0.02 * half, 1e-6)
    upper = loop[band & (loop[:, 1] > 0.0)]
    assert upper.size
    assert abs(float(np.max(upper[:, 1])) - half) < 1e-6
    near_le = loop[:, 0] <= a_le + 1e-9
    resid = ((loop[near_le, 0] - a_le) / a_le) ** 2 + (loop[near_le, 1] / half) ** 2
    assert float(np.max(np.abs(resid - 1.0))) < 0.05
    full = rounded_plate(t, 100, le_radius_frac=1.0)
    if np.allclose(full[0], full[-1]):
        full = full[:-1]
    mid_y = half * 0.98
    sharp_flat = loop[(loop[:, 0] > a_le + 0.02) & (np.abs(loop[:, 1]) > mid_y)]
    full_flat = full[(full[:, 0] > half + 0.02) & (np.abs(full[:, 1]) > mid_y)]
    assert float(np.min(sharp_flat[:, 0])) < float(np.min(full_flat[:, 0])) - 0.01


def test_section_loop_2d_passes_le_radius_frac():
    t = 0.10
    half = 0.5 * t
    a_le = 0.2 * half
    loop = section_loop_2d(
        "plate", max_camber=0.0, camber_pos=0.4, thickness=t, n_points=80,
        le_radius_frac=0.2, te_radius_frac=1.0,
    )
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    near_le = loop[:, 0] <= a_le + 1e-9
    assert near_le.any()
    resid = ((loop[near_le, 0] - a_le) / a_le) ** 2 + (loop[near_le, 1] / half) ** 2
    assert float(np.max(np.abs(resid - 1.0))) < 0.05


def test_blade_params_plate_le_thick_scale_roundtrips():
    flat = blade_to_flat(BladeParams(section_family=SECTION_PLATE, le_thick_scale=0.25, te_thick_scale=0.2))
    assert flat["le_thick_scale"] == pytest.approx(0.25)
    assert flat["te_thick_scale"] == pytest.approx(0.2)
    p = blade_from_flat(flat)
    assert p.section_family == SECTION_PLATE
    assert p.le_thick_scale == pytest.approx(0.25)
    assert p.te_thick_scale == pytest.approx(0.2)


def test_plate_default_le_follows_te_roundness():
    """Uniform-wall plate: legacy LE=1.0 (full bullnose) must not stay a t/2 bead."""
    from fansim.geometry.blade import _thick_scale_kw

    p = BladeParams(section_family=SECTION_PLATE, le_thick_scale=1.0, te_thick_scale=0.2)
    kw = _thick_scale_kw(p)
    assert kw["te_thick_scale"] == pytest.approx(0.2)
    assert kw["le_thick_scale"] == pytest.approx(0.2)
    # Explicit LE still wins.
    p2 = BladeParams(section_family=SECTION_PLATE, le_thick_scale=0.5, te_thick_scale=0.2)
    assert _thick_scale_kw(p2)["le_thick_scale"] == pytest.approx(0.5)


def test_plate_camber_bows_face():
    flat = rounded_plate(0.08, 80, max_camber=0.0)
    cam = rounded_plate(0.08, 80, max_camber=0.05, camber_pos=0.4)
    # Cambered mid-surface sits above y=0; flat plate is symmetric.
    assert abs(float(np.max(flat[:, 1]) + np.min(flat[:, 1]))) < 1e-9
    assert float(np.max(cam[:, 1]) + np.min(cam[:, 1])) > 0.02


def test_section_loop_2d_dispatch():
    naca = section_loop_2d("naca", max_camber=0.0, camber_pos=0.4, thickness=0.08, n_points=40)
    plate = section_loop_2d("plate", max_camber=0.0, camber_pos=0.4, thickness=0.08, n_points=40)
    assert naca.shape[1] == 2 and plate.shape[1] == 2
    assert abs(float(np.max(plate[:, 1]) + np.min(plate[:, 1]))) < 1e-9


def test_blade_params_default_naca_and_flat_roundtrip():
    assert BladeParams().section_family == SECTION_NACA
    flat = blade_to_flat(BladeParams())
    assert flat["section_family"] == "naca"
    p = blade_from_flat(dict(flat, section_family="plate"))
    assert p.section_family == SECTION_PLATE
    slim = {k: v for k, v in flat.items() if k != "section_family"}
    assert blade_from_flat(slim).section_family == SECTION_NACA
