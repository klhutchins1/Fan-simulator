"""Headless "we say X, we do Y" checks (adopted from QA r12 Task E, roadmap 29.1 / 29.2).

No CFD, no 3-D, no real fuse: worker boundaries are stubbed by name, as in
tests/test_fan_tab_setup_smoke.py. Seeded from r12 Task D (PLA+ picker): on 143d5a8 the two material tests FAIL
by design; that is the finding, not a test bug.

R3.7: one check per tab that ships. A control whose label promises an action is bound to the
handler that performs it, and copy that says a number is not validated does not carry a pass mark.
Those handlers are not called, so no solver runs.
"""
from __future__ import annotations

import ast
import asyncio
import inspect
import json
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("pytest", sys.modules[__name__])
trame = pytest.importorskip("trame.app")


class _T(dict):
    def __bool__(self):
        return True


@pytest.fixture
def ui(tmp_path, monkeypatch):
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab
    from fansim.cockpit.context import CockpitCtx

    tasks: list = []
    monkeypatch.setattr(fan_runtime, "asynchronous",
                        SimpleNamespace(create_task=lambda c: tasks.append(c) or MagicMock()), raising=False)
    sessions: list = []

    class Cap(fan_tab.FanSession):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            sessions.append(self)

    monkeypatch.setattr(fan_tab, "FanSession", Cap)
    server = trame.get_server(f"qa12e_{tmp_path.name}")
    server.controller.figure_update = lambda *a, **k: None
    server.controller.view_update = lambda *a, **k: None
    ctx = CockpitCtx(server=server, state=server.state, ctrl=server.controller, run_dir=tmp_path,
                     runs_root=tmp_path.parent, plotter=MagicMock(), busy_bar=lambda *a, **k: None,
                     busy_expr=lambda *a, **k: "", spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
                     study_name=None, study_designs=[], user_designs=[], by_trial=_T(), next_id=[9000],
                     assess_dir=tmp_path / "cockpit_assess")
    fan_tab.setup_fan_tab(ctx)
    for c in tasks:
        c.close()
    tasks.clear()
    return SimpleNamespace(ctx=ctx, st=ctx.state, s=sessions[0], tasks=tasks)


def _drive(tasks):
    loop = asyncio.new_event_loop()
    try:
        while tasks:
            loop.run_until_complete(tasks.pop(0))
    finally:
        loop.close()


def _export_payload(ui, monkeypatch, tmp_path):
    """Press Export with the isolated worker stubbed; return (payload, export_msg)."""
    import fansim.cockpit.fan_export as fe
    import fansim.isolated_job as ij
    from fansim.manufacturability import print_id as pid_mod

    monkeypatch.setattr(pid_mod, "INDEX_PATH", tmp_path / "index.jsonl")
    monkeypatch.setattr(fe, "exports_dir", lambda: tmp_path / "exports")
    got: dict = {}

    def fake(mod, payload, **kw):
        got.update(payload)
        Path(payload["result"]).write_text(json.dumps({"ok": True, "mount_fits": None, "mount_msg": "",
                                                       "mirror_note": "", "gauge": None,
                                                       "print_id": payload["print_id"]}))

    monkeypatch.setattr(ij, "run_worker_module", fake)
    # Pin the memory tier: otherwise the export's free-RAM gate refuses on a busy box and the
    # worker is never called (these tests are about what reaches the worker, not the box's RAM).
    monkeypatch.setenv("FANSIM_MEMORY_TIER", "16gb")

    ui.st.cup_build_ok = True
    ui.ctx.fan_export_stl_current()
    _drive(ui.tasks)
    return got, ui.st.export_msg or ""


def test_export_material_follows_picker(ui, monkeypatch, tmp_path):
    """Kimball 2026-10-14: PLA+ picked, Export README/temps still PETG. The worker gets the spec it prints from."""
    ui.st.assess_material = "PLA+"
    payload, _ = _export_payload(ui, monkeypatch, tmp_path)
    assert payload, "export worker was not called"
    assert payload["spec"].get("material") == "PLA+", payload["spec"].get("material")


