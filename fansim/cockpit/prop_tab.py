"""Propeller cockpit tab (instant BEMT design + optional CFD refine).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import random
import sys
import threading
import time
from pathlib import Path

_log = logging.getLogger(__name__)

from fansim.cockpit.airflow_panel import pick_airflow_uri, render_airflow_pack
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.data import design_dropdown_items
from fansim.cockpit.fan_widgets import slider as _shared_slider
from fansim.cockpit.figures import prop_mission_figure, prop_scatter_figure
from fansim.cockpit.paths import exports_dir, session_tmp
from fansim.cockpit.plotters import ensure_plotter
from fansim.cockpit.tab_shell import (
    SCATTER_HEIGHT_PX,
    VTK_VIEW_STYLE,
    render_action_row,
    render_left_shell,
)
from fansim.prop_spec import get_prop_spec, prop_spec_names
from fansim.propeller.airflow_case import first_prop_cfd_workdir, prop_cfd_workdir_from_study
from fansim.propeller.bemt import analyze as bemt_analyze
from fansim.propeller.honesty import PROP_BEMT_HONESTY, PROP_CFD_HONESTY
from fansim.propeller.noise import estimate_prop_noise
from fansim.propeller.optimize import (
    random_prop_flat,
    run_prop_study,
)
from fansim.propeller.optimize import (
    refine_pareto_cfd as refine_prop_pareto_cfd,
)
from fansim.propeller.persist import (
    PROP_ASSESS_DIRNAME,
    latest_prop_study_dir,
    load_all_prop_results,
    merge_prop_rows,
    prop_out_path,
    prop_row_from_bemt,
    save_prop_analyze_point,
)
from fansim.propeller.polar import DEFAULT_V_INF_MS, run_bemt_polar

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



def prop_static_headline(spec) -> str:
    """First readout line: these grams are hover at rpm_max, not a cruise figure (23.18)."""
    return (
        f"⚙ {spec.n_blades}-blade  {spec.diameter_in}×{spec.pitch_in:.1f} in  "
        f"@ {spec.rpm_max:,.0f} rpm (max), static"
    )


def prop_reference_line(spec, perf) -> str:
    """Compare BEMT thrust/power with the class's typical figures (roadmap §23.18).

    A 5" FPV prop reading 2087 g / 743 W looked implausible with nothing to compare against; the
    preset's own typical figures (1850 g / 650 W at 30k rpm) put that at about +13 % / +14 %,
    consistent with the open BEMT over-prediction (Audit #3). The reference is moved to the
    evaluated RPM with the affinity laws (thrust ∝ n², power ∝ n³).
    """
    ref_t, ref_p, ref_n = (getattr(spec, k, None) for k in ("ref_thrust_g", "ref_power_w", "ref_rpm"))
    n = float(getattr(spec, "rpm_max", 0.0) or 0.0)
    if not ref_t or not ref_n or n <= 0:
        return ""
    k = n / float(ref_n)
    t_ref = float(ref_t) * k * k
    bits = [f"Typical for this class @ {n:.0f} rpm: {t_ref:.0f} g"]
    dt = 100.0 * (float(perf.thrust_g) / t_ref - 1.0)
    tail = f"BEMT thrust {dt:+.0f}%"
    if ref_p:
        p_ref = float(ref_p) * k ** 3
        bits.append(f"{p_ref:.0f} W")
        tail += f", power {100.0 * (float(perf.power_w) / p_ref - 1.0):+.0f}%"
    return " / ".join(bits) + f" → {tail} (BEMT is a ranking estimate, not a measurement)"

def prop_cfd_mesh_knobs(preset: str) -> tuple[float, int]:
    p = (preset or "smoke").strip().lower()
    if p == "refine":
        return (0.004, 600)
    return (0.005, 400)


def prop_mission_kwargs(mission, weight_n, n_rotors, battery_wh, cruise_mps, min_minutes) -> dict:
    """Arguments for ``run_prop_study`` besides trials, power cap, directory, and model."""
    mission = str(mission or "thrust_efficiency")
    if mission == "thrust_efficiency":
        return {"ok": True, "kwargs": {"mission": mission}}
    if mission == "quiet_thrust":
        text = str(min_minutes).strip()
        if text == "":
            return {"ok": True, "kwargs": {"mission": mission}}
        try:
            floor = float(text)
        except (TypeError, ValueError):
            return {"ok": False, "message": "minimum hover minutes must be a positive number"}
        if floor <= 0.0:
            return {"ok": False, "message": "minimum hover minutes must be a positive number"}
        vehicle = _vehicle(weight_n, n_rotors, battery_wh)
        if not vehicle["ok"]:
            return vehicle
        return {"ok": True, "kwargs": {"mission": mission, "min_hover_minutes": floor, **vehicle["fields"]}}
    vehicle = _vehicle(weight_n, n_rotors, battery_wh)
    if not vehicle["ok"]:
        return vehicle
    fields = {"mission": mission, **vehicle["fields"]}
    if mission == "hover_endurance":
        return {"ok": True, "kwargs": fields}
    if mission == "range":
        try:
            cruise = float(cruise_mps)
        except (TypeError, ValueError):
            cruise = 0.0
        if cruise <= 0.0:
            return {"ok": False, "message": "cruise speed must be positive"}
        fields["cruise_mps"] = cruise
        return {"ok": True, "kwargs": fields}
    return {"ok": False, "message": f"unknown mission {mission}"}


def _vehicle(weight_n, n_rotors, battery_wh) -> dict:
    try:
        weight = float(weight_n)
        rotors = int(float(n_rotors))
        battery = float(battery_wh)
    except (TypeError, ValueError):
        return {"ok": False, "message": "weight, rotors, and battery must be numbers"}
    if weight <= 0.0:
        return {"ok": False, "message": "all-up weight must be positive"}
    if rotors < 1:
        return {"ok": False, "message": "rotor count must be at least 1"}
    if battery <= 0.0:
        return {"ok": False, "message": "battery watt-hours must be positive"}
    return {"ok": True, "fields": {
        "all_up_weight_n": weight, "n_rotors": rotors, "battery_wh": battery,
    }}


def prop_polar_backend_items(ui_mode: str) -> list[dict]:
    """BEMT polar choices. NeuralFoil stays Expert-only until it converges (QA-51)."""
    items = [{"title": "UIUC tables (default)", "value": "table"}]
    if str(ui_mode or "simple") == "expert":
        items.append({
            "title": "NeuralFoil (experimental, needs --extra neuralfoil)",
            "value": "neuralfoil",
        })
    return items


def _apply_prop_polar_backend_items(state, ui_mode) -> None:
    mode = str(ui_mode or "simple")
    state.prop_polar_backend_items = prop_polar_backend_items(mode)
    backend = str(getattr(state, "prop_polar_backend", "table") or "table")
    if mode != "expert" and backend == "neuralfoil":
        state.prop_polar_backend = "table"


def setup_prop_tab(ctx: CockpitCtx) -> None:
    """Init prop_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    runs_root = ctx.runs_root
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # ---- PROPELLER ARCHETYPE ---------------------------------------------------------------
    prop_preview_stl = session_tmp("fansim_prop_preview.stl")  # per-cockpit (QA UI-30)
    prop_pareto_store: list[dict] = []  # Optimize rows (click index base)
    prop_user_store: list[dict] = []  # Analyze rows (appended after Optimize in click index)

    # Shared objects for render + callbacks (kept per-session).
    ctx.prop_preview_stl = prop_preview_stl  # type: ignore[attr-defined]
    ctx.prop_pareto_store = prop_pareto_store  # type: ignore[attr-defined]
    ctx.prop_user_store = prop_user_store  # type: ignore[attr-defined]

    state.prop_model = "fpv_5inch"
    state.prop_models = prop_spec_names()
    state.prop_model_items = [
        {"title": get_prop_spec(k).name, "value": k}
        for k in state.prop_models
    ]
    state.prop_info = "Pick a size, tune the blade, then Analyze (instant) or Optimize."
    state.prop_design_panels = [0]  # Geometry open; Optimize closed (§21.1c)
    state.prop_ux_banner = True  # dismissible BEMT honesty (§21.1c / §21.2d)
    state.prop_readout = ["Press Analyze (~1 s) to see thrust, efficiency (g/W), and power."]
    state.prop_busy = False
    state.prop_opt_running = False
    state.prop_subtab = "design"
    state.prop_cfd_mesh_items = ["smoke", "refine"]
    state.prop_export_items = []
    state.prop_msg = ""
    state.prop_export_msg = ""
    state.prop_export_busy = False
    state.prop_trials = 400
    state.prop_maxpower = 700.0
    state.prop_pareto = []  # display rows for the optimizer front table
    state.prop_resume = False
    state.prop_mission = "thrust_efficiency"
    state.prop_mission_items = [
        {"title": "Thrust & efficiency", "value": "thrust_efficiency"},
        {"title": "Quiet thrust", "value": "quiet_thrust"},
        {"title": "Hover endurance", "value": "hover_endurance"},
        {"title": "Cruise range", "value": "range"},
    ]
    state.prop_weight_n = 5.0
    state.prop_n_rotors = 4
    state.prop_battery_wh = 50.0
    state.prop_cruise_mps = 15.0
    state.prop_min_minutes = ""
    state.prop_cfd_top = 0
    state.prop_cfd_mesh_preset = "smoke"
    state.prop_bemt_floor = 0.0
    state.prop_polar_backend = "table"  # §19.15 / §20.2: table | neuralfoil
    _apply_prop_polar_backend_items(state, getattr(state, "ui_mode", "simple"))

    @state.change("ui_mode")
    def _prop_polar_items_follow_mode(ui_mode=None, **_kwargs):
        _apply_prop_polar_backend_items(state, ui_mode)

    state.prop_refine_busy = False
    state.prop_polar_v = "0,5,10,15,20"
    state.prop_geo_ready = False
    # VSelect items must be bound through a state var: trame treats a raw list passed to
    # ``items=[...]`` as a ``(state_var, default)`` binding and calls ``.startswith`` on the first
    # element (a dict) -> the whole select renders as an html-error. Bind by name instead.
    state.p_thick_mode_items = [
        {"title": "Tapered t/c", "value": "tapered"},
        {"title": "Uniform wall mm", "value": "uniform"},
    ]
    _prop_runs = runs_root if runs_root.exists() else Path("runs")
    _prop_last = latest_prop_study_dir(_prop_runs)
    state.prop_last_opt = str(_prop_last) if _prop_last else ""
    state.prop_has_front = False  # set True after load / Optimize
    state.prop_airflow_field = "U"
    state.prop_airflow_img_uri = ""
    state.prop_airflow_caption = "Run CFD refine to see open-air airflow for a scored case."
    state.prop_airflow_busy = False

    def _init_prop_editor(spec, flat: dict | None = None):
        """Load prop sliders from a spec (+ optional Pareto/Analyze flat)."""
        from fansim.cockpit.blade_editor import apply_shape_flat_to_state, init_shape_state
        from fansim.propeller.params_io import prop_design_defaults

        flat = flat or {}
        state.p_n_blades = int(flat.get("n_blades", spec.n_blades))
        state.p_pitch = float(flat.get("pitch_in", spec.pitch_in))
        state.p_chord_root = float(flat.get("chord_root", 0.20))
        state.p_chord_mid = float(flat.get("chord_mid", 0.26))
        state.p_chord_tip = float(flat.get("chord_tip", 0.10))
        # Legacy single camber for older UI bindings / readout.
        if "camber_mid" in flat:
            state.p_camber = float(flat["camber_mid"])
        elif "camber" in flat:
            state.p_camber = float(flat["camber"])
        else:
            state.p_camber = 0.04
        base = prop_design_defaults()
        base.update({k: flat[k] for k in flat if k in base})
        if "camber" in flat and "camber_mid" not in flat:
            c = float(flat["camber"])
            base["camber_root"] = base["camber_mid"] = base["camber_tip"] = c
        apply_shape_flat_to_state(state, "p_", base)
        # Ensure thick_mode select exists even if init skipped.
        if not hasattr(state, "p_thick_mode"):
            init_shape_state(state, "p_", base)

    def _prop_click_store() -> list[dict]:
        return list(prop_pareto_store) + list(prop_user_store)

    state.prop_sel_idx = None  # previous-runs dropdown (loads by click index)
    state.prop_trial_items = design_dropdown_items(_prop_click_store(), by_index=True)

    def _prop_table_rows(store: list[dict], limit: int = 14) -> list[dict]:
        rows = []
        for i, r in enumerate(store[:limit]):
            p = r.get("params") or {}
            rows.append(
                {
                    "idx": i,
                    "thrust": f"{r['thrust_g']:.0f}",
                    "eff": f"{r['eff_g_per_w']:.2f}",
                    "power": f"{float(r.get('power_w') or 0):.0f}",
                    "fm": f"{float(r.get('fm') or 0):.2f}",
                    "nb": r.get("n_blades"),
                    "pitch": f"{float(p.get('pitch_in') or 0):.1f}",
                    "noise": f"{r['rel_dba']:.0f}" if r.get("rel_dba") is not None else "—",
                }
            )
        return rows

    def _refresh_prop_figure():
        if hasattr(ctrl, "prop_fig_update"):
            mission = str(state.prop_mission)
            if mission == "hover_endurance":
                fig = prop_mission_figure(
                    prop_pareto_store, prop_user_store,
                    y_key="hover_minutes", y_title="hover (min)",
                )
            elif mission == "range":
                fig = prop_mission_figure(
                    prop_pareto_store, prop_user_store,
                    y_key="range_km", y_title="range (km)",
                )
            else:
                fig = prop_scatter_figure(prop_pareto_store, prop_user_store)
            ctrl.prop_fig_update(fig)
        state.prop_trial_items = design_dropdown_items(_prop_click_store(), by_index=True)

    def _reload_prop_from_disk():
        """Load Optimize + Analyze points from runs/ into the in-memory stores."""
        loaded = load_all_prop_results(runs_root if runs_root.exists() else Path("runs"))
        opt = [r for r in loaded if str(r.get("source")) != "analyze"]
        user = [r for r in loaded if str(r.get("source")) == "analyze"]
        prop_pareto_store.clear()
        prop_pareto_store.extend(opt)
        prop_user_store.clear()
        prop_user_store.extend(user)
        state.prop_pareto = _prop_table_rows(_prop_click_store())

    # --- Open-air airflow viz (§17.3 Prop): same pack as Mixed/CROR, axial freestream ----------
    _prop_airflow = {"uris": {}, "gen": 0}

    def _apply_prop_airflow_field():
        uri, cap = pick_airflow_uri(_prop_airflow["uris"], state.prop_airflow_field or "U")
        state.prop_airflow_img_uri = uri
        if uri:
            state.prop_airflow_caption = cap
        elif not state.prop_airflow_busy:
            state.prop_airflow_caption = "Run CFD refine to see open-air airflow for a scored case."

    def _render_prop_airflow(case_dir):
        if not case_dir or asynchronous is None:
            _prop_airflow["uris"] = {}
            state.prop_airflow_img_uri = ""
            state.prop_airflow_caption = "Run CFD refine to see open-air airflow for a scored case."
            return
        _prop_airflow["gen"] += 1
        gen = _prop_airflow["gen"]
        state.prop_airflow_busy = True
        state.prop_airflow_img_uri = ""
        state.prop_airflow_caption = "Rendering open-air airflow…"
        state.flush()

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(
                    None, lambda: render_airflow_pack(str(case_dir)))
                if _prop_airflow["gen"] != gen:
                    return
                _prop_airflow["uris"] = pack["uris"]
                state.prop_airflow_busy = False
                _apply_prop_airflow_field()
            except Exception:  # noqa: BLE001 — viz must never break the tab
                if _prop_airflow["gen"] == gen:
                    _prop_airflow["uris"] = {}
                    state.prop_airflow_busy = False
                    state.prop_airflow_img_uri = ""
                    state.prop_airflow_caption = "Airflow not available for this design"
            finally:
                try:
                    state.flush()
                    ctrl.prop_view_update()
                except Exception:  # noqa: BLE001, S110
                    pass

        asynchronous.create_task(task())

    @state.change("prop_airflow_field")
    def _on_prop_airflow_field(**_):
        _apply_prop_airflow_field()
        try:
            state.flush()
        except Exception:  # noqa: BLE001, S110
            pass

    _init_prop_editor(get_prop_spec(state.prop_model))
    _reload_prop_from_disk()
    state.prop_has_front = bool(prop_pareto_store) or bool(prop_user_store)

    def _prop_model_readout():
        s = get_prop_spec(state.prop_model)
        tip_ms = s.tip_speed_ms(s.rpm_max)
        state.prop_info = (
            f"{s.name}: {s.diameter_in}×{s.pitch_in} in, {s.n_blades}-blade, "
            f"{s.shaft.shaft_dia_mm:.0f} mm shaft, ≤{s.rpm_max:.0f} rpm "
            f"(tip {tip_ms:.0f} m/s, Mach {s.tip_mach(s.rpm_max):.2f}). {s.material}."
        )

    _prop_model_readout()

    @state.change("prop_model")
    def _on_prop_model(**_):
        _init_prop_editor(get_prop_spec(state.prop_model))
        _prop_model_readout()

    def prop_editor_spec():
        """The selected prop envelope with the editor's blade-count + pitch applied."""
        return dataclasses.replace(
            get_prop_spec(state.prop_model),
            n_blades=int(state.p_n_blades),
            pitch_in=float(state.p_pitch),
        )

    def prop_editor_params():
        from fansim.cockpit.blade_editor import shape_flat_from_state
        from fansim.propeller.params_io import prop_params_from_flat

        flat = {
            "n_blades": int(state.p_n_blades),
            "pitch_in": float(state.p_pitch),
            "chord_root": float(state.p_chord_root),
            "chord_mid": float(state.p_chord_mid),
            "chord_tip": float(state.p_chord_tip),
            **shape_flat_from_state(state, "p_"),
        }
        # Keep legacy p_camber in sync with mid when the user moves mid.
        state.p_camber = float(flat["camber_mid"])
        return prop_params_from_flat(prop_editor_spec(), flat)

    def _prop_flat_from_state() -> dict:
        from fansim.cockpit.blade_editor import shape_flat_from_state

        return {
            "n_blades": int(state.p_n_blades),
            "pitch_in": float(state.p_pitch),
            "chord_root": float(state.p_chord_root),
            "chord_mid": float(state.p_chord_mid),
            "chord_tip": float(state.p_chord_tip),
            **shape_flat_from_state(state, "p_"),
        }

    def _draw_prop(path):
        prop_plotter = ensure_plotter(ctx, "prop_plotter")
        if prop_plotter is None:
            return
        prop_plotter.clear_actors()
        try:
            prop_plotter.add_mesh(pv.read(str(path)), color="cadetblue", smooth_shading=True)
            prop_plotter.reset_camera()
        except Exception:  # noqa: BLE001, S110 - nothing to show
            pass
        try:
            ctrl.prop_view_update()
        except Exception:  # noqa: BLE001, S110
            pass

    def _prop_perf_lines(spec, params):
        """BEMT readout for the current prop: static hover thrust/eff/FM + a forward-flight note."""
        from fansim.propeller.bemt import get_polar_backend, set_polar_backend

        backend = str(state.prop_polar_backend or "table").strip().lower()
        prev = get_polar_backend()
        try:
            if backend in ("table", "neuralfoil"):
                set_polar_backend(backend)
            perf = bemt_analyze(params, rpm=spec.rpm_max)
            lines = [
                prop_static_headline(spec),
                f"Thrust {perf.thrust_g:.0f} g   ·   {perf.efficiency_g_per_w:.2f} g/W   ·   {perf.power_w:.0f} W",
                f"Figure of merit {perf.figure_of_merit:.2f}   (0.6–0.8 = a good real prop)",
                f"Polar backend: {get_polar_backend()}",
            ]
            ref_line = prop_reference_line(spec, perf)
            if ref_line:
                lines.insert(2, ref_line)
            nz = estimate_prop_noise(params, spec.rpm_max, perf)
            lines.append(
                f"🔉 Noise {nz['rel_dba']:.0f} (relative) · tip Mach {nz['tip_mach']:.2f} · "
                f"BPF {nz['bpf_hz']:.0f} Hz  (relative rank, not calibrated dBA)"
            )
            # Forward-flight polar (BEMT) — V∞ list from the editor
            try:
                from fansim.propeller.polar import parse_float_list

                raw = parse_float_list(str(state.prop_polar_v or ""))
                v_list = raw if raw else list(DEFAULT_V_INF_MS)
            except Exception:  # noqa: BLE001
                v_list = list(DEFAULT_V_INF_MS)
            try:
                pts = run_bemt_polar(params, spec.rpm_max, v_list)
                bits = []
                for p in pts[:6]:
                    eta = f"{100 * p.eta:.0f}%" if p.eta is not None else "—"
                    bits.append(f"V∞={p.v_inf:.0f} J={p.J:.2f} η={eta}")
                if bits:
                    lines.append("Polar (BEMT): " + " · ".join(bits))
            except Exception:  # noqa: BLE001
                fwd = bemt_analyze(params, rpm=spec.rpm_max, v_forward=15.0)
                if fwd.prop_efficiency is not None:
                    lines.append(f"At 15 m/s forward: prop efficiency {100 * fwd.prop_efficiency:.0f}%")
            return lines
        finally:
            set_polar_backend(prev)

    def analyze_prop(persist=True, **_):
        """Instant BEMT readout, then an async 3-D preview build (geometry is the slow part).

        Analyze button persists a diamond onto the prop scatter; scatter clicks pass
        ``persist=False`` so reloads do not spam ``cockpit_prop_assess``.
        """
        if not isinstance(persist, bool):
            persist = True
        if state.prop_busy:
            return
        spec, params = prop_editor_spec(), prop_editor_params()
        try:
            state.prop_readout = _prop_perf_lines(
                spec, params
            )  # BEMT is instant — show it now
            if persist:
                from fansim.propeller.bemt import get_polar_backend, set_polar_backend

                backend = str(state.prop_polar_backend or "table").strip().lower()
                prev = get_polar_backend()
                try:
                    if backend in ("table", "neuralfoil"):
                        set_polar_backend(backend)
                    perf = bemt_analyze(params, rpm=spec.rpm_max)
                finally:
                    set_polar_backend(prev)
                nz = estimate_prop_noise(params, spec.rpm_max, perf)
                flat = _prop_flat_from_state()
                row = prop_row_from_bemt(
                    params_flat=flat,
                    thrust_g=perf.thrust_g,
                    eff_g_per_w=perf.efficiency_g_per_w,
                    power_w=perf.power_w,
                    fm=perf.figure_of_merit,
                    rel_dba=nz.get("rel_dba"),
                    tip_mach=nz.get("tip_mach"),
                    prop_model=str(state.prop_model),
                    n_blades=int(state.p_n_blades),
                )
                assess_root = (
                    runs_root if runs_root.exists() else Path("runs")
                ) / PROP_ASSESS_DIRNAME
                try:
                    save_prop_analyze_point(assess_root, row)
                except Exception as exc:  # noqa: BLE001
                    _log.warning(
                        "skip prop assess design.json write %s: %s: %s",
                        assess_root, type(exc).__name__, exc)
                prop_user_store[:] = merge_prop_rows(list(prop_user_store) + [row])
                state.prop_pareto = _prop_table_rows(_prop_click_store())
                _refresh_prop_figure()
        except Exception as exc:  # noqa: BLE001
            state.prop_readout = [f"⚠ Analysis failed: {type(exc).__name__}: {exc}"]
            state.flush()
            return

        async def task():
            state.prop_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Analyze",
                msg_attr="prop_msg",
                busy_attr="prop_busy",
                note="building 3-D prop",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                # Lazy import: geometry touches CadQuery/OCCT in solid-build paths.
                from fansim.propeller.geometry import build_prop_preview

                await loop.run_in_executor(
                    None,
                    lambda: build_prop_preview(spec, prop_preview_stl, params=params),
                )
                _draw_prop(prop_preview_stl)
                state.prop_geo_ready = True
                state.prop_msg = ""
            except Exception as exc:  # noqa: BLE001 - geometry failure shouldn't break the readout
                state.prop_msg = (
                    f"⚠ 3-D build failed: {type(exc).__name__} (numbers above are still valid)"
                )
            finally:
                state.prop_busy = False
                ticker.cancel()
                state.flush()

        asynchronous.create_task(task())

    opt_stop = threading.Event()

    def stop_prop_optimize():
        if not state.prop_opt_running:
            return
        opt_stop.set()
        state.prop_msg = "⏹ Stopping after the current trial…"
        state.flush()

    def optimize_prop():
        """Auto-design the blade front (thrust vs efficiency) with BEMT — fast enough to run live."""
        if state.prop_busy:
            return
        base = get_prop_spec(state.prop_model)  # optimizer searches n_blades + pitch itself
        try:
            cap = float(state.prop_maxpower)
        except (TypeError, ValueError):
            cap = None
        if not cap or cap <= 0:  # blank or 0 = no power budget
            cap = None
        try:
            trials = max(50, int(float(state.prop_trials)))
        except (TypeError, ValueError):
            trials = 400
        root = runs_root if runs_root.exists() else Path("runs")
        resume = bool(state.prop_resume)
        last = state.prop_last_opt or None
        if resume and not last:
            found = latest_prop_study_dir(root)
            last = str(found) if found else None
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = prop_out_path(resume=resume, last_dir=last, stamp=stamp, runs_root=root)
        mode = "resume" if resume and last and out_dir == Path(last) else "new"
        mission_call = prop_mission_kwargs(
            state.prop_mission, state.prop_weight_n, state.prop_n_rotors,
            state.prop_battery_wh, state.prop_cruise_mps, state.prop_min_minutes,
        )
        if not mission_call["ok"]:
            state.prop_msg = mission_call["message"]
            return
        if str(state.prop_mission) != "thrust_efficiency":
            resume = False
            out_dir = prop_out_path(resume=False, last_dir=None, stamp=stamp, runs_root=root)
            mode = "new"

        opt_stop.clear()
        state.prop_opt_running = True

        async def task():
            state.prop_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Optimize",
                msg_attr="prop_msg",
                busy_attr="prop_busy",
                note=f"{trials} blade designs, BEMT, {mode}",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                study, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_prop_study(
                        base,
                        n_trials=trials,
                        max_power_w=cap,
                        out_dir=out_dir,
                        prop_model=str(state.prop_model),
                        stop_event=opt_stop,
                        polar_backend=str(state.prop_polar_backend or "table"),
                        **mission_call["kwargs"],
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.prop_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.prop_busy = False
                state.prop_opt_running = False
                ticker.cancel()
                state.flush()
                return
            state.prop_last_opt = str(out_dir)
            # Reload all disk fronts so prior Optimize runs stay on the graph.
            _reload_prop_from_disk()
            state.prop_has_front = bool(prop_pareto_store) or bool(prop_user_store)
            # Prefer the just-finished front at the head of the click store for the table.
            if pareto:
                prop_pareto_store[:] = merge_prop_rows(list(pareto) + list(prop_pareto_store))
                state.prop_pareto = _prop_table_rows(_prop_click_store())
            _refresh_prop_figure()
            if opt_stop.is_set():
                state.prop_msg = (
                    f"⏹ Stopped after {len(study.trials)} trials "
                    f"({mode} → {out_dir.name})."
                )
            else:
                cap_txt = f" ≤{cap:.0f} W" if cap else ""
                state.prop_msg = (
                    f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt} "
                    f"({mode} → {out_dir.name}). Click a point (or row) to load it."
                )
            state.prop_busy = False
            state.prop_opt_running = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def refine_prop_cfd():
        """CFD-refine top-N rows from the last prop Optimize front (--cfd-top / --bemt-floor)."""
        if state.prop_busy or state.prop_refine_busy:
            return
        try:
            n_top = int(float(state.prop_cfd_top))
        except (TypeError, ValueError):
            n_top = 0
        n_top = max(0, min(8, n_top))
        if n_top <= 0:
            state.prop_msg = "Set CFD refine top N ≥ 1 (uses last prop Optimize front)."
            state.flush()
            return
        try:
            floor = float(state.prop_bemt_floor)
        except (TypeError, ValueError):
            floor = 0.0
        root = runs_root if runs_root.exists() else Path("runs")
        last = state.prop_last_opt or None
        if not last:
            found = latest_prop_study_dir(root)
            last = str(found) if found else None
        if not last:
            state.prop_msg = "⚠ No prop Optimize front yet — run Optimize first."
            state.flush()
            return
        pareto_dir = Path(last)
        from fansim.propeller.persist import load_prop_pareto

        pareto = load_prop_pareto(pareto_dir) or list(prop_pareto_store)
        if not pareto:
            state.prop_msg = f"⚠ No Pareto rows in {pareto_dir.name}"
            state.flush()
            return
        base = get_prop_spec(state.prop_model)
        out = pareto_dir / "cfd_refine"
        mesh_preset = str(state.prop_cfd_mesh_preset)
        base_cell, iters = prop_cfd_mesh_knobs(mesh_preset)

        async def task():
            state.prop_refine_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="CFD refine",
                msg_attr="prop_msg",
                busy_attr="prop_refine_busy",
                note=(
                    f"top {n_top}, BEMT floor {floor:g} g, "
                    f"mesh {mesh_preset} (cell={base_cell}, iters={iters}) → {out.name}"
                ),
                interval=2.0,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                rows = await loop.run_in_executor(
                    None,
                    lambda: refine_prop_pareto_cfd(
                        base,
                        pareto,
                        out,
                        n_top=n_top,
                        bemt_floor_g=floor,
                        spec_key=str(state.prop_model),
                        base_cell=base_cell,
                        iters=iters,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.prop_msg = f"⚠ Prop CFD refine failed: {type(exc).__name__}: {exc}"
                state.prop_refine_busy = False
                ticker.cancel()
                state.flush()
                return
            ran = sum(1 for r in rows if not r.get("skipped"))
            skip = sum(1 for r in rows if r.get("skipped"))
            state.prop_msg = (
                f"✓ Prop CFD refine {ran} ran / {skip} skipped → {out} (see summary.json). "
                f"CFD is {PROP_CFD_HONESTY}. BEMT: {PROP_BEMT_HONESTY}.")
            state.prop_refine_busy = False
            ticker.cancel()
            workdir = first_prop_cfd_workdir(rows)
            if workdir:
                _render_prop_airflow(workdir)
            state.flush()

        asynchronous.create_task(task())

    def load_prop_row(idx=None, **_):
        """Load an optimizer-front / Analyze design into the prop sliders, then analyze it."""
        store = _prop_click_store()
        if idx is None or not (0 <= int(idx) < len(store)):
            return
        p = store[int(idx)]["params"]
        if store[int(idx)].get("prop_model"):
            try:
                state.prop_model = str(store[int(idx)]["prop_model"])
            except Exception:  # noqa: BLE001, S110
                pass
        _init_prop_editor(get_prop_spec(state.prop_model), flat=p)
        state.flush()
        analyze_prop(persist=False)
        row = store[int(idx)]
        workdir = row.get("workdir") or prop_cfd_workdir_from_study(state.prop_last_opt or None)
        if workdir:
            _render_prop_airflow(workdir)

    def _refresh_prop_export_items():
        rows: list[dict] = []
        root = exports_dir()
        for folder, kind in ((root, "STL"), (root / "pythrust", "PyThrust")):
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
                if not path.is_file():
                    continue
                if kind == "STL" and path.suffix.lower() != ".stl":
                    continue
                if kind == "PyThrust" and path.suffix.lower() not in (".csv", ".json"):
                    continue
                try:
                    rel = path.resolve().relative_to(root.resolve()).as_posix()
                except ValueError:
                    rel = path.name
                rows.append({
                    "title": f"{kind} · {path.name}",
                    "value": str(path.resolve()),
                    "href": f"fansim_exports/{rel}",
                })
                if len(rows) >= 24:
                    break
            if len(rows) >= 24:
                break
        state.prop_export_items = rows

    _refresh_prop_export_items()

    def export_prop_stl():
        """Save the current prop as a printable, shaft-bored STL into exports/."""
        if state.prop_busy or state.prop_refine_busy or state.prop_export_busy:
            return
        spec = prop_editor_spec()
        exports = exports_dir()
        exports.mkdir(exist_ok=True)
        out = exports / f"prop_{state.prop_model}.stl"

        async def task():
            state.prop_export_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Export",
                msg_attr="prop_export_msg",
                busy_attr="prop_export_busy",
                note="printable prop STL",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                # Lazy import: geometry touches CadQuery/OCCT in solid-build paths.
                from fansim.propeller.geometry import build_prop

                rep = await loop.run_in_executor(
                    None,
                    lambda: build_prop(spec, out, params=prop_editor_params()),
                )
            except Exception as exc:  # noqa: BLE001
                state.prop_export_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
                state.prop_export_busy = False
                ticker.cancel()
                state.flush()
                return
            wt = "watertight" if rep.ok else "⚠ NON-manifold"
            state.prop_export_msg = f"✓ Saved {out.resolve()} (+ .step)  ({wt})"
            state.prop_export_busy = False
            _refresh_prop_export_items()
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def export_prop_pythrust_csv():
        """Export BEMT CT/CP table as PyThrust JSON+CSV under exports/pythrust/."""
        if state.prop_busy or state.prop_refine_busy or state.prop_export_busy:
            return
        spec = prop_editor_spec()
        out_dir = exports_dir() / "pythrust"
        from fansim.propeller.pythrust_export import prop_id_for_export

        prop_id = prop_id_for_export(state.prop_model)

        async def task():
            state.prop_export_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Export CT/CP",
                msg_attr="prop_export_msg",
                busy_attr="prop_export_busy",
                note="BEMT → PyThrust CSV",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                from fansim.propeller.pythrust_export import export_bemt_pythrust_catalog

                result = await loop.run_in_executor(
                    None,
                    lambda: export_bemt_pythrust_catalog(
                        prop_editor_params(),
                        prop_id=prop_id,
                        diameter_in=spec.diameter_in,
                        pitch_in=spec.pitch_in,
                        blade_count=spec.n_blades,
                        out_dir=out_dir,
                        geometry_match="design_blade",
                        model=spec.name,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.prop_export_msg = (
                    f"⚠ CT/CP export failed: {type(exc).__name__}: {exc}"
                )
                state.prop_export_busy = False
                ticker.cancel()
                state.flush()
                return
            state.prop_export_msg = (
                f"✓ PyThrust CT/CP → {result['csv']}  ({result['n_rows']} rows)"
            )
            state.prop_export_busy = False
            _refresh_prop_export_items()
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    # Expose callbacks for the UI renderer.
    ctx.analyze_prop = analyze_prop  # type: ignore[attr-defined]
    ctx.optimize_prop = optimize_prop  # type: ignore[attr-defined]
    ctx.stop_prop_optimize = stop_prop_optimize  # type: ignore[attr-defined]
    ctx.refine_prop_cfd = refine_prop_cfd  # type: ignore[attr-defined]
    ctx.load_prop_row = load_prop_row  # type: ignore[attr-defined]
    ctx.export_prop_stl = export_prop_stl  # type: ignore[attr-defined]
    ctx.export_prop_pythrust_csv = export_prop_pythrust_csv  # type: ignore[attr-defined]

    def randomize_prop():
        spec = get_prop_spec(state.prop_model)
        flat = random_prop_flat(spec, random.Random())
        _init_prop_editor(spec, flat)
        state.prop_msg = "🎲 Randomized the blade. Analyze to score it."
        state.flush()

    ctx.randomize_prop = randomize_prop  # type: ignore[attr-defined]


def render_prop_tab(ctx: CockpitCtx) -> None:
    """Build Prop UI (call inside layout content)."""
    ctrl = ctx.ctrl
    prop_plotter = ensure_plotter(ctx, "prop_plotter")
    prop_pareto_store = ctx.prop_pareto_store  # set by setup_prop_tab
    prop_user_store = ctx.prop_user_store  # set by setup_prop_tab

    def _slider(
        label: str,
        model: str,
        mn: float,
        mx: float,
        step: float,
        disabled=None,
        unit: str = "",
        simple_label: str | None = None,
        simple_unit: str | None = None,
        **_kw,
    ):
        # Shared slider: label + exact value + unit + hover tooltip/diagram always wired.
        _shared_slider(
            label,
            model,
            mn,
            mx,
            step,
            disabled=disabled,
            unit=unit,
            simple_label=simple_label,
            simple_unit=simple_unit,
        )

    # ---- PROPELLER TAB -------------------------------------------------------------
    with html.Div(v_show="active_tab === 'propeller'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):
                def _prop_design():
                    v3.VAlert(
                        "Propeller tab — a fast estimate (~1 s), not the full Fan CFD. "
                        "Analyze for thrust; Optimize searches many designs. Fan tab is the "
                        "printable PC-fan path.",
                        type="info",
                        density="compact",
                        variant="tonal",
                        classes="mb-2",
                        closable=True,
                        v_model=("prop_ux_banner",),
                        v_show="ui_mode === 'simple'",
                    )
                    v3.VAlert(
                        "Propeller tab — fast BEMT estimate (~1 s), not full CFD. "
                        f"BEMT: {PROP_BEMT_HONESTY}. "
                        "Use Analyze for instant thrust/efficiency; Optimize searches "
                        "many BEMT designs. Optional CFD refine checks finalists spin and push "
                        f"air the right way, but is {PROP_CFD_HONESTY}. Fan tab is the "
                        "CFD-checked PC-fan path.",
                        type="info",
                        density="compact",
                        variant="tonal",
                        classes="mb-2",
                        closable=True,
                        v_model=("prop_ux_banner",),
                        v_show="ui_mode === 'expert'",
                    )
                    html.Div(
                        "Start here: pick size → tune blade → Analyze (~1 s) → Export STL.",
                        classes="text-caption text-medium-emphasis mb-2",
                        v_show="ui_mode === 'simple'",
                    )
                    html.Div(
                        "Start here: pick size → tune blade → Analyze (~1 s) → "
                        "Optimize (optional) → Export STL. CFD refine = direction check only.",
                        classes="text-caption text-medium-emphasis mb-2",
                        v_show="ui_mode === 'expert'",
                    )
                    with v3.VCard(classes="mb-2 pa-3"):
                        v3.VSelect(
                            label="Propeller size",
                            v_model=("prop_model",),
                            items=("prop_model_items",),
                            item_title="title",
                            item_value="value",
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                        )
                        html.Div(
                            "{{ prop_info }}",
                            classes="text-caption mt-2",
                            style="white-space: pre-line",
                        )
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div("Actions", classes="text-subtitle-2 mb-1")
                        html.Div(
                            "{{ prop_mission }} mission — change under Optimize below.",
                            classes="text-caption text-medium-emphasis mb-1",
                            v_show="ui_mode === 'expert'",
                        )
                        render_action_row(
                            v3,
                            {
                                "score": {
                                    "label": "Analyze (~1 s)",
                                    "color": "primary",
                                    "size": "small",
                                    "click": (ctx.analyze_prop,),
                                    "loading": ("prop_busy",),
                                    "disabled": ("prop_busy || prop_refine_busy",),
                                },
                                "export": [
                                    {
                                        "label": "Export STL",
                                        "size": "small",
                                        "variant": "tonal",
                                        "color": "primary",
                                        "click": (ctx.export_prop_stl,),
                                        "loading": ("prop_export_busy",),
                                        "disabled": (
                                            "prop_busy || prop_refine_busy || prop_export_busy || !prop_geo_ready",
                                        ),
                                    },
                                    {
                                        "label": "Export CT/CP (PyThrust)",
                                        "size": "small",
                                        "variant": "tonal",
                                        "color": "primary",
                                        "click": (ctx.export_prop_pythrust_csv,),
                                        "loading": ("prop_export_busy",),
                                        "disabled": (
                                            "prop_busy || prop_refine_busy || prop_export_busy",
                                        ),
                                        "v_show": "ui_mode === 'expert'",
                                    },
                                ],
                                "optimize": {
                                    "label": "Optimize (BEMT)",
                                    "color": "success",
                                    "size": "small",
                                    "click": (ctx.optimize_prop,),
                                    "loading": ("prop_busy",),
                                    "disabled": ("prop_busy || prop_refine_busy",),
                                    "v_show": "ui_mode === 'expert'",
                                },
                                "stop": {
                                    "label": "Stop",
                                    # Red only while there is something to stop: a disabled tonal
                                    # red still read faint pink (§23.26, QA UI-13 re-test).
                                    "color": ("prop_opt_running ? 'error' : undefined",),
                                    "variant": "tonal",
                                    "size": "small",
                                    "click": (ctx.stop_prop_optimize,),
                                    "disabled": ("!prop_opt_running",),
                                    "v_show": "ui_mode === 'expert' && prop_opt_running",
                                },
                                "randomize": {
                                    "label": "Randomize",
                                    "size": "small",
                                    "variant": "tonal",
                                    "click": (ctx.randomize_prop,),
                                    "disabled": ("prop_busy || prop_refine_busy",),
                                    "v_show": "ui_mode === 'expert'",
                                },
                            },
                        )
                        html.Div(
                            "Export STL unlocks after Analyze finishes the 3-D build.",
                            classes="text-caption text-medium-emphasis mt-1",
                            v_show="!prop_geo_ready",
                        )
                        html.Div(
                            "{{ prop_msg }}",
                            classes="text-caption mt-2",
                            style="white-space: pre-line",
                        )
                        html.Div(
                            "{{ prop_export_msg }}",
                            classes="text-caption mt-1",
                            style="white-space: pre-line",
                        )
                        ctx.busy_bar(
                            "prop_busy",
                            "prop_refine_busy",
                            "prop_export_busy",
                            color="success",
                        )
                    with v3.VExpansionPanels(
                        v_model=("prop_design_panels",),
                        multiple=True,
                        variant="accordion",
                        classes="mb-2",
                    ):
                        with v3.VExpansionPanel(title="Geometry — modify blade"):
                            with v3.VExpansionPanelText():
                                html.Div(
                                    "Hover any slider for what it does. Expand inner panels for wall, 3-D curve, and tip.",
                                    classes="text-caption mb-2",
                                )
                                _slider("Blades", "p_n_blades", 2, 4, 1)
                                _slider("Pitch", "p_pitch", 1.5, 8.0, 0.1, unit="in")
                                _slider("Chord root", "p_chord_root", 0.08, 0.30, 0.01, unit="×R", simple_label="Blade width root")
                                _slider("Chord mid", "p_chord_mid", 0.10, 0.32, 0.01, unit="×R", simple_label="Blade width mid")
                                _slider("Chord tip", "p_chord_tip", 0.04, 0.18, 0.01, unit="×R", simple_label="Blade width tip")
                                from fansim.cockpit.blade_editor import render_shape_panels
                                from fansim.cockpit.fan_widgets import help_select as _help_select
                                from fansim.cockpit.fan_widgets import help_switch as _help_switch
                                from fansim.cockpit.prop_copy import PROP_DESC

                                _help_select(
                                    "p_thick_mode",
                                    "Wall mode",
                                    items="p_thick_mode_items",
                                    help_map=PROP_DESC,
                                )

                                render_shape_panels(
                                    prefix="p_",
                                    slider=_slider,
                                    help_switch=_help_switch,
                                    v3=v3,
                                    html=html,
                                    title_thick="Wall & scoop",
                                )
                        with v3.VExpansionPanel(
                            title="Optimize & CFD refine",
                            v_show="ui_mode === 'expert'",
                        ):
                            with v3.VExpansionPanelText():
                                html.Div(
                                    "Multi-objective BEMT search (~1 s/trial). "
                                    "CFD refine scores top-N finalists when Docker is up.",
                                    classes="text-caption mb-2",
                                )
                                html.Div(
                                    "Turn on Continue last prop study to append trials into the "
                                    "most recent cockpit_prop_* Optuna DB (same as Fan resume).",
                                    classes="text-caption mb-2",
                                    style="white-space: pre-line",
                                )
                                with v3.VRow(no_gutters=True, classes="align-center"):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VTextField(
                                            label="Trials",
                                            v_model=("prop_trials",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        v3.VTextField(
                                            label="Max power W (0=any)",
                                            v_model=("prop_maxpower",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                v3.VSelect(
                                    label="Mission",
                                    v_model=("prop_mission",),
                                    items=("prop_mission_items",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mt-2",
                                )
                                with v3.VRow(no_gutters=True, classes="align-center mt-1"):
                                    with v3.VCol(cols=4, classes="pr-1"):
                                        v3.VTextField(
                                            label="Weight (N)",
                                            v_model=("prop_weight_n",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=4, classes="px-1"):
                                        v3.VTextField(
                                            label="Rotors",
                                            v_model=("prop_n_rotors",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=4, classes="pl-1"):
                                        v3.VTextField(
                                            label="Battery (Wh)",
                                            v_model=("prop_battery_wh",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                with v3.VRow(no_gutters=True, classes="align-center mt-1"):
                                    with v3.VCol(cols=6, classes="pr-1"):
                                        v3.VTextField(
                                            label="Cruise (m/s)",
                                            v_model=("prop_cruise_mps",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=6, classes="pl-1"):
                                        v3.VTextField(
                                            label="Min hover (min)",
                                            v_model=("prop_min_minutes",),
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                v3.VSwitch(
                                    v_model=("prop_resume",),
                                    density="compact",
                                    hide_details=True,
                                    color="primary",
                                    inset=True,
                                    label="Continue last prop study",
                                    classes="mt-2",
                                )
                                html.Div(
                                    "CFD refine checks top-N BEMT finalists for direction and "
                                    f"flow pictures (Docker); {PROP_CFD_HONESTY}. "
                                    f"BEMT: {PROP_BEMT_HONESTY}. "
                                    "BEMT floor skips hopeless CFD. "
                                    "Smoke mesh is fast sanity-check; Refine is denser for ranking. "
                                    "Polar V∞ list feeds Analyze.",
                                    classes="text-caption mt-3 mb-1",
                                    style="white-space: pre-line",
                                )
                                with v3.VRow(no_gutters=True, classes="align-center"):
                                    with v3.VCol(cols=3, classes="pr-1"):
                                        v3.VTextField(
                                            label="CFD top N",
                                            v_model=("prop_cfd_top",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=3, classes="px-1"):
                                        v3.VTextField(
                                            label="BEMT floor g",
                                            v_model=("prop_bemt_floor",),
                                            type="number",
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=3, classes="px-1"):
                                        v3.VSelect(
                                            label="CFD mesh",
                                            v_model=("prop_cfd_mesh_preset",),
                                            items=("prop_cfd_mesh_items",),
                                            density="compact",
                                            variant="outlined",
                                            hide_details=True,
                                        )
                                    with v3.VCol(cols=3, classes="pl-1"):
                                        v3.VBtn(
                                            "CFD refine",
                                            color="warning",
                                            variant="tonal",  # same as Mixed/CROR: solid looked enabled (UI-21)
                                            size="small",
                                            block=True,
                                            click=(ctx.refine_prop_cfd,),
                                            loading=("prop_refine_busy",),
                                            disabled=(
                                                "prop_busy || prop_refine_busy || !prop_has_front || !(prop_cfd_top > 0)",
                                            ),
                                        )
                                v3.VSelect(
                                    label="BEMT polar backend",
                                    v_model=("prop_polar_backend",),
                                    items=("prop_polar_backend_items",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mt-2",
                                )
                                v3.VTextField(
                                    label="Polar V∞ (m/s, comma)",
                                    v_model=("prop_polar_v",),
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                    classes="mt-2",
                                    hint="BEMT forward-flight sweep on Analyze",
                                )

                def _prop_results():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("prop_sel_idx",),
                            items=("prop_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(ctx.load_prop_row, "[$event]"),
                        )
                        html.Div(
                            "No scored props yet — Analyze one on Design (or Optimize in Expert) "
                            "to fill this plot.",
                            classes="text-caption text-medium-emphasis mt-2",
                            v_show="!prop_pareto || !prop_pareto.length",
                        )
                    with v3.VCard(style=f"height:{SCATTER_HEIGHT_PX}px;", classes="pa-1 mb-2"):
                        prop_fig_widget = plotly_widgets.Figure(
                            figure=prop_scatter_figure(prop_pareto_store, prop_user_store),
                            click=(
                                ctx.load_prop_row,
                                "[$event?.points?.[0]?.customdata]",
                            ),
                            style="width:100%;",
                        )
                        ctrl.prop_fig_update = prop_fig_widget.update
                    with v3.VCard(classes="pa-2", v_if="prop_pareto.length"):
                        html.Div(
                            "Optimizer / Analyze front — click a point above or a row here "
                            "(top = most thrust; ◆ = Analyze saves)",
                            classes="text-subtitle-2 mb-1",
                        )
                        with v3.VList(density="compact", lines=False):
                            with v3.VListItem(
                                v_for="row in prop_pareto",
                                key="row.idx",
                                click=(ctx.load_prop_row, "[row.idx]"),
                            ):
                                v3.VListItemTitle(
                                    "{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                    "·  🔉 {{ row.noise }}  ·  {{ row.power }} W  "
                                    "·  {{ row.nb }}-blade  {{ row.pitch }} in"
                                )

                def _prop_library():
                    with v3.VCard(classes="pa-2 mb-2"):
                        html.Div(
                            "Load a previous Optimize / Analyze front into Design.",
                            classes="text-caption mb-2",
                        )
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("prop_sel_idx",),
                            items=("prop_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(ctx.load_prop_row, "[$event]"),
                        )
                    with v3.VCard(classes="pa-2"):
                        html.Div(
                            "Exported printable STL files under exports/.",
                            classes="text-caption mb-2",
                            v_show="ui_mode === 'simple'",
                        )
                        html.Div(
                            "Exported STL and PyThrust files under exports/.",
                            classes="text-caption mb-2",
                            v_show="ui_mode === 'expert'",
                        )
                        with v3.VList(density="compact", lines="one"):
                            with v3.VListItem(v_for="it in prop_export_items", key="it.value"):
                                with v3.VListItemTitle():
                                    html.A(
                                        "{{ it.title }}",
                                        href=("it.href",),
                                        download=True,
                                        classes="text-decoration-none",
                                    )
                        html.Div(
                            "No exports yet — press Analyze, then Export STL on Design.",
                            classes="text-caption text-medium-emphasis",
                            v_if="!prop_export_items.length && ui_mode === 'simple'",
                        )
                        html.Div(
                            "No exports yet — use Export STL on Design (CT/CP export is Expert).",
                            classes="text-caption text-medium-emphasis",
                            v_if="!prop_export_items.length && ui_mode === 'expert'",
                        )

                render_left_shell(
                    v3,
                    html,
                    state_key="prop_subtab",
                    design=_prop_design,
                    results=_prop_results,
                    library=_prop_library,
                )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div("{{ line }}", v_for="line in prop_readout", classes="text-body-2")
                with v3.VCard(style=VTK_VIEW_STYLE, classes="mb-2"):
                    html.Div(
                        "3-D preview appears here after you press Analyze (~1 s).",
                        classes="text-caption text-medium-emphasis px-3 pt-2",
                        v_show="!prop_geo_ready",
                    )
                    prop_view = plotter_ui(prop_plotter)
                    ctrl.prop_view_update = prop_view.update
                with v3.VCard(
                    classes="mb-2 pa-2",
                    v_show="prop_subtab === 'results' && ui_mode === 'expert'",
                ):
                    html.Div(
                        "Open-air airflow — top CFD-refined design",
                        classes="text-subtitle-2 mb-1",
                    )
                    html.Div(
                        "From the best design of the last CFD refine (open-air MRF; flow "
                        "pattern, not a performance number, Audit #8). |U|/pressure "
                        "midplane; axial Uz (blue = thrust wake, red = reverse); streamlines by |U|.",
                        classes="text-caption text-medium-emphasis mb-2",
                    )
                    with v3.VBtnToggle(
                        v_model=("prop_airflow_field",),
                        density="compact",
                        color="primary",
                        classes="mb-2",
                        mandatory=True,
                    ):
                        v3.VBtn("|U| midplane", value="U", size="small")
                        v3.VBtn("pressure midplane", value="p", size="small")
                        v3.VBtn("axial Uz", value="uz", size="small")
                        v3.VBtn("streamlines", value="stream", size="small")
                    html.Div(
                        "{{ prop_airflow_caption }}",
                        classes="text-caption text-medium-emphasis mb-1",
                    )
                    html.Img(
                        src=("prop_airflow_img_uri",),
                        v_show="prop_airflow_img_uri",
                        alt=("prop_airflow_caption || 'Prop duct airflow field'",),
                        aria_label=("prop_airflow_caption || 'Prop duct airflow field'",),
                        style=(
                            "width:100%;max-height:520px;object-fit:contain;"
                            "display:block;background:#fafafa;border-radius:4px;"
                        ),
                    )
