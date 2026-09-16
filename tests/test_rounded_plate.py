"""Rounded-plate (bullnose / sharp-TE / cambered) section family."""

from __future__ import annotations

import numpy as np

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
    loop = rounded_plate(t, 100, te_radius_frac=0.2)
    if np.allclose(loop[0], loop[-1]):
        loop = loop[:-1]
    R_le = 0.5 * t
    R_te = 0.2 * R_le
    # TE tip neighborhood should track the small TE circle, not the flat ±t/2 face.
    near_te_tip = loop[:, 0] > (1.0 - R_te) - 1e-6
    assert near_te_tip.any()
    d_te = np.hypot(loop[near_te_tip, 0] - (1.0 - R_te), loop[near_te_tip, 1])
    assert abs(float(np.mean(d_te)) - R_te) < 0.05 * R_le + 1e-3
    assert R_te < 0.35 * R_le


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