def test_preview_fit_grams_follow_picker(ui, tmp_path, monkeypatch):
    """The Preview '✓ fits … g' line must weigh the part in the picked filament.

    Checked at the weight call, not the caption: the caption rounds to whole grams and the 2.4 % PETG/PLA+ density gap
    disappears for small parts (Stock: 11.13 vs 10.87 g, both "11 g")."""
    import trimesh
    import fansim.cockpit.fan_assess as fa

    seen = []
    real = fa.estimate_weight_g
    monkeypatch.setattr(fa, "estimate_weight_g", lambda v, m: seen.append(m) or real(v, m))
    stl = tmp_path / "c.stl"
    trimesh.creation.annulus(r_min=46, r_max=52, height=14).export(str(stl))
    ui.st.assess_material = "PLA+"
    ok, msg = ui.s.spec_status(stl, ui.s.build_edit_params())
    assert msg.startswith("✓ fits"), msg
    assert seen == ["PLA+"], seen


def test_export_caption_print_id_matches_file(ui, monkeypatch, tmp_path):
    """28.2: the code we tell the user to Sharpie is the one in the file name."""
    payload, msg = _export_payload(ui, monkeypatch, tmp_path)
    from fansim.manufacturability.print_id import verify_print_id

    pid = payload["print_id"]
    assert verify_print_id(pid)
    assert Path(payload["out"]).name.startswith(pid + "_")
    assert f"`{pid}`" in msg


def test_picker_offers_only_registered_materials(ui):
    from fansim.manufacturability.materials import MATERIALS

    items = [i if isinstance(i, str) else (i.get("value") or i.get("title")) for i in ui.st.assess_material_items]
    assert "PLA+" in items and set(items) <= set(MATERIALS), items


def test_preview_verdict_uses_the_material_from_the_click(ui, tmp_path, monkeypatch):
    """24.4 (Kimball 2026-10-15: snapshot): the "✓ fits / weight" line used the material as it was when
    Preview *finished*. Changing the picker mid-build must not change the verdict for this build."""
    import trimesh

    import fansim.cockpit.fan_assess as fa
    import fansim.geometry.isolated as iso

    seen = []
    real = fa.estimate_weight_g
    monkeypatch.setattr(fa, "estimate_weight_g", lambda v, m: seen.append(m) or real(v, m))

    def fake_build(flat, feat, out, **kw):
        trimesh.creation.annulus(r_min=46, r_max=52, height=14).export(str(out))
        ui.st.assess_material = "PETG"          # the user changes the picker while it builds

    monkeypatch.setattr(iso, "build_stl_isolated", fake_build)
    ui.st.assess_material = "PLA+"
    ui.s.do_preview()
    _drive(ui.tasks)
    assert seen == ["PLA+"], seen


def test_export_hint_uses_the_fit_hub_setting_from_the_click(ui, monkeypatch, tmp_path):
    """24.4: the finished Export message read the live "Fit hub" switch for its hint."""
    import fansim.cockpit.fan_export as fe
    import fansim.isolated_job as ij
    from fansim.manufacturability import print_id as pid_mod

    monkeypatch.setattr(pid_mod, "INDEX_PATH", tmp_path / "index.jsonl")
    monkeypatch.setattr(fe, "exports_dir", lambda: tmp_path / "exports")

    def fake(mod, payload, **kw):
        Path(payload["result"]).write_text(json.dumps({"ok": True, "mount_fits": False,
                                                       "mount_msg": "cup too wide", "mirror_note": "",
                                                       "gauge": None, "print_id": payload["print_id"]}))
        ui.st.export_fit_hub = True             # the user flips the switch while it exports

    monkeypatch.setattr(ij, "run_worker_module", fake)
    monkeypatch.setenv("FANSIM_MEMORY_TIER", "16gb")   # not the box's free RAM: the hint is under test
    ui.st.cup_build_ok = True
    ui.st.export_fit_hub = False
    ui.ctx.fan_export_stl_current()
    _drive(ui.tasks)
    assert "turn on 'Fit hub to motor on export'" in (ui.st.export_msg or ""), ui.st.export_msg


# --- R3.7: one "says X, does Y" check per tab that ships ---------------------------------

