"""``chord_basis``: legacy loft-chord designs rebuild as scored; new designs use measured chord."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from fansim.geometry.blade import BladeParams
from fansim.geometry.chord_realisation import prepare_loft_chords, with_loft_chords
from fansim.geometry.config import load_blade_params
from fansim.optimize.search_space import blade_from_flat, blade_to_flat, stock_blade_flat
from fansim.optimize.trial_attrs import (
    CHORD_BASIS_CUTOFF,
    chord_basis_at,
    chord_basis_for_trial,
    trial_flat,
)


def test_default_basis_is_measured():
    assert BladeParams().chord_basis == "measured"


def test_loft_basis_is_built_unchanged():
    bp = BladeParams(chord_basis="loft")
    assert prepare_loft_chords(bp) is bp  # no build→measure loop, chords used as-is


def test_unknown_basis_raises():
    with pytest.raises(ValueError, match="chord_basis"):
        prepare_loft_chords(BladeParams(chord_basis="bogus"))


def test_realised_params_are_marked_loft_so_preparing_twice_is_a_noop():
    bp = BladeParams()
    realised = with_loft_chords(bp, [s.chord * 1.2 for s in bp.stations])
    assert realised.chord_basis == "loft"
    assert prepare_loft_chords(realised) is realised


def test_flat_round_trip_keeps_basis():
    flat = stock_blade_flat("a12x25")
    assert flat["chord_basis"] == "measured"
    assert blade_from_flat(flat).chord_basis == "measured"
    legacy = {**flat, "chord_basis": "loft"}
    bp = blade_from_flat(legacy)
    assert bp.chord_basis == "loft"
    assert blade_to_flat(bp)["chord_basis"] == "loft"


def test_unstamped_flat_reads_as_measured():
    flat = stock_blade_flat("a12x25")
    flat.pop("chord_basis")
    assert blade_from_flat(flat).chord_basis == "measured"


@pytest.mark.parametrize("name", [
    "config/problems/a12x25.yaml",
    "config/problems/a12x25_approx.yaml",
    "config/problems/a12x25_flow_candidate.yaml",
    "config/problems/a12x25_reference_v1.yaml",
    "config/design_space.yaml",
])
def test_legacy_recipes_are_loft(name):
    assert load_blade_params(name).chord_basis == "loft"


def test_stock_recipe_is_measured():
    assert load_blade_params("config/problems/a12x25_reference.yaml").chord_basis == "measured"


def test_basis_from_time():
    assert chord_basis_at(None) == "loft"
    assert chord_basis_at(CHORD_BASIS_CUTOFF - timedelta(seconds=1)) == "loft"
    assert chord_basis_at(CHORD_BASIS_CUTOFF) == "measured"
    # optuna stores naive local times; they are read as local and compared in UTC
    naive_after = (CHORD_BASIS_CUTOFF + timedelta(days=1)).astimezone().replace(tzinfo=None)
    assert chord_basis_at(naive_after) == "measured"


def _trial(params, attrs=None, start=None):
    return SimpleNamespace(params=params, user_attrs=attrs or {}, datetime_start=start)


def test_trial_stamp_wins_over_time():
    old = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert chord_basis_for_trial(_trial({}, {"chord_basis": "measured"}, old)) == "measured"
    assert chord_basis_for_trial(_trial({}, {}, old)) == "loft"


def test_trial_flat_adds_basis_without_overwriting():
    old = datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert trial_flat(_trial({"chord_tip": 30.0}, start=old))["chord_basis"] == "loft"
    assert trial_flat(_trial({"chord_basis": "measured"}, start=old))["chord_basis"] == "measured"


def test_suggest_params_stamps_trial():
    import optuna

    from fansim.optimize.search_space import suggest_params

    study = optuna.create_study(directions=["maximize"] * 3)
    trial = study.ask()
    bp = suggest_params(trial)
    assert trial.user_attrs["chord_basis"] == bp.chord_basis == "measured"
