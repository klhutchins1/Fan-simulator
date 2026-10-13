"""fit_recipe_to_stl keeps every recipe setting, including those after the station list (2026-10-13)."""
from __future__ import annotations

from pathlib import Path

from scripts.fit_recipe_to_stl import recipe_settings

ROOT = Path(__file__).resolve().parents[1]


def test_settings_after_the_stations_are_kept():
    text = (ROOT / "config/problems/a12x25_reference_planar.yaml").read_text()
    out = recipe_settings(text, "cylinder")
    assert "le_thick_scale: 0.2" in out and "te_thick_scale: 0.2" in out
    assert "section_family: plate" in out
    assert out[-1] == "section_wrap: cylinder"
    assert not any(ln.lstrip().startswith("- ") or ln.strip() == "stations:" for ln in out)