_ROOT = Path(__file__).resolve().parents[1]
_COCKPIT = _ROOT / "fansim" / "cockpit"

# A pass mark on a sentence that already says the number is not a validated result.
_DISCLAIMERS = (
    "not validated",
    "unvalidated",
    "not judged",
    "not a measurement",
    "not a comparison",
    "relative noise only",
    "not full cfd",
    "ranking only",
    "ranking-only",
)


def _call_name(node):
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def _bound_name(node):
    """Callable name from ``click=(fn,)`` or ``click=(getattr(ctx, "fn"),)``."""
    if isinstance(node, ast.Tuple) and node.elts:
        node = node.elts[0]
    if isinstance(node, ast.Name):
        return node.id
    if (
        isinstance(node, ast.Call)
        and _call_name(node.func) == "getattr"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ):
        return node.args[1].value
    return None


def _dict_value(node: ast.Dict, key: str):
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


def _ctx_aliases(tree: ast.AST) -> dict[str, str]:
    """``do_preview = getattr(ctx, "fan_do_preview")`` → local name to ctx attribute."""
    aliases = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        bound = _bound_name(node.value)
        if bound and isinstance(node.value, ast.Call):
            aliases[target.id] = bound
    return aliases


def _button_dicts(node):
    if isinstance(node, ast.Dict):
        return [node]
    if isinstance(node, ast.List):
        return [elt for elt in node.elts if isinstance(elt, ast.Dict)]
    return []


def _actions(path: Path) -> dict[str, set[str]]:
    """Visible button/select label → ctx handler names it calls."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    aliases = _ctx_aliases(tree)
    found: dict[str, set[str]] = {}

    def add(label, raw):
        if not label or not raw:
            return
        found.setdefault(label, set()).add(aliases.get(raw, raw))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name == "render_action_row" and len(node.args) >= 2:
            mapping = node.args[1]
            if not isinstance(mapping, ast.Dict):
                continue
            for value in mapping.values:
                for btn in _button_dicts(value):
                    label_node = _dict_value(btn, "label")
                    click_node = _dict_value(btn, "click")
                    if isinstance(label_node, ast.Constant) and isinstance(label_node.value, str):
                        add(label_node.value, _bound_name(click_node) if click_node else None)
            continue
        if name not in ("VBtn", "VSelect"):
            continue
        label = None
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            label = node.args[0].value
        raw = None
        for kw in node.keywords:
            if kw.arg == "label" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                label = kw.value.value
            if kw.arg in ("click", "update_modelValue"):
                raw = _bound_name(kw.value)
        add(label, raw)
    return found


def _require(actions: dict[str, set[str]], label: str, handler: str) -> None:
    got = actions.get(label)
    assert got == {handler}, f"{label!r} bound to {got!r}; labels: {sorted(actions)}"


def _source_texts(fn) -> list[str]:
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return _static_texts(tree)


def _static_texts(tree: ast.AST) -> list[str]:
    texts = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            texts.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                else:
                    parts.append("")
            texts.append("".join(parts))
    return texts


def _static_strings(path: Path) -> list[str]:
    return _static_texts(ast.parse(path.read_text(encoding="utf-8")))


def _assert_unmarked(texts) -> None:
    """A sentence that says the number is not validated does not also wear a pass mark."""
    for text in texts:
        low = text.lower()
        if any(phrase in low for phrase in _DISCLAIMERS) and "✓" in text:
            raise AssertionError(text)


def _body(ctx, name: str) -> str:
    return inspect.getsource(getattr(ctx, name))


def _product_tabs(path: Path) -> list[tuple[str, str, str | None]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tabs = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "VTab":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        label = node.args[0].value
        if not isinstance(label, str):
            continue
        value = show = None
        for kw in node.keywords:
            if kw.arg == "value" and isinstance(kw.value, ast.Constant):
                value = kw.value.value
            if kw.arg == "v_show" and isinstance(kw.value, ast.Constant):
                show = kw.value.value
        if isinstance(value, str):
            tabs.append((label, value, show if isinstance(show, str) else None))
    return tabs


@pytest.fixture(scope="module")
def tabs(tmp_path_factory):
    """Headless cockpit with every shipping tab's handlers bound. Nothing is clicked."""
    import fansim.cockpit.fan_runtime as fan_runtime
    import fansim.cockpit.fan_tab as fan_tab
    from fansim.cockpit.context import CockpitCtx
    from fansim.cockpit.cror_tab import setup_cror_tab
    from fansim.cockpit.mixed_tab import setup_mixed_tab
    from fansim.cockpit.prop_tab import setup_prop_tab
    from fansim.cockpit.volute_tab import setup_volute_tab

    root = tmp_path_factory.mktemp("r37_tabs")
    tasks: list = []
    orig = fan_runtime.asynchronous
    fan_runtime.asynchronous = SimpleNamespace(
        create_task=lambda coro: tasks.append(coro) or MagicMock()
    )
    try:
        server = trame.get_server(f"r37_tabs_{root.name}")
        server.controller.figure_update = lambda *a, **k: None
        server.controller.view_update = lambda *a, **k: None
        ctx = CockpitCtx(
            server=server,
            state=server.state,
            ctrl=server.controller,
            run_dir=root,
            runs_root=root,
            plotter=MagicMock(),
            busy_bar=lambda *a, **k: None,
            busy_expr=lambda *a, **k: "",
            spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
            study_name=None,
            study_designs=[],
            user_designs=[],
            by_trial=_T(),
            next_id=[9000],
            assess_dir=root / "cockpit_assess",
        )
        fan_tab.setup_fan_tab(ctx)
        setup_mixed_tab(ctx)
        setup_volute_tab(ctx)
        setup_prop_tab(ctx)
        setup_cror_tab(ctx)
    finally:
        fan_runtime.asynchronous = orig
        for coro in tasks:
            coro.close()
    return SimpleNamespace(ctx=ctx, st=ctx.state)


