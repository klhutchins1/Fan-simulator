"""Tests for live-audited UX fixes (#99, #101, #102, #103, Home CTA, Prop model label)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from trame.app import get_server

from fansim.catalog import CatalogEntry
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.library_view import filter_library_items, library_list_items
from fansim.fan_spec import get_fan_spec

ROOT = Path(__file__).resolve().parents[1]


def _make_ctx(tmp_path, name: str) -> CockpitCtx:
    server = get_server(f"ux_live_{name}_{tmp_path.name}")
    server.controller.figure_update = lambda *a, **k: None
    server.controller.view_update = lambda *a, **k: None
    return CockpitCtx(
        server=server,
        state=server.state,
        ctrl=server.controller,
        run_dir=tmp_path,
        runs_root=tmp_path,
        plotter=MagicMock(),
        busy_bar=lambda *a, **k: None,
        busy_expr=lambda *a, **k: "",
        spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
        study_name=None,
        study_designs=[],
        user_designs=[],
        by_trial={},
        next_id=[9000],
        assess_dir=tmp_path / "cockpit_assess",
    )


def test_issue_99_library_omits_duplicate_run_caption_and_filters():
    spec = get_fan_spec("a12x25")
    fitting_params = {
        "n_blades": 7, "hub_radius": 21.5, "tip_radius": 54.0,
        "stagger_root": 24, "stagger_mid": 31, "stagger_tip": 22,
        "chord_root": 26, "chord_mid": 32, "chord_tip": 26,
        "sweep_mid": 0, "sweep_tip": 0, "max_camber": 0.04, "camber_pos": 0.4,
        "lean_mid": 10, "lean_tip": 20, "le_sweep_mid": 0, "le_sweep_tip": 0,
        "skew_mid": 0, "skew_tip": 0, "winglet_span": 0.85, "winglet_sweep": 0, "winglet_lean": 0,
        "hub_height": 18.0, "hub_profile": "cylinder", "hub_nose": 0,
        "thickness_root": 0.08, "thickness_mid": 0.05, "thickness_tip": 0.03,
    }
    oversize_params = dict(fitting_params, hub_radius=16.5, tip_radius=59.0, n_blades=9)

    e_unlabelled = CatalogEntry(
        design_id="opt_r08b_coarse_t1",
        run="opt_r08b_coarse",
        n_blades=7,
        cfm_free=54.0,
        params=fitting_params,
    )
    e_labelled = CatalogEntry(
        design_id="opt_run1_t2",
        run="opt_run1",
        n_blades=9,
        cfm_free=88.0,
        params=oversize_params,
    )
    items = library_list_items([e_unlabelled, e_labelled], spec)
    groups = [i for i in items if i["role"] == "group"]

    # Unlabelled run must NOT repeat the raw folder slug in caption.
    assert groups[0]["title"] == "opt_r08b_coarse"
    assert groups[0]["caption"] == ""
    # Labelled run keeps its descriptive title and folder caption.
    assert groups[1]["title"] == "First unconstrained 120 mm search"
    assert groups[1]["caption"] == "opt_run1"

    # Search filtering matches by blade count / run / id and prunes empty groups.
    by_blades = filter_library_items(items, query="9 blades")
    assert [i["role"] for i in by_blades] == ["group", "row"]
    assert by_blades[1]["value"] == "opt_run1_t2"

    # Fits-only filter keeps fitting designs and drops oversize ones & empty groups.
    fits_only = filter_library_items(items, fits_only=True)
    row_ids = [i["value"] for i in fits_only if i["role"] == "row"]
    assert "opt_r08b_coarse_t1" in row_ids
    assert "opt_run1_t2" not in row_ids
    assert len([i for i in fits_only if i["role"] == "group"]) == 1


def test_issue_101_idle_cancel_and_stop_buttons_hidden_until_active():
    fan_ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    i_opt = fan_ui.index('"⏹ Cancel opt"')
    opt_block = fan_ui[i_opt : i_opt + 500]
    assert "opt_running" in opt_block and "v_show" in opt_block

    i_ass = fan_ui.index('"⏹ Cancel Assess"')
    ass_block = fan_ui[i_ass : i_ass + 500]
    assert "v_show" in ass_block and "assess_busy" in ass_block

    prop_ui = (ROOT / "fansim" / "cockpit" / "prop_tab.py").read_text(encoding="utf-8")
    i_stop = prop_ui.index('"label": "Stop"')
    stop_block = prop_ui[i_stop : i_stop + 750]
    assert "v_show" in stop_block and "prop_opt_running" in stop_block


def test_issue_102_stale_mesh_banner_on_3d_viewer():
    fan_ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    i_card = fan_ui.index("with v3.VCard(style=VTK_VIEW_STYLE")
    viewer_block = fan_ui[i_card : i_card + 1500]
    assert "edited_stale && !preview_busy" in viewer_block
    assert "3-D view shows previous shape" in viewer_block
    assert "do_preview" in viewer_block


def test_issue_103_fan_results_simple_hint_and_compact_empty_state():
    fan_ui = (ROOT / "fansim" / "cockpit" / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "Higher and farther right means more airflow" in fan_ui
    assert "Go to Design & run Assess" in fan_ui
    assert "fan_subtab = 'design'" in fan_ui
    # Empty 640px Plotly card is hidden in Simple mode when no designs are scored.
    i_plot_card = fan_ui.index('style="height:640px;"')
    card_line = fan_ui[i_plot_card - 80 : i_plot_card + 220]
    assert "n_scored_designs" in card_line or "ui_mode === 'expert'" in card_line


def test_home_accuracy_cta_reflects_open_state_and_prop_dropdown_drops_raw_slug(tmp_path):
    home = (ROOT / "fansim" / "cockpit" / "home_tab.py").read_text(encoding="utf-8")
    assert "Hide accuracy guide" in home

    from fansim.cockpit import fan_runtime
    from fansim.cockpit.prop_tab import setup_prop_tab

    ctx = _make_ctx(tmp_path, "prop_label")
    tasks: list = []
    orig = fan_runtime.asynchronous
    fan_runtime.asynchronous = SimpleNamespace(
        create_task=lambda coro: tasks.append(coro) or MagicMock()
    )
    try:
        setup_prop_tab(ctx)
    finally:
        fan_runtime.asynchronous = orig
        for c in tasks:
            c.close()

    fpv = next(it for it in ctx.state.prop_model_items if it["value"] == "fpv_5inch")
    assert "(fpv_5inch)" not in fpv["title"]
    assert "5" in fpv["title"]


def test_slider_value_formatter_strips_float_noise():
    from fansim.cockpit.fan_widgets import _fmt_value_expr

    assert "toFixed(1)" in _fmt_value_expr("e_n_blades", 1)
    assert "toFixed(2)" in _fmt_value_expr("e_chord_root", 0.5)
    assert "toFixed(3)" in _fmt_value_expr("e_camber", 0.01)
    assert "toFixed(4)" in _fmt_value_expr("e_thick", 0.005)

