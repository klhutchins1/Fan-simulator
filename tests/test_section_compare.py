"""Known-answer tests for the blade-section measurement (synthetic rotors, no CFD)."""

from __future__ import annotations

import pytest

from fansim.audit.synthetic import cambered_blade_fan
from fansim.validation.section_compare import measure_sections


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    def make(**kw):
        p = tmp_path_factory.mktemp("sc") / "fan.stl"
        cambered_blade_fan(**kw).export(str(p))
        return p
    return make


@pytest.mark.parametrize("stagger,camber", [(60.0, 0.06), (35.0, 0.10)])
def test_known_answer(synth, stagger, camber):
    chord, thick, n = 20.0, 1.0, 5
    rows = measure_sections(synth(n_blades=n, chord=chord, stagger_deg=stagger, camber=camber,
                                  thick=thick), radii_frac=(0.6, 0.8))
    assert len(rows) == 2
    for r in rows:
        assert r["n_blades"] == n
        assert r["chord_mm"] == pytest.approx(chord, rel=0.03)
        assert abs(r["stagger_deg"] - stagger) < 1.5
        assert abs(r["camber_ratio"] - camber) < 0.01
        assert r["max_thickness_mm"] == pytest.approx(thick, rel=0.10)
        assert r["thickness_ratio"] == pytest.approx(thick / chord, rel=0.10)
        assert r["camber_pos"] == pytest.approx(0.5, abs=0.1)