def test_simple_mode_shows_fan_and_prop_only():
    """Simple mode says Fan and Prop. Mixed, Volute and CROR stay on Expert, and the code bounces back."""
    product = {value: (label, show) for label, value, show in _product_tabs(_COCKPIT / "app.py")}
    assert product["fan"] == ("Fan · blades", None)
    assert product["propeller"] == ("Prop · fast estimate", None)
    assert product["mixed"][0] == "Mixed · experimental"
    assert product["volute"][0] == "Volute · estimate"
    assert product["cror"][0] == "CROR · estimate"
    for proxy in ("mixed", "volute", "cror"):
        assert product[proxy][1] == "ui_mode === 'expert'"

    from fansim.cockpit.fan_core import tab_for_ui_mode

    for proxy in ("mixed", "volute", "cror"):
        assert tab_for_ui_mode("simple", proxy) == "fan"
        assert tab_for_ui_mode("expert", proxy) == proxy
    assert tab_for_ui_mode("simple", "fan") == "fan"
    assert tab_for_ui_mode("simple", "propeller") == "propeller"

    app = _static_strings(_COCKPIT / "app.py")
    _assert_unmarked(app)
    blob = "\n".join(app)
    assert "Experimental: not validated against published data" in blob
    assert "ranking only, unvalidated" in blob
    assert "not full CFD" in blob
    assert "Fan: printable PC-fan blades (airflow check). Prop: propeller (fast estimate)." in blob


def test_each_archetype_ships_design_results_library():
    """Design, Results and Library are the three subtabs, and each panel follows that name."""
    shell = (_COCKPIT / "tab_shell.py").read_text(encoding="utf-8")
    fan = (_COCKPIT / "fan_tab_ui.py").read_text(encoding="utf-8")
    for name, key in (("Design", "design"), ("Results", "results"), ("Library", "library")):
        assert f'VTab("{name}"' in shell
        assert f"=== '{key}'" in shell
        assert f'VTab("{name}"' in fan
        assert f"fan_subtab === '{key}'" in fan
    for fname in ("mixed_tab.py", "volute_tab.py", "prop_tab.py", "cror_tab.py"):
        src = (_COCKPIT / fname).read_text(encoding="utf-8")
        assert "render_left_shell(" in src
        assert "design=" in src and "results=" in src and "library=" in src


