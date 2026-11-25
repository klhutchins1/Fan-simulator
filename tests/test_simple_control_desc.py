"""#65: Simple-mode geometry tooltips stay plain-language."""

from __future__ import annotations

import re

from fansim.cockpit.fan_copy import CONTROL_DESC, CONTROL_DESC_SIMPLE

# Jargon Simple hover text must not use (Expert CONTROL_DESC may).
_BANNED = re.compile(
    r"\b(camber|stagger|NACA|PCHIP|t/c|chord)\b",
    re.IGNORECASE,
)


def test_simple_control_desc_covers_main_design_keys():
    required = {
        "e_n_blades", "e_stagger_root", "e_stagger_mid", "e_stagger_tip",
        "e_chord_root", "e_chord_mid", "e_chord_tip",
        "e_camber_root", "e_camber_mid", "e_camber_tip", "e_camber_pos",
        "e_section_family", "e_thick_mm", "e_le_face_root", "e_te_face_tip",
    }
    assert required <= CONTROL_DESC_SIMPLE.keys()
    assert required <= CONTROL_DESC.keys()


def test_simple_control_desc_avoids_expert_jargon():
    for key, text in CONTROL_DESC_SIMPLE.items():
        bad = _BANNED.search(text)
        assert bad is None, f"{key} Simple tooltip still says {bad.group()!r}: {text}"


def test_slider_emits_mode_gated_tooltip_divs():
    from pathlib import Path
    src = Path("fansim/cockpit/fan_widgets.py").read_text(encoding="utf-8")
    assert "CONTROL_DESC_SIMPLE" in src
    assert 'v_show="ui_mode === \'simple\'"' in src
    assert 'v_show="ui_mode === \'expert\'"' in src
