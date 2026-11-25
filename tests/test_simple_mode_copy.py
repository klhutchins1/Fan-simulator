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
    src = UI.read_text(encoding="utf-8")
    i = src.find("Start here:")
    assert i >= 0
    assert _gate_offset("Start here:", "simple") < 2000


def test_start_here_does_not_repeat_button_timings():
    """Banner + button labels keep durations; the step list only names the steps."""
    src = UI.read_text(encoding="utf-8")
    i = src.find("Start here:")
    assert i >= 0
    window = src[i : i + 280]
    assert "(sec)" not in window
    assert "15–30" not in window
    assert "hours" not in window


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
    # Blurb lives inside the Expert Assess Div (gate is above, not on the Div itself).
    src = UI.read_text(encoding="utf-8")
    i = src.find("Also applied when you press Optimize")
    assert i >= 0
    assert "ui_mode === 'expert'" in src[max(0, i - 2000) : i + 40]


def test_optimize_panel_is_expert_only():
    assert _gate_offset("Optimize (hours · many CFD trials)") < 400


def test_proxy_tabs_are_expert_only():
    src = APP.read_text(encoding="utf-8")
    for needle in ('"Mixed · experimental"', '"Volute · estimate"', '"CROR · estimate"'):
        assert _gate_offset(needle, src=src) < 400


def test_tab_labels_do_not_say_proxy_or_bemt():
    src = APP.read_text(encoding="utf-8")
    assert "Mixed · proxy" not in src
    assert "Volute · proxy" not in src
    assert "CROR · proxy" not in src
    assert "Prop · BEMT" not in src
    assert "Prop · fast estimate" in src


def test_simple_tab_strip_says_what_fan_and_prop_are():
    src = APP.read_text(encoding="utf-8")
    # Prefer plain language; do not lead Simple with an unexplained CFD acronym.
    needle = next(
        s for s in (
            "Fan: printable PC-fan blades. Prop: propeller (fast estimate).",
            "Fan: printable PC-fan blades (airflow check). Prop: propeller (fast estimate).",
        )
        if s in src
    )
    assert _gate_offset(needle, "simple", src=src) < 400


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

def test_optimize_action_button_is_expert_only():
    """#1: Optimize settings were Expert-only; the green action button was not."""
    src = UI.read_text(encoding="utf-8")
    i = src.find('"label": "Optimize (hours)"')
    assert i >= 0
    window = src[i : i + 700]
    assert "ui_mode === 'expert'" in window


def test_randomize_action_button_is_expert_only():
    src = UI.read_text(encoding="utf-8")
    i = src.find('"label": "Randomize geometry"')
    assert i >= 0
    window = src[i : i + 500]
    assert "ui_mode === 'expert'" in window


def test_features_and_fit_seed_panels_are_expert_only():
    assert _gate_offset("Features (bio-inspired)") < 400
    assert _gate_offset("Fit & seed") < 400


def test_assess_bem_honesty_sweep_are_expert_only():
    """#2: Assess jargon controls must not appear in Simple.

    BEM / Honesty / Sweep sit inside one Expert ``html.Div``, so the gate is
    just *before* the BEM button (not after, like `_gate_offset` expects).
    """
    src = UI.read_text(encoding="utf-8")
    i = src.find("Score multi-point BEM (ranking only)")
    assert i >= 0
    assert "ui_mode === 'expert'" in src[max(0, i - 250) : i + 80]
    j = src.find("Honesty / fidelity")
    assert j >= 0
    assert "ui_mode === 'expert'" in src[max(0, j - 2000) : j + 40]
    k = src.find('label="Sweep"')
    assert k >= 0
    assert "ui_mode === 'expert'" in src[max(0, k - 2500) : k + 80]


def test_empty_scatter_uses_scored_count_not_dropdown_length():
    """#3: Reference+Outline must not hide the empty Results caption."""
    src = UI.read_text(encoding="utf-8")
    i = src.find("No scored designs yet")
    assert i >= 0
    window = src[i : i + 450]
    assert "n_scored_designs" in window
    assert "trial_items.length < 2" not in window
    j = src.find("How the air moves")
    assert j >= 0
    flow_window = src[max(0, j - 350) : j + 40]
    assert "n_scored_designs" in flow_window


def test_start_here_assumes_stock_loaded():
    """#8: cold-open already loads Stock — do not say Pick a design first."""
    src = UI.read_text(encoding="utf-8")
    assert "Start here: 1) Pick a design" not in src
    assert "Stock loaded" in src or "stock loaded" in src.lower()
    assert _gate_offset("Stock loaded", "simple") < 2000 or _gate_offset(
        "Start here:", "simple"
    ) < 2000


def test_print_material_label_is_plain():
    """#7: stress/flutter caveats belong in Expert help, not the label."""
    src = UI.read_text(encoding="utf-8")
    assert 'label="Print material"' in src
    assert "stress gate; vibration is estimate" not in src


def test_simple_fan_tab_avoids_bare_cfd_acronym():
    """#10: Simple-facing Fan tab should not lead with unexplained CFD."""
    src = APP.read_text(encoding="utf-8")
    # Tab label itself
    assert "Fan · CFD" not in src or "Fan · blades" in src or "Fan · printable" in src
    # Prefer plain tab present
    assert "Fan · blades" in src or "Fan · printable blades" in src


def test_load_stock_button_exists():
    """#9: Design Actions exposes Load Stock / Reference."""
    src = UI.read_text(encoding="utf-8")
    assert "Load Stock" in src or "Load stock" in src
    assert "load_stock_reference" in src or "fan_load_stock_reference" in src


def test_screening_honesty_near_assess():
    """#6: Assess action area mentions screening / rank-not-absolute."""
    src = UI.read_text(encoding="utf-8")
    assert "screening" in src.lower() or "rank designs" in src.lower() or "not absolute" in src.lower()
    # Expert-visible near Assess
    low = src.lower()
    assert "gci" in low or "rank designs" in low or "compare designs, not absolute" in low


def test_geometry_panel_titles_plain_for_simple():
    """#5: panel titles avoid stagger/camber jargon as the primary name."""
    src = UI.read_text(encoding="utf-8")
    assert 'title="Pitch / twist — stagger"' not in src
    assert 'title="Airfoil — camber & thickness"' not in src
    assert "Blade angle" in src or "blade angle" in src.lower()
    assert "Scoop" in src or "scoop" in src


def test_library_info_empty_is_plain():
    from fansim.cockpit.library_view import empty_library_info, HINT_BIG
    assert "Fits this hub" not in empty_library_info(0)
    assert "Scale" in empty_library_info(3) or "click" in empty_library_info(3).lower()
    assert "Fits it" not in HINT_BIG
