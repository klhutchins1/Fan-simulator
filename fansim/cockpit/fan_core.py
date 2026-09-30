"""Fan-tab core binder: reactive-state defaults + shared services (§13.9).

``apply_state_defaults`` seeds every ``state.*`` the Fan tab reads before a design is
selected. ``bind`` defines the widely-shared services (active_spec, the hub/design
lookups, and the Results dropdown/scatter refreshers) and attaches them to the
``FanSession`` so the other binders can call them via ``session.<name>``.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

from fansim.catalog import load_catalog, results_for_hub
from fansim.cockpit.data import Design, feasible_designs, load_designs
from fansim.cockpit.errors import log_caught
from fansim.cockpit.fan_helpers import _has_real_cfm
from fansim.cockpit.figures import filter_fitting_designs, scatter_figure
from fansim.cockpit.library_view import library_list_items
from fansim.cockpit.placement import fit_envelope, nominal_fits_spec
from fansim.fan_spec import (
    fan_spec_names,
    get_fan_spec,
    is_builtin,
    published_scatter_point,
)
from fansim.optimize.presets import assess_load, assess_preset_items

_log = logging.getLogger(__name__)

# Reserved trial id for the synthetic published-reference entry in the runs dropdown
# (well above user-assessed ids, which start at 9000). Selectable, but never scored/saved.
A12X25_REF_TRIAL = 100000


def apply_state_defaults(session) -> None:
    """Seed all Fan-tab reactive state (order-independent literal defaults)."""
    from fansim.manufacturability.materials import DEFAULT_MATERIAL, MATERIALS
    from fansim.optimize.pwm_table import pwm_caption

    state = session.state

    state.selected_trial = None
    state.info_lines = ["Select a design (click a point or use the dropdown)."]
    state.preview_msg = "Select a design, then edit and press Preview geometry."
    state.export_msg = ""
    state.export_busy = False
    state.export_fit_hub = True
    state.export_fit_frame = True
    state.export_also_mirror = False  # §19.4 CW⇄CCW pair beside the primary STL
    state.preview_motor_cup = True
    state.assess_preset = "case"
    state.assess_preset_items = assess_preset_items()
    state.assess_refine_op = False
    state.assess_wall_ks = False
    state.assess_material = DEFAULT_MATERIAL
    state.assess_material_items = [
        {"title": f"{k} — {MATERIALS[k].note}" if MATERIALS[k].note else k, "value": k}
        for k in MATERIALS
        if MATERIALS[k].blade_suitable
    ]
    state.multi_point_msg = ""  # §20.6 BEM duty-cycle readout
    # §20.4 meanline seed-from-duty (Design panel)
    state.seed_duty_cfm = 60.0
    state.seed_duty_pa = 15.0
    state.seed_duty_rpm = 2000.0
    state.seed_duty_vortex = "free"
    state.seed_duty_vortex_items = [
        {"title": "Free vortex (r·Cu = const)", "value": "free"},
        {"title": "Forced vortex (Cu ∝ r)", "value": "forced"},
    ]
    state.seed_duty_msg = ""
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
    state.show_dir_cues = True  # rotation (CCW) + airflow (−Z) direction cues in the 3-D view
    state.fan_subtab = "design"
    state.airflow_img_uri = ""
    state.airflow_caption = "Select a scored design to load duct airflow (midplane)."
    state.airflow_field = "U"
    state.airflow_busy = False
    state._airflow_u_uri = ""
    state._airflow_p_uri = ""
    state._airflow_uz_uri = ""       # axial-velocity (Uz) cut-plane
    state._airflow_stream_uri = ""   # streamlines colored by |U|
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
    state.hub_fit_info = ""
    state.tip_fit_info = ""
    state.depth_fit_info = ""
    # fan-model MANAGER
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
    # sweep
    state.sweep_param = "stagger mid"
    state.sweep_steps = 3
    state.sweep_active = False
    state.sweep_cancel = False
    state.sweep_progress = 0


def bind(session) -> None:
    state, ctrl = session.state, session.ctrl
    run_dir = session.run_dir
    study_designs = session.study_designs
    user_designs = session.user_designs
    by_trial = session.by_trial
    designs_lock = session.designs_lock
    study_name = session.study_name

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
        from validation.store import make_design_id

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

    def _register_reference_design():
        """Synthetic published-reference entry for the runs dropdown (a12x25 only).

        Registered in ``by_trial`` so it is selectable/loadable (drops the parametric stock
        recipe into the editor), but NOT added to study/user designs, so it does not duplicate
        the published scatter star. Returns the dropdown item, or None when not applicable.
        """
        if str(state.fan_model) != "a12x25":
            by_trial.pop(A12X25_REF_TRIAL, None)
            return None
        try:
            spec = get_fan_spec("a12x25")
            if not spec.ref_cfm:
                return None
            from fansim.geometry.features import Features
            from fansim.optimize.search_space import stock_blade_flat

            flat = fit_envelope(stock_blade_flat("a12x25"), spec, features=Features()).flat
            load_pa, _hose = assess_load(str(state.assess_preset or "case"))
            pub = published_scatter_point(spec, load_pa)
            cfm_free = float(spec.ref_cfm)
            cfm_load = float(pub["cfm_load"]) if pub else cfm_free
        except Exception as exc:  # noqa: BLE001 - reference entry is best-effort
            log_caught(_log, "reference dropdown entry", exc, level=logging.DEBUG)
            return None
        by_trial[A12X25_REF_TRIAL] = Design(
            trial=A12X25_REF_TRIAL,
            params=dict(flat),
            objectives={"cfm_free": cfm_free, "cfm_load": cfm_load, "efficiency": 0.0},
            feasible=True,
            is_pareto=False,
            stl_path=None,
            extra={"n_blades": flat.get("n_blades"), "fan_model": "a12x25",
                   "source": "reference", "is_reference": True},
        )
        return {"title": "◆ Reference · Noctua A12x25 (published)", "value": A12X25_REF_TRIAL}

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
        ref_item = _register_reference_design()
        if ref_item is not None:
            items.insert(0, ref_item)
        state.trial_items = items

    def refresh_library():
        spec = active_spec()
        items = library_list_items(load_catalog(), spec)
        state.library_items = items
        n = sum(1 for it in items if it.get("role") == "row")
        state.library_info = (
            f"{n} recipe(s) — click Fits this hub and draws it. " "Scale shrinks a huge recipe first."
        )

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

    session._label = _label
    session._design_id = _design_id
    session._purge_sentinel_user_designs = _purge_sentinel_user_designs
    session.active_spec = active_spec
    session._hub_designs = _hub_designs
    session._resync_study_from_disk = _resync_study_from_disk
    session.refresh_items = refresh_items
    session.refresh_library = refresh_library
    session._thin = _thin
    session.refresh_figure = refresh_figure
