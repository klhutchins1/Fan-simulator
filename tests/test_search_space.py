"""Guided / open search-space bounds and frame tip-radius cap."""

import optuna
import pytest

from fansim.geometry.blade import BladeParams, RadialStation, SHROUD_DEFAULT_MM, open_tip_rmax_mm
from fansim.optimize.search_space import (
    SICKLE_BOUNDS,
    STATOR_BOUNDS,
    TIP_CAP_CLEARANCE_MM,
    suggest_params,
    suggest_sickle,
    suggest_stator,
    tip_radius_cap_mm,
)

optuna.logging.set_verbosity(optuna.logging.WARNING)

FRAME_HALF = 55.0  # A12x25 110 mm ID
OLD_PAD_CAP = FRAME_HALF - 4.0  # 51 mm


def _stations(*, chord_tip: float, lean_tip: float, lean_mid: float = 0.0) -> list[RadialStation]:
    return [
        RadialStation(0.0, 18.0, 40.0, thickness=0.10, lean_deg=0.0),
        RadialStation(0.5, 18.0, 40.0, thickness=0.08, lean_deg=lean_mid),
        RadialStation(1.0, chord_tip, 40.0, thickness=0.06, lean_deg=lean_tip),
    ]


def test_low_lean_cap_beats_the_four_mm_pad():
    cap = tip_radius_cap_mm(_stations(chord_tip=14.0, lean_tip=0.0), 21.5, FRAME_HALF)
    assert cap > OLD_PAD_CAP


def test_high_lean_cap_is_tighter_than_low_lean_when_trim_off():
    """Legacy bulge: wrap costs radius. With cylindrical tip off, high lean must shrink the cap."""
    low = tip_radius_cap_mm(_stations(chord_tip=14.0, lean_tip=0.0), 21.5, FRAME_HALF,
                            cylindrical_tip=False, section_wrap="planar")
    high = tip_radius_cap_mm(_stations(chord_tip=40.0, lean_tip=45.0, lean_mid=25.0),
                             21.5, FRAME_HALF, cylindrical_tip=False, section_wrap="planar")
    assert high < low - 1.0
    assert high < FRAME_HALF - TIP_CAP_CLEARANCE_MM  # never the zero-bulge ceiling


def test_wrapped_sections_do_not_bulge_even_with_trim_off():
    """27.4: wrapped sections lie on their cylinder, so lean costs no radius at all."""
    low = tip_radius_cap_mm(_stations(chord_tip=14.0, lean_tip=0.0), 21.5, FRAME_HALF,
                            cylindrical_tip=False)
    high = tip_radius_cap_mm(_stations(chord_tip=40.0, lean_tip=45.0, lean_mid=25.0),
                             21.5, FRAME_HALF, cylindrical_tip=False)
    assert high == pytest.approx(low, abs=0.01)
    assert low == pytest.approx(FRAME_HALF - TIP_CAP_CLEARANCE_MM, abs=0.2)  # one 0.15 mm step


def test_cylindrical_tip_cap_ignores_lean_bulge():
    """With trim on, LE/TE corners do not push past tip_radius — lean barely moves the cap."""
    low = tip_radius_cap_mm(_stations(chord_tip=14.0, lean_tip=0.0), 21.5, FRAME_HALF)
    high = tip_radius_cap_mm(_stations(chord_tip=40.0, lean_tip=45.0, lean_mid=25.0),
                             21.5, FRAME_HALF)
    assert abs(high - low) < 0.5
    assert low >= FRAME_HALF - TIP_CAP_CLEARANCE_MM - 0.2


def test_capped_probe_leaves_half_mm_leftover():
    stations = _stations(chord_tip=30.0, lean_tip=20.0, lean_mid=10.0)
    cap = tip_radius_cap_mm(stations, 21.5, FRAME_HALF)
    probe = BladeParams(hub_radius=21.5, tip_radius=cap, stations=stations)
    assert open_tip_rmax_mm(probe) + 0.5 <= FRAME_HALF + 0.2


