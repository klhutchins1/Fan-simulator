"""Shared cockpit tab shell helpers."""

from __future__ import annotations

from fansim.cockpit.tab_shell import ACTION_SLOTS, action_slot_order


def test_action_slot_order_is_locked():
    assert action_slot_order() == (
        "preview",
        "score",
        "export",
        "optimize",
        "stop",
        "randomize",
    )
    assert ACTION_SLOTS[0] == "preview"
    assert ACTION_SLOTS[-1] == "randomize"
