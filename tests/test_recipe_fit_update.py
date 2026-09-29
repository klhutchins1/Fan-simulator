"""Pure update step of the recipe-to-STL section fit (fansim.validation.recipe_fit)."""

from __future__ import annotations

import pytest

from fansim.validation.recipe_fit import BOUNDS, DAMPING, residuals, update_station, within_tol

ST = {"chord": 16.0, "stagger_deg": 52.0, "thickness": 0.10, "max_camber": 0.10,
      "camber_pos": 0.40, "sweep": 0.0, "skew": 3.0, "lean_deg": 14.0}
BUILT = {"chord_mm": 15.0, "stagger_deg": 54.0, "camber_ratio": 0.065, "camber_pos": 0.42,
         "thickness_ratio": 0.12}
REF = {"chord_mm": 24.0, "stagger_deg": 34.0, "camber_ratio": 0.035, "camber_pos": 0.47,
       "thickness_ratio": 0.10}


def test_update_moves_damped_toward_target():
    new, hit = update_station(ST, BUILT, REF)
    d = DAMPING
    assert hit == []
    assert new["stagger_deg"] == pytest.approx(52.0 + d * (34.0 - 54.0))
    assert new["chord"] == pytest.approx(16.0 + d * (16.0 * 24.0 / 15.0 - 16.0))
    assert new["max_camber"] == pytest.approx(0.10 + d * (0.10 * 0.035 / 0.065 - 0.10))
    assert new["camber_pos"] == pytest.approx(0.40 + d * (0.47 - 0.42))
    assert new["thickness"] == pytest.approx(0.10 + d * (0.10 * 0.10 / 0.12 - 0.10))
    # untouched fields (sweep/skew/lean) unless adjustment requested
    assert (new["sweep"], new["skew"], new["lean_deg"]) == (0.0, 3.0, 14.0)


def test_undamped_is_exact_correction_and_fixed_point_when_matched():
    new, _ = update_station(ST, BUILT, REF, damping=1.0)
    assert new["stagger_deg"] == pytest.approx(52.0 - 20.0)
    assert new["chord"] == pytest.approx(16.0 * 24.0 / 15.0)
    same, _ = update_station(ST, REF, REF)
    for k in ("chord", "stagger_deg", "thickness", "max_camber", "camber_pos"):
        assert same[k] == pytest.approx(ST[k])


def test_clamping_reports_hits():
    huge = dict(REF, chord_mm=1000.0, stagger_deg=-500.0)
    new, hit = update_station(ST, BUILT, huge, damping=1.0)
    assert new["chord"] == BOUNDS["chord"][1]
    assert new["stagger_deg"] == BOUNDS["stagger_deg"][0]
    assert {"chord", "stagger_deg"} <= set(hit)


def test_sweep_skew_adjust_only_when_asked_and_opposes_offset():
    new, _ = update_station(ST, BUILT, REF, adjust_sweep=True, adjust_skew=True,
                            d_le_z_mm=3.0, d_skew_mm=-4.0)
    assert new["sweep"] == pytest.approx(-DAMPING * 3.0)
    assert new["skew"] == pytest.approx(3.0 + DAMPING * 4.0)


def test_residuals_and_tolerance():
    assert within_tol(residuals(REF, REF))
    near = dict(REF, stagger_deg=REF["stagger_deg"] + 1.4, chord_mm=REF["chord_mm"] * 1.029)
    assert within_tol(residuals(near, REF))
    far = dict(REF, camber_ratio=REF["camber_ratio"] + 0.006)
    assert not within_tol(residuals(far, REF))
