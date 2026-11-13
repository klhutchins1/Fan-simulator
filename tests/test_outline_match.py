"""The outline match applies the pre-registered leading-edge step. No mesh build."""
import dataclasses
from pathlib import Path

import pytest

from fansim.geometry.config import load_blade_params
from scripts.outline_match import LE_DELTA, _candidate

ROOT = Path(__file__).resolve().parents[1]


def test_full_step_uses_the_logged_residuals_and_extrapolates_the_root():
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    got = _candidate(v3, 1.0)
    assert got.stations[1].sweep == pytest.approx(v3.stations[1].sweep - LE_DELTA[0][0])
    assert got.stations[1].skew == pytest.approx(v3.stations[1].skew - LE_DELTA[0][1])
    assert got.stations[1].stagger_deg == pytest.approx(v3.stations[1].stagger_deg)
    # r_frac 0 from the moved stations at 0.2214 and 0.3771.
    assert got.stations[0].stagger_deg == pytest.approx(43.949, abs=0.01)
    assert got.stations[0].chord == pytest.approx(v3.stations[0].chord)


def test_half_step_is_half_the_logged_residual():
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    full = _candidate(v3, 1.0)
    half = _candidate(v3, 0.5)
    assert half.stations[6].skew == pytest.approx(
        v3.stations[6].skew - 0.5 * LE_DELTA[5][1])
    # Stagger is not part of the leading-edge step, so the extrapolated root angle matches.
    # Sweep does move, and the half step lands between the unmoved extrapolation and the full one.
    assert half.stations[0].stagger_deg == pytest.approx(full.stations[0].stagger_deg)
    assert half.stations[0].sweep == pytest.approx(-2.874, abs=0.01)
    assert dataclasses.asdict(half.stations[3])["chord"] == dataclasses.asdict(
        v3.stations[3])["chord"]
