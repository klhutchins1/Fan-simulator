"""Hub-wall step keeps the blade radii of the outline candidate. No mesh build."""
from pathlib import Path

import pytest

from fansim.geometry.config import load_blade_params
from scripts.outline_hub import with_hub
from scripts.outline_match import _candidate

ROOT = Path(__file__).resolve().parents[1]


def test_hub_wall_does_not_move_the_blade_sections():
    v3 = load_blade_params(ROOT / "config/problems/a12x25_reference.yaml")
    base = _candidate(v3, 1.0)
    got = with_hub(base, 26.0, 6.5)
    assert got.hub_radius == 26.0
    assert got.root_embed == 6.5
    assert got.hub_radius - got.root_embed == pytest.approx(base.hub_radius - base.root_embed)
    assert got.stations[1].sweep == pytest.approx(base.stations[1].sweep)
    assert got.stations[0].stagger_deg == pytest.approx(base.stations[0].stagger_deg)
