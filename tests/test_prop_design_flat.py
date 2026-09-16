"""Prop Design flat / Optimize contracts (roadmap §14.1)."""

from __future__ import annotations

import optuna
import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import blade_params_from_trial_params, suggest_prop
from fansim.propeller.params_io import (
    PROP_DESIGN_KEYS,
    prop_flat_from_params,
    prop_params_from_flat,
)


def test_legacy_camber_flat_still_builds():
    spec = get_prop_spec("fpv_5inch")
    bp = prop_params_from_flat(spec, {
        "n_blades": 3, "pitch_in": 4.3,
        "chord_root": 0.2, "chord_mid": 0.26, "chord_tip": 0.1,
        "camber": 0.045,
    })
    assert all(abs(s.max_camber - 0.045) < 1e-9 for s in bp.stations)


def test_prop_design_flat_round_trip():
    spec = get_prop_spec("fpv_5inch")
    flat = {
        "n_blades": 3, "pitch_in": 4.5,
        "chord_root": 0.18, "chord_mid": 0.24, "chord_tip": 0.09,
        "thickness_root": 0.10, "thickness_mid": 0.07, "thickness_tip": 0.05,
        "camber_root": 0.03, "camber_mid": 0.04, "camber_tip": 0.035,
        "sweep_mid": 1.0, "sweep_tip": 5.0,
        "le_skew_mid": 2.0, "le_skew_tip": 8.0,
        "lean_tip": 6.0,
        "cylindrical_tip": True,
        "thick_mode": "tapered",
    }
    bp = prop_params_from_flat(spec, flat)
    tip = max(bp.stations, key=lambda s: s.r_frac)
    mid = min(bp.stations, key=lambda s: abs(s.r_frac - 0.5))
    assert tip.le_skew == pytest.approx(8.0)
    assert mid.sweep == pytest.approx(1.0)
    assert tip.lean_deg == pytest.approx(6.0)
    out = prop_flat_from_params(bp, pitch_in=4.5)
    assert out["le_skew_tip"] == pytest.approx(8.0)
    assert out["camber_mid"] == pytest.approx(0.04)


def test_uniform_wall_overrides_tc():
    spec = get_prop_spec("fpv_5inch")
    bp = prop_params_from_flat(spec, {
        "chord_root": 0.2, "chord_mid": 0.26, "chord_tip": 0.1,
        "thick_mode": "uniform", "thick_mm": 2.0,
        "thickness_root": 0.09, "thickness_mid": 0.06, "thickness_tip": 0.04,
    })
    for st in bp.stations:
        assert st.thickness * st.chord == pytest.approx(2.0, rel=1e-3)


def test_suggest_prop_emits_design_keys():
    spec = get_prop_spec("fpv_5inch")
    study = optuna.create_study(directions=["maximize", "maximize"])
    trial = study.ask()
    suggest_prop(trial, spec)
    for key in (
        "thickness_root", "camber_mid", "sweep_tip", "le_skew_tip", "lean_tip", "tip_round",
    ):
        assert key in trial.params


def test_blade_params_from_legacy_and_new_flats():
    spec = get_prop_spec("fpv_5inch")
    legacy = {
        "n_blades": 3, "pitch_in": 4.3,
        "chord_root": 0.20, "chord_mid": 0.26, "chord_tip": 0.10,
        "camber": 0.04,
    }
    a = blade_params_from_trial_params(spec, legacy)
    assert a.n_blades == 3
    assert a.stations[0].chord > 0
    full = {**legacy, "camber_root": 0.03, "camber_mid": 0.04, "camber_tip": 0.05,
            "le_skew_tip": 7.0}
    b = blade_params_from_trial_params(spec, full)
    assert max(b.stations, key=lambda s: s.r_frac).le_skew == pytest.approx(7.0)


def test_prop_design_keys_listed():
    assert "le_skew_tip" in PROP_DESIGN_KEYS
    assert "thick_mode" in PROP_DESIGN_KEYS


def test_cockpit_declares_prop_shape_panels():
    from pathlib import Path
    text = Path("fansim/cockpit/prop_tab.py").read_text(encoding="utf-8")
    assert "render_shape_panels" in text
    assert "p_thick_mode" in text
