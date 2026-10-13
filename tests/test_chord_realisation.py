"""§19.7: station chord is the measured cylinder-cut target under cylindrical_tip."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fansim.geometry.chord_realisation import (
    loft_chords_for_measured_targets,
    measure_station_chords,
    with_loft_chords,
)
from fansim.geometry.config import load_blade_params


@pytest.fixture(scope="module")
def stock():
    return load_blade_params("config/problems/a12x25_reference.yaml")


def test_cylindrical_tip_realizes_tip_chord_within_5pct(stock):
    """Builder realizes station tip chord as measured chord within 5%."""
    tip_target = float(stock.stations[-1].chord)
    assert tip_target < 40.0  # honest measured tip, not the old loft inflation
    loft = loft_chords_for_measured_targets(stock, n_iter=2)
    trial = with_loft_chords(stock, loft)
    built = measure_station_chords(trial)
    tip_built = built[-1]
    assert tip_built is not None
    assert tip_built == pytest.approx(tip_target, rel=0.05)
    # Planar sections lose tip chord to the trim and need a longer loft; wrapped ones (27.4) don't.
    planar = replace(stock, section_wrap="planar")
    assert loft_chords_for_measured_targets(planar, n_iter=2)[-1] > tip_target * 1.1
    assert loft[-1] == pytest.approx(tip_target, rel=0.05)


def test_no_compensation_when_cylindrical_tip_off(stock):
    p = replace(stock, cylindrical_tip=False)
    loft = loft_chords_for_measured_targets(p, n_iter=1)
    assert loft == [float(s.chord) for s in p.stations]


def test_tip_wall_preserved_through_loft_scale(stock):
    """Absolute tip wall (t/c × measured chord) is unchanged after loft preparation."""
    tip = stock.stations[-1]
    wall0 = float(tip.thickness) * float(tip.chord)
    loft = loft_chords_for_measured_targets(stock, n_iter=2)
    prep = with_loft_chords(stock, loft)
    tip_loft = prep.stations[-1]
    wall1 = float(tip_loft.thickness) * float(tip_loft.chord)
    assert wall1 == pytest.approx(wall0, rel=1e-6)
    assert wall0 == pytest.approx(2.44, abs=0.05)
