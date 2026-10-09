# EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12
# source: agent-transcripts/9f43d5b7...jsonl write@3374 + 0 later StrReplace
# NOT verified against lost E: tree — re-check before deleting RECOVERED-FROM-CHAT peers.

"""Fan-tab-local Trame widgets (sliders / switches with hover help)."""

from __future__ import annotations

import sys

from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP, _IMG_URI

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3


def slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None):
    """A labelled slider with a HOVER TOOLTIP: what it does + a min/max illustration."""
    desc, uri = CONTROL_DESC.get(model, ""), _IMG_URI.get(model)
    extra = {}
    if disabled is not None:
        extra["disabled"] = disabled
    if not desc and not uri:
        v3.VSlider(
            v_model=(model,),
            min=mn,
            max=mx,
            step=step,
            label=label,
            thumb_label=True,
            density="compact",
            hide_details=True,
            classes="mb-1",
            **extra,
        )
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=380):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSlider(
                v_bind="props",
                v_model=(model,),
                min=mn,
                max=mx,
                step=step,
                label=label,
                thumb_label=True,
                density="compact",
                hide_details=True,
                classes="mb-1",
                **extra,
            )
        if uri:
            html.Img(
                src=uri,
                style="width:360px;max-width:100%;display:block;"
                "margin-bottom:4px;border-radius:4px;",
            )
        html.Div(desc, classes="text-caption")


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
    if not desc:
        v3.VSwitch(**kwargs)
        return
    with v3.VTooltip(location="end", open_delay=150, max_width=420):
        with v3.Template(v_slot_activator="{ props }"):
            v3.VSwitch(v_bind="props", **kwargs)
        html.Div(desc, classes="text-caption")


# Back-compat aliases used by render_fan_tab
_slider = slider
_opt_section = opt_section
_help_switch = help_switch
