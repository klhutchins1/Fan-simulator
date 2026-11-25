"""Shared Design / Results / Library chrome for cockpit archetype tabs."""

from __future__ import annotations

from typing import Any, Callable

# Locked across tabs. A missing slot is omitted, not replaced with a spacer.
ACTION_SLOTS = ("preview", "score", "export", "optimize", "stop", "randomize")
VTK_HEIGHT_PX = 320
# 3-D viewer card: height follows the column width (3:2) between VTK_HEIGHT_PX and ~48 % of the
# window. Cap is tight so the impeller stays above the fold at 1366×768 (UI-27 / #37); a fixed
# 400 px on a wide column used to give a ~2.8:1 canvas (QA UI-9).
VTK_VIEW_STYLE = (
    f"width:100%;aspect-ratio:3 / 2;min-height:{VTK_HEIGHT_PX}px;"
    "max-height:min(48vh, 420px);"
)
SCATTER_HEIGHT_PX = 360


def action_slot_order() -> tuple[str, ...]:
    return ACTION_SLOTS


def render_subtabs(v3, *, state_key: str) -> None:
    """Design | Results | Library. ``state_key`` must already exist on state."""
    with v3.VTabs(v_model=(state_key,), color="primary", classes="mb-3"):
        v3.VTab("Design", value="design")
        v3.VTab("Results", value="results")
        v3.VTab("Library", value="library")


def render_action_row(v3, buttons: dict[str, Any]) -> None:
    """Render the locked action-row slots.

    ``buttons`` maps a slot name to one VBtn kwargs dict, a list of kwargs dicts
    (for multiple Export buttons), or ``None`` / missing to skip the slot.
    Pass the button label as ``label=``; it becomes the first positional child.
    """
    with v3.VRow(no_gutters=True, classes="mt-2 flex-wrap"):
        for slot in ACTION_SLOTS:
            cfg = buttons.get(slot)
            if not cfg:
                continue
            items = cfg if isinstance(cfg, list) else [cfg]
            for btn in items:
                kw = dict(btn)
                classes = kw.pop("classes", "mr-2 mb-1")
                label = kw.pop("label", kw.pop("children", slot.title()))
                v3.VBtn(label, classes=classes, **kw)


def render_left_shell(
    v3,
    html,
    *,
    state_key: str,
    design: Callable[[], None],
    results: Callable[[], None],
    library: Callable[[], None],
) -> None:
    """Sub-tabs plus three panels. Call inside the left ``VCol``."""
    render_subtabs(v3, state_key=state_key)
    with html.Div(v_show=f"{state_key} === 'design'"):
        design()
    with html.Div(v_show=f"{state_key} === 'results'"):
        results()
    with html.Div(v_show=f"{state_key} === 'library'"):
        library()
