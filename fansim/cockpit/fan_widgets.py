"""Shared cockpit Trame widgets (sliders / switches / selects with hover help & diagrams)."""

from __future__ import annotations

import sys

from fansim.cockpit.blade_copy import BLADE_DESC, BLADE_DESC_SIMPLE, CROR_DESC
from fansim.cockpit.diagrams import diagram_for_control
from fansim.cockpit.fan_copy import _IMG_URI, CONTROL_DESC, CONTROL_DESC_SIMPLE, OPT_SEARCH_HELP
from fansim.cockpit.mixed_copy import MIXED_DESC
from fansim.cockpit.prop_copy import PROP_DESC, PROP_DESC_SIMPLE
from fansim.cockpit.volute_copy import VOLUTE_DESC

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3


def resolve_tooltip(
    model: str,
    *,
    help_map: dict[str, str] | None = None,
    simple_help_map: dict[str, str] | None = None,
) -> tuple[str, str, str]:
    """Return ``(simple_desc, expert_desc, image_or_svg_uri)`` for any cockpit control key.

    Checks explicit caller maps first, then falls back across Fan, Prop, Mixed, Volute,
    CROR, shared BladeParams, and Optimize help maps. Image prefers rendered control PNGs
    (``docs/control_images``) and falls back to inline explanatory SVG diagrams.
    """
    expert = ""
    simple = ""
    if help_map is not None:
        expert = help_map.get(model, "")
        if simple_help_map is not None:
            simple = simple_help_map.get(model, expert)
        elif help_map is CONTROL_DESC:
            simple = CONTROL_DESC_SIMPLE.get(model, expert)
        else:
            simple = expert
    else:
        for exp_map, simp_map in (
            (CONTROL_DESC, CONTROL_DESC_SIMPLE),
            (PROP_DESC, PROP_DESC_SIMPLE),
            (MIXED_DESC, MIXED_DESC),
            (VOLUTE_DESC, VOLUTE_DESC),
            (CROR_DESC, CROR_DESC),
            (BLADE_DESC, BLADE_DESC_SIMPLE),
            (OPT_SEARCH_HELP, OPT_SEARCH_HELP),
        ):
            if model in exp_map:
                expert = exp_map[model]
                simple = simp_map.get(model, expert)
                break
        if not expert:
            for prefix in ("p_", "cror_f_", "cror_r_"):
                if model.startswith(prefix):
                    bare = model[len(prefix) :]
                    if bare in BLADE_DESC:
                        expert = BLADE_DESC[bare]
                        simple = BLADE_DESC_SIMPLE.get(bare, expert)
                        break

    uri = _IMG_URI.get(model) or diagram_for_control(model)
    return simple, expert, uri


def slider(
    label: str,
    model: str,
    mn: float,
    mx: float | str,
    step: float,
    disabled=None,
    unit: str = "",
    *,
    simple_label: str | None = None,
    simple_unit: str | None = None,
    help_map: dict[str, str] | None = None,
    simple_help_map: dict[str, str] | None = None,
):
    """Slider with always-visible value + unit and hover tooltip/diagram.

    ``mx`` may be a float or a state variable name (str) for a reactive max.
    """
    simple, desc, uri = resolve_tooltip(
        model, help_map=help_map, simple_help_map=simple_help_map
    )
    extra = {}
    if disabled is not None:
        extra["disabled"] = disabled
    unit_s = f" {unit}" if unit else ""
    s_unit = unit if simple_unit is None else simple_unit
    s_unit_s = f" {s_unit}" if s_unit else ""
    max_kw = (mx,) if isinstance(mx, str) else mx

    def _body():
        with html.Div(classes="d-flex justify-space-between align-center text-caption mb-0"):
            if simple_label:
                html.Span(simple_label, v_show="ui_mode === 'simple'")
                html.Span(label, v_show="ui_mode === 'expert'")
            else:
                html.Span(label)
            if simple_unit is not None and s_unit_s != unit_s:
                html.Span(
                    f"{{{{ {model} }}}}{s_unit_s}",
                    classes="font-weight-medium text-no-wrap ml-2",
                    v_show="ui_mode === 'simple'",
                )
                html.Span(
                    f"{{{{ {model} }}}}{unit_s}",
                    classes="font-weight-medium text-no-wrap ml-2",
                    v_show="ui_mode === 'expert'",
                )
            else:
                html.Span(
                    f"{{{{ {model} }}}}{unit_s}",
                    classes="font-weight-medium text-no-wrap ml-2",
                )
        with v3.VSlider(
            v_model=(model,),
            min=mn,
            max=max_kw,
            step=step,
            # Thumb label only while dragging (an always-on one overlapped neighbouring labels,
            # §23.21). Vuetify's default thumb text is the value SNAPPED to the step, so a recipe
            # value between steps read "18.0" on the thumb vs "17.75" beside it (QA UI-8, §23.50);
            # show the model value itself, same as the side label.
            thumb_label=True,
            density="compact",
            hide_details=True,
            classes="mt-0 mb-2",
            **extra,
        ):
            with v3.Template(v_slot_thumb_label=True):
                html.Span(f"{{{{ {model} }}}}")

    if not desc and not simple and not uri:
        _body()
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=380):
        with (
            v3.Template(v_slot_activator="{ props }"),
            html.Div(v_bind="props"),
        ):
            _body()
        if uri:
            html.Img(
                src=uri,
                style="width:360px;max-width:100%;display:block;"
                "margin-bottom:4px;border-radius:4px;",
            )
        if simple:
            html.Div(simple, classes="text-caption", v_show="ui_mode === 'simple'")
        if desc:
            html.Div(desc, classes="text-caption", v_show="ui_mode === 'expert'")