def test_fan_design_buttons_do_what_they_say(tabs):
    """Fan Design: Preview builds geometry, Assess runs Assess, Run uses the 2–12 step check."""
    actions = _actions(_COCKPIT / "fan_tab_ui.py")
    _require(actions, "Preview (sec)", "fan_do_preview")
    _require(actions, "Assess (~15–30 min)", "fan_on_assess")
    _require(actions, "Run", "fan_on_sweep")
    _require(actions, "Score multi-point BEM (ranking only)", "fan_score_multi_point_bem")
    _require(actions, "⏹ Cancel Assess", "fan_cancel_assess")

    preview = _body(tabs.ctx, "fan_do_preview")
    assert "preview_busy = True" in preview
    assert 'action="Preview"' in preview
    assert "_build_preview_stl" in preview
    assert "_assess(" not in preview

    assess = _body(tabs.ctx, "fan_on_assess")
    assert "assess_busy = True" in assess
    assert 'busy_caption("Assess"' in assess
    assert "await _assess(" in assess
    assert "run_prop_study" not in assess

    sweep = _body(tabs.ctx, "fan_on_sweep")
    assert "_check_steps" in sweep
    assert 'label="steps (2–12)"' in (_COCKPIT / "fan_tab_ui.py").read_text(encoding="utf-8")

    cancel = _body(tabs.ctx, "fan_cancel_assess")
    assert "assess_cancel = True" in cancel
    assert "Cancelling Assess" in cancel

    score = _body(tabs.ctx, "fan_score_multi_point_bem")
    assert "format_multi_point" in score
    assert "score_multi_point" in score
    from fansim.optimize.multi_point import MultiPointScore, PointScore, format_multi_point

    note = MultiPointScore.__dataclass_fields__["note"].default
    assert "ranking-only" in note and "not absolute" in note
    assert "✓" not in note
    lines = format_multi_point(MultiPointScore(
        points=[PointScore(50.0, 1000.0, 10.0, 1.0, 40.0, 30.0, 12.0, 0.1, 80.0)],
        weighted_cfm_load=30.0,
        weighted_cfm_free=40.0,
        weighted_rel_noise_db=12.0,
    ))
    assert any(note in line for line in lines)
    assert all("✓" not in line for line in lines)
    _assert_unmarked(_static_strings(_COCKPIT / "fan_tab_ui.py"))
    assert "Noise ranking is not validated." in "\n".join(_static_strings(_COCKPIT / "fan_tab_ui.py"))


def test_fan_results_noise_number_is_not_a_pass(tabs):
    """Results says click a point to load Design, and an unjudged noise number is not a pass mark."""
    ui = (_COCKPIT / "fan_tab_ui.py").read_text(encoding="utf-8")
    assert "Click a point to load Design" in ui
    assert "click=(on_plotly_click," in ui
    click = _body(tabs.ctx, "fan_on_plotly_click")
    assert "state.selected_trial" in click
    trials = (_COCKPIT / "fan_trials.py").read_text(encoding="utf-8")
    assert '@state.change("selected_trial")' in trials
    assert "select(selected_trial)" in trials

    actions = _actions(_COCKPIT / "fan_tab_ui.py")
    _require(actions, "⏹ Cancel viz", "fan_cancel_airflow")
    assert "airflow_cancel = True" in _body(tabs.ctx, "fan_cancel_airflow")

    assert "{{ row.icon }} {{ row.title }}" in ui
    assert "!row.expert_only || ui_mode === 'expert'" in ui
    from fansim.cfd.flow_report import FlowMetrics
    from fansim.cfd.flow_verdicts import ICONS, judge, overall_line

    stock = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5, mean_dp0_pa=6.0)
    noise = judge(stock, stock)[4]
    assert noise.expert_only is True
    assert "Not judged" in noise.text
    assert noise.status == "na"
    assert ICONS[noise.status] != "✓"
    assert "✓" not in noise.text
    assert "noise" not in overall_line(judge(stock, stock), compared=True).lower()

    hinted = stock.to_dict() | {"noise_hint_db": 76.4, "noise_swl_db": None}
    base = stock.to_dict() | {"noise_hint_db": 75.4, "noise_swl_db": None}
    row = judge(FlowMetrics.from_dict(hinted), FlowMetrics.from_dict(base))[4]
    assert "not a comparison" in row.text
    assert row.status == "na" and ICONS[row.status] != "✓"
    assert "✓" not in row.text


