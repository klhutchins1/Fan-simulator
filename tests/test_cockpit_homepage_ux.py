"""Unit tests for the cockpit Home page, tooltips/units/SVG diagrams, and UX fixes.

Tests drive cockpit state and pure helpers rather than grepping source text.
"""

from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from trame.app import get_server

from fansim.cockpit.context import CockpitCtx


def _make_ctx(tmp_path, name: str) -> CockpitCtx:
    server = get_server(f"ux_home_{name}_{tmp_path.name}")
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


def test_home_tab_routing_and_state(tmp_path):
    from fansim.cockpit.fan_core import tab_for_ui_mode
    from fansim.cockpit.home_tab import HOME_TAB, setup_home_tab

    assert HOME_TAB == "home"
    assert tab_for_ui_mode("simple", "home") == "home"
    assert tab_for_ui_mode("expert", "home") == "home"

    ctx = _make_ctx(tmp_path, "routing")
    ctx.state.active_tab = HOME_TAB
    ctx.state.fan_subtab = "design"
    ctx.state.prop_subtab = "design"
    ctx.state.n_scored_designs = 0

    setup_home_tab(ctx)

    # State carries structured plain-language content (not hardcoded only in template).
    assert ctx.state.home_tagline
    assert len(ctx.state.home_choices) == 4
    assert len(ctx.state.home_steps) >= 3
    assert len(ctx.state.home_validated_items) >= 2
    assert len(ctx.state.home_experimental_items) >= 2
    assert ctx.state.home_accuracy_open is False

    # Honesty invariant: never put a pass mark in experimental / not-validated lines.
    for item in ctx.state.home_experimental_items:
        text = f"{item['title']} {item['detail']}"
        assert "✓" not in text

    # Choice 1: Design a PC fan -> Fan / Design
    ctx.home_go_fan()
    assert ctx.state.active_tab == "fan"
    assert ctx.state.fan_subtab == "design"

    # Choice 2: Design a propeller -> Propeller / Design
    ctx.home_go_prop()
    assert ctx.state.active_tab == "propeller"
    assert ctx.state.prop_subtab == "design"

    # Choice 3: Open a saved design -> Library when 0 scored designs, Results when >= 1
    ctx.state.n_scored_designs = 0
    ctx.home_go_saved()
    assert ctx.state.active_tab == "fan"
    assert ctx.state.fan_subtab == "library"

    ctx.state.n_scored_designs = 3
    ctx.home_go_saved()
    assert ctx.state.active_tab == "fan"
    assert ctx.state.fan_subtab == "results"

    # Choice 4: How accuracy is checked -> toggles accuracy detail panel on Home
    ctx.state.active_tab = HOME_TAB
    ctx.home_toggle_accuracy()
    assert ctx.state.home_accuracy_open is True
    ctx.home_toggle_accuracy()
    assert ctx.state.home_accuracy_open is False


def test_explanatory_svg_diagrams_are_valid():
    from fansim.cockpit.diagrams import DIAGRAM_KEYS, diagram_data_uri

    expected = {"blade_pitch", "blade_sweep", "hub_ratio", "static_pressure", "blade_scoop"}
    assert expected.issubset(set(DIAGRAM_KEYS))

    for key in expected:
        uri = diagram_data_uri(key)
        assert uri.startswith("data:image/svg+xml;base64,"), key
        svg = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
        assert svg.lstrip().startswith("<svg"), key
        assert "</svg>" in svg, key


def test_tooltips_resolved_for_all_tabs():
    from fansim.cockpit.fan_widgets import resolve_tooltip

    # Fan controls (existing + newly added selects/diagrams)
    s_simple, s_expert, s_uri = resolve_tooltip("assess_preset")
    assert s_simple and "pressure" in s_simple.lower() or "resistance" in s_simple.lower()
    assert s_expert
    assert s_uri and s_uri.startswith("data:image/svg+xml;base64,")

    m_simple, m_expert, _ = resolve_tooltip("assess_material")
    assert m_simple and m_expert

    h_simple, h_expert, _ = resolve_tooltip("e_hub_profile")
    assert h_simple and h_expert

    # Prop controls (previously missing tooltips!)
    p_simple, p_expert, p_uri = resolve_tooltip("p_pitch")
    assert p_simple and "pitch" in p_simple.lower()
    assert p_expert and "pitch" in p_expert.lower()
    assert p_uri and p_uri.startswith("data:image/svg+xml;base64,")

    for key in ("p_n_blades", "p_chord_mid", "p_sweep_tip", "p_thickness_mid", "p_tip_round"):
        simp, exp, _ = resolve_tooltip(key)
        assert simp, f"missing simple tooltip for {key}"
        assert exp, f"missing expert tooltip for {key}"

    # Mixed / Volute / CROR controls (previously missing tooltips!)
    for key in (
        "mf_n_blades", "mf_r_eye", "mf_stagger", "mf_chord_root", "mf_stagger_tip",
        "volute_n_blades", "volute_r_hub", "volute_spiral", "volute_tongue_angle",
        "cror_hub_r", "cror_tip_r", "cror_gap", "cror_f_n", "cror_f_stagger",
        "cror_f_sweep_tip", "cror_r_camber_mid",
    ):
        simp, exp, _ = resolve_tooltip(key)
        assert exp, f"missing tooltip for {key}"


def test_friendly_model_items_and_plain_simple_readouts(tmp_path):
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab
    from fansim.cockpit.prop_tab import setup_prop_tab

    ctx = _make_ctx(tmp_path, "models")
    tasks: list = []
    orig = fan_runtime.asynchronous
    fan_runtime.asynchronous = SimpleNamespace(
        create_task=lambda coro: tasks.append(coro) or MagicMock()
    )
    try:
        fan_tab.setup_fan_tab(ctx)
        setup_prop_tab(ctx)
    finally:
        fan_runtime.asynchronous = orig
        for c in tasks:
            c.close()

    # Friendly fan model items preserve value key while showing human title.
    fan_items = ctx.state.fan_model_items
    assert isinstance(fan_items, list) and fan_items
    a12 = next(it for it in fan_items if it["value"] == "a12x25")
    assert "Noctua" in a12["title"]

    # Simple model summary avoids raw electrical/bracket jargon.
    assert ctx.state.model_info_simple
    assert "V×" not in ctx.state.model_info_simple
    assert "built-in ref" not in ctx.state.model_info_simple
    assert "Noctua" in ctx.state.model_info_simple

    # Friendly prop model items + friendly prop mission titles (no raw snake_case).
    prop_items = ctx.state.prop_model_items
    fpv = next(it for it in prop_items if it["value"] == "fpv_5inch")
    assert "fpv_5inch" != fpv["title"]

    mission_titles = [it["title"] for it in ctx.state.prop_mission_items]
    for title in mission_titles:
        assert "_" not in title, f"raw snake_case mission title: {title}"


def test_library_missing_design_has_no_rebuild_dead_end(tmp_path):
    """Leftover #27: missing catalog design must not tell user to 'rebuild' with no UI button."""
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab

    ctx = _make_ctx(tmp_path, "lib27")
    tasks: list = []
    orig = fan_runtime.asynchronous
    fan_runtime.asynchronous = SimpleNamespace(
        create_task=lambda coro: tasks.append(coro) or MagicMock()
    )
    try:
        fan_tab.setup_fan_tab(ctx)
        ctx.fan_select_library_design("nonexistent_design_xyz")
    finally:
        fan_runtime.asynchronous = orig
        for c in tasks:
            c.close()

    assert "rebuild" not in (ctx.state.preview_msg or "").lower()
    assert "rebuild" not in (ctx.state.library_msg or "").lower()
