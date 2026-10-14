"""24.2 first slice: Results help copy is Expert-only so Simple keeps the plot above the fold."""

from __future__ import annotations

from pathlib import Path

UI = Path(__file__).resolve().parents[1] / "fansim" / "cockpit" / "fan_tab_ui.py"


def _gate_offset(needle: str) -> int:
    """Chars from *needle* to the Simple/Expert gate on the same html.Div."""
    src = UI.read_text(encoding="utf-8")
    i = src.find(needle)
    assert i >= 0, needle
    j = src.find("ui_mode === 'expert'", i)
    assert j >= 0, f"no expert gate after {needle!r}"
    return j - i


def test_results_glossary_is_expert_only():
    assert _gate_offset("Glossary — CFM") < 2000


def test_gold_x_blurb_is_expert_only():
    assert _gate_offset("Gold ✕ = datasheet") < 2000


def test_fits_only_blurb_is_expert_only():
    assert _gate_offset("Hide scatter points whose built tip") < 2000


def test_scatter_how_to_read_is_expert_only():
    assert _gate_offset("CFM scatter — up and right is better") < 2000
