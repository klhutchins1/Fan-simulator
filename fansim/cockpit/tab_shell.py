"""Shared Design / Results / Library chrome for cockpit archetype tabs."""

from __future__ import annotations

from typing import Any, Callable

# Locked across tabs. A missing slot is omitted, not replaced with a spacer.
ACTION_SLOTS = ("preview", "score", "export", "optimize", "stop", "randomize")
VTK_HEIGHT_PX = 400
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
