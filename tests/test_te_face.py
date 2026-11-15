"""Trailing-edge face thickness. 1 keeps today's plate. 0 brings the back edge to the chord."""

from __future__ import annotations

import numpy as np
import pytest

from fansim.geometry.airfoil import rounded_plate
from fansim.geometry.blade import BladeParams, Features, _section_loop
from fansim.optimize.search_space import blade_from_flat, blade_to_flat


def _drop_close(loop):
    if np.allclose(loop[0], loop[-1]):
        return loop[:-1]
    return loop


def test_full_face_matches_todays_plate():
    kwargs = dict(te_radius_frac=0.2, le_radius_frac=0.2, max_camber=0.04, camber_pos=0.4)
    today = rounded_plate(0.10, 80, **kwargs)
    same = rounded_plate(0.10, 80, te_face=1.0, **kwargs)
    assert np.allclose(today, same)


def test_zero_face_thins_the_trailing_edge_and_keeps_the_leading_edge():
    kwargs = dict(te_radius_frac=0.2, le_radius_frac=0.2, return_chord_param=True)
    full, x_full = rounded_plate(0.10, 120, te_face=1.0, **kwargs)
    thin, x_thin = rounded_plate(0.10, 120, te_face=0.0, **kwargs)
    full, thin = _drop_close(full), _drop_close(thin)
    x_full, x_thin = x_full[: len(full)], x_thin[: len(thin)]
    le = x_full < 0.40
    assert np.allclose(full[le], thin[le])
    te = x_thin > 0.98
    assert te.any()
    assert float(np.max(np.abs(thin[te, 1]))) < 0.005
    mid = np.abs(x_thin - 0.40) < 0.03
    assert abs(float(np.max(np.abs(thin[mid, 1]))) - 0.05) < 1e-3


def test_zero_front_thins_the_leading_edge_and_keeps_the_trailing_edge():
    kwargs = dict(te_radius_frac=0.2, le_radius_frac=0.2, te_face=1.0, return_chord_param=True)
    full, x_full = rounded_plate(0.10, 120, le_face=1.0, **kwargs)
    thin, x_thin = rounded_plate(0.10, 120, le_face=0.0, **kwargs)
    full, thin = _drop_close(full), _drop_close(thin)
    x_full, x_thin = x_full[: len(full)], x_thin[: len(thin)]
    te = x_full > 0.60
    assert np.allclose(full[te], thin[te])
    le = x_thin < 0.02
    assert le.any()
    assert float(np.max(np.abs(thin[le, 1]))) < 0.005


def test_face_and_root_embed_roundtrip():
    params = BladeParams(section_family="plate", hub_radius=26.0, root_embed=6.5)
    for station, back_face, front_face in zip(params.stations, (0.4, 0.7, 0.2), (0.3, 0.0, 0.9)):
        station.te_face = back_face
        station.le_face = front_face
    back = blade_from_flat(blade_to_flat(params))
    assert back.root_embed == pytest.approx(6.5)
    assert back.hub_radius == pytest.approx(26.0)
    ordered = sorted(back.stations, key=lambda s: s.r_frac)
    assert [s.te_face for s in ordered] == pytest.approx([0.4, 0.7, 0.2])
    assert [s.le_face for s in ordered] == pytest.approx([0.3, 0.0, 0.9])


def test_outline_copy_is_the_hub26_plate_not_stock():
    from fansim.optimize.search_space import outline_blade_flat, stock_blade_flat

    copy = blade_from_flat(outline_blade_flat())
    stock = blade_from_flat(stock_blade_flat("a12x25"))
    assert copy.hub_radius == pytest.approx(26.0)
    assert copy.root_embed == pytest.approx(6.5)
    assert copy.section_family == "plate"
    assert stock.hub_radius == pytest.approx(21.5)
    assert all(s.te_face == pytest.approx(0.0) for s in copy.stations)
    ordered = sorted(copy.stations, key=lambda s: s.r_frac)
    # r/R 0.50 is the sharp front. r/R 0.90 keeps most of the front wall.
    by_frac = {round(s.r_frac, 4): s.le_face for s in ordered}
    assert by_frac[0.2214] == pytest.approx(0.0, abs=0.02)
    assert by_frac[0.8443] == pytest.approx(0.86, abs=0.02)


def test_sharper_face_shortens_the_section_and_holds_the_high_edge():
    def ends(face: float):
        _x, pts = _section_loop(
            r=40.0, r_frac=0.5, chord=25.0, stagger_deg=30.0, thickness=0.10,
            max_camber=0.04, camber_pos=0.4, sweep=0.0, skew=0.0, le_sweep=0.0,
            lean_deg=0.0, n_chord=60, features=Features(),
            section_family="plate", le_thick_scale=0.2, te_thick_scale=0.2,
            te_face=face, wrap=False,
        )
        z = [p.z for p in pts]
        return max(z) - min(z), max(z)

    full, high = ends(1.0)
    thin, high_thin = ends(0.0)
    assert thin < full - 0.5
    assert abs(high_thin - high) < 0.15
