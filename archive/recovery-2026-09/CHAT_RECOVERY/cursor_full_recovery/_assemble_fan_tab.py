"""Assemble slim fan_tab.py from original core ranges + new binders."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("fansim/cockpit")
SRC = (ROOT / "fan_tab.py").read_text(encoding="utf-8").splitlines()


def block(start: int, end: int, indent_strip: int = 0) -> list[str]:
    lines = SRC[start - 1 : end]
    if not indent_strip:
        return list(lines)
    out = []
    for line in lines:
        if line.startswith(" " * indent_strip):
            out.append(line[indent_strip:])
        else:
            out.append(line)
    return out


header = '''\
"""Fan cockpit tab (CFD design + Assess + Optimize + Library).

Coordinator after fan-tab extract: core editor/library/measurement live here;
Assess / Optimize / viz / models bind onto FanSession.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import json
import logging
import queue
import random
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_log = logging.getLogger(__name__)

from fansim.catalog import build_catalog, get_entry, load_catalog, results_for_hub
from fansim.cfd.glyphs import ensure_velocity_glyphs, make_glyph_arrows
from fansim.cfd.midplane import ensure_midplane_artifacts
from fansim.cfd.runner import kill_cfd_containers
from fansim.cockpit.busy import (
    busy_caption,
    cfd_stage_hint,
    format_elapsed,
)
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.cockpit.fan_assess import bind_fan_assess
from fansim.cockpit.fan_copy import CONTROL_DESC, OPT_SEARCH_HELP
from fansim.cockpit.fan_helpers import (
    _blade_max_dia,
    _blade_z_extent,
    _depth_drivers,
    _has_real_cfm,
    append_user_designs,
    upsert_by_trial,
)
from fansim.cockpit.fan_models import bind_fan_models
from fansim.cockpit.fan_optimize import bind_fan_optimize
from fansim.cockpit.fan_session import FanSession
from fansim.cockpit.fan_viz import bind_fan_viz
from fansim.cockpit.fan_widgets import _help_switch, _opt_section, _slider
from fansim.cockpit.figures import (
    filter_fitting_designs,
    reject_hint,
    scatter_figure,
)
from fansim.cockpit.library_view import apply_library_recipe, library_list_items
from fansim.cockpit.placement import (
    fit_envelope,
    nominal_fits_spec,
    prepare_export_flat,
    preview_changes,
    scale_to_hub,
)
from fansim.cockpit.score_caption import score_caption, stamp_score_extra
from fansim.fan_spec import (
    MotorMount,
    check_build,
    delete_user_fan_model,
    estimate_weight_g,
    fan_spec_names,
    get_fan_spec,
    is_builtin,
    load_fan_models_dir,
    mount_min_hub_radius,
    over_spec_flags,
    published_scatter_point,
    save_user_fan_model,
)
from fansim.geometry.blade import normalize_shroud_thick_mm
from fansim.geometry.features import Features
from fansim.manufacturability import check_printability
from fansim.manufacturability.fdm_rules import preview_unprintable_note
from fansim.optimize.cli_argv import (
    OPT_TRIAL_OFFSET,
    merge_opt_designs,
    opt_out_path,
    optimization_argv,
)
from fansim.optimize.isolated_eval import cfd_eval_timeout, evaluate_candidate_isolated
from fansim.optimize.presets import assess_load, assess_preset_items
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
from validation.ingest import MeasuredPoint
from validation.store import make_design_id, record_measurement, sim_vs_real

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    plotter_ui = None  # type: ignore[assignment]
    asynchronous = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from pyvista.trame.ui import plotter_ui
    from trame.app import asynchronous
    from trame.widgets import html
    from trame.widgets import plotly as plotly_widgets
    from trame.widgets import vuetify3 as v3


def setup_fan_tab(ctx: CockpitCtx) -> None:
    """Init Fan state + controllers (call before SinglePageLayout)."""
    s = FanSession(ctx)
    state, ctrl = s.state, s.ctrl
    run_dir = s.run_dir
    runs_root = s.runs_root
    plotter = s.plotter
    spawn_busy_ticker = s.spawn_busy_ticker
    study_designs = s.study_designs
    user_designs = s.user_designs
    by_trial = s.by_trial
    next_id = s.next_id
    assess_dir = s.assess_dir
    study_name = s.study_name
    designs_lock = s.designs_lock
    preview_stl = s.preview_stl
    sel_sig = s.sel_sig
    render_state = s.render_state
    airflow_gen = s.airflow_gen
    airflow_lock = s.airflow_lock

