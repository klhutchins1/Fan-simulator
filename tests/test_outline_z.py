"""Z-edge step: hold the leading edge, lift the trailing edge. No mesh build."""
from pathlib import Path

import numpy as np
import pytest

from fansim.geometry.airfoil import section_loop_2d
from fansim.geometry.config import load_blade_params
from scripts.outline_z import (
    DAMP,
    HUB26_ERRORS,
    apply_edge,
    edge_shift,
    edges_pass,
    extrapolate_delta,
    section_errors,
    starting_params,
    worst_edge,
)

ROOT_SWEEP_STEP = extrapolate_delta(0.0, 0.2214, 2.11, 0.3771, 1.23)


def test_shift_holds_the_leading_edge_and_lifts_the_trailing_edge():
    d_sweep, d_le_sweep = edge_shift(d_le=-0.09, d_ext=2.02)
    assert d_le_sweep == pytest.approx(-2.02)
    assert d_sweep == pytest.approx(2.11)
    assert d_sweep + d_le_sweep == pytest.approx(0.09)


def test_a_pure_offset_does_not_bend_the_section():
    d_sweep, d_le_sweep = edge_shift(d_le=-0.40, d_ext=0.0)
    assert d_le_sweep == pytest.approx(0.0)
    assert d_sweep == pytest.approx(0.40)


def test_hub26_extent_fails_the_bar_and_a_match_passes_it():
    assert edges_pass(HUB26_ERRORS) is False
    assert worst_edge(HUB26_ERRORS) == pytest.approx(2.02)
    assert edges_pass({k: (0.0, 0.0) for k in HUB26_ERRORS}) is True


def test_apply_moves_only_sweep_and_le_sweep():
    base = starting_params()
    got = apply_edge(base, HUB26_ERRORS, damp=1.0)
    # r/R 0.50 is station 1. The step is the undamped shift.
    assert got.stations[1].sweep - base.stations[1].sweep == pytest.approx(2.11)
    assert got.stations[1].le_sweep - base.stations[1].le_sweep == pytest.approx(-2.02)
    assert got.stations[1].stagger_deg == pytest.approx(base.stations[1].stagger_deg)
    assert got.stations[1].chord == pytest.approx(base.stations[1].chord)
    assert got.stations[1].max_camber == pytest.approx(base.stations[1].max_camber)
    assert got.stations[1].thickness == pytest.approx(base.stations[1].thickness)
    assert got.stations[1].skew == pytest.approx(base.stations[1].skew)
    # Root is inside the hub: extrapolate the 0.50 and 0.60 steps.
    assert got.stations[0].sweep - base.stations[0].sweep == pytest.approx(ROOT_SWEEP_STEP)
    # Tip takes the r/R 0.95 cut, not a cut through the tip cap.
    tip_sweep, tip_le = edge_shift(*HUB26_ERRORS[0.95])
    assert got.stations[-1].le_sweep - base.stations[-1].le_sweep == pytest.approx(tip_le)
    assert got.stations[-1].sweep - base.stations[-1].sweep == pytest.approx(tip_sweep)


def test_damped_step_is_seventy_percent():
    base = starting_params()
    got = apply_edge(base, HUB26_ERRORS)
    full = apply_edge(base, HUB26_ERRORS, damp=1.0)
    assert DAMP == pytest.approx(0.7)
    assert got.stations[1].le_sweep == pytest.approx(DAMP * full.stations[1].le_sweep)


def test_section_errors_are_built_minus_reference():
    built = [{"r_frac": 0.50, "n_blades": 9, "le_z_mm": 4.18, "axial_extent_mm": 15.13}]
    ref = [{"r_frac": 0.50, "n_blades": 9, "le_z_mm": 4.27, "axial_extent_mm": 13.11}]
    # The other five radii are absent, so those errors are infinite.
    errors = section_errors(built, ref)
    assert errors[0.50] == pytest.approx((-0.09, 2.02))
    assert edges_pass(errors) is False


def _wire_le_extent(station, params):
    """Leading-edge z and axial extent of one station wire, millimetres."""
    loop, x = section_loop_2d(
        params.section_family, max_camber=station.max_camber, camber_pos=station.camber_pos,
        thickness=station.thickness, n_points=params.n_chord, return_chord_param=True,
    )
    if np.allclose(loop[0], loop[-1]):
        loop, x = loop[:-1], x[:-1]
    beta = np.radians(station.stagger_deg)
    a = (loop[:, 0] - 0.5) * station.chord
    b = loop[:, 1] * station.chord
    if station.stagger_deg >= 0.0:
        a = -a
    w_le = np.where(x < 0.5, 0.5 * (1.0 + np.cos(2.0 * np.pi * x)), 0.0)
    axial = a * np.sin(beta) + b * np.cos(beta) + station.sweep + station.le_sweep * w_le
    return float(axial[int(np.argmin(x))]), float(axial.max() - axial.min())


def test_the_step_cancels_the_error_on_the_station_wire():
    params = starting_params()
    station = params.stations[1]
    le, extent = _wire_le_extent(station, params)
    d_sweep, d_le_sweep = edge_shift(d_le=-0.4, d_ext=1.5)
    moved = station.__class__(**{**station.__dict__, "sweep": station.sweep + d_sweep,
                                  "le_sweep": station.le_sweep + d_le_sweep})
    new_le, new_extent = _wire_le_extent(moved, params)
    assert new_le - le == pytest.approx(0.4, abs=0.05)
    assert extent - new_extent == pytest.approx(1.5, abs=0.15)


def test_stock_camber_targets_are_unchanged():
    """This attempt must not retune the wrapped Stock recipe."""
    stock = load_blade_params(
        Path(__file__).resolve().parents[1] / "config/problems/a12x25_reference.yaml"
    )
    assert [s.max_camber for s in stock.stations] == pytest.approx(
        [0.0235, 0.0261, 0.0446, 0.0478, 0.0451, 0.0419, 0.0445], abs=1e-4
    )
