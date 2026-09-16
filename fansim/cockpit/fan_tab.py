"""Fan cockpit tab (CFD design + Assess + Optimize + Library).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
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
from fansim.cockpit.fan_helpers import (
    _blade_max_dia,
    _blade_z_extent,
    _depth_drivers,
    _has_real_cfm,
    append_user_designs,
    upsert_by_trial,
)
from fansim.cockpit.figures import (
    filter_fitting_designs,
    reject_hint,
    scatter_figure,
)
from fansim.cockpit.library_view import apply_library_recipe, library_list_items
from fansim.cockpit.placement import (
    fit_envelope,
    frame_gap_note,
    impeller_z_extent,
    nominal_fits_spec,
    prepare_export_flat,
    preview_changes,
    scale_to_hub,
)
from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
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
from fansim.geometry.blade import normalize_shroud_thick_mm, uniform_thickness_tc
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


from fansim.cockpit.fan_tab_ui import render_fan_tab  # re-export for app.py


def setup_fan_tab(ctx: CockpitCtx) -> None:
    """Init Fan state + controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    run_dir = ctx.run_dir
    runs_root = ctx.runs_root
    plotter = ctx.plotter
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # Fan session state prepared by the shell (build_server) before setup_fan_tab().
    study_designs = ctx.study_designs or []  # type: ignore[attr-defined]
    user_designs = ctx.user_designs or []  # type: ignore[attr-defined]
    by_trial = ctx.by_trial or {}  # type: ignore[attr-defined]
    next_id = ctx.next_id or [9000]  # type: ignore[attr-defined]
    assess_dir = ctx.assess_dir or (run_dir / "cockpit_assess")  # type: ignore[attr-defined]
    study_name = getattr(ctx, "study_name", None)
    # Protects user_designs / by_trial against Optimize poll_merge (executor) vs Assess UI (§9.11).
    designs_lock = threading.Lock()

    def _label(d):
        if d.is_pareto:
            tag = "  ★"
        elif d.trial >= 9000:  # user-assessed; note which run it was assessed under
            run = d.extra.get("source_run", "")
            tag = f"  ◆ {run}" if run else "  ◆"
        else:
            tag = ""
        stale = "  ⧗" if d.extra.get("cfd_stale") else ""
        return {"title": f"#{d.trial}{tag}{stale}", "value": d.trial}

    def _design_id(d: Design) -> str | None:
        """Catalog design_id (<run>_t<trial>) for a loaded Design, if we can infer it."""
        run = d.extra.get("source_run") or run_dir.name
        trial = d.extra.get("orig_trial", d.trial) if d.trial >= 9000 else d.trial
        try:
            return make_design_id(run, int(trial))
        except Exception:  # noqa: BLE001
            return None

    def _purge_sentinel_user_designs() -> int:
        """Drop infeasible Optimize merges (cfm=-1e6) that stretch the scatter axes."""
        keep: list[Design] = []
        removed = 0
        with designs_lock:
            for d in user_designs:
                if d.extra.get("source") == "cockpit_opt" and not _has_real_cfm(d):
                    by_trial.pop(int(d.trial), None)
                    removed += 1
                    continue
                keep.append(d)
            if removed:
                user_designs[:] = keep
        return removed

    def active_spec():
        """The selected fan model with the current leeway margins applied (nominal untouched)."""
        return dataclasses.replace(
            get_fan_spec(state.fan_model),
            leeway_tip_dia_mm=float(state.lee_tip),
            leeway_depth_mm=float(state.lee_depth),
            leeway_weight_g=float(state.lee_weight),
            over_voltage_v=float(state.lee_overvolt),
        )

    def _hub_designs():
        """Designs relevant to the selected hub (catalog says fits, or nominally fits by params)."""
        _purge_sentinel_user_designs()
        allowed = {e.design_id for e in results_for_hub(load_catalog(), state.fan_model)}
        spec = active_spec()
        out = [d for d in study_designs if _has_real_cfm(d)]
        seen = {id(d) for d in out}
        opened = run_dir.name
        with designs_lock:
            users = list(user_designs)
        for d in users:
            if id(d) in seen:
                continue
            if not _has_real_cfm(d) and not d.extra.get("cfd_stale"):
                continue
            src = str(d.extra.get("source") or "")
            src_run = str(d.extra.get("source_run") or "")
            from_opened = src_run == opened or (
                d.stl_path is not None and opened in Path(d.stl_path).parts
            )
            if src == "cockpit_opt" or from_opened:
                out.append(d)
                seen.add(id(d))
                continue
            did = _design_id(d)
            if (did in allowed) or nominal_fits_spec(d.params, spec):
                out.append(d)
                seen.add(id(d))
        return out

    def _resync_study_from_disk() -> int:
        """Reload Optuna trials for the opened run (after Continue-the-opened-run Optimize)."""
        fresh = feasible_designs(load_designs(run_dir, study_name))
        study_designs.clear()
        study_designs.extend(fresh)
        with designs_lock:
            keep_users = {d.trial: d for d in user_designs}
            by_trial.clear()
            by_trial.update({d.trial: d for d in study_designs})
            by_trial.update(keep_users)
        return len(study_designs)

    def refresh_items():
        hub_all = _hub_designs()
        scored = [d for d in hub_all if not d.extra.get("cfd_stale")]
        stale = [d for d in hub_all if d.extra.get("cfd_stale")]
        scored = sorted(scored, key=lambda d: -(d.objectives.get("cfm_load") or -1e9))
        stale = sorted(stale, key=lambda d: d.trial)
        items = [_label(d) for d in scored]
        if stale:
            items.append({"title": "— Unscored on this hub —", "value": None, "disabled": True})
            items += [_label(d) for d in stale]
        state.trial_items = items

    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.export_msg = ""
    state.export_busy = False
    state.export_fit_hub = True
    state.export_fit_frame = True
    state.preview_motor_cup = True
    state.assess_preset = "case"
    state.assess_preset_items = assess_preset_items()
    state.assess_refine_op = False
    state.assess_wall_ks = False
    from fansim.manufacturability.materials import MATERIALS, DEFAULT_MATERIAL

    state.assess_material = DEFAULT_MATERIAL
    state.assess_material_items = [
        {"title": f"{k} — {MATERIALS[k].note}" if MATERIALS[k].note else k, "value": k}
        for k in MATERIALS
        if MATERIALS[k].blade_suitable
    ]
    state.opt_trials = 8
    state.opt_shroud = False
    state.opt_bem = False
    state.opt_gp = False
    state.opt_gp_boost = False
    state.opt_gp_nn = False
    state.opt_resume = False
    state.opt_stator = False
    state.opt_stator_stack = False
    state.opt_sickle = False
    state.opt_stepped = False
    state.opt_notched = False
    state.opt_search_rpm = False
    state.opt_rpm_min = 450.0
    state.opt_rpm_max = 2000.0
    from fansim.optimize.pwm_table import pwm_caption

    state.opt_pwm_caption = pwm_caption()
    state.opt_msg = ""
    state.opt_running = False
    state.opt_cancel = False
    state.preview_busy = False
    state.assess_msg = ""
    state.assess_busy = False
    state.assess_cancel = False
    state.edited_stale = False
    state.stale_msg = ""
    state.highlight_spec = True
    state.show_envelope = False
    state.fan_subtab = "design"
    state.airflow_img_uri = ""
    state.airflow_caption = "Select a scored design to load duct airflow (midplane)."
    state.airflow_field = "U"
    state.airflow_busy = False
    state._airflow_u_uri = ""
    state._airflow_p_uri = ""
    airflow_gen = [0]
    airflow_lock = threading.Lock()
    state.show_glyphs = True
    state.glyph_mode = "on"
    state.glyph_density = "medium"
    state.glyph_density_items = ["coarse", "medium", "fine"]
    state.glyph_scale = 2.0
    state.glyph_caption = "Select a scored design for 3-D velocity arrows."
    state.hub_profiles = ["cylinder", "cone", "dome"]
    state.section_family_items = [
        {"title": "NACA airfoil", "value": "naca"},
        {"title": "Rounded plate (bullnose)", "value": "plate"},
    ]
    state.thick_mode_items = [
        {"title": "Uniform wall (mm through blade)", "value": "uniform"},
        {"title": "Tapered (t/c by span)", "value": "tapered"},
    ]
    state.thick_wall_readout = "Wall ≈ — mm (set Thickness span / Blade thickness)"
    state.declutter = False
    state.fits_only = True
    state.show_stock = True
    state.meas_cfm = None
    state.meas_static = None
    state.meas_noise = None
    state.meas_rpm = None
    state.meas_material = ""
    state.meas_print_type = ""
    state.meas_weight = None
    state.meas_print_types = ["FDM", "SLA / resin", "SLS", "other"]
    state.meas_instrument = ""
    state.meas_notes = ""
    state.meas_msg = "Select a design, print + test it, then record what you measured."
    state.library_items = []
    state.library_sel = None
    state.library_info = ""
    state.library_parent_id = ""
    state.library_place_op = ""
    state.library_leftover = ""

    state.fan_model = "a12x25"
    state.fan_models = fan_spec_names()
    state.lee_tip = 0.0
    state.lee_depth = 0.0
    state.lee_overvolt = 0.0
    state.lee_weight = 0.0

    def refresh_library():
        spec = active_spec()
        items = library_list_items(load_catalog(), spec)
        state.library_items = items
        n = sum(1 for it in items if it.get("role") == "row")
        state.library_info = (
            f"{n} recipe(s) — click Fits this hub and draws it. " "Scale shrinks a huge recipe first."
        )

    try:
        build_catalog()
    except Exception as exc:  # noqa: BLE001
        _log.warning("skip catalog rebuild on Fan tab init: %s: %s", type(exc).__name__, exc)
    refresh_library()

    def _model_readout():
        s = get_fan_spec(state.fan_model)
        refs = (
            f" Published {s.ref_cfm:.0f} CFM / {s.ref_static_pa:.0f} Pa / {s.ref_noise_dba:.0f} dBA."
            if s.ref_cfm is not None
            else " (no published reference — exploratory model)."
        )
        tag = " [built-in ref, read-only]" if is_builtin(state.fan_model) else " [user model]"
        wt = f"≤{s.max_weight_g:.0f} g." if s.max_weight_g else ""
        state.model_info = (
            f"{s.name}{tag}: tip ≤{s.tip_dia_mm[1]:.0f} mm, depth ≤{s.depth_mm[1]:.0f} mm, "
            f"hub {s.hub_dia_mm[0]:.0f}-{s.hub_dia_mm[1]:.0f} mm, "
            f"{s.max_shaft_power_w:.2f} W shaft ({s.voltage_v:.0f} V×{s.max_current_a:.2f} A), "
            f"{wt}{refs}"
        )

    def _hub_fit_readout():
        s = get_fan_spec(state.fan_model)
        need = mount_min_hub_radius(s)
        if need is None:
            state.hub_fit_info = f"{s.name}: no motor mount defined — hub size unconstrained."
            return
        cav = s.motor_mount.cavity_dia_mm
        cur = state.e_hub_radius
        if cur is None:
            state.hub_fit_info = f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm."
            return
        cur = float(cur)
        state.hub_fit_info = (
            f"Motor hub {cav:.1f} mm → this hub needs radius ≥ {need:.1f} mm. "
            + (
                f"Current {cur:.1f} mm ✓ fits — cup will carve."
                if cur >= need
                else f"Current {cur:.1f} mm ✗ TOO SMALL, won't fit (raise Hub radius)."
            )
        )

    def _tip_fit_readout():
        s = get_fan_spec(state.fan_model)
        max_dia = s.tip_dia_mm[1]
        floor = float(OPTIMIZER_TIP_GAP_MM)
        if state.e_tip_radius is None:
            state.tip_fit_info = f"Frame ≤ {max_dia:.0f} mm dia (need ≥{floor:.1f} mm tip gap)."
            return
        try:
            dia = _blade_max_dia(build_edit_params())
        except Exception:  # noqa: BLE001
            dia = 2.0 * float(state.e_tip_radius)
        gap = max_dia / 2.0 - dia / 2.0
        note = frame_gap_note(dia, s)
        if note:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"(gap {gap:.2f} mm) ✗ {note} — use Fit envelope."
            )
        elif dia > max_dia:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"✗ over by {dia - max_dia:.1f} mm — use Fit envelope."
            )
        else:
            state.tip_fit_info = (
                f"Frame ≤ {max_dia:.0f} mm → built tip dia {dia:.1f} mm "
                f"(gap {gap:.2f} mm ≥ {floor:.1f} mm) ✓ fits."
            )

    def _depth_fit_readout():
        s = get_fan_spec(state.fan_model)
        max_d = s.depth_mm[1]
        if state.e_sweep_tip is None:
            state.depth_fit_info = f"Frame ≤ {max_d:.0f} mm deep."
            return
        try:
            d = impeller_z_extent(build_edit_params())
        except Exception:  # noqa: BLE001
            state.depth_fit_info = ""
            return
        state.depth_fit_info = (
            f"Frame ≤ {max_d:.0f} mm deep → impeller {d:.1f} mm "
            + (
                "✓ fits."
                if d <= max_d
                else f"✗ over by {d-max_d:.1f} mm — use Fit envelope, or add Extra-depth leeway."
            )
        )

    state.hub_fit_info = ""
    state.tip_fit_info = ""
    state.depth_fit_info = ""
    _model_readout()
    _hub_fit_readout()
    _tip_fit_readout()
    _depth_fit_readout()

    def reload_models():
        load_fan_models_dir()
        state.fan_models = fan_spec_names()
        _model_readout()
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        refresh_library()
        refresh_items()
        refresh_figure()
        state.flush()

    # ---- fan-model MANAGER -----------------------------------------------------------------
    state.fm_key = ""
    state.fm_tip_max = 110.0
    state.fm_hub_min = 30.0
    state.fm_hub_max = 60.0
    state.fm_depth_max = 25.0
    state.fm_rpm = 2000.0
    state.fm_cav_dia = 37.25
    state.fm_cav_depth = 13.0
    state.fm_hub_h = 15.0
    state.fm_msg = ""
    state.model_is_builtin = is_builtin(state.fan_model)

    def load_model_into_form(**_):
        s = get_fan_spec(state.fan_model)
        state.fm_key = "" if is_builtin(state.fan_model) else state.fan_model
        state.fm_tip_max = float(s.tip_dia_mm[1])
        state.fm_hub_min = float(s.hub_dia_mm[0])
        state.fm_hub_max = float(s.hub_dia_mm[1])
        state.fm_depth_max = float(s.depth_mm[1])
        state.fm_rpm = float(s.rpm)
        m = s.motor_mount
        state.fm_cav_dia = float(m.cavity_dia_mm) if m else 0.0
        state.fm_cav_depth = float(m.cavity_depth_mm) if m else 0.0
        state.fm_hub_h = float(getattr(m, "min_hub_height_mm", 0.0)) if m else 0.0
        state.fm_msg = (
            "Loaded a built-in — Save under a NEW name to make an editable copy."
            if is_builtin(state.fan_model)
            else f"Loaded user model '{state.fan_model}' — edit + Save."
        )
        state.flush()

    def save_model():
        key = (state.fm_key or "").strip().lower().replace(" ", "_")
        if not key:
            state.fm_msg = "⚠ Enter a model name first."
            state.flush()
            return
        base = get_fan_spec(state.fan_model)
        mount = None
        if float(state.fm_cav_dia) > 0:
            mount = MotorMount(
                cavity_dia_mm=float(state.fm_cav_dia),
                cavity_depth_mm=float(state.fm_cav_depth),
                rear_bore_dia_mm=(base.motor_mount.rear_bore_dia_mm if base.motor_mount else 0.0),
                shaft_dia_mm=(base.motor_mount.shaft_dia_mm if base.motor_mount else 0.0),
                min_hub_height_mm=float(state.fm_hub_h),
                grip_count=int(getattr(base.motor_mount, "grip_count", 0) or 0) if base.motor_mount else 0,
                grip_dia_mm=float(getattr(base.motor_mount, "grip_dia_mm", 2.4) or 2.4) if base.motor_mount else 2.4,
                grip_clearance_mm=float(getattr(base.motor_mount, "grip_clearance_mm", 0.35) or 0.35) if base.motor_mount else 0.35,
                grip_protrude_mm=float(getattr(base.motor_mount, "grip_protrude_mm", 0.7) or 0.7) if base.motor_mount else 0.7,
            )
        spec = dataclasses.replace(
            base,
            name=key.replace("_", " ").title(),
            tip_dia_mm=(base.tip_dia_mm[0], float(state.fm_tip_max)),
            hub_dia_mm=(float(state.fm_hub_min), float(state.fm_hub_max)),
            depth_mm=(base.depth_mm[0], float(state.fm_depth_max)),
            rpm=float(state.fm_rpm),
            motor_mount=mount,
            leeway_tip_dia_mm=0.0,
            leeway_depth_mm=0.0,
            leeway_weight_g=0.0,
            over_voltage_v=0.0,
        )
        try:
            path = save_user_fan_model(key, spec)
        except Exception as exc:  # noqa: BLE001
            state.fm_msg = f"⚠ Save failed: {exc}"
            state.flush()
            return
        state.fan_models = fan_spec_names()
        state.fan_model = key
        state.fm_msg = f"✓ Saved user model '{key}' → {path}"
        state.flush()

    def delete_model():
        key = state.fan_model
        try:
            ok = delete_user_fan_model(key)
        except Exception as exc:  # noqa: BLE001
            state.fm_msg = f"⚠ {exc}"
            state.flush()
            return
        state.fan_models = fan_spec_names()
        state.fan_model = "a12x25"
        state.fm_msg = f"{'✓ Deleted' if ok else '⚠ Not found:'} '{key}'."
        state.flush()

    @state.change("fan_model")
    def _on_model(**_):
        _model_readout()
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        state.model_is_builtin = is_builtin(state.fan_model)
        refresh_library()
        refresh_items()
        refresh_figure()
        state.flush()

    state.sweep_param = "stagger mid"
    state.sweep_steps = 3
    state.sweep_active = False
    state.sweep_cancel = False
    state.sweep_progress = 0
    refresh_items()

    preview_stl = Path(tempfile.gettempdir()) / "fansim_cockpit_preview.stl"

    def _thin(designs, cell: float = 2.5):
        best = {}
        for d in designs:
            key = (round(d.objectives["cfm_free"] / cell), round(d.objectives["cfm_load"] / cell))
            cur = best.get(key)
            rank = (d.is_pareto, d.objectives.get("efficiency", 0))
            if cur is None or rank > (cur.is_pareto, cur.objectives.get("efficiency", 0)):
                best[key] = d
        return list(best.values())

    def refresh_figure():
        hub_all = _hub_designs()
        scored = [d for d in hub_all if not d.extra.get("cfd_stale")]
        if state.fits_only:
            scored = filter_fitting_designs(scored, active_spec())
        sd = [d for d in scored if d in study_designs]
        with designs_lock:
            users_snap = list(user_designs)
        ud = [d for d in scored if d in users_snap]
        if state.declutter:
            sd, ud = _thin(sd), _thin(list(ud))
        load_pa, _ = assess_load(str(state.assess_preset or "case"))
        stock = published_scatter_point(active_spec(), load_pa) if state.show_stock else None
        fig = scatter_figure(sd, ud, stock_ref=stock)
        if hasattr(ctrl, "figure_update"):
            ctrl.figure_update(fig)

    @state.change("declutter", "fits_only", "show_stock", "assess_preset")
    def _on_plot_filter(**_):
        refresh_figure()

    def _init_editor(p: dict, feat: Features | None = None):
        feat = feat or Features()
        state.e_n_blades = int(p.get("n_blades", 7))
        state.e_stagger_root = float(p.get("stagger_root", 26.0))
        state.e_stagger_mid = float(p.get("stagger_mid", 26.0))
        state.e_stagger_tip = float(p.get("stagger_tip", 22.0))
        state.e_chord_root = float(p.get("chord_root", 34.0))
        state.e_chord_mid = float(p.get("chord_mid", 44.0))
        state.e_chord_tip = float(p.get("chord_tip", 38.0))
        _cam = float(p.get("max_camber", 0.05))
        state.e_camber_root = float(p.get("camber_root", _cam))
        state.e_camber_mid = float(p.get("camber_mid", _cam))
        state.e_camber_tip = float(p.get("camber_tip", _cam))
        state.e_camber = state.e_camber_mid
        state.e_sweep_mid = float(p.get("sweep_mid", 3.0))
        state.e_sweep_tip = float(p.get("sweep_tip", 5.0))
        state.e_lean_mid = float(p.get("lean_mid", 14.0))
        state.e_lean_tip = float(p.get("lean_tip", 26.0))
        state.e_le_mid = float(p.get("le_sweep_mid", 0.0))
        state.e_le_tip = float(p.get("le_sweep_tip", 0.0))
        _le_skew_mid = float(p.get("le_skew_mid", 0.0) or 0.0)
        _le_skew_tip = float(p.get("le_skew_tip", 0.0) or 0.0)
        _sickle = float(p.get("sickle_mm", 0.0) or 0.0)
        if _le_skew_mid == 0.0 and _le_skew_tip == 0.0 and _sickle > 0.0:
            _le_skew_tip = _sickle
            _le_skew_mid = 0.40 * _sickle
        state.e_le_skew_mid = _le_skew_mid
        state.e_le_skew_tip = _le_skew_tip
        state.e_skew_mid = float(p.get("skew_mid", 0.0))
        state.e_skew_tip = float(p.get("skew_tip", 0.0))
        state.e_smooth_span = (
            str(p.get("span_interp", "linear") or "linear").lower() == "pchip"
        )
        state.e_winglet_span = float(p.get("winglet_span", 0.85))
        state.e_winglet_sweep = float(p.get("winglet_sweep", 0.0))
        state.e_winglet_lean = float(p.get("winglet_lean", 0.0))
        state.e_shroud_thick = normalize_shroud_thick_mm(float(p.get("shroud_thick_mm", 0.0)))
        state.e_shroud_height = min(max(float(p.get("shroud_height_frac", 1.0)), 0.0), 1.0)
        state.e_tip_round = float(p.get("tip_round", 0.0))
        state.e_tip_start = float(p.get("tip_round_start", 0.80))
        state.e_tip_notched = bool(
            int(p.get("tip_notch_count", 0) or 0) > 0
            or p.get("notched_tips")
            or float(p.get("tip_notch_depth_mm", 0.0) or 0.0) > 0.0
        )
        state.e_tip_notch_depth = float(
            p.get("tip_notch_depth_mm", 1.5) or 1.5
        ) if state.e_tip_notched else 1.5
        _ct = p.get("cylindrical_tip", True)
        if isinstance(_ct, str):
            state.e_cylindrical_tip = _ct.strip().lower() not in (
                "0",
                "false",
                "no",
                "off",
                "",
            )
        else:
            state.e_cylindrical_tip = bool(_ct) if _ct is not None else True
        state.e_hub_radius = float(p.get("hub_radius", 21.5))
        state.e_tip_radius = float(p.get("tip_radius", 56.5))
        state.e_hub_height = float(p.get("hub_height", 0.0))
        state.e_blade_hub_z = float(p.get("blade_hub_z", p.get("blade_hub_z_mm", 0.0)) or 0.0)
        state.e_hub_profile = str(p.get("hub_profile", "cylinder"))
        state.e_hub_nose = float(p.get("hub_nose", 0.0))
        state.e_thick_root = float(p.get("thickness_root", 0.10))
        state.e_thick_mid = float(p.get("thickness_mid", 0.08))
        state.e_thick_tip = float(p.get("thickness_tip", 0.06))
        cr = float(p.get("chord_root", state.e_chord_root or 34.0))
        cm = float(p.get("chord_mid", state.e_chord_mid or 44.0))
        ct = float(p.get("chord_tip", state.e_chord_tip or 38.0))
        # Absolute wall (mm) at each station — uniform mode means equal mm, not equal t/c.
        ar = state.e_thick_root * cr
        am = state.e_thick_mid * cm
        at = state.e_thick_tip * ct
        mode = str(p.get("thick_mode") or "").strip().lower()
        if mode in ("uniform", "tapered"):
            state.e_thick_mode = mode
        else:
            state.e_thick_mode = (
                "uniform"
                if abs(ar - am) < 0.12 and abs(am - at) < 0.12
                else "tapered"
            )
        if p.get("thick_mm") is not None:
            try:
                state.e_thick_mm = round(float(p["thick_mm"]), 2)
            except Exception:  # noqa: BLE001
                state.e_thick_mm = round((ar + am + at) / 3.0, 2)
        else:
            state.e_thick_mm = round((ar + am + at) / 3.0, 2)
        # Refresh mm readout after load (Uniform preferred when walls already match).
        if state.e_thick_mode == "uniform":
            th_r, th_m, th_t = uniform_thickness_tc(
                float(state.e_thick_mm), cr, cm, ct,
            )
            state.e_thick_root = round(th_r, 4)
            state.e_thick_mid = round(th_m, 4)
            state.e_thick_tip = round(th_t, 4)
            state.thick_wall_readout = (
                f"Wall ≈ {float(state.e_thick_mm):.2f} mm at root/mid/tip "
                f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
            )
        else:
            state.thick_wall_readout = (
                f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip"
            )
        state.e_le_thick = float(p.get("le_thick_scale", 1.0))
        state.e_te_thick = float(p.get("te_thick_scale", 1.0))
        _sf = str(p.get("section_family", "naca") or "naca").lower().strip()
        state.e_section_family = _sf if _sf in ("naca", "plate") else "naca"
        state.e_camber_pos = float(p.get("camber_pos", 0.4))
        state.e_spacing = float(p.get("spacing_spread", 0.0))
        state.e_tub_amp = float(p.get("tubercle_amp", feat.tubercle_amp))
        state.e_tub_waves = int(p.get("tubercle_waves", feat.tubercle_waves))
        state.e_ser_amp = float(p.get("serration_amp", feat.serration_amp))
        state.e_ser_waves = int(p.get("serration_waves", feat.serration_waves))
        state.e_dim_amp = float(p.get("dimple_amp", feat.dimple_amp))
        state.e_dim_rows = int(p.get("dimple_rows", feat.dimple_rows))
        state.e_dim_cols = int(p.get("dimple_cols", feat.dimple_cols))

    _init_editor({})

    def edit_flat() -> dict:
        shroud = normalize_shroud_thick_mm(state.e_shroud_thick)
        if float(state.e_shroud_thick or 0.0) != shroud:
            state.e_shroud_thick = shroud
        if str(getattr(state, "e_thick_mode", "tapered")) == "uniform":
            th_r, th_m, th_t = uniform_thickness_tc(
                float(getattr(state, "e_thick_mm", 2.0) or 2.0),
                float(state.e_chord_root),
                float(state.e_chord_mid),
                float(state.e_chord_tip),
            )
        else:
            th_r = float(state.e_thick_root)
            th_m = float(state.e_thick_mid)
            th_t = float(state.e_thick_tip)
        return dict(
            n_blades=int(state.e_n_blades),
            stagger_root=state.e_stagger_root,
            stagger_mid=state.e_stagger_mid,
            stagger_tip=state.e_stagger_tip,
            chord_root=state.e_chord_root,
            chord_mid=state.e_chord_mid,
            chord_tip=state.e_chord_tip,
            sweep_mid=state.e_sweep_mid,
            sweep_tip=state.e_sweep_tip,
            camber_root=float(state.e_camber_root),
            camber_mid=float(state.e_camber_mid),
            camber_tip=float(state.e_camber_tip),
            max_camber=float(state.e_camber_mid),
            camber_pos=state.e_camber_pos,
            lean_mid=state.e_lean_mid,
            lean_tip=state.e_lean_tip,
            le_sweep_mid=state.e_le_mid,
            le_sweep_tip=state.e_le_tip,
            le_skew_mid=float(getattr(state, "e_le_skew_mid", 0.0) or 0.0),
            le_skew_tip=float(getattr(state, "e_le_skew_tip", 0.0) or 0.0),
            skew_mid=state.e_skew_mid,
            skew_tip=state.e_skew_tip,
            span_interp=("pchip" if bool(state.e_smooth_span) else "linear"),
            winglet_span=state.e_winglet_span,
            winglet_sweep=state.e_winglet_sweep,
            winglet_lean=state.e_winglet_lean,
            shroud_thick_mm=shroud,
            shroud_height_frac=min(max(float(state.e_shroud_height or 0.0), 0.0), 1.0),
            tip_round=state.e_tip_round,
            tip_round_start=state.e_tip_start,
            cylindrical_tip=bool(state.e_cylindrical_tip),
            notched_tips=bool(getattr(state, "e_tip_notched", False)),
            tip_notch_count=(3 if bool(getattr(state, "e_tip_notched", False)) else 0),
            tip_notch_depth_mm=(
                float(getattr(state, "e_tip_notch_depth", 1.5) or 1.5)
                if bool(getattr(state, "e_tip_notched", False))
                else 0.0
            ),
            hub_radius=state.e_hub_radius,
            tip_radius=state.e_tip_radius,
            hub_height=state.e_hub_height,
            blade_hub_z=float(getattr(state, "e_blade_hub_z", 0.0) or 0.0),
            hub_profile=state.e_hub_profile,
            hub_nose=state.e_hub_nose,
            thickness_root=th_r,
            thickness_mid=th_m,
            thickness_tip=th_t,
            thick_mode=str(getattr(state, "e_thick_mode", "tapered") or "tapered"),
            thick_mm=float(getattr(state, "e_thick_mm", 2.0) or 2.0),
            le_thick_scale=float(state.e_le_thick),
            te_thick_scale=float(state.e_te_thick),
            section_family=str(state.e_section_family or "naca"),
            spacing_spread=state.e_spacing,
            spacing_seed=0,
        )

    def _apply_editor_flat(flat: dict) -> None:
        mapping = {
            "n_blades": ("e_n_blades", int),
            "stagger_root": ("e_stagger_root", float),
            "stagger_mid": ("e_stagger_mid", float),
            "stagger_tip": ("e_stagger_tip", float),
            "chord_root": ("e_chord_root", float),
            "chord_mid": ("e_chord_mid", float),
            "chord_tip": ("e_chord_tip", float),
            "sweep_mid": ("e_sweep_mid", float),
            "sweep_tip": ("e_sweep_tip", float),
            "camber_root": ("e_camber_root", float),
            "camber_mid": ("e_camber_mid", float),
            "camber_tip": ("e_camber_tip", float),
            "max_camber": ("e_camber_mid", float),
            "camber_pos": ("e_camber_pos", float),
            "lean_mid": ("e_lean_mid", float),
            "lean_tip": ("e_lean_tip", float),
            "le_sweep_mid": ("e_le_mid", float),
            "le_sweep_tip": ("e_le_tip", float),
            "le_skew_mid": ("e_le_skew_mid", float),
            "le_skew_tip": ("e_le_skew_tip", float),
            "skew_mid": ("e_skew_mid", float),
            "skew_tip": ("e_skew_tip", float),
            "winglet_span": ("e_winglet_span", float),
            "winglet_sweep": ("e_winglet_sweep", float),
            "winglet_lean": ("e_winglet_lean", float),
            "shroud_thick_mm": ("e_shroud_thick", float),
            "shroud_height_frac": ("e_shroud_height", float),
            "tip_round": ("e_tip_round", float),
            "tip_round_start": ("e_tip_start", float),
            "tip_notch_depth_mm": ("e_tip_notch_depth", float),
            "hub_radius": ("e_hub_radius", float),
            "tip_radius": ("e_tip_radius", float),
            "hub_height": ("e_hub_height", float),
            "blade_hub_z": ("e_blade_hub_z", float),
            "hub_profile": ("e_hub_profile", str),
            "hub_nose": ("e_hub_nose", float),
            "thickness_root": ("e_thick_root", float),
            "thickness_mid": ("e_thick_mid", float),
            "thickness_tip": ("e_thick_tip", float),
            "thick_mm": ("e_thick_mm", float),
            "le_thick_scale": ("e_le_thick", float),
            "te_thick_scale": ("e_te_thick", float),
            "section_family": ("e_section_family", str),
            "spacing_spread": ("e_spacing", float),
        }
        for k, (sv, cast) in mapping.items():
            if k not in flat:
                continue
            v = flat.get(k)
            if v is None:
                continue
            try:
                setattr(state, sv, cast(v))
            except Exception:  # noqa: BLE001
                continue
        if "thick_mode" in flat:
            mode = str(flat.get("thick_mode") or "").strip().lower()
            if mode in ("uniform", "tapered"):
                state.e_thick_mode = mode
        state.e_camber = float(getattr(state, "e_camber_mid", getattr(state, "e_camber", 0.05)))
        _sf = str(getattr(state, "e_section_family", "naca") or "naca").lower().strip()
        state.e_section_family = _sf if _sf in ("naca", "plate") else "naca"
        if "span_interp" in flat:
            state.e_smooth_span = str(flat.get("span_interp") or "linear").lower() == "pchip"
        if "cylindrical_tip" in flat:
            _ct = flat.get("cylindrical_tip")
            if isinstance(_ct, str):
                state.e_cylindrical_tip = _ct.strip().lower() not in (
                    "0",
                    "false",
                    "no",
                    "off",
                    "",
                )
            else:
                state.e_cylindrical_tip = bool(_ct) if _ct is not None else True
        state.e_tip_notched = bool(
            int(flat.get("tip_notch_count", 0) or 0) > 0
            or flat.get("notched_tips")
            or float(flat.get("tip_notch_depth_mm", 0.0) or 0.0) > 0.0
        )
        if "tip_notch_depth_mm" in flat and float(flat.get("tip_notch_depth_mm") or 0) > 0:
            state.e_tip_notch_depth = float(flat["tip_notch_depth_mm"])

    def on_fit_envelope():
        res = fit_envelope(edit_flat(), active_spec(), features=edit_features())
        _apply_editor_flat(res.flat)
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        state.edited_stale = True
        state.preview_msg = preview_changes(res.changes)
        state.flush()

    def on_scale_to_hub():
        res = scale_to_hub(edit_flat(), active_spec(), features=edit_features())
        _apply_editor_flat(res.flat)
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        state.edited_stale = True
        state.preview_msg = preview_changes(res.changes)
        state.flush()

    def edit_features() -> Features:
        tw = int(state.e_tub_waves) or (6 if state.e_tub_amp > 0 else 0)
        sw = int(state.e_ser_waves) or (8 if state.e_ser_amp > 0 else 0)
        dr = int(state.e_dim_rows) or (5 if state.e_dim_amp > 0 else 0)
        dc = int(state.e_dim_cols) or (5 if state.e_dim_amp > 0 else 0)
        return Features(
            tubercle_amp=state.e_tub_amp,
            tubercle_waves=tw,
            serration_amp=state.e_ser_amp,
            serration_waves=sw,
            dimple_amp=state.e_dim_amp,
            dimple_rows=dr,
            dimple_cols=dc,
        )

    def randomize_features():
        on = {k: random.random() < 0.6 for k in ("tub", "ser", "dim")}
        if not any(on.values()):
            on[random.choice(("tub", "ser", "dim"))] = True
        state.e_tub_amp = round(random.uniform(0.02, 0.10), 3) if on["tub"] else 0.0
        state.e_tub_waves = random.randint(3, 8) if on["tub"] else 0
        state.e_ser_amp = round(random.uniform(0.015, 0.06), 3) if on["ser"] else 0.0
        state.e_ser_waves = random.randint(4, 12) if on["ser"] else 0
        state.e_dim_amp = round(random.uniform(0.10, 0.35), 2) if on["dim"] else 0.0
        state.e_dim_rows = random.randint(2, 6) if on["dim"] else 0
        state.e_dim_cols = random.randint(2, 6) if on["dim"] else 0
        active = ", ".join(k for k, v in on.items() if v)
        state.preview_msg = f"🎲 Randomized features ({active}). Press Preview geometry to see it."
        state.flush()

    def randomize_geometry():
        import random as _r

        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        state.e_n_blades = _r.randint(5, 11)
        state.e_stagger_root = round(_r.uniform(18, 48), 1)
        state.e_stagger_mid = round(_r.uniform(18, 48), 1)
        state.e_stagger_tip = round(_r.uniform(16, 40), 1)
        state.e_chord_root = round(_r.uniform(16, 40), 1)
        state.e_chord_mid = round(_r.uniform(18, 50), 1)
        state.e_chord_tip = round(_r.uniform(20, 60), 1)
        state.e_sweep_mid = round(_r.uniform(-8, 16), 1)
        state.e_sweep_tip = round(_r.uniform(-4, 20), 1)
        state.e_camber_root = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber_mid = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber_tip = round(_r.uniform(0.0, 0.06), 3)
        state.e_camber = state.e_camber_mid
        state.e_camber_pos = round(_r.uniform(0.3, 0.5), 2)
        state.e_lean_mid = round(_r.uniform(0, 25), 1)
        state.e_lean_tip = round(_r.uniform(0, 45), 1)
        state.e_le_mid = round(_r.uniform(-8, 8), 1)
        state.e_le_tip = round(_r.uniform(-8, 8), 1)
        state.e_le_skew_mid = round(_r.uniform(0, 6), 1)
        state.e_le_skew_tip = round(_r.uniform(0, 10), 1)
        state.e_skew_mid = round(_r.uniform(-4, 4), 1)
        state.e_skew_tip = round(_r.uniform(-4, 4), 1)
        wl = _r.random() < 0.4
        state.e_winglet_span = round(_r.uniform(0.75, 0.9), 2)
        state.e_winglet_sweep = round(_r.uniform(4, 12), 1) if wl else 0.0
        state.e_winglet_lean = round(_r.uniform(0, 20), 1) if wl else 0.0
        tipr = _r.random() < 0.5
        state.e_tip_round = round(_r.uniform(0.3, 0.9), 2) if tipr else 0.0
        state.e_tip_start = round(_r.uniform(0.7, 0.88), 2)
        state.e_hub_radius = round(_r.uniform(17, 28), 1)
        state.e_tip_radius = round(_r.uniform(48, 58), 1)
        state.e_thick_mode = "uniform"
        state.e_thick_mm = round(_r.uniform(1.2, 2.4), 1)
        th_r, th_m, th_t = uniform_thickness_tc(
            state.e_thick_mm, state.e_chord_root, state.e_chord_mid, state.e_chord_tip,
        )
        state.e_thick_root = round(th_r, 3)
        state.e_thick_mid = round(th_m, 3)
        state.e_thick_tip = round(th_t, 3)
        state.e_hub_profile = _r.choice(["cylinder", "cylinder", "cone", "dome"])
        state.e_hub_nose = (
            round(_r.uniform(3, 12), 1) if state.e_hub_profile != "cylinder" else 0.0
        )
        state.preview_msg = (
            "🎲 Randomized geometry. Press Preview geometry to see it (may be out-of-spec)."
        )
        state.flush()

    def build_edit_params():
        return blade_from_flat(edit_flat(), edit_features())

    def _do_export(params, out, mount, spec):
        from fansim.manufacturability.mount_gauge import write_print_fit_sidecars
        from fansim.manufacturability.print_export import (
            balance_summary,
            export_print_ready,
            print_readme,
            recommend_print_settings,
        )

        rep = export_print_ready(params, out, mount=mount)
        try:
            settings = recommend_print_settings(spec.material)
            bal = balance_summary(params, spec.rpm)
            (out.with_suffix(".md")).write_text(
                print_readme(out.stem, params, spec.material, rep, bal, settings, None),
                encoding="utf-8",
            )
        except Exception:  # noqa: BLE001
            pass
        gauge = None
        if mount is not None:
            try:
                gauge = write_print_fit_sidecars(
                    out,
                    spec,
                    report_mount_fits=rep.mount_fits,
                    report_mount_msg=rep.mount_msg or "",
                    params_summary={
                        "n_blades": int(params.n_blades),
                        "hub_radius": float(params.hub_radius),
                        "tip_radius": float(params.tip_radius),
                        "rpm": float(params.rpm),
                    },
                )
            except Exception:  # noqa: BLE001
                gauge = None
        return rep, gauge

    def export_stl_current():
        if state.export_busy or state.preview_busy or state.assess_busy:
            return
        from datetime import datetime

        spec = active_spec()
        fitted, frame_changes = prepare_export_flat(
            edit_flat(),
            spec,
            fit_frame=bool(state.export_fit_frame),
            features=edit_features(),
            fit_hub=bool(state.export_fit_hub),
        )
        _apply_editor_flat(fitted)
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        if frame_changes:
            state.edited_stale = True
        grew_from = None
        grew_h_from = None
        for ch in frame_changes:
            if ch.field == "hub_radius" and ch.after > ch.before:
                grew_from = ch.before
            if ch.field == "hub_height" and ch.after > ch.before:
                grew_h_from = ch.before
        params = build_edit_params()
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        tid = state.selected_trial
        base = f"design_{tid}" if tid is not None else "fan"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = exports / f"{base}_{stamp}.stl"

        async def task():
            state.export_busy = True
            heavy = "features are heavy — up to ~3 min" if params.features.active else ""
            ticker, _t0 = spawn_busy_ticker(
                action="Export",
                msg_attr="export_msg",
                busy_attr="export_busy",
                note=heavy,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                rep, gauge = await loop.run_in_executor(
                    None, _do_export, params, out, spec.motor_mount, spec
                )
            except Exception as exc:  # noqa: BLE001
                state.export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
                state.export_busy = False
                ticker.cancel()
                state.flush()
                return
            wt = "watertight" if rep.ok else "⚠ NON-manifold"
            if rep.mount_fits is True:
                mnt = f" · ✓ motor cup carved ({rep.mount_msg})"
            elif rep.mount_fits is False:
                mnt = f" · ⚠ {rep.mount_msg}"
                if not state.export_fit_hub:
                    mnt += " — turn on 'Fit hub to motor on export' to widen it and carve the cup"
            else:
                mnt = " · (this fan model has no motor-mount defined)"
            gauge_txt = ""
            if gauge is not None:
                mk = "PASS" if gauge.mount_ok else "FAIL"
                fk = "PASS" if gauge.frame_ok else "FAIL"
                gauge_txt = (
                    f"\n↳ Print-fit gauge: mount {mk}, frame {fk} "
                    f"(tip OD {gauge.tip_od_mm:.1f} mm). See {out.stem}_mount_checklist.md"
                )
                if not gauge.mount_ok or not gauge.frame_ok:
                    for n in gauge.notes[:3]:
                        gauge_txt += f"\n  · {n}"
            extra = ""
            if frame_changes:
                extra += "\n" + preview_changes(frame_changes)
            if grew_from is not None:
                extra += (
                    f"\n↳ Hub widened {grew_from:.1f} → {state.e_hub_radius:.1f} mm to fit the "
                    f"{spec.motor_mount.cavity_dia_mm:.1f} mm motor hub."
                )
            if grew_h_from is not None:
                extra += (
                    f"\n↳ Hub height set to {state.e_hub_height:.0f} mm so the cup has a cap and "
                    f"clears the frame spokes."
                )
            if extra:
                extra += (
                    " Press Preview to see it; the CFM/eff shown were for the original geometry, so "
                    "they're now approximate — re-Assess for exact numbers."
                )
            state.export_msg = f"✓ Saved {out.resolve()}  ({wt}{mnt}){gauge_txt}{extra}"
            state.export_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def _build_preview_stl(flat, feat):
        from dataclasses import asdict

        from fansim.geometry.isolated import build_stl_isolated

        mount = None
        if bool(getattr(state, "preview_motor_cup", False)):
            spec = active_spec()
            if spec.motor_mount is not None:
                mount = asdict(spec.motor_mount)
        # Motor cup needs a real boolean solid (not the fast non-fused preview mesh).
        build_stl_isolated(
            flat, feat, preview_stl, timeout=300.0,
            preview=mount is None,
            motor_mount=mount,
        )

    render_state = {
        "path": None,
        "color": "lightsteelblue",
        "glyph_cloud": None,
        "glyph_arrows": None,
    }

    _GLYPH_STRIDE = {"coarse": 4, "medium": 2, "fine": 1}
    _GLYPH_MAX = {"coarse": 250, "medium": 500, "fine": 800}

    def _rebuild_glyph_arrows():
        cloud = render_state.get("glyph_cloud")
        if cloud is None:
            render_state["glyph_arrows"] = None
            return
        dens = getattr(state, "glyph_density", "medium") or "medium"
        if dens not in _GLYPH_STRIDE:
            dens = "medium"
        try:
            factor = float(state.glyph_scale) if state.glyph_scale not in (None, "") else 2.0
        except (TypeError, ValueError):
            factor = 2.0
        factor = max(0.2, min(factor, 20.0))
        try:
            render_state["glyph_arrows"] = make_glyph_arrows(
                cloud,
                stride=_GLYPH_STRIDE[dens],
                factor=factor,
                max_arrows=_GLYPH_MAX[dens],
            )
        except Exception:  # noqa: BLE001
            render_state["glyph_arrows"] = None

    def _clear_glyphs(msg: str = "Velocity arrows not available for this design"):
        render_state["glyph_cloud"] = None
        render_state["glyph_arrows"] = None
        state.glyph_caption = msg

    def _spec_limits():
        s = active_spec()
        return s.tip_dia_mm[1] / 2.0, s.depth_mm[1]

    def _out_of_spec_mask(mesh):
        import numpy as np

        pts = mesh.points
        r = np.hypot(pts[:, 0], pts[:, 1])
        z = pts[:, 2]
        tip_r, depth_lim = _spec_limits()
        zmid = 0.5 * (float(z.min()) + float(z.max()))
        mask = (r > tip_r) | (np.abs(z - zmid) > depth_lim / 2.0)
        return mask.astype(float)

    def _add_envelope(mesh):
        zc = mesh.points[:, 2]
        zmid = 0.5 * (float(zc.min()) + float(zc.max()))
        tip_r, depth_lim = _spec_limits()
        cyl = pv.Cylinder(
            center=(0, 0, zmid),
            direction=(0, 0, 1),
            radius=tip_r,
            height=depth_lim,
            resolution=64,
        )
        plotter.add_mesh(cyl, color="seagreen", opacity=0.10)
        try:
            plotter.add_mesh(cyl.extract_feature_edges(), color="seagreen", line_width=2)
        except Exception:  # noqa: BLE001
            pass

    def _apply_render(reset: bool = False):
        plotter.clear_actors()
        p = render_state["path"]
        mesh = None
        if p:
            try:
                mesh = pv.read(str(p))
            except Exception:  # noqa: BLE001
                mesh = None
        if mesh is not None:
            base = render_state["color"]
            if state.highlight_spec:
                mask = _out_of_spec_mask(mesh)
                if mask.any():
                    mesh["spec"] = mask
                    plotter.add_mesh(
                        mesh,
                        scalars="spec",
                        cmap=[base, "red"],
                        clim=[0, 1],
                        show_scalar_bar=False,
                        smooth_shading=True,
                    )
                else:
                    plotter.add_mesh(mesh, color=base, smooth_shading=True)
            else:
                plotter.add_mesh(mesh, color=base, smooth_shading=True)
            if state.show_envelope:
                _add_envelope(mesh)
        if state.show_glyphs and render_state.get("glyph_arrows") is not None:
            try:
                plotter.add_mesh(
                    render_state["glyph_arrows"],
                    scalars="U_mag",
                    cmap="viridis",
                    show_scalar_bar=True,
                    scalar_bar_args={"title": "|U| m/s", "n_labels": 3},
                )
            except Exception:  # noqa: BLE001
                try:
                    plotter.add_mesh(
                        render_state["glyph_arrows"],
                        color="royalblue",
                        show_scalar_bar=False,
                    )
                except Exception:
                    pass
        if reset and (mesh is not None or render_state.get("glyph_arrows") is not None):
            plotter.reset_camera()

    def _draw(path, color: str):
        render_state["path"] = str(path)
        render_state["color"] = color
        _apply_render(reset=True)

    @state.change("highlight_spec", "show_envelope", "fan_model", "show_glyphs")
    def _on_viz_toggle(**_):
        _apply_render(reset=False)
        try:
            ctrl.view_update()
        except Exception:  # noqa: BLE001
            pass

    @state.change("glyph_mode")
    def _on_glyph_mode(glyph_mode=None, **_):
        on = str(glyph_mode or "on") == "on"
        if bool(state.show_glyphs) != on:
            state.show_glyphs = on
            state.flush()

    @state.change("glyph_density", "glyph_scale")
    def _on_glyph_params(**_):
        if render_state.get("glyph_cloud") is None:
            return
        _rebuild_glyph_arrows()
        _apply_render(reset=False)
        try:
            ctrl.view_update()
        except Exception:  # noqa: BLE001
            pass

    def do_preview():
        if state.preview_busy or state.assess_busy:
            return
        try:
            params = build_edit_params()
            printable = check_printability(params)
            print_warn = "" if printable.printable else "\n" + preview_unprintable_note(printable.reason)
            flat, feat = edit_flat(), edit_features()
        except Exception as exc:  # noqa: BLE001 - sync preamble; surface or the button looks dead
            state.preview_msg = f"⚠ Preview setup failed: {type(exc).__name__}: {exc}"
            state.flush()
            return

        async def task():
            state.preview_busy = True
            heavy = ""
            if params.features.active:
                heavy = "features are heavy — up to ~2 min"
            elif int(getattr(params, "tip_notch_count", 0) or 0) > 0:
                heavy = "tip TE notches — first build can take ~30–60 s"
            ticker, _t0 = spawn_busy_ticker(
                action="Preview",
                msg_attr="preview_msg",
                busy_attr="preview_busy",
                note=heavy,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, _build_preview_stl, flat, feat)
            except TimeoutError:
                state.preview_msg = (
                    "⚠ Geometry build timed out — previous mesh kept (so nothing looks "
                    "changed). Tip TE notches / bio-features are heavy; wait for Preview to "
                    "finish, or turn notches off briefly to tweak Sickle/Wrap, then re-enable."
                )
                state.preview_busy = False
                ticker.cancel()
                state.flush()
                return
            except Exception as exc:  # noqa: BLE001
                state.preview_msg = f"⚠ Geometry failed: {type(exc).__name__}: {exc}"
                state.preview_busy = False
                ticker.cancel()
                state.flush()
                return
            _draw(preview_stl, "darkorange")
            feats = "features ON" if params.features.active else "smooth"
            _, status = spec_status(preview_stl, params, flat)
            try:
                from fansim.manufacturability.printability_score import grade_printability

                print_line = "\n🖨 " + grade_printability(params).summary
            except Exception:  # noqa: BLE001
                print_line = ""
            tone_line = ""
            if params.blade_angles_deg is not None:
                try:
                    import numpy as _np
                    from fansim.acoustics.tonal import peak_tone_reduction_db

                    drop = -peak_tone_reduction_db(_np.radians(_np.asarray(params.blade_angles_deg)))
                    odd = (
                        ""
                        if params.n_blades % 2
                        else "  (even blade count — odd counts spread the tone more)"
                    )
                    tone_line = (
                        f"\n🔉 Uneven spacing: predicted peak tone −{drop:.1f} dB, free of any flow cost{odd}"
                    )
                except Exception:  # noqa: BLE001
                    tone_line = ""
            state.preview_msg = (
                f"Preview (orange): {params.n_blades} blades, "
                f"camber {state.e_camber_root:.3f}/{state.e_camber_mid:.3f}/{state.e_camber_tip:.3f}, {feats}.\n{status}{print_line}"
                f"{tone_line}{print_warn}"
            )
            state.preview_busy = False
            ticker.cancel()
            try:
                ctrl.view_update()
            except Exception:
                pass
            state.flush()

        asynchronous.create_task(task())

    # --- Assess (run CFD) + Sweep (regression over one parameter) ---
    # Each sweep step is a full ~4-min CFD run, so this lists the params that actually move the CFD
    # objectives (flow/eff) — the high-value levers from the design-rules study — grouped like the
    # editor. Deliberately omitted: LE-curve/skew/thickness/camber-pos (minor aero or structural) and
    # UNEVEN SPACING (a tonal-NOISE lever a flow/eff CFD sweep can't see — the Preview shows it live).
    SWEEP_OPTIONS = [
        # planform / solidity — biggest flow + pressure levers
        ("blades", "flat", "n_blades", 5.0, 11.0),
        ("chord mid", "flat", "chord_mid", 14.0, 60.0),
        ("chord tip", "flat", "chord_tip", 14.0, 70.0),
        # pitch / twist (stagger mid = the win-win-win lever from the design rules)
        ("stagger root", "flat", "stagger_root", 15.0, 55.0),
        ("stagger mid", "flat", "stagger_mid", 15.0, 55.0),
        ("stagger tip", "flat", "stagger_tip", 15.0, 55.0),
        # airfoil
        ("camber", "flat", "max_camber", 0.0, 0.06),
        ("camber position", "flat", "camber_pos", 0.2, 0.6),
        # 3-D shape
        ("sweep mid", "flat", "sweep_mid", -3.0, 8.0),
        ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
        ("wrap tip", "flat", "lean_tip", 0.0, 45.0),
        # winglet (mild CFD effect ~+4% flow; near the screening noise floor)
        ("winglet sweep", "flat", "winglet_sweep", 0.0, 15.0),
        # size / hub (blade length + flow annulus / mountability)
        ("tip radius (length)", "flat", "tip_radius", 45.0, 59.0),
        ("hub radius", "flat", "hub_radius", 15.0, 35.0),
        # bio-inspired features
        ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
        ("serration amp", "ser", "serration_amp", 0.0, 0.06),
        ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
    ]
    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]

    def _feat_dict() -> dict:
        f = edit_features()
        return dict(
            tubercle_amp=f.tubercle_amp,
            tubercle_waves=f.tubercle_waves,
            serration_amp=f.serration_amp,
            serration_waves=f.serration_waves,
            dimple_amp=f.dimple_amp,
            dimple_rows=f.dimple_rows,
            dimple_cols=f.dimple_cols,
        )

    # --- Edited-since-assessment tracking ---------------------------------------------------------
    # EDITOR_VARS is every slider that feeds the geometry/CFD, so a change to ANY of them can make a
    # prior assessment stale. sel_sig holds the signature of the selected design's assessed config.
    EDITOR_VARS = (
        "e_n_blades",
        "e_stagger_root",
        "e_stagger_mid",
        "e_stagger_tip",
        "e_chord_root",
        "e_chord_mid",
        "e_chord_tip",
        "e_sweep_mid",
        "e_sweep_tip",
        "e_camber_root",
        "e_camber_mid",
        "e_camber_tip",
        "e_camber",
        "e_camber_pos",
        "e_lean_mid",
        "e_lean_tip",
        "e_le_mid",
        "e_le_tip",
        "e_le_skew_mid",
        "e_le_skew_tip",
        "e_skew_mid",
        "e_skew_tip",
        "e_smooth_span",
        "e_winglet_span",
        "e_winglet_sweep",
        "e_winglet_lean",
        "e_shroud_thick",
        "e_shroud_height",
        "e_tip_round",
        "e_tip_start",
        "e_tip_notched",
        "e_tip_notch_depth",
        "e_cylindrical_tip",
        "e_hub_radius",
        "e_tip_radius",
        "e_hub_height",
        "e_blade_hub_z",
        "e_hub_profile",
        "e_hub_nose",
        "e_thick_mode",
        "e_thick_mm",
        "e_thick_root",
        "e_thick_mid",
        "e_thick_tip",
        "e_le_thick",
        "e_te_thick",
        "e_section_family",
        "e_spacing",
        "e_tub_amp",
        "e_tub_waves",
        "e_ser_amp",
        "e_ser_waves",
        "e_dim_amp",
        "e_dim_rows",
        "e_dim_cols",
    )
    sel_sig = [None]  # signature of the currently-selected design's assessed geometry+features

    def _editor_sig() -> dict:
        """Normalized signature of the current editor state (geometry + features)."""
        s = {**edit_flat(), **_feat_dict()}
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}

    def _set_baseline():
        """Mark the current editor state as the assessed baseline (not stale)."""
        sel_sig[0] = _editor_sig()
        state.edited_stale = False
        state.stale_msg = ""

    def _recompute_stale(**_):
        _hub_fit_readout()
        _tip_fit_readout()
        _depth_fit_readout()
        if sel_sig[0] is None:
            return
        stale = _editor_sig() != sel_sig[0]
        state.edited_stale = stale
        state.stale_msg = (
            "⚠ Edited since assessment — the shown CFM/efficiency are for the "
            "un-edited design. Press Assess to evaluate your changes."
            if stale
            else ""
        )

    state.change(*EDITOR_VARS)(_recompute_stale)

    @state.change("e_thick_mode")
    def _on_thick_mode(e_thick_mode=None, **_):
        mode = str(e_thick_mode if e_thick_mode is not None else getattr(state, "e_thick_mode", "tapered"))
        if mode == "uniform":
            # Prefer the Blade-thickness mm control; fall back to root wall if unset.
            mm = float(getattr(state, "e_thick_mm", 0.0) or 0.0)
            if mm < 0.8:
                mm = float(state.e_thick_root) * float(state.e_chord_root)
            state.e_thick_mm = round(max(mm, 0.8), 2)
            th_r, th_m, th_t = uniform_thickness_tc(
                state.e_thick_mm,
                float(state.e_chord_root),
                float(state.e_chord_mid),
                float(state.e_chord_tip),
            )
            state.e_thick_root = round(th_r, 4)
            state.e_thick_mid = round(th_m, 4)
            state.e_thick_tip = round(th_t, 4)
            state.thick_wall_readout = (
                f"Wall ≈ {state.e_thick_mm:.2f} mm at root/mid/tip "
                f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
            )
        else:
            mm = float(getattr(state, "e_thick_mm", 2.0) or 2.0)
            th_r, th_m, th_t = uniform_thickness_tc(
                mm,
                float(state.e_chord_root),
                float(state.e_chord_mid),
                float(state.e_chord_tip),
            )
            state.e_thick_root = round(th_r, 4)
            state.e_thick_mid = round(th_m, 4)
            state.e_thick_tip = round(th_t, 4)
            ar = th_r * float(state.e_chord_root)
            am = th_m * float(state.e_chord_mid)
            at = th_t * float(state.e_chord_tip)
            state.thick_wall_readout = (
                f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip "
                f"(t/c sliders — tip was historically too thin at 3%)"
            )

    @state.change("e_thick_mm", "e_chord_root", "e_chord_mid", "e_chord_tip")
    def _sync_uniform_tc(**_):
        """Keep station t/c aligned with Blade thickness (mm) while Uniform is active."""
        if str(getattr(state, "e_thick_mode", "tapered") or "tapered") != "uniform":
            return
        mm = float(getattr(state, "e_thick_mm", 2.0) or 2.0)
        th_r, th_m, th_t = uniform_thickness_tc(
            mm,
            float(state.e_chord_root),
            float(state.e_chord_mid),
            float(state.e_chord_tip),
        )
        state.e_thick_root = round(th_r, 4)
        state.e_thick_mid = round(th_m, 4)
        state.e_thick_tip = round(th_t, 4)
        state.thick_wall_readout = (
            f"Wall ≈ {mm:.2f} mm at root/mid/tip "
            f"(t/c {th_r:.3f} / {th_m:.3f} / {th_t:.3f})"
        )

    @state.change("e_thick_root", "e_thick_mid", "e_thick_tip", "e_thick_mode")
    def _sync_tapered_wall_readout(**_):
        if str(getattr(state, "e_thick_mode", "tapered") or "tapered") == "uniform":
            return
        ar = float(state.e_thick_root) * float(state.e_chord_root)
        am = float(state.e_thick_mid) * float(state.e_chord_mid)
        at = float(state.e_thick_tip) * float(state.e_chord_tip)
        state.thick_wall_readout = (
            f"Wall ≈ {ar:.2f} / {am:.2f} / {at:.2f} mm root/mid/tip "
            f"(t/c sliders — tip was historically too thin at 3%)"
        )

    @state.change("assess_preset", "assess_refine_op", "assess_wall_ks")
    def _on_assess_score_settings(
        assess_preset=None, assess_refine_op=None, assess_wall_ks=None, **_
    ):
        if sel_sig[0] is None:
            return
        cur = None
        if state.selected_trial is not None:
            cur = by_trial.get(int(state.selected_trial))
        scored_preset = (cur.extra.get("preset") if cur else None) or "legacy"
        scored_refine = bool(cur.extra.get("refine_op")) if cur else False
        scored_ks = float((cur.extra.get("wall_ks_mm") if cur else None) or 0) > 0
        preset = str(
            assess_preset if assess_preset is not None else state.assess_preset or "case"
        )
        refine = bool(state.assess_refine_op) if assess_refine_op is None else bool(assess_refine_op)
        wall_ks = bool(state.assess_wall_ks) if assess_wall_ks is None else bool(assess_wall_ks)
        if preset != str(scored_preset) or refine != scored_refine or wall_ks != scored_ks:
            state.edited_stale = True
            state.stale_msg = (
                "⚠ Assess settings changed — the shown load CFM is for the "
                "previous hose / refine-op / wall-ks. Press Assess to rescore."
            )
        else:
            _recompute_stale()

    def load_catalog_design(design_id=None, **_):
        if not design_id:
            return
        e = get_entry(design_id)
        if e is None:
            state.catalog_info = f"'{design_id}' not in the catalog (rebuild it if it's new)."
            state.flush()
            return
        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        _init_editor(e.params)
        _set_baseline()
        parts = [f"Loaded {e.design_id}", f"{e.source}"]
        if isinstance(e.cfm_free, (int, float)):
            parts.append(
                f"sim {e.cfm_free:.0f}/{e.cfm_load or 0:.0f} CFM  eff {e.efficiency or 0:.0f}%"
            )
        if e.dp_op_pa is not None:
            parts.append(f"op {e.dp_op_pa:.1f} Pa @ {e.q_ref_cfm or 50:.0f} CFM")
        try:
            from fansim.manufacturability.printability_score import grade_printability

            lp = blade_from_flat(e.params)
            need = mount_min_hub_radius(active_spec())
            parts.append("mountable" if (need is None or lp.hub_radius >= need) else "NOT mountable")
            parts.append(f"print {grade_printability(lp).difficulty:.0f}/100")
        except Exception:  # noqa: BLE001
            pass
        if e.has_measurement and e.measured_cfm is not None:
            parts.append(
                f"MEASURED {e.measured_cfm:.0f} CFM (sim {e.cfm_error_pct:+.0f}%)"
                if e.cfm_error_pct is not None
                else f"MEASURED {e.measured_cfm:.0f} CFM"
            )
        state.catalog_info = "  ·  ".join(parts)
        state.preview_msg = (
            f"Loaded {e.design_id} from the catalog. Press Preview geometry to see it."
        )
        state.flush()

    def _apply_library_to_editor(design_id: str, op: str):
        if not state.fan_model:
            state.preview_msg = "Select a hub first."
            state.flush()
            return
        if not design_id:
            state.preview_msg = "Select a library recipe first."
            state.flush()
            return
        e = get_entry(design_id)
        if e is None:
            state.preview_msg = f"'{design_id}' not in the catalog (rebuild it if it's new)."
            state.flush()
            return
        rec = apply_library_recipe(e.params or {}, active_spec(), op=op, parent_id=design_id)
        state.library_sel = design_id
        state.library_parent_id = rec.parent_id
        state.library_place_op = rec.place_op
        state.library_leftover = rec.leftover or rec.message
        if not rec.ok or rec.flat is None:
            state.preview_msg = rec.message or rec.leftover
            state.flush()
            return
        _init_editor(rec.flat)
        _set_baseline()
        do_preview()
        state.flush()

    def select_library_design(design_id=None, **_):
        if not design_id:
            return
        _apply_library_to_editor(design_id, "fit_envelope")

    def on_library_scale_to_hub():
        _apply_library_to_editor(state.library_sel, "scale_to_hub")

    def _depth_driver_msg(flat):
        try:
            drivers = _depth_drivers(flat)
        except Exception:  # noqa: BLE001
            return ""
        if not drivers:
            return ""
        return "  Top depth drivers here: " + ", ".join(
            f"{lab} (~{mm:.0f} mm)" for lab, mm in drivers
        )

    def spec_status(stl_path, params, flat=None):
        spec = active_spec()
        try:
            import trimesh

            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            vol = abs(float(m.volume))
            meta = Path(str(stl_path) + ".meta.json")
            if meta.exists():
                try:
                    vol = float(json.loads(meta.read_text()).get("volume_mm3", vol))
                except Exception:  # noqa: BLE001
                    pass
            weight = estimate_weight_g(vol, spec.material)
        except Exception:  # noqa: BLE001
            return True, ""
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        depth_msg = _depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
        if not ok:
            return (
                False,
                f"⚠ Out of spec — Assess will reject: {reason}. {reject_hint(reason)}{depth_msg}",
            )
        from fansim.cockpit.placement import frame_gap_note

        gap = frame_gap_note(dia, spec)
        if gap:
            return False, f"⚠ Out of spec — Assess will reject: {gap}. {reject_hint(gap)}"
        over = over_spec_flags(spec, dia, depth, weight)
        if over:
            dm = _depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"

    assess_proc = [None]

    def _blocking_eval(flat, features, workdir):
        from fansim.cfd.wall_roughness import FDM_WALL_KS_MM

        load_pa, _ = assess_load(str(state.assess_preset or "case"))
        ks = FDM_WALL_KS_MM if state.assess_wall_ks else None
        return evaluate_candidate_isolated(
            flat,
            features,
            workdir,
            spec=active_spec(),
            procs=8,
            base_cell=0.006,
            iters=500,
            timeout=cfd_eval_timeout(),
            load_pa=load_pa,
            refine_op=bool(state.assess_refine_op),
            material=str(state.assess_material or "PETG"),
            wall_ks_mm=ks,
            proc_holder=assess_proc,
        )

    def _cfd_progress_hint(workdir: Path | None) -> str:
        return cfd_stage_hint(workdir)

    async def _assess_progress_ticker(t0: float, workdir_holder, *, note: str = ""):
        while state.assess_busy and not state.assess_cancel:
            if state.sweep_active or state.opt_running:
                await asyncio.sleep(5.0)
                continue
            wd = workdir_holder[0] if workdir_holder else None
            state.assess_msg = busy_caption(
                "Assess",
                time.time() - t0,
                hint=_cfd_progress_hint(wd),
                note=note,
            )
            state.flush()
            await asyncio.sleep(2.0)

    def _stamp_assess_extra(extra, result):
        load_pa, _ = assess_load(str(state.assess_preset or "case"))
        stamp_score_extra(
            extra,
            result.raw,
            load_pa=load_pa,
            preset=str(state.assess_preset or "case"),
            refine_op=bool(state.assess_refine_op),
        )

    async def _assess(params, flat, label, workdir_holder=None):
        tid = next_id[0]
        next_id[0] += 1
        workdir = assess_dir / f"design_{tid}"
        if workdir_holder is not None:
            workdir_holder[0] = workdir
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
        if state.assess_cancel:
            raise RuntimeError("Assess cancelled")
        if not result.feasible:
            hint = reject_hint(result.reason)
            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
            state.flush()
            return None
        stl = workdir / "impeller.stl"
        extra = {
            "n_blades": params.n_blades,
            "source": "user",
            "source_run": run_dir.name,
            "over_spec": list(result.over_spec),
            "fan_model": state.fan_model,
            "actual_rpm": round(result.actual_rpm),
            "material": str(state.assess_material or "PETG"),
        }
        _stamp_assess_extra(extra, result)
        if state.library_parent_id:
            extra["parent_id"] = state.library_parent_id
            extra["place_op"] = state.library_place_op or "fit_envelope"
            extra["placed_on"] = state.fan_model
            extra["cfd_stale"] = False
        d = Design(
            trial=tid,
            params=dict(flat),
            objectives={
                "cfm_free": result.cfm_free,
                "cfm_load": result.cfm_load,
                "efficiency": result.efficiency,
            },
            feasible=True,
            is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra=extra,
        )
        try:
            (workdir / "design.json").write_text(
                json.dumps(
                    {
                        "trial": d.trial,
                        "params": d.params,
                        "objectives": d.objectives,
                        "feasible": True,
                        "reason": d.reason,
                        "extra": d.extra,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "skip assess design.json write %s: %s: %s",
                workdir / "design.json", type(exc).__name__, exc)
        append_user_designs(designs_lock, user_designs, by_trial, d)
        refresh_items()
        refresh_figure()
        state.flush()
        return d

    async def _assess_existing(d: Design, params, flat, label, workdir_holder=None):
        tid = int(d.trial)
        workdir = assess_dir / f"design_{tid}"
        if workdir_holder is not None:
            workdir_holder[0] = workdir
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir)
        if state.assess_cancel:
            raise RuntimeError("Assess cancelled")
        if not result.feasible:
            hint = reject_hint(result.reason)
            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
            state.flush()
            return None
        stl = workdir / "impeller.stl"
        d.params = dict(flat)
        d.objectives = {
            "cfm_free": result.cfm_free,
            "cfm_load": result.cfm_load,
            "efficiency": result.efficiency,
        }
        d.feasible = True
        d.is_pareto = False
        d.stl_path = stl if stl.exists() else None
        d.reason = ""
        d.extra.update(
            {
                "source": d.extra.get("source", "user"),
                "source_run": run_dir.name,
                "over_spec": list(result.over_spec),
                "fan_model": state.fan_model,
                "actual_rpm": round(result.actual_rpm),
                "cfd_stale": False,
            }
        )
        _stamp_assess_extra(d.extra, result)
        try:
            workdir.mkdir(parents=True, exist_ok=True)
            (workdir / "design.json").write_text(
                json.dumps(
                    {
                        "trial": d.trial,
                        "params": d.params,
                        "objectives": d.objectives,
                        "feasible": True,
                        "reason": d.reason,
                        "extra": d.extra,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "skip assess design.json write %s: %s: %s",
                workdir / "design.json", type(exc).__name__, exc)
        upsert_by_trial(designs_lock, by_trial, d)
        refresh_items()
        refresh_figure()
        state.flush()
        return d

    def on_assess():
        if state.assess_busy:
            return
        params, flat = build_edit_params(), {**edit_flat(), **_feat_dict()}

        async def task():
            state.assess_busy = True
            state.assess_cancel = False
            t0 = time.time()
            budget_m = max(1, int(round(cfd_eval_timeout() / 60.0)))
            note = f"typically 15–30 min free+load; timeout {budget_m} min"
            wd_holder: list = [None]
            state.assess_msg = busy_caption("Assess", 0, note=note)
            state.flush()
            ticker = asynchronous.create_task(_assess_progress_ticker(t0, wd_holder, note=note))
            try:
                try:
                    # Always gate on LIVE editor geometry — never orphan Preview STL bounds
                    # (edit-after-Preview used to false-reject or skip the gate).
                    from fansim.cockpit.placement import frame_gap_note, impeller_z_extent

                    spec = active_spec()
                    dia = _blade_max_dia(params)
                    depth = impeller_z_extent(params)
                    ok_prev, reason_prev = check_build(
                        spec, dia, 2.0 * float(params.hub_radius), depth, None,
                    )
                    if ok_prev:
                        gap = frame_gap_note(dia, spec)
                        if gap:
                            ok_prev, reason_prev = False, gap
                    if not ok_prev:
                        hint = reject_hint(reason_prev)
                        state.assess_msg = (
                            f"Assess: rejected — {reason_prev}"
                            + (f"\n{hint}" if hint else "")
                        )
                        return
                except Exception:  # noqa: BLE001 — never block Assess on readout failure
                    pass
                cur = (
                    by_trial.get(int(state.selected_trial))
                    if state.selected_trial is not None
                    else None
                )
                if cur is not None and cur.extra.get("cfd_stale"):
                    d = await _assess_existing(cur, params, flat, "Assess", wd_holder)
                else:
                    d = await _assess(params, flat, "Assess", wd_holder)
                if state.assess_cancel:
                    state.assess_msg = "⏹ Assess cancelled."
                    return
                if d:
                    o = d.objectives
                    over = d.extra.get("over_spec") or []
                    tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                    spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
                    rpm = d.extra.get("actual_rpm", 0)
                    rpm_tag = (
                        f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
                        if rpm and rpm < spec.rpm * 0.995
                        else ""
                    )
                    state.assess_msg = (
                        f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                        f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                        f"  (added to Results plot){rpm_tag}{tag}"
                    )
                    cap = score_caption(d.extra)
                    if cap:
                        state.assess_msg += f"\n{cap}"
                    select(d.trial)
                    state.fan_subtab = "results"
                    _set_baseline()
            except Exception as exc:  # noqa: BLE001
                if state.assess_cancel or "cancelled" in str(exc).lower():
                    state.assess_msg = "⏹ Assess cancelled."
                else:
                    state.assess_msg = f"Assess failed: {type(exc).__name__}: {exc}"
            finally:
                state.assess_busy = False
                state.assess_cancel = False
                assess_proc[0] = None
                ticker.cancel()
                state.flush()

        asynchronous.create_task(task())

    def on_sweep():
        if state.assess_busy:
            return
        import numpy as np

        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
        label, kind, field, mn, mx = opt
        base_flat, base_feat = edit_flat(), _feat_dict()
        steps = max(2, int(state.sweep_steps))
        raw = list(np.linspace(mn, mx, steps))
        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw

        async def task():
            state.assess_busy = True
            state.assess_cancel = False
            state.sweep_active = True
            state.sweep_cancel = False
            state.sweep_progress = 0
            done = 0
            n = len(values)
            try:
                for i, val in enumerate(values):
                    if state.sweep_cancel or state.assess_cancel:
                        state.assess_msg = (
                            f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
                        )
                        break
                    flat, feat = dict(base_flat), dict(base_feat)
                    if kind == "flat":
                        flat[field] = int(val) if field == "n_blades" else float(val)
                    else:
                        feat[field] = float(val)
                        if kind == "tub" and feat["tubercle_waves"] == 0:
                            feat["tubercle_waves"] = 6
                        if kind == "ser" and feat["serration_waves"] == 0:
                            feat["serration_waves"] = 8
                        if kind == "dim":
                            feat["dimple_rows"] = feat["dimple_rows"] or 5
                            feat["dimple_cols"] = feat["dimple_cols"] or 5
                    params = blade_from_flat(flat, Features(**feat))
                    state.assess_msg = (
                        f"Sweep {label} {i+1}/{n} = {val:g}: running CFD… "
                        f"(~15–30 min/step; {done} added so far)"
                    )
                    state.sweep_progress = int(100 * i / n)
                    state.flush()
                    if not check_printability(params).printable:
                        continue
                    try:
                        if await _assess(params, flat, f"sweep {label}={val:g}"):
                            done += 1
                    except Exception as exc:  # noqa: BLE001
                        if state.assess_cancel or "cancelled" in str(exc).lower():
                            state.assess_msg = (
                                f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
                            )
                            break
                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
                        state.flush()
                else:
                    if done == 0:
                        state.assess_msg = (
                            f"Sweep of {label} done: 0 ◆ added — every design was rejected before CFD "
                            "(not a crash). Usually the base design is out of spec or too close to the "
                            "frame: Preview shows the exact verdict, or click Fit envelope first."
                        )
                    else:
                        state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
                state.sweep_progress = 100
            finally:
                state.assess_busy = False
                state.assess_cancel = False
                state.sweep_active = False
                state.sweep_cancel = False
                assess_proc[0] = None
                state.flush()

        asynchronous.create_task(task())

    def _kill_assess_proc():
        p = assess_proc[0]
        if p is not None and getattr(p, "poll", lambda: 0)() is None:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    capture_output=True,
                    text=True,
                )
            else:
                p.terminate()
        assess_proc[0] = None
        kill_cfd_containers()

    def cancel_sweep():
        if state.sweep_active or (state.assess_busy and not state.opt_running):
            state.sweep_cancel = True
            state.assess_cancel = True
            _kill_assess_proc()
            state.assess_msg = "⏹ Cancelling…"
            state.flush()

    def cancel_assess():
        if not state.assess_busy or state.opt_running:
            return
        state.assess_cancel = True
        if state.sweep_active:
            state.sweep_cancel = True
        _kill_assess_proc()
        state.assess_msg = "⏹ Cancelling Assess…"
        state.flush()

    opt_proc = [None]

    def _kill_opt_proc():
        p = opt_proc[0]
        if p is None or p.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                capture_output=True,
                text=True,
            )
        else:
            p.terminate()
        kill_cfd_containers()

    def cancel_optimize():
        if not state.opt_running:
            return
        state.opt_cancel = True
        _kill_opt_proc()
        state.opt_msg = "⏹ Cancelling optimize…"
        state.flush()

    def on_optimize_fan():
        if state.assess_busy or state.preview_busy or state.export_busy or state.opt_running:
            return
        try:
            trials = int(float(state.opt_trials))
        except (TypeError, ValueError):
            trials = 8
        trials = max(2, min(40, trials))
        resume = bool(state.opt_resume)
        out = opt_out_path(resume=resume, run_dir=run_dir)
        resume_study = None
        if resume:
            resume_study = study_name or "fansim"
        search_rpm = bool(state.opt_search_rpm)
        rpm_min = rpm_max = None
        if search_rpm:
            from fansim.optimize.pwm_table import pwm_caption, resolve_pwm_table

            try:
                lo = float(state.opt_rpm_min)
                hi = float(state.opt_rpm_max)
            except (TypeError, ValueError):
                lo, hi = 450.0, 2000.0
            try:
                tab = resolve_pwm_table(lo, hi)
            except ValueError as exc:
                state.opt_msg = f"⚠ PWM band invalid: {exc}"
                state.flush()
                return
            rpm_min, rpm_max = tab.rpm_min, tab.rpm_max
            state.opt_rpm_min = rpm_min
            state.opt_rpm_max = rpm_max
            state.opt_pwm_caption = pwm_caption(tab)
        from fansim.cfd.wall_roughness import FDM_WALL_KS_MM

        argv = optimization_argv(
            trials=trials,
            out=out,
            fan_model=str(state.fan_model or "a12x25"),
            preset=str(state.assess_preset or "case"),
            refine_op=bool(state.assess_refine_op),
            shroud=bool(state.opt_shroud),
            bem_floor=32.0 if state.opt_bem else 0.0,
            gp_floor=40.0 if state.opt_gp else 0.0,
            gp_boost=bool(state.opt_gp_boost),
            gp_nn=bool(state.opt_gp_nn),
            study_name=resume_study,
            stator=bool(state.opt_stator) and not bool(state.opt_stator_stack),
            stator_stack=bool(state.opt_stator_stack),
            sickle=bool(state.opt_sickle),
            stepped_inlet=bool(state.opt_stepped),
            notched_tips=bool(state.opt_notched),
            search_rpm=search_rpm,
            rpm_min=rpm_min,
            rpm_max=rpm_max,
            wall_ks_mm=FDM_WALL_KS_MM if state.assess_wall_ks else None,
            material=str(state.assess_material or "PETG"),
        )

        async def task():
            state.assess_busy = True
            state.opt_running = True
            state.opt_cancel = False
            mode = "resume" if resume else "new"
            t0 = time.time()
            note = f"{trials} trials, guided, mountable, {mode}"
            state.opt_msg = busy_caption("Optimize", 0, note=note)
            state.flush()
            kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                proc = subprocess.Popen(argv, **kwargs)
            except Exception as exc:  # noqa: BLE001
                state.opt_msg = f"⚠ Optimize failed to start: {type(exc).__name__}: {exc}"
                state.assess_busy = False
                state.opt_running = False
                state.flush()
                return
            opt_proc[0] = proc
            lines: list[str] = []
            log_q: queue.Queue = queue.Queue()
            with designs_lock:
                seen_keys: set[tuple[str, int]] = {
                    (str(d.extra.get("source_run") or ""), int(d.extra.get("orig_trial", d.trial)))
                    for d in user_designs
                    if d.extra.get("source") == "cockpit_opt"
                }
            last_poll = 0.0

            def reader():
                try:
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        log_q.put(line.rstrip())
                finally:
                    log_q.put(None)

            def poll_merge() -> int:
                try:
                    loaded = load_designs(out, resume_study)
                except Exception:  # noqa: BLE001
                    return 0
                fresh = merge_opt_designs(
                    loaded, source_run=out.name, existing_keys=seen_keys
                )
                append_user_designs(designs_lock, user_designs, by_trial, fresh)
                if fresh:
                    refresh_items()
                    refresh_figure()
                return len(fresh)

            def _opt_busy_body(extra: str = "") -> str:
                head = busy_caption("Optimize", time.time() - t0, note=note)
                body = "\n".join(lines[-18:])
                if extra:
                    body = f"{body}\n{extra}" if body else extra
                return f"{head}\n{body}" if body else head

            threading.Thread(target=reader, daemon=True).start()
            loop = asyncio.get_running_loop()

            def get_item():
                try:
                    return log_q.get(timeout=0.25)
                except queue.Empty:
                    return Ellipsis

            while True:
                item = await loop.run_in_executor(None, get_item)
                now = time.time()
                if now - last_poll >= 5.0:
                    last_poll = now
                    n_new = await loop.run_in_executor(None, poll_merge)
                    if n_new:
                        state.opt_msg = _opt_busy_body(
                            f"… live: +{n_new} trial(s) on plot ({len(seen_keys)} from this run)"
                        )
                        state.flush()
                    elif item is Ellipsis:
                        state.opt_msg = _opt_busy_body()
                        state.flush()
                if item is Ellipsis:
                    continue
                if item is None:
                    break
                lines.append(str(item))
                state.opt_msg = _opt_busy_body()
                state.flush()
            rc = proc.wait()
            opt_proc[0] = None
            if state.opt_cancel or rc not in (0, None):
                if state.opt_cancel:
                    state.opt_msg = (
                        f"{state.opt_msg}\n⏹ Cancelled." if state.opt_msg else "⏹ Cancelled."
                    )
                else:
                    tail = "\n".join(lines[-8:])
                    state.opt_msg = f"⚠ Optimize exited {rc}\n{tail}"
                await loop.run_in_executor(None, poll_merge)
                if resume:
                    await loop.run_in_executor(None, _resync_study_from_disk)
                refresh_items()
                refresh_figure()
                state.assess_busy = False
                state.opt_running = False
                state.opt_cancel = False
                state.flush()
                return
            n = await loop.run_in_executor(None, poll_merge)
            n_study = 0
            if resume:
                n_study = await loop.run_in_executor(None, _resync_study_from_disk)
            refresh_items()
            refresh_figure()
            state.opt_msg = (
                f"✓ Optimize finished → {out.name}. "
                f"{len(seen_keys)} merged from this run (trial ids +{OPT_TRIAL_OFFSET}; "
                f"+{n} on final merge)"
                + (f"; opened study now {n_study} feasible" if resume else "")
                + f"  · elapsed {format_elapsed(time.time() - t0)}"
                + ". Open Results and click a ◆ diamond for the 3-D impeller "
                "+ velocity arrows + duct midplane airflow when case fields are still on disk."
            )
            state.fan_subtab = "results"
            state.assess_busy = False
            state.opt_running = False
            state.flush()

        asynchronous.create_task(task())

    def _png_data_uri(path: Path | None) -> str:
        if path is None or not Path(path).is_file():
            return ""
        try:
            return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()
        except Exception:  # noqa: BLE001
            return ""

    def _apply_airflow_field():
        field = getattr(state, "airflow_field", "U") or "U"
        if field == "p" and state._airflow_p_uri:
            state.airflow_img_uri = state._airflow_p_uri
            state.airflow_caption = "pressure midplane — FRONT LEFT -> OUTLET RIGHT"
        elif state._airflow_u_uri:
            state.airflow_img_uri = state._airflow_u_uri
            state.airflow_caption = "Umag midplane — FRONT LEFT -> OUTLET RIGHT"
        elif state._airflow_p_uri:
            state.airflow_img_uri = state._airflow_p_uri
            state.airflow_caption = "pressure midplane — FRONT LEFT -> OUTLET RIGHT"
        else:
            state.airflow_img_uri = ""
            if not state.airflow_busy:
                state.airflow_caption = "Airflow not available for this design"

    def _clear_airflow(msg: str = "Airflow not available for this design"):
        state.airflow_busy = False
        state._airflow_u_uri = ""
        state._airflow_p_uri = ""
        state.airflow_img_uri = ""
        state.airflow_caption = msg
        _clear_glyphs("Velocity arrows not available for this design")

    def _schedule_airflow(d: Design):
        case = Path(d.stl_path).parent if d.has_model else None
        if case is None or d.extra.get("cfd_stale"):
            _clear_airflow("Airflow not available for this design")
            _apply_render(reset=False)
            return
        state.airflow_busy = True
        state.airflow_img_uri = ""
        state.airflow_caption = "Loading duct airflow midplane…"
        state._airflow_u_uri = ""
        state._airflow_p_uri = ""
        _clear_glyphs("Loading 3-D velocity arrows…")
        _apply_render(reset=False)
        token = int(d.trial)
        airflow_gen[0] += 1
        gen = airflow_gen[0]

        def _load_airflow_pack():
            with airflow_lock:
                if airflow_gen[0] != gen:
                    return None, None
                mid = ensure_midplane_artifacts(case)
                if airflow_gen[0] != gen:
                    return None, None
                gly = ensure_velocity_glyphs(case)
                return mid, gly

        async def task():
            try:
                loop = asyncio.get_running_loop()
                art, gly = await loop.run_in_executor(None, _load_airflow_pack)
                if state.selected_trial != token or art is None:
                    return
                if art.available:
                    state._airflow_u_uri = _png_data_uri(art.u_png)
                    state._airflow_p_uri = _png_data_uri(art.p_png)
                    state.airflow_busy = False
                    _apply_airflow_field()
                else:
                    state.airflow_busy = False
                    state._airflow_u_uri = ""
                    state._airflow_p_uri = ""
                    state.airflow_img_uri = ""
                    state.airflow_caption = art.caption or "Airflow not available for this design"
                if gly is not None and gly.available and gly.cloud is not None:
                    render_state["glyph_cloud"] = gly.cloud
                    state.glyph_caption = gly.caption
                    _rebuild_glyph_arrows()
                elif gly is not None:
                    _clear_glyphs(gly.caption or "Velocity arrows not available for this design")
                _apply_render(reset=False)
            except Exception:  # noqa: BLE001
                if state.selected_trial == token:
                    state.airflow_busy = False
                    state._airflow_u_uri = ""
                    state._airflow_p_uri = ""
                    state.airflow_img_uri = ""
                    state.airflow_caption = "Airflow not available for this design"
                    _clear_glyphs()
                    _apply_render(reset=False)
            finally:
                if state.selected_trial == token and airflow_gen[0] == gen:
                    state.airflow_busy = False
                try:
                    state.flush()
                    ctrl.view_update()
                except Exception:
                    pass

        asynchronous.create_task(task())

    @state.change("airflow_field")
    def _on_airflow_field(airflow_field=None, **_):
        _apply_airflow_field()
        try:
            state.flush()
        except Exception:
            pass

    def select(trial: int | None):
        _log.debug("select(%r)", trial)
        if trial is None:
            return
        d = by_trial.get(int(trial))
        if d is None:
            return
        state.library_parent_id = ""
        state.library_place_op = ""
        state.library_leftover = ""
        if d.has_model:
            _draw(d.stl_path, "lightsteelblue")
        else:
            plotter.clear_actors()
        o, p = d.objectives, d.params
        state.selected_trial = int(trial)
        state.info_lines = [
            f"Trial {d.trial}   {d.extra.get('n_blades')} blades" + ("   ★ Pareto" if d.is_pareto else ""),
            f"CFM free {o['cfm_free']:.1f}   CFM load {o['cfm_load']:.1f}"
            f"   efficiency {o['efficiency']:.1f}%",
            f"stagger r/m/t {p.get('stagger_root',0):.0f}/{p.get('stagger_mid',0):.0f}"
            f"/{p.get('stagger_tip',0):.0f}   camber {p.get('max_camber',0):.3f}",
            f"chord r/m/t {p.get('chord_root',0):.1f}/{p.get('chord_mid',0):.1f}"
            f"/{p.get('chord_tip',0):.1f}   sweep m/t {p.get('sweep_mid',0):.1f}"
            f"/{p.get('sweep_tip',0):.1f}",
        ]
        rpm = d.extra.get("actual_rpm", 0)
        spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
        if rpm and rpm < spec.rpm * 0.995:
            state.info_lines.append(
                f"⚙ motor-limited: runs at {rpm:.0f} RPM "
                f"({100*rpm/spec.rpm:.0f}% of {spec.rpm:.0f}) — flow already derated"
            )
        if d.extra.get("over_spec"):
            state.info_lines.append("⚠ OVER-SPEC: " + "; ".join(d.extra["over_spec"]))
        cap = score_caption(d.extra)
        if cap:
            state.info_lines.append(cap)
        if d.extra.get("preset"):
            state.assess_preset = d.extra["preset"]
        state.assess_refine_op = bool(d.extra.get("refine_op"))
        state.assess_wall_ks = float(d.extra.get("wall_ks_mm") or 0) > 0
        _init_editor(p)
        _set_baseline()
        if d.extra.get("cfd_stale"):
            parent_id = d.extra.get("parent_id") or ""
            op = d.extra.get("place_op") or ""
            state.info_lines.append("⧗ CFD stale — press Assess to score this hub.")
            if parent_id:
                state.info_lines.append(f"↳ placed from {parent_id}" + (f" ({op})" if op else ""))
            state.preview_msg = "Placed onto this hub. CFD is stale until you press Assess."
        else:
            state.preview_msg = "Edit the sliders below, then press Preview geometry."
        _schedule_airflow(d)
        try:
            ctrl.view_update()
        except Exception:
            pass

    @state.change("selected_trial")
    def _on_dropdown(selected_trial=None, **_):
        select(selected_trial)

    def _mf(v):
        try:
            return float(v) if v not in (None, "", "None") else None
        except (TypeError, ValueError):
            return None

    def save_measurement():
        tid = state.selected_trial
        d = by_trial.get(int(tid)) if tid is not None else None
        if d is None:
            state.meas_msg = "⚠ Select a design first (click a point or use the dropdown)."
            state.flush()
            return
        if _mf(state.meas_cfm) is None and _mf(state.meas_static) is None and _mf(state.meas_noise) is None:
            state.meas_msg = "⚠ Enter at least one measured value (CFM / static Pa / dB(A))."
            state.flush()
            return
        run = d.extra.get("source_run") or run_dir.name
        design_id = make_design_id(run, d.trial)
        sim = {
            "cfm_free": d.objectives.get("cfm_free"),
            "cfm_load": d.objectives.get("cfm_load"),
            "efficiency": d.objectives.get("efficiency"),
            "actual_rpm": d.extra.get("actual_rpm"),
        }
        rpm = _mf(state.meas_rpm) or d.extra.get("actual_rpm") or active_spec().rpm
        pt = MeasuredPoint(
            rpm=float(rpm),
            cfm=_mf(state.meas_cfm),
            static_pressure_pa=_mf(state.meas_static),
            noise_dba=_mf(state.meas_noise),
            source=state.meas_instrument or "",
        )
        rec = record_measurement(
            design_id,
            pt,
            run=run,
            trial=d.trial,
            stl_path=str(d.stl_path) if d.has_model else "",
            material=(state.meas_material or active_spec().material),
            print_type=state.meas_print_type or "",
            weight_g=_mf(state.meas_weight),
            sim=sim,
            instrument=state.meas_instrument,
            notes=state.meas_notes,
        )
        last = sim_vs_real(rec)[-1]
        parts = []
        if "cfm" in last:
            parts.append(
                f"CFM {last['cfm']['measured']:.1f} vs sim free {last['cfm']['sim']:.1f} "
                f"(sim over-reads {last['cfm']['pct_error']:+.0f}%)"
            )
        if "noise_dba" in last:
            parts.append(
                f"noise {last['noise_dba']['measured']:.1f} dBA "
                f"(Δ{last['noise_dba']['delta_db']:+.1f} vs sim)"
            )
        state.meas_msg = (
            f"✓ Saved to validation/measurements/ for {design_id} "
            f"({len(rec.measured)} point(s)). "
            + "  ".join(parts)
        )
        state.flush()

    def on_plotly_click(trial=None):
        if isinstance(trial, (list, tuple)):
            trial = trial[0] if trial else None
        if trial is None:
            return
        if trial == "stock":
            load_stock_reference()
            return
        try:
            state.selected_trial = int(trial)
        except (TypeError, ValueError):
            return
        state.flush()

    def load_stock_reference():
        if state.preview_busy or state.assess_busy:
            return
        key = str(state.fan_model or "a12x25")
        try:
            flat = stock_blade_flat(key)
        except KeyError:
            state.preview_msg = (
                f"⚠ No parametric stock geometry for '{key}'. "
                "Switch Fan model to a12x25 (Noctua) to load the reference blade."
            )
            state.flush()
            return
        except FileNotFoundError as exc:
            state.preview_msg = f"⚠ Stock geometry file missing: {exc}"
            state.flush()
            return

        from fansim.cockpit.placement import fit_envelope
        from fansim.cockpit.stock_cache import (
            stock_cache_hit,
            stock_cache_paths,
            write_stock_cache_meta,
        )

        spec = active_spec()
        # Bake frame/mount fit into the editor so gold ✕ does not need a manual Fit.
        fitted = fit_envelope(flat, spec, features=Features())
        flat = fitted.flat
        load_pa, hose = assess_load(str(state.assess_preset or "case"))
        pub = published_scatter_point(spec, load_pa)
        _init_editor(flat, Features())
        state.selected_trial = None
        state.fan_subtab = "design"
        state.edited_stale = False
        fit_note = ""
        if fitted.changes:
            bits = ", ".join(f"{c.field}→{c.after:g}" for c in fitted.changes[:4])
            fit_note = f" Frame-fit applied ({bits})."
        state.info_lines = [
            f"Stock reference — {spec.name} (parametric, not OEM CAD)",
            (
                f"Published free {pub['cfm_free']:.1f} CFM · hose-est load "
                f"{pub['cfm_load']:.1f} CFM ({hose})"
                if pub
                else "No published CFM on this fan model."
            ),
            "Sliders = Stock recipe (frame-fitted). Edit then Preview / Assess for CFD ◆."
            + fit_note,
        ]
        state.preview_msg = "Loading stock 3-D preview…"
        state.stale_msg = (
            "Stock reference loaded — geometry is a parametric stand-in for the real fan. "
            "Edit freely; re-Assess after changes for CFD numbers."
        )
        _clear_airflow("Stock reference — no CFD case (Assess to generate airflow viz).")
        state.glyph_caption = "Loading schematic flow arrows…"
        state.flush()

        flat_s, feat_s = edit_flat(), edit_features()
        cache_stl, _cache_meta = stock_cache_paths(key)

        def _ensure_stock_preview() -> Path:
            hit = stock_cache_hit(key, flat_s, preview=True)
            if hit is not None:
                return hit
            from fansim.geometry.isolated import build_stl_isolated

            cache_stl.parent.mkdir(parents=True, exist_ok=True)
            # Fast fused-free preview mesh for gold ✕ (Export / Assess still do full solids).
            build_stl_isolated(flat_s, feat_s, cache_stl, timeout=300.0, preview=True)
            write_stock_cache_meta(key, flat_s, preview=True)
            return cache_stl

        async def task():
            state.preview_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Stock preview",
                msg_attr="preview_msg",
                busy_attr="preview_busy",
                note="cached parametric mesh" if stock_cache_hit(key, flat_s, preview=True) else "building Stock cache once",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                path = await loop.run_in_executor(None, _ensure_stock_preview)
                _draw(path, "gold")
                from fansim.cfd.glyphs import schematic_axial_flow_cloud

                hub_r = float(flat_s.get("hub_radius") or 21.5)
                tip_r = float(flat_s.get("tip_radius") or (active_spec().tip_dia_mm[1] / 2.0 - 0.5))
                z_span = float(flat_s.get("hub_height") or 22.0)
                render_state["glyph_cloud"] = schematic_axial_flow_cloud(
                    hub_radius_mm=hub_r,
                    tip_radius_mm=tip_r,
                    z_span_mm=max(z_span, 20.0),
                )
                state.glyph_caption = (
                    "Schematic axial flow (stock has no CFD case — Assess for real velocity arrows)"
                )
                _rebuild_glyph_arrows()
                _apply_render(reset=False)
                cached = stock_cache_hit(key, flat_s, preview=True) is not None
                state.preview_msg = (
                    f"✓ Stock reference loaded ({spec.name})"
                    + (" — cached mesh." if cached else " — cached for next click.")
                    + " Gold = parametric Stock; published CFM is the ✕, not this mesh's CFD."
                )
            except Exception as exc:  # noqa: BLE001
                state.preview_msg = f"⚠ Stock preview failed: {exc}"
            finally:
                state.preview_busy = False
                ticker.cancel()
                try:
                    state.flush()
                    ctrl.view_update()
                except Exception:
                    pass

        asynchronous.create_task(task())

    # Expose callbacks for the UI renderer (render_fan_tab).
    ctx.fan_select = select  # type: ignore[attr-defined]
    ctx.fan_on_plotly_click = on_plotly_click  # type: ignore[attr-defined]
    ctx.fan_load_stock_reference = load_stock_reference  # type: ignore[attr-defined]
    ctx.fan_do_preview = do_preview  # type: ignore[attr-defined]
    ctx.fan_on_assess = on_assess  # type: ignore[attr-defined]
    ctx.fan_export_stl_current = export_stl_current  # type: ignore[attr-defined]
    ctx.fan_on_optimize = on_optimize_fan  # type: ignore[attr-defined]
    ctx.fan_cancel_optimize = cancel_optimize  # type: ignore[attr-defined]
    ctx.fan_cancel_assess = cancel_assess  # type: ignore[attr-defined]
    ctx.fan_on_sweep = on_sweep  # type: ignore[attr-defined]
    ctx.fan_cancel_sweep = cancel_sweep  # type: ignore[attr-defined]
    ctx.fan_on_fit_envelope = on_fit_envelope  # type: ignore[attr-defined]
    ctx.fan_on_scale_to_hub = on_scale_to_hub  # type: ignore[attr-defined]
    ctx.fan_randomize_geometry = randomize_geometry  # type: ignore[attr-defined]
    ctx.fan_randomize_features = randomize_features  # type: ignore[attr-defined]
    ctx.fan_select_library_design = select_library_design  # type: ignore[attr-defined]
    ctx.fan_on_library_scale_to_hub = on_library_scale_to_hub  # type: ignore[attr-defined]
    ctx.fan_load_model_into_form = load_model_into_form  # type: ignore[attr-defined]
    ctx.fan_save_model = save_model  # type: ignore[attr-defined]
    ctx.fan_delete_model = delete_model  # type: ignore[attr-defined]
    ctx.fan_save_measurement = save_measurement  # type: ignore[attr-defined]
    ctx.fan_hub_designs = _hub_designs  # type: ignore[attr-defined]
    ctx.fan_active_spec = active_spec  # type: ignore[attr-defined]


