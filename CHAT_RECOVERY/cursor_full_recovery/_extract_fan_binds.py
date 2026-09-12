"""One-shot: emit fan_models / fan_viz / fan_assess / fan_optimize from fan_tab.py ranges."""
from __future__ import annotations

from pathlib import Path

ROOT = Path("fansim/cockpit")
SRC = (ROOT / "fan_tab.py").read_text(encoding="utf-8").splitlines()


def dedent_block(start: int, end: int) -> str:
    """1-based inclusive line range; strip one 4-space indent."""
    out = []
    for line in SRC[start - 1 : end]:
        if line.startswith("    "):
            out.append(line[4:])
        elif line.strip() == "":
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


HEADER = '''\
"""{doc}"""
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
from fansim.cockpit.busy import busy_caption, cfd_stage_hint, format_elapsed
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.cockpit.fan_helpers import (
    _blade_max_dia,
    _blade_z_extent,
    _depth_drivers,
    _has_real_cfm,
    append_user_designs,
    upsert_by_trial,
)
from fansim.cockpit.fan_session import FanSession
from fansim.cockpit.figures import filter_fitting_designs, reject_hint, scatter_figure
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
    asynchronous = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from trame.app import asynchronous


'''

# Aliases: names looked up on session at call time via thin wrappers / locals
COMMON_ALIAS = """
    state = s.state
    ctrl = s.ctrl
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
    assess_proc = s.assess_proc
    opt_proc = s.opt_proc
    airflow_gen = s.airflow_gen
    airflow_lock = s.airflow_lock
    sel_sig = s.sel_sig
    render_state = s.render_state
    preview_stl = s.preview_stl

    def active_spec():
        return s.active_spec()

    def refresh_items():
        return s.refresh_items()

    def refresh_figure():
        return s.refresh_figure()

    def refresh_library():
        return s.refresh_library()

    def reload_models():
        return s.reload_models()

    def edit_flat():
        return s.edit_flat()

    def edit_features():
        return s.edit_features()

    def build_edit_params():
        return s.build_edit_params()

    def _init_editor(p, feat=None):
        return s._init_editor(p, feat)

    def _feat_dict():
        return s._feat_dict()

    def _set_baseline():
        return s._set_baseline()

    def _recompute_stale(**kw):
        return s._recompute_stale(**kw)

    def _model_readout():
        return s._model_readout()

    def _hub_fit_readout():
        return s._hub_fit_readout()

    def _tip_fit_readout():
        return s._tip_fit_readout()

    def _depth_fit_readout():
        return s._depth_fit_readout()

    def spec_status(stl_path, params, flat=None):
        return s.spec_status(stl_path, params, flat)

    def select(trial):
        return s.select(trial)

    def do_preview():
        return s.do_preview()

    def _draw(path, color):
        return s._draw(path, color)

    def _apply_render(reset=False):
        return s._apply_render(reset=reset)

    def _resync_study_from_disk():
        return s._resync_study_from_disk()

    def _hub_designs():
        return s._hub_designs()
"""


def emit(path: str, doc: str, bind_name: str, body: str, expose: list[str], extra_alias: str = "") -> None:
    text = HEADER.format(doc=doc)
    text += f"def {bind_name}(s: FanSession) -> None:\n"
    text += '    """Attach handlers onto FanSession."""\n'
    # indent COMMON_ALIAS and body
    for line in (COMMON_ALIAS + extra_alias).splitlines():
        text += line + "\n"
    for line in body.splitlines():
        text += ("    " + line if line else "") + "\n"
    text += "\n"
    for name in expose:
        text += f"    s.{name} = {name}\n"
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")
    print("wrote", path, "lines", text.count(chr(10)) + 1)


# --- models: 657-761 (manager state + load/save/delete/_on_model) ---
# Include state init for fm_* 
models_body = dedent_block(657, 761)
emit(
    "fan_models.py",
    "Fan-model manager (CRUD + fan_model change handler).",
    "bind_fan_models",
    models_body,
    ["load_model_into_form", "save_model", "delete_model"],
)

# --- viz: 1177-1413 preview/glyphs + 2275-2384 airflow (before select) ---
viz_a = dedent_block(1177, 1413)
viz_b = dedent_block(2275, 2384)
# Remove render_state = {...} from viz_a since session owns it — keep assignment overwrite OK
# Actually viz_a redefines render_state locally - need to skip those lines
viz_a_lines = []
skip = False
for line in viz_a.splitlines():
    if line.startswith("render_state = {"):
        skip = True
        continue
    if skip:
        if line.strip() == "}":
            skip = False
        continue
    viz_a_lines.append(line)
viz_body = "\n".join(viz_a_lines) + "\n\n" + viz_b
emit(
    "fan_viz.py",
    "Fan preview STL, glyphs, plotter draw, and airflow midplane.",
    "bind_fan_viz",
    viz_body,
    [
        "do_preview",
        "_build_preview_stl",
        "_rebuild_glyph_arrows",
        "_clear_glyphs",
        "_apply_render",
        "_draw",
        "_png_data_uri",
        "_apply_airflow_field",
        "_clear_airflow",
        "_schedule_airflow",
    ],
)

# --- assess: SWEEP_OPTIONS (1415-1446) + CFD from assess_proc (1691-2058) ---
# Keep _feat_dict / stale / library / spec_status in fan_tab core.
assess_sweep = dedent_block(1415, 1446)
assess_cfd = dedent_block(1691, 2058)
assess_cfd_lines = []
for line in assess_cfd.splitlines():
    if line.strip() == "assess_proc = [None]":
        continue
    if line.strip() == "opt_proc = [None]":
        break
    assess_cfd_lines.append(line)
assess_body = assess_sweep + "\n" + "\n".join(assess_cfd_lines)
assess_body += "\n\ns.SWEEP_OPTIONS = SWEEP_OPTIONS\n"
emit(
    "fan_assess.py",
    "Fan Assess / Sweep CFD controllers and cancel helpers.",
    "bind_fan_assess",
    assess_body,
    ["on_assess", "on_sweep", "cancel_assess", "cancel_sweep"],
)

# --- optimize: 2060-2273 ---
opt_body_lines = []
for line in dedent_block(2060, 2273).splitlines():
    if line.strip() == "opt_proc = [None]":
        continue
    opt_body_lines.append(line)
emit(
    "fan_optimize.py",
    "Fan Optimize subprocess controller and cancel helper.",
    "bind_fan_optimize",
    "\n".join(opt_body_lines),
    ["on_optimize_fan", "cancel_optimize"],
)

print("done")