def test_fan_library_save_and_scale_do_what_they_say(tabs):
    """Library: Save model writes the model, and Scale to this hub scales to the hub."""
    actions = _actions(_COCKPIT / "fan_tab_ui.py")
    _require(actions, "💾 Save model", "fan_save_model")
    assert actions["Scale to this hub"] == {"fan_on_scale_to_hub", "fan_on_library_scale_to_hub"}
    assert "save_user_fan_model" in _body(tabs.ctx, "fan_save_model")
    for name in actions["Scale to this hub"]:
        assert "scale_to_hub" in _body(tabs.ctx, name)


def test_mixed_tab_assess_and_export_match_the_experimental_label(tabs):
    """Mixed says experimental / not validated. Assess runs mixed CFD; the export sheet has no pass mark."""
    actions = _actions(_COCKPIT / "mixed_tab.py")
    _require(actions, "Preview", "mf_preview")
    _require(actions, "Assess", "mf_assess")
    _require(actions, "Export STL", "mf_export")
    _require(actions, "Optimize", "optimize_mixed")
    _require(actions, "Previous runs", "load_mf_trial")
    _require(actions, "CFD refine", "refine_mixed_cfd")

    preview = _body(tabs.ctx, "mf_preview")
    assert 'action="Preview"' in preview and "build_mixed_stl_isolated" in preview
    assert "evaluate_mixed_flow_isolated" not in preview

    assess = _body(tabs.ctx, "mf_assess")
    assert "mf_assess_busy = True" in assess
    assert 'action="Assess"' in assess
    assert "evaluate_mixed_flow_isolated" in assess
    assert "run_mixed_study" not in assess
    assert "not validated" in assess

    export = _body(tabs.ctx, "mf_export")
    assert "mixed_export_readme" in export
    assert 'action="Export"' in export
    from fansim.cockpit.mixed_tab import mixed_export_readme

    readme = mixed_export_readme()
    assert "not validated" in readme
    assert "✓" not in readme

    assert "not validated" in "\n".join(tabs.st.mf_readout)
    _assert_unmarked(_static_strings(_COCKPIT / "mixed_tab.py"))
    _assert_unmarked([tabs.st.mf_msg, *tabs.st.mf_readout, readme, *_source_texts(tabs.ctx.mf_assess)])
    assert "mf_n_blades" in _body(tabs.ctx, "load_mf_trial")


def test_volute_tab_assess_matches_the_unvalidated_label(tabs):
    """Volute says ranking-only / unvalidated. Assess runs the volute CFD, and that label has no pass mark."""
    actions = _actions(_COCKPIT / "volute_tab.py")
    _require(actions, "Preview", "volute_preview")
    _require(actions, "Assess", "volute_assess")
    _require(actions, "Export STLs", "volute_export")
    _require(actions, "Optimize", "optimize_volute")
    _require(actions, "Previous runs", "load_volute_trial")

    preview = _body(tabs.ctx, "volute_preview")
    assert 'action="Preview"' in preview and "build_volute_preview_isolated" in preview
    assert "evaluate_volute_isolated" not in preview

    assess = _body(tabs.ctx, "volute_assess")
    assert "volute_assess_busy = True" in assess
    assert 'action="Assess"' in assess
    assert "evaluate_volute_isolated" in assess
    assert "unvalidated" in assess

    idle = "\n".join([tabs.st.volute_msg, *tabs.st.volute_readout])
    assert "unvalidated" in idle
    _assert_unmarked(_static_strings(_COCKPIT / "volute_tab.py"))
    _assert_unmarked([idle, *_source_texts(tabs.ctx.volute_assess)])
    assert "volute_n_blades" in _body(tabs.ctx, "load_volute_trial")


