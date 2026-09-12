"""Lazy PyVista plotter helpers for non-Fan cockpit tabs."""

from __future__ import annotations

import sys
from typing import Any

_RUNNING_TESTS = "pytest" in sys.modules


def make_white_plotter():
    """Construct an off-screen white Plotter with axes (or None under pytest)."""
    if _RUNNING_TESTS:
        return None
    import pyvista as pv

    pl = pv.Plotter()
    pl.background_color = "white"
    pl.add_axes()
    return pl


def ensure_plotter(ctx: Any, attr: str):
    """Return ``ctx.<attr>``, creating a white Plotter on first use."""
    pl = getattr(ctx, attr, None)
    if pl is None:
        pl = make_white_plotter()
        setattr(ctx, attr, pl)
    return pl
