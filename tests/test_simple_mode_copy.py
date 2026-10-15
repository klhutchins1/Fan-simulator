"""24.2: Results + Design help copy is Expert-only so Simple keeps the plot above the fold."""

from __future__ import annotations

from pathlib import Path

from fansim.cockpit.fan_core import tab_for_ui_mode

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "fansim" / "cockpit" / "fan_tab_ui.py"
APP = ROOT / "fansim" / "cockpit" / "app.py"


def _gate_offset(needle: str, mode: str = "expert", *, src: str | None = None) -> int:
    """Chars from *needle* to the Simple/Expert gate on the same widget."""
    text = src if src is not None else UI.read_text(encoding="utf-8")
    i = text.find(needle)
    assert i >= 0, needle
    token = f"ui_mode === '{mode}'"
    j = text.find(token, i)
    assert j >= 0, f"no {mode} gate after {needle!r}"
    return j - i


def test_results_glossary_is_expert_only():
    assert _gate_offset("Glossary — CFM") < 2000


def test_gold_x_blurb_is_expert_only():
    assert _gate_offset("Gold ✕ = datasheet") < 2000


def test_fits_only_blurb_is_expert_only():
    assert _gate_offset("Hide scatter points whose built tip") < 2000


def test_scatter_how_to_read_is_expert_only():
    assert _gate_offset("CFM scatter — up and right is better") < 2000


def test_design_chord_blurb_is_expert_only():
    assert _gate_offset("Chord = LE→TE blade width") < 2000


def test_design_naca_blurb_is_expert_only():
    assert _gate_offset("NACA = cambered airfoil") < 2000


def test_design_camber_blurb_is_expert_only():
    assert _gate_offset("Camber = the scoop in the blade face") < 2000


def test_design_wall_blurb_is_expert_only():
    assert _gate_offset("Wall = the thin dimension through the blade") < 2000


def test_design_le_te_blurb_is_expert_only():
    assert _gate_offset("NACA: LE/TE scales reshape") < 2000


def test_design_notch_blurb_is_expert_only():
    assert _gate_offset("Three boxy / skewed-rectangle bites") < 2000


def test_design_shroud_blurb_is_expert_only():
    assert _gate_offset("0 thickness = off. First thickness step") < 2000


def test_design_blade_on_hub_blurb_is_expert_only():
    assert _gate_offset("Blade on hub: + raises blades") < 2000


def test_design_banner_is_simple_only():
    """Cold-open Design is dominated by this banner; Expert must not show it."""
    assert _gate_offset("Design 3D-printable replacement blades", "simple") < 2000


def test_start_here_line_is_simple_only():
    assert _gate_offset("Start here: 1) Pick a design", "simple") < 2000


def test_start_here_does_not_repeat_button_timings():
    """Banner + button labels keep durations; the step list only names the steps."""
    src = UI.read_text(encoding="utf-8")
    i = src.find("Start here: 1) Pick a design")
    assert i >= 0
    window = src[i : i + 220]
    assert "(sec)" not in window
    assert "15–30" not in window
    assert "hours" not in window


def test_empty_scatter_does_not_also_show_the_flow_card():
    src = UI.read_text(encoding="utf-8")
    i = src.find("How the air moves")
    assert i >= 0
    window = src[max(0, i - 400) : i + 80]
    assert "trial_items.length >= 2" in window


def test_actions_hose_chip_is_expert_only():
    assert _gate_offset("change under Assess & print below") < 2000


def test_print_export_blurb_is_expert_only():
    assert _gate_offset("Export STL writes a print-ready file") < 2000


def test_assess_printability_blurb_is_expert_only():
    assert _gate_offset("Assess checks printability") < 2000


def test_assess_hose_blurb_is_expert_only():
    assert _gate_offset("Case ≈ open airflow") < 2000


def test_assess_material_blurb_is_expert_only():
    assert _gate_offset("Pick PLA+ here before Optimize") < 2000


def test_assess_honesty_blurb_is_expert_only():
    assert _gate_offset("Also applied when you press Optimize") < 2000


def test_optimize_panel_is_expert_only():
    assert _gate_offset("Optimize (hours · many CFD trials)") < 400


def test_proxy_tabs_are_expert_only():
    src = APP.read_text(encoding="utf-8")
    for needle in ('"Mixed · estimate"', '"Volute · estimate"', '"CROR · estimate"'):
        assert _gate_offset(needle, src=src) < 400


def test_tab_labels_do_not_say_proxy_or_bemt():
    src = APP.read_text(encoding="utf-8")
    assert "Mixed · proxy" not in src
    assert "Volute · proxy" not in src
    assert "CROR · proxy" not in src
    assert "Prop · BEMT" not in src
    assert "Prop · fast estimate" in src


def test_simple_tab_strip_says_what_fan_and_prop_are():
    assert _gate_offset(
        "Fan: printable PC-fan blades (CFD). Prop: propeller (fast estimate).",
        "simple",
        src=APP.read_text(encoding="utf-8"),
    ) < 400


def test_prop_simple_banner_skips_bemt_and_audit():
    src = (ROOT / "fansim" / "cockpit" / "prop_tab.py").read_text(encoding="utf-8")
    needle = "Propeller tab — a fast estimate (~1 s), not the full Fan CFD."
    assert _gate_offset(needle, "simple", src=src) < 600
    i = src.find(needle)
    window = src[i : i + 280]
    assert "BEMT" not in window
    assert "Audit" not in window


def test_simple_mode_leaves_proxy_tabs():
    assert tab_for_ui_mode("simple", "mixed") == "fan"
    assert tab_for_ui_mode("simple", "volute") == "fan"
    assert tab_for_ui_mode("simple", "cror") == "fan"
    assert tab_for_ui_mode("simple", "fan") == "fan"
    assert tab_for_ui_mode("simple", "propeller") == "propeller"
    assert tab_for_ui_mode("expert", "mixed") == "mixed"
