"""Fan-tab-local Trame widgets (sliders / switches with hover help)."""

from __future__ import annotations

import sys

from fansim.cockpit.fan_copy import _IMG_URI, CONTROL_DESC, CONTROL_DESC_SIMPLE, OPT_SEARCH_HELP

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3


def slider(label: str, model: str, mn: float, mx: float | str, step: float, disabled=None, unit: str = ""):
    """Slider with always-visible value + unit (not only on thumb click).

    ``mx`` may be a float or a state variable name (str) for a reactive max.
    """
    desc = CONTROL_DESC.get(model, "")
    simple = CONTROL_DESC_SIMPLE.get(model, desc)
    uri = _IMG_URI.get(model)
    extra = {}
    if disabled is not None:
        extra["disabled"] = disabled
    unit_s = f" {unit}" if unit else ""
    max_kw = (mx,) if isinstance(mx, str) else mx

    def _body():
        with html.Div(classes="d-flex justify-space-between align-center text-caption mb-0"):
            html.Span(label)
            html.Span(
                f"{{{{ {model} }}}}{unit_s}",
                classes="font-weight-medium text-no-wrap ml-2",
            )
        with v3.VSlider(  # noqa: SIM117 — trame nested contexts
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
    with v3.VTooltip(location="end", open_delay=150, max_width=380):  # noqa: SIM117
        with v3.Template(v_slot_activator="{ props }"):  # noqa: SIM117 — trame activator nest
            with html.Div(v_bind="props"):
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
    desc = (help_map or OPT_SEARCH_HELP).get(model, "")
    uri = _IMG_URI.get(model)
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
    if not desc and not uri:
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
        if desc:
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
    """Outlined VSelect with the same hover image+text tooltip as design sliders."""
    base = help_map or CONTROL_DESC
    desc = base.get(model, "")
    simple = CONTROL_DESC_SIMPLE.get(model, desc) if base is CONTROL_DESC else desc
    uri = _IMG_URI.get(model)
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
