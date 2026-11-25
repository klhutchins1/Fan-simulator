"""Review fixes on PR #43 (Claude review, 2026-11-24)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "fansim" / "cockpit" / "fan_tab_ui.py"
TRIALS = ROOT / "fansim" / "cockpit" / "fan_trials.py"
VIZ = ROOT / "fansim" / "cockpit" / "fan_viz.py"


def _about_text() -> str:
    src = UI.read_text(encoding="utf-8")
    start = src.index('"About Fan Simulator"')
    return src[start:src.index('"Close"', start)]


def test_about_does_not_claim_more_validation_than_the_rulings():
    """lt120 is TRENDS (2026-10-30 release text); QA-64 says 'within 8 %' overstates it."""
    about = _about_text()
    assert "Validated: axial Fan CFD method vs published fans" not in about
    assert "lt120" in about and "25 %" in about           # the loaded over-prediction is stated
    assert "8 %" not in about and "within 10" not in about  # no number until QA-64 is ruled


def test_simple_export_caption_only_names_switches_simple_can_see():
    src = UI.read_text(encoding="utf-8")
    m = re.search(r'"Fit hub / tip = shrink[^)]*?v_show="ui_mode === \'simple\'"', src, re.DOTALL)
    assert m, "Simple print/export caption not found"
    assert "Mirror" not in m.group(0)
    assert "Motor cup in Preview" not in m.group(0)


def test_memory_note_shows_in_simple_when_the_cup_cannot_be_built():
    src = UI.read_text(encoding="utf-8")
    i = src.index('"{{ memory_tier_note }}"')
    block = src[i:i + 300]
    assert "ui_mode === 'expert' || !cup_build_ok" in block


def test_assess_restore_notice_is_plain_in_simple():
    src = TRIALS.read_text(encoding="utf-8")
    i = src.index("Assess settings restored")
    block = src[i - 400:i + 600]
    assert "ui_mode" in block                              # the jargon line is Expert-only
    assert "Assess settings restored from this design's saved run." in src


def test_spacing_tone_line_is_labelled_an_unvalidated_estimate():
    src = VIZ.read_text(encoding="utf-8")
    i = src.index("Uneven spacing")
    line = src[i:i + 300]
    assert "not validated" in line
    assert "free of any flow cost" not in line