def opt_section(title: str, blurb: str = ""):
    """Small section header inside Advanced search / Assess settings."""
    html.Div(title, classes="text-subtitle-2 mt-3 mb-1")
    if blurb:
        html.Div(blurb, classes="text-caption text-medium-emphasis mb-1")


def help_switch(
    model: str,
    label: str,
    *,
    help_map: dict | None = None,
    classes: str = "",
    disabled=None,
):
    """Compact switch with a hover tooltip (same pattern as design sliders)."""
    simple, desc, uri = resolve_tooltip(model, help_map=help_map or OPT_SEARCH_HELP)
    extra = {}
    if disabled is not None:
        extra["disabled"] = disabled
    cls = f"mb-1 {classes}".strip()
    kwargs = dict(
        v_model=(model,),
        density="compact",
        hide_details=True,
        color="primary",
        inset=True,
        label=label,
        classes=cls,
        **extra,
    )
    if not desc and not simple and not uri:
        v3.VSwitch(**kwargs)
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=420):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSwitch(v_bind="props", **kwargs)
        if uri:
            html.Img(
                src=uri,
                style="width:360px;max-width:100%;display:block;"
                "margin-bottom:4px;border-radius:4px;",
            )
        if simple and simple != desc:
            html.Div(simple, classes="text-caption", v_show="ui_mode === 'simple'")
            html.Div(desc, classes="text-caption", v_show="ui_mode === 'expert'")
        elif desc:
            html.Div(desc, classes="text-caption")


def help_select(
    model: str,
    label: str,
    *,
    items: str,
    help_map: dict | None = None,
    item_title: str = "title",
    item_value: str = "value",
    classes: str = "mb-2",
):
    """Outlined VSelect with the same hover image/diagram + text tooltip as design sliders."""
    simple, desc, uri = resolve_tooltip(model, help_map=help_map or CONTROL_DESC)
    kwargs = {
        "label": label,
        "v_model": (model,),
        "items": (items,),
        "item_title": item_title,
        "item_value": item_value,
        "density": "compact",
        "variant": "outlined",
        "hide_details": True,
        "classes": classes,
    }
    if not desc and not simple and not uri:
        v3.VSelect(**kwargs)
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=420):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSelect(v_bind="props", **kwargs)
        if uri:
            html.Img(
                src=uri,
                style="width:360px;max-width:100%;display:block;"
                "margin-bottom:4px;border-radius:4px;",
            )
        if simple:
            html.Div(simple, classes="text-caption", v_show="ui_mode === 'simple'")
        if desc:
            html.Div(desc, classes="text-caption", v_show="ui_mode === 'expert'")


# Back-compat aliases used by render_fan_tab
_slider = slider
_opt_section = opt_section
_help_switch = help_switch
_help_select = help_select
