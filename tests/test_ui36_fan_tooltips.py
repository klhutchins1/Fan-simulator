"""UI-36: Fan tab high-impact settings and action buttons must carry tooltips."""

from __future__ import annotations

import ast
from pathlib import Path

from fansim.cockpit.fan_copy import CONTROL_DESC, CONTROL_DESC_SIMPLE

FAN_TAB_UI = Path("fansim/cockpit/fan_tab_ui.py")

REQUIRED_EXPERT_KEYS = (
    "fan_model",
    "sweep_param",
    "sweep_steps",
    "intake_overbuild",
    "intake_overbuild_mm",
    "seed_duty_cfm",
    "seed_duty_pa",
    "seed_duty_rpm",
    "seed_duty_vortex",
    "export_fit_hub",
    "export_fit_frame",
    "export_also_mirror",
    "preview_motor_cup",
)

REQUIRED_SIMPLE_KEYS = (
    "fan_model",
    "export_fit_hub",
    "export_fit_frame",
)


def _bound_models_with_tooltips(path: Path) -> set[str]:
    """Return v_model keys in ``path`` wired to tooltip-emitting helpers or inside VTooltip."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()

    def _call_name(fn: ast.AST) -> str:
        if isinstance(fn, ast.Name):
            return fn.id
        if isinstance(fn, ast.Attribute):
            return fn.attr
        return ""

    def _first_str_model(call: ast.Call) -> str | None:
        # _help_switch(model, ...) / _help_select(model, ...)
        if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return call.args[0].value
        for kw in call.keywords:
            if kw.arg == "model" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return None

    def _slider_model(call: ast.Call) -> str | None:
        # _slider(label, model, ...)
        if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant) and isinstance(call.args[1].value, str):
            return call.args[1].value
        for kw in call.keywords:
            if kw.arg == "model" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
        return None

    def _v_model_kw(call: ast.Call) -> str | None:
        for kw in call.keywords:
            if kw.arg == "v_model" and isinstance(kw.value, ast.Tuple) and kw.value.elts:
                elt = kw.value.elts[0]
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    return elt.value
        return None

    def _walk(node: ast.AST, in_tooltip: bool) -> None:
        if isinstance(node, ast.With):
            is_tt = any(
                isinstance(item.context_expr, ast.Call)
                and _call_name(item.context_expr.func) == "VTooltip"
                for item in node.items
            )
            for child in node.body:
                _walk(child, in_tooltip or is_tt)
            return
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in ("_help_switch", "help_switch", "_help_select", "help_select"):
                m = _first_str_model(node)
                if m:
                    found.add(m)
            elif name in ("_slider", "slider"):
                m = _slider_model(node)
                if m:
                    found.add(m)
            elif in_tooltip:
                m = _v_model_kw(node)
                if m:
                    found.add(m)
        for child in ast.iter_child_nodes(node):
            _walk(child, in_tooltip)

    _walk(tree, False)
    return found


def test_ui36_high_impact_controls_have_descriptions():
    missing_expert = [k for k in REQUIRED_EXPERT_KEYS if len(CONTROL_DESC.get(k, "").strip()) < 15]
    missing_simple = [k for k in REQUIRED_SIMPLE_KEYS if len(CONTROL_DESC_SIMPLE.get(k, "").strip()) < 15]
    assert not missing_expert, f"Missing/short CONTROL_DESC entries: {missing_expert}"
    assert not missing_simple, f"Missing/short CONTROL_DESC_SIMPLE entries: {missing_simple}"


def test_ui36_high_impact_controls_wired_to_tooltips_in_fan_tab_ui():
    wired = _bound_models_with_tooltips(FAN_TAB_UI)
    missing = [k for k in REQUIRED_EXPERT_KEYS if k not in wired]
    assert not missing, f"Fan-tab controls missing hover tooltips (UI-36): {missing}"


def test_ui36_primary_action_buttons_have_tooltips():
    tree = ast.parse(FAN_TAB_UI.read_text(encoding="utf-8"))
    labels_with_tooltip: set[str] = set()

    def _call_name(fn: ast.AST) -> str:
        if isinstance(fn, ast.Name):
            return fn.id
        if isinstance(fn, ast.Attribute):
            return fn.attr
        return ""

    def _walk(node: ast.AST, in_tooltip: bool) -> None:
        if isinstance(node, ast.With):
            is_tt = any(
                isinstance(item.context_expr, ast.Call)
                and _call_name(item.context_expr.func) == "VTooltip"
                for item in node.items
            )
            for child in node.body:
                _walk(child, in_tooltip or is_tt)
            return
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name == "render_action_row" and len(node.args) >= 2 and isinstance(node.args[1], ast.Dict):
                for val in node.args[1].values:
                    dicts = val.elts if isinstance(val, ast.List) else [val]
                    for d in dicts:
                        if not isinstance(d, ast.Dict):
                            continue
                        kv = {
                            k.value: v
                            for k, v in zip(d.keys, d.values)
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        }
                        lbl = kv.get("label")
                        tt = kv.get("tooltip")
                        if (
                            isinstance(lbl, ast.Constant)
                            and isinstance(lbl.value, str)
                            and isinstance(tt, ast.Constant)
                            and isinstance(tt.value, str)
                            and len(tt.value.strip()) >= 15
                        ):
                            labels_with_tooltip.add(lbl.value)
            elif name == "VBtn" and in_tooltip and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                    labels_with_tooltip.add(arg0.value)
        for child in ast.iter_child_nodes(node):
            _walk(child, in_tooltip)

    _walk(tree, False)
    expected = {
        "Preview (sec)",
        "Assess (~30–40 min)",
        "Load Stock / Reference",
        "Reset",
    }
    missing = expected - labels_with_tooltip
    assert not missing, f"Action buttons missing tooltips (UI-36): {sorted(missing)}"
