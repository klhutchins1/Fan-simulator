"""UX round 2 (#22–#35-ish): About dialog, Prop Simple gates, plain readiness copy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAN_UI = ROOT / "fansim" / "cockpit" / "fan_tab_ui.py"
PROP = ROOT / "fansim" / "cockpit" / "prop_tab.py"
RUNNER = ROOT / "fansim" / "cfd" / "runner.py"
TRIALS = ROOT / "fansim" / "cockpit" / "fan_trials.py"
VIZ = ROOT / "fansim" / "cockpit" / "fan_viz.py"
BLADE = ROOT / "fansim" / "cockpit" / "blade_editor.py"


def test_about_opens_dialog_not_only_simple_banner():
    src = FAN_UI.read_text(encoding="utf-8")
    assert "fan_about_dialog" in src
    assert "About Fan Simulator" in src
    i = src.find("def show_fan_about")
    assert i >= 0
    window = src[i : i + 280]
    assert "fan_about_dialog = True" in window


def test_prop_optimize_randomize_ctcp_are_expert_only():
    src = PROP.read_text(encoding="utf-8")
    for needle in (
        '"label": "Optimize (BEMT)"',
        '"label": "Randomize"',
        '"label": "Export CT/CP (PyThrust)"',
    ):
        i = src.find(needle)
        assert i >= 0, needle
        # v_show sits after click/loading/disabled; CT/CP's disabled tuple is long.
        assert "ui_mode === 'expert'" in src[i : i + 900]


def test_prop_mission_chip_and_optimize_panel_are_expert_only():
    src = PROP.read_text(encoding="utf-8")
    i = src.find("mission — change under Optimize below")
    assert i >= 0
    # v_show is on the next kwargs after the caption string.
    assert "ui_mode === 'expert'" in src[i : i + 200]
    assert 'title="Optimize & CFD refine"' in src
    j = src.find('title="Optimize & CFD refine"')
    assert "ui_mode === 'expert'" in src[j : j + 200]


def test_prop_simple_start_here_skips_optimize():
    src = PROP.read_text(encoding="utf-8")
    i = src.find('v_show="ui_mode === \'simple\'"')
    # Find the Simple start-here line
    assert "pick size → tune blade → Analyze" in src
    s = src.find("pick size → tune blade → Analyze (~1 s) → Export STL.")
    assert s >= 0
    window = src[s : s + 200]
    assert "Optimize" not in window
    assert "CFD refine" not in window


def test_airflow_check_ready_line():
    src = RUNNER.read_text(encoding="utf-8")
    assert "Airflow check ready. You can press Assess." in src
    assert 'CFD ready. You can press Assess.' not in src


def test_stock_gold_jargon_is_expert_only_in_source():
    src = TRIALS.read_text(encoding="utf-8")
    assert "Gold = parametric Stock" in src
    assert 'ui_mode or "simple") == "expert"' in src or "ui_mode or 'simple') == 'expert'" in src


def test_preview_simple_hides_camber_difficulty_path():
    src = VIZ.read_text(encoding="utf-8")
    assert "hide camber / Difficulty" in src or "Difficulty N/100" in src
    assert 'Preview: {params.n_blades} blades' in src


def test_prop_shape_panel_plain_titles():
    src = PROP.read_text(encoding="utf-8")
    assert 'title_thick="Wall & scoop"' in src
    blade = BLADE.read_text(encoding="utf-8")
    assert 'slider("Scoop root"' in blade


def test_optimize_discloses_ignores_design_sliders():
    src = FAN_UI.read_text(encoding="utf-8")
    assert "Does not start from your current Design sliders" in src


def test_library_expert_panels_gated():
    src = FAN_UI.read_text(encoding="utf-8")
    assert "fan_subtab === 'library' && ui_mode === 'expert'" in src


def test_prop_export_items_include_href():
    src = PROP.read_text(encoding="utf-8")
    assert '"href":' in src or "'href':" in src
    assert "fansim_exports/" in src


def test_prop_results_empty_caption():
    src = PROP.read_text(encoding="utf-8")
    assert "No scored props yet" in src


def test_assess_button_uses_30_40_min():
    src = FAN_UI.read_text(encoding="utf-8")
    assert '"Assess (~30–40 min)"' in src
    assert '"Assess (~15–30 min)"' not in src
    assert "CFD (~30–40 min)" in src


def test_boost_nn_disabled_without_catalog_gp():
    src = FAN_UI.read_text(encoding="utf-8")
    for model in ('"opt_gp_boost"', '"opt_gp_nn"'):
        i = src.find(model)
        assert i >= 0, model
        assert 'disabled=("!opt_gp",)' in src[i : i + 220]
    assert "Boost / NN mean need Catalog GP skip on" in src