'''

# Core helpers: lines 351-655 (nested defs + state through reload_models)
# Original had designs_lock create at 349 - now on session
core1 = block(351, 655)

# Skip models 657-761; keep from preview_stl line? 761 is preview_stl assign - skip, use session
# 763 starts _thin
core2 = block(763, 1175)

# Keep _feat_dict through spec_status (1448-1690), skip SWEEP/assess
core3 = block(1448, 1690)

# After core3: bind extractors, then select/meas/stock (2386-2602), then expose via session

bind_call = '''
    # Attach extracted binders (callables close over session aliases).
    def _attach_core_callables():
        s.active_spec = active_spec
        s.refresh_items = refresh_items
        s.refresh_figure = refresh_figure
        s.refresh_library = refresh_library
        s.reload_models = reload_models
        s.edit_flat = edit_flat
        s.edit_features = edit_features
        s.build_edit_params = build_edit_params
        s._init_editor = _init_editor
        s._feat_dict = _feat_dict
        s._set_baseline = _set_baseline
        s._recompute_stale = _recompute_stale
        s._model_readout = _model_readout
        s._hub_fit_readout = _hub_fit_readout
        s._tip_fit_readout = _tip_fit_readout
        s._depth_fit_readout = _depth_fit_readout
        s.spec_status = spec_status
        s._hub_designs = _hub_designs
        s._resync_study_from_disk = _resync_study_from_disk
        s._label = _label

    _attach_core_callables()
    bind_fan_models(s)
    bind_fan_viz(s)
    bind_fan_assess(s)
    bind_fan_optimize(s)

    # Local aliases for binders attached above (select / stock need them).
    do_preview = s.do_preview
    _draw = s._draw
    _apply_render = s._apply_render
    _clear_glyphs = s._clear_glyphs
    _rebuild_glyph_arrows = s._rebuild_glyph_arrows
    _schedule_airflow = s._schedule_airflow
    _clear_airflow = s._clear_airflow
    _apply_airflow_field = s._apply_airflow_field
    _build_preview_stl = s._build_preview_stl
    on_assess = s.on_assess
    on_sweep = s.on_sweep
    cancel_assess = s.cancel_assess
    cancel_sweep = s.cancel_sweep
    on_optimize_fan = s.on_optimize_fan
    cancel_optimize = s.cancel_optimize
    load_model_into_form = s.load_model_into_form
    save_model = s.save_model
    delete_model = s.delete_model

'''

core4 = block(2386, 2602)

expose = '''
    s.select = select
    s.on_plotly_click = on_plotly_click
    s.load_stock_reference = load_stock_reference
    s.export_stl_current = export_stl_current
    s.on_fit_envelope = on_fit_envelope
    s.on_scale_to_hub = on_scale_to_hub
    s.randomize_geometry = randomize_geometry
    s.randomize_features = randomize_features
    s.select_library_design = select_library_design
    s.on_library_scale_to_hub = on_library_scale_to_hub
    s.save_measurement = save_measurement
    s.expose_to_ctx()


'''

# render_fan_tab from original 2630-end
render = "\n".join(block(2630, len(SRC))) + "\n"

out_lines = [header]
out_lines.extend(core1)
out_lines.append("")
out_lines.extend(core2)
out_lines.append("")
out_lines.extend(core3)
out_lines.append(bind_call)
out_lines.extend(core4)
out_lines.append(expose)
out_lines.append(render)

text = "\n".join(out_lines)
# Fix: core1 still references designs_lock = threading.Lock() removed - and airflow_gen create
# Original 505-506 created airflow_gen - still in core1 state init section
# Original 349 designs_lock - not in core1 (starts 351)
# preview_stl at 761 was between models and _thin - we skipped it; session has it
# But core2 might still reference creating nothing

# Remove duplicate airflow_gen/lock creation if present in core1 - session owns them
fixed = []
skip_airflow = False
for line in text.splitlines():
    if "airflow_gen = [0]" in line and "s.airflow" not in line:
        continue
    if "airflow_lock = threading.Lock()" in line and "s.airflow" not in line:
        continue
    fixed.append(line)

Path("fansim/cockpit/fan_tab.py").write_text("\n".join(fixed) + "\n", encoding="utf-8", newline="\n")
print("fan_tab lines", len(fixed))