def test_shroud_drops_cap_by_ring_thickness():
    stations = _stations(chord_tip=20.0, lean_tip=10.0)
    open_cap = tip_radius_cap_mm(stations, 21.5, FRAME_HALF, shroud_mm=0.0)
    ring_cap = tip_radius_cap_mm(stations, 21.5, FRAME_HALF, shroud_mm=SHROUD_DEFAULT_MM)
    assert ring_cap < open_cap
    assert open_cap - ring_cap >= SHROUD_DEFAULT_MM * 0.8
    probe = BladeParams(hub_radius=21.5, tip_radius=ring_cap, stations=stations)
    probe.shroud_thick_mm = SHROUD_DEFAULT_MM
    built = open_tip_rmax_mm(probe) + SHROUD_DEFAULT_MM
    assert built + 0.5 <= FRAME_HALF + 0.2


def test_suggest_params_samples_at_or_below_the_cap():
    study = optuna.create_study()
    for _ in range(8):
        t = study.ask()
        bp = suggest_params(t, frame_half_mm=FRAME_HALF)
        cap = tip_radius_cap_mm(bp.stations, bp.hub_radius, FRAME_HALF)
        assert bp.tip_radius <= cap + 1e-9
        study.tell(t, 0.0)


def _sample(space: str, n: int):
    # Random, not TPE: on a constant objective TPE has nothing to learn and can stick near an
    # unlucky first 10 trials (no n_blades >= 9 through trial 30 in ~1 of 680 unseeded runs).
    # These tests are about what the bounds can reach, not how TPE behaves.
    study = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=0))
    study.optimize(
        lambda t: (suggest_params(t, space=space), 0.0)[1],
        n_trials=n,
    )
    return study.trials


def test_sample_helper_is_reproducible():
    # Reach tests below must not depend on luck: an unseeded study failed the suite on 2026-11-08.
    a = [t.params for t in _sample("guided", 12)]
    b = [t.params for t in _sample("guided", 12)]
    assert a == b


def test_guided_reaches_open_camber_and_blade_count():
    trials = _sample("guided", 30)
    blades = [t.params["n_blades"] for t in trials]
    camber = [t.params["max_camber"] for t in trials]
    assert all(5 <= n <= 11 for n in blades)
    assert all(0.0 <= c <= 0.06 for c in camber)
    assert any(n >= 9 for n in blades)
    assert any(c > 0.02 for c in camber)


def test_guided_lc_reopens_camber_keeps_load_spread_blades():
    trials = _sample("guided_lc", 20)
    blades = [t.params["n_blades"] for t in trials]
    camber = [t.params["max_camber"] for t in trials]
    assert all(7 <= n <= 11 for n in blades)
    assert all(0.0 <= c <= 0.06 for c in camber)
    assert any(c > 0.02 for c in camber)


def test_suggest_stator_within_bounds():
    lo_s, hi_s = STATOR_BOUNDS["stator_stagger_deg"]
    lo_e, hi_e = STATOR_BOUNDS["stator_n_extra"]
    study = optuna.create_study()
    for _ in range(12):
        t = study.ask()
        s = suggest_stator(t)
        assert lo_s <= s["stagger_deg"] <= hi_s
        assert lo_e <= s["n_extra"] <= hi_e
        assert "stator_stagger_deg" in t.params
        assert "stator_n_extra" in t.params
        study.tell(t, 0.0)


def test_suggest_params_without_stator_omits_stator_keys():
    study = optuna.create_study()
    t = study.ask()
    suggest_params(t)
    assert "stator_stagger_deg" not in t.params
    assert "stator_n_extra" not in t.params
    study.tell(t, 0.0)


def test_suggest_sickle_within_bounds():
    lo, hi = SICKLE_BOUNDS
    study = optuna.create_study()
    for _ in range(12):
        t = study.ask()
        tip = suggest_sickle(t)
        assert lo <= tip <= hi
        assert "sickle_mm" in t.params
        study.tell(t, 0.0)


def test_suggest_params_without_sickle_omits_sickle_mm():
    study = optuna.create_study()
    t = study.ask()
    suggest_params(t)
    assert "sickle_mm" not in t.params
    study.tell(t, 0.0)
