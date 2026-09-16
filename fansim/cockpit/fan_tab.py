"""Fan cockpit tab (CFD design + Assess + Optimize + Library).

``setup_fan_tab`` is a thin coordinator: it builds a :class:`FanSession`, seeds reactive state,
and calls the per-domain binders (core / models / editor / viz / library / export / assess /
optimize / trials), each of which defines its closures and attaches the shared ones onto the
session. The UI renderer (:func:`render_fan_tab`) reads the resulting ``ctx.fan_*`` handlers.

Split out of a single 2700-line function during the §13.9 binder refactor.
"""

from __future__ import annotations

import logging

from fansim.catalog import build_catalog
from fansim.cockpit import (
    fan_assess,
    fan_core,
    fan_editor,
    fan_export,
    fan_library,
    fan_models,
    fan_optimize,
    fan_trials,
    fan_viz,
)
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_session import FanSession
from fansim.cockpit.fan_tab_ui import render_fan_tab  # re-export for app.py

__all__ = ["render_fan_tab", "setup_fan_tab"]

_log = logging.getLogger(__name__)


def setup_fan_tab(ctx: CockpitCtx) -> None:
    """Init Fan state + controllers (call before SinglePageLayout)."""
    session = FanSession(ctx)

    fan_core.apply_state_defaults(session)

    # Bind each domain: defines its closures and attaches the shared ones onto ``session``.
    # Cross-domain calls resolve through ``session`` at call time, so bind order is only about
    # having every service attached before the initial-population calls below run.
    fan_core.bind(session)
    fan_models.bind(session)
    fan_editor.bind(session)
    fan_viz.bind(session)
    fan_library.bind(session)
    fan_export.bind(session)
    fan_assess.bind(session)
    fan_optimize.bind(session)
    fan_trials.bind(session)

    # Initial population (order mirrors the original setup_fan_tab).
    try:
        build_catalog()
    except Exception as exc:  # noqa: BLE001
        _log.warning("skip catalog rebuild on Fan tab init: %s: %s", type(exc).__name__, exc)
    session.refresh_library()
    session._model_readout()
    session._hub_fit_readout()
    session._tip_fit_readout()
    session._depth_fit_readout()
    session.refresh_items()
    session._init_editor({})

    session.expose_to_ctx()