def test_prop_tab_analyze_is_the_fast_estimate(tabs):
    """Prop says fast estimate, not full CFD. Analyze runs BEMT; the estimate line has no pass mark."""
    actions = _actions(_COCKPIT / "prop_tab.py")
    _require(actions, "Analyze (~1 s)", "analyze_prop")
    _require(actions, "Optimize (BEMT)", "optimize_prop")
    _require(actions, "Stop", "stop_prop_optimize")
    _require(actions, "Export STL", "export_prop_stl")
    _require(actions, "Export CT/CP (PyThrust)", "export_prop_pythrust_csv")
    _require(actions, "Previous runs", "load_prop_row")
    _require(actions, "CFD refine", "refine_prop_cfd")

    analyze = _body(tabs.ctx, "analyze_prop")
    assert "bemt_analyze" in analyze and "_prop_perf_lines" in analyze
    assert "run_prop_study" not in analyze
    assert "refine_prop_pareto_cfd" not in analyze

    optimize = _body(tabs.ctx, "optimize_prop")
    assert "run_prop_study" in optimize and "BEMT" in optimize
    assert 'action="Optimize"' in optimize

    stop = _body(tabs.ctx, "stop_prop_optimize")
    assert "opt_stop.set()" in stop
    assert "Stopping after the current trial" in stop

    assert "build_prop" in _body(tabs.ctx, "export_prop_stl")
    ctcp = _body(tabs.ctx, "export_prop_pythrust_csv")
    assert "export_bemt_pythrust_catalog" in ctcp
    assert 'action="Export CT/CP"' in ctcp

    assert "_init_prop_editor" in _body(tabs.ctx, "load_prop_row")
    prop_src = (_COCKPIT / "prop_tab.py").read_text(encoding="utf-8")
    assert "Load a previous Optimize / Analyze front into Design." in prop_src
    assert "not full CFD" in prop_src

    from fansim.cockpit.prop_tab import prop_reference_line

    line = prop_reference_line(
        SimpleNamespace(ref_thrust_g=1850, ref_power_w=650, ref_rpm=30000, rpm_max=30000),
        SimpleNamespace(thrust_g=2000.0, power_w=700.0),
    )
    assert "not a measurement" in line and "BEMT" in line
    assert "✓" not in line
    _assert_unmarked(_static_strings(_COCKPIT / "prop_tab.py"))
    _assert_unmarked([line, tabs.st.prop_info, *tabs.st.prop_readout])


def test_cror_tab_preview_is_a_preview_and_noise_is_not_a_pass(tabs):
    """CROR says fast estimate. Preview builds the stack; relative noise is not a pass mark."""
    actions = _actions(_COCKPIT / "cror_tab.py")
    _require(actions, "Preview", "preview_cror")
    _require(actions, "Thin to depth", "thin_cror_now")
    _require(actions, "Export STL", "export_cror_now")
    _require(actions, "Optimize", "optimize_cror")
    _require(actions, "Previous runs", "load_cror_row")
    _require(actions, "CFD refine", "refine_cror_cfd")

    preview = _body(tabs.ctx, "preview_cror")
    assert "cror_preview_busy = True" in preview
    assert 'action="Preview"' in preview
    assert "export_cror_stl" in preview
    assert "run_cror_study" not in preview
    for text in _source_texts(tabs.ctx.preview_cror):
        if "noise" in text.lower():
            assert "✓" not in text, text

    thin = _body(tabs.ctx, "thin_cror_now")
    assert 'action="Thin"' in thin and "thin_cror_for_frame" in thin

    optimize = _body(tabs.ctx, "optimize_cror")
    assert "run_cror_study" in optimize and "BEMT" in optimize
    assert "export_cror_stl" not in optimize

    idle = "\n".join(tabs.st.cror_readout)
    assert "Relative noise only" in idle
    _assert_unmarked(_static_strings(_COCKPIT / "cror_tab.py"))
    _assert_unmarked([idle, *_source_texts(tabs.ctx.preview_cror), *_source_texts(tabs.ctx.optimize_cror)])
    assert "apply_shape_flat_to_state" in _body(tabs.ctx, "load_cror_row")
