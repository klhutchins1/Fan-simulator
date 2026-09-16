"""CROR Design flat contracts (roadmap §14.5)."""

from __future__ import annotations

import optuna
import pytest

from fansim.cror.optimize import cror_params_from_trial_params, suggest_cror
from fansim.cror.params_io import cror_flat_from_params, cror_params_from_flat


def test_legacy_optuna_flat_still_builds():
    p = cror_params_from_flat({
        "axial_gap_mm": 6.0,
        "n_front": 7,
        "n_rear": 9,
        "stagger_deg": 40.0,
        "chord_mm": 14.0,
    })
    assert p.front.n_blades == 7
    assert p.rear.n_blades == 9
    assert p.front.stations[0].stagger_deg > 0
    assert p.rear.stations[0].stagger_deg < 0


def test_prefixed_design_flat_round_trip():
    p = cror_params_from_flat({
        "axial_gap_mm": 5.0,
        "n_front": 6,
        "n_rear": 8,
        "f_chord_root": 16.0, "f_chord_mid": 15.0, "f_chord_tip": 11.0,
        "f_stagger": 42.0, "f_le_skew_tip": 5.0,
        "r_chord_root": 15.0, "r_chord_mid": 14.0, "r_chord_tip": 10.0,
        "r_stagger": 38.0,
    })
    assert max(p.front.stations, key=lambda s: s.r_frac).le_skew == pytest.approx(5.0)
    flat = cror_flat_from_params(p)
    assert flat["n_front"] == 6
    assert flat["f_le_skew_tip"] == pytest.approx(5.0)
    q = cror_params_from_flat(flat)
    assert q.front.n_blades == 6
    assert q.rear.stations[0].stagger_deg < 0


def test_suggest_cror_emits_prefixed_keys():
    study = optuna.create_study(directions=["maximize", "maximize"])
    trial = study.ask()
    suggest_cror(trial)
    assert "f_chord_mid" in trial.params
    assert "r_stagger" in trial.params
    assert "f_le_skew_tip" in trial.params


def test_cror_params_from_trial_params_thins():
    p = cror_params_from_trial_params({
        "axial_gap_mm": 8.0,
        "n_front": 7,
        "n_rear": 9,
        "f_chord_root": 18.0, "f_chord_mid": 18.0, "f_chord_tip": 14.0,
        "f_stagger": 45.0,
        "r_chord_root": 18.0, "r_chord_mid": 18.0, "r_chord_tip": 14.0,
        "r_stagger": 45.0,
    })
    from fansim.cror.optimize import cror_stack_depth_mm
    assert cror_stack_depth_mm(p) <= 25.5


def test_cockpit_declares_cror_design_panels():
    from pathlib import Path
    text = Path("fansim/cockpit/cror_tab.py").read_text(encoding="utf-8")
    assert "cror_f_chord_mid" in text
    assert "render_shape_panels" in text
    assert "Front rotor" in text
