"""Shared Fan-tab session bag for extracted binders (Assess / Optimize / viz / models)."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from typing import Any

from fansim.cockpit.context import CockpitCtx

# Public ctx.fan_* attrs expected by render_fan_tab (duck-typed).
_EXPOSE = (
    ("fan_select", "select"),
    ("fan_on_plotly_click", "on_plotly_click"),
    ("fan_load_stock_reference", "load_stock_reference"),
    ("fan_do_preview", "do_preview"),
    ("fan_on_assess", "on_assess"),
    ("fan_export_stl_current", "export_stl_current"),
    ("fan_on_optimize", "on_optimize_fan"),
    ("fan_cancel_optimize", "cancel_optimize"),
    ("fan_cancel_assess", "cancel_assess"),
    ("fan_on_sweep", "on_sweep"),
    ("fan_cancel_sweep", "cancel_sweep"),
    ("fan_on_fit_envelope", "on_fit_envelope"),
    ("fan_on_scale_to_hub", "on_scale_to_hub"),
    ("fan_randomize_geometry", "randomize_geometry"),
    ("fan_randomize_features", "randomize_features"),
    ("fan_select_library_design", "select_library_design"),
    ("fan_on_library_scale_to_hub", "on_library_scale_to_hub"),
    ("fan_load_model_into_form", "load_model_into_form"),
    ("fan_save_model", "save_model"),
    ("fan_delete_model", "delete_model"),
    ("fan_save_measurement", "save_measurement"),
    ("fan_hub_designs", "_hub_designs"),
    ("fan_active_spec", "active_spec"),
)


class FanSession:
    """Mutable bag shared by Fan binders; callables are attached during setup."""

    def __init__(self, ctx: CockpitCtx) -> None:
        self.ctx = ctx
        self.state = ctx.state
        self.ctrl = ctx.ctrl
        self.run_dir = ctx.run_dir
        self.runs_root = ctx.runs_root
        self.plotter = ctx.plotter
        self.spawn_busy_ticker = ctx.spawn_busy_ticker

        self.study_designs = ctx.study_designs or []
        self.user_designs = ctx.user_designs or []
        self.by_trial = ctx.by_trial or {}
        self.next_id = ctx.next_id or [9000]
        self.assess_dir = ctx.assess_dir or (self.run_dir / "cockpit_assess")
        self.study_name = getattr(ctx, "study_name", None)

        self.designs_lock = threading.Lock()
        self.assess_proc: list[Any] = [None]
        self.opt_proc: list[Any] = [None]
        self.airflow_gen = [0]
        self.airflow_lock = threading.Lock()
        self.sel_sig: list[Any] = [None]
        self.render_state = {
            "path": None,
            "color": "lightsteelblue",
            "glyph_cloud": None,
            "glyph_arrows": None,
        }
        self.preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"
        self.SWEEP_OPTIONS: list = []

    def expose_to_ctx(self) -> None:
        """Copy public handlers onto ``ctx`` for ``render_fan_tab``."""
        for ctx_name, attr in _EXPOSE:
            setattr(self.ctx, ctx_name, getattr(self, attr))
