"""Propeller cockpit tab (instant BEMT design + optional CFD refine).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import sys
import tempfile
import time
from pathlib import Path

_log = logging.getLogger(__name__)

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.data import design_dropdown_items
from fansim.cockpit.figures import prop_scatter_figure
from fansim.cockpit.plotters import ensure_plotter

from fansim.prop_spec import get_prop_spec, prop_spec_names
from fansim.propeller.bemt import analyze as bemt_analyze
from fansim.propeller.noise import estimate_prop_noise
from fansim.propeller.optimize import refine_pareto_cfd as refine_prop_pareto_cfd, run_prop_study
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


def setup_prop_tab(ctx: CockpitCtx) -> None:
    """Init prop_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    runs_root = ctx.runs_root
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # ---- PROPELLER ARCHETYPE ---------------------------------------------------------------
    prop_preview_stl = Path(tempfile.gettempdir()) / "fansim_prop_preview.stl"
    prop_pareto_store: list[dict] = []  # Optimize rows (click index base)
    prop_user_store: list[dict] = []  # Analyze rows (appended after Optimize in click index)

    # Shared objects for render + callbacks (kept per-session).
    ctx.prop_preview_stl = prop_preview_stl  # type: ignore[attr-defined]
    ctx.prop_pareto_store = prop_pareto_store  # type: ignore[attr-defined]
    ctx.prop_user_store = prop_user_store  # type: ignore[attr-defined]

    state.prop_model = "fpv_5inch"
    state.prop_models = prop_spec_names()
    state.prop_info = "Pick a size, tune the blade, then Analyze (instant) or Optimize."
    state.prop_readout = ["Analyze a prop to see thrust, efficiency, and figure of merit."]
    state.prop_busy = False
    state.prop_msg = ""
    state.prop_export_msg = ""
    state.prop_export_busy = False
    state.prop_trials = 400
    state.prop_maxpower = 700.0
    state.prop_pareto = []  # display rows for the optimizer front table
    state.prop_resume = False
    state.prop_cfd_top = 0
    state.prop_bemt_floor = 0.0
    state.prop_refine_busy = False
    state.prop_polar_v = "0,5,10,15,20"
    state.prop_geo_ready = False
    _prop_runs = runs_root if runs_root.exists() else Path("runs")
    _prop_last = latest_prop_study_dir(_prop_runs)
    state.prop_last_opt = str(_prop_last) if _prop_last else ""
    state.prop_has_front = False  # set True after load / Optimize

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
            ctrl.prop_fig_update(prop_scatter_figure(prop_pareto_store, prop_user_store))
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
        except Exception:  # noqa: BLE001 - nothing to show
            pass
        try:
            ctrl.prop_view_update()
        except Exception:  # noqa: BLE001
            pass

    def _prop_perf_lines(spec, params):
        """BEMT readout for the current prop: static hover thrust/eff/FM + a forward-flight note."""
        perf = bemt_analyze(params, rpm=spec.rpm_max)
        lines = [
            f"⚙ {spec.n_blades}-blade  {spec.diameter_in}×{spec.pitch_in:.1f} in  @ {spec.rpm_max:.0f} rpm",
            f"Thrust {perf.thrust_g:.0f} g   ·   {perf.efficiency_g_per_w:.2f} g/W   ·   {perf.power_w:.0f} W",
            f"Figure of merit {perf.figure_of_merit:.2f}   (0.6–0.8 = a good real prop)",
        ]
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
                perf = bemt_analyze(params, rpm=spec.rpm_max)
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
                _, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_prop_study(
                        base,
                        n_trials=trials,
                        max_power_w=cap,
                        out_dir=out_dir,
                        prop_model=str(state.prop_model),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.prop_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.prop_busy = False
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
            cap_txt = f" ≤{cap:.0f} W" if cap else ""
            state.prop_msg = (
                f"✓ {len(pareto)} designs on the thrust↔efficiency front{cap_txt} "
                f"({mode} → {out_dir.name}). Click a point (or row) to load it."
            )
            state.prop_busy = False
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

        async def task():
            state.prop_refine_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="CFD refine",
                msg_attr="prop_msg",
                busy_attr="prop_refine_busy",
                note=f"top {n_top}, BEMT floor {floor:g} g → {out.name}",
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
            state.prop_msg = f"✓ Prop CFD refine {ran} ran / {skip} skipped → {out} (see summary.json)"
            state.prop_refine_busy = False
            ticker.cancel()
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
            except Exception:  # noqa: BLE001
                pass
        _init_prop_editor(get_prop_spec(state.prop_model), flat=p)
        state.flush()
        analyze_prop(persist=False)

    def export_prop_stl():
        """Save the current prop as a printable, shaft-bored STL into exports/."""
        if state.prop_busy or state.prop_refine_busy or state.prop_export_busy:
            return
        spec = prop_editor_spec()
        exports = Path("exports")
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
            state.prop_export_msg = f"✓ Saved {out.resolve()}  ({wt})"
            state.prop_export_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    # Expose callbacks for the UI renderer.
    ctx.analyze_prop = analyze_prop  # type: ignore[attr-defined]
    ctx.optimize_prop = optimize_prop  # type: ignore[attr-defined]
    ctx.refine_prop_cfd = refine_prop_cfd  # type: ignore[attr-defined]
    ctx.load_prop_row = load_prop_row  # type: ignore[attr-defined]
    ctx.export_prop_stl = export_prop_stl  # type: ignore[attr-defined]


def render_prop_tab(ctx: CockpitCtx) -> None:
    """Build Prop UI (call inside layout content)."""
    state, ctrl = ctx.state, ctx.ctrl
    prop_plotter = ensure_plotter(ctx, "prop_plotter")
    prop_pareto_store = getattr(ctx, "prop_pareto_store")  # set by setup_prop_tab
    prop_user_store = getattr(ctx, "prop_user_store")  # set by setup_prop_tab

    def _slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None):
        extra = {}
        if disabled is not None:
            extra["disabled"] = disabled
        v3.VSlider(
            v_model=(model,),
            min=mn,
            max=mx,
            step=step,
            label=label,
            thumb_label=True,
            density="compact",
            hide_details=True,
            classes="mb-1",
            **extra,
        )

    # ---- PROPELLER TAB -------------------------------------------------------------
    with html.Div(v_show="active_tab === 'propeller'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):
                with v3.VCard(classes="mb-2 pa-3"):
                    v3.VSelect(
                        label="Propeller size",
                        v_model=("prop_model",),
                        items=("prop_models",),
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
                    html.Div(
                        "Blade — pitch drives the twist; expand panels for thickness / 3-D / tip",
                        classes="text-subtitle-2 mb-2",
                    )
                    _slider("Blades", "p_n_blades", 2, 4, 1)
                    _slider("Pitch (in)", "p_pitch", 1.5, 8.0, 0.1)
                    _slider("Chord root (×tip R)", "p_chord_root", 0.08, 0.30, 0.01)
                    _slider("Chord mid (×tip R)", "p_chord_mid", 0.10, 0.32, 0.01)
                    _slider("Chord tip (×tip R)", "p_chord_tip", 0.04, 0.18, 0.01)
                    v3.VSelect(
                        label="Wall mode",
                        v_model=("p_thick_mode",),
                        items=[
                            {"title": "Tapered t/c", "value": "tapered"},
                            {"title": "Uniform wall mm", "value": "uniform"},
                        ],
                        density="compact",
                        variant="outlined",
                        hide_details=True,
                        classes="mb-2",
                    )
                    from fansim.cockpit.blade_editor import render_shape_panels
                    from fansim.cockpit.fan_widgets import help_switch as _help_switch

                    def _pslider(label, model, mn, mx, step, unit="", disabled=None, **_kw):
                        _slider(label, model, mn, mx, step, disabled=disabled)

                    render_shape_panels(
                        prefix="p_",
                        slider=_pslider,
                        help_switch=_help_switch,
                        v3=v3,
                        html=html,
                    )
                    with v3.VRow(no_gutters=True, classes="mt-2"):
                        v3.VBtn(
                            "Analyze",
                            color="primary",
                            size="small",
                            click=(getattr(ctx, "analyze_prop"),),
                            classes="mr-2",
                            loading=("prop_busy",),
                            disabled=("prop_busy || prop_refine_busy",),
                        )
                        v3.VBtn(
                            "Export STL",
                            size="small",
                            variant="tonal",
                            color="primary",
                            click=(getattr(ctx, "export_prop_stl"),),
                            classes="mr-2",
                            loading=("prop_export_busy",),
                            disabled=(
                                "prop_busy || prop_refine_busy || prop_export_busy || !prop_geo_ready",
                            ),
                        )
                        v3.VBtn(
                            "Optimize",
                            color="success",
                            size="small",
                            click=(getattr(ctx, "optimize_prop"),),
                            loading=("prop_busy",),
                            disabled=("prop_busy || prop_refine_busy",),
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
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "Auto-optimize the blade (thrust ↔ efficiency, ~1 s)",
                        classes="text-subtitle-2 mb-1",
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
                        "CFD refine scores top-N BEMT finalists (Docker). "
                        "BEMT floor skips hopeless CFD. Polar V∞ list feeds Analyze.",
                        classes="text-caption mt-3 mb-1",
                        style="white-space: pre-line",
                    )
                    with v3.VRow(no_gutters=True, classes="align-center"):
                        with v3.VCol(cols=4, classes="pr-1"):
                            v3.VTextField(
                                label="CFD top N",
                                v_model=("prop_cfd_top",),
                                type="number",
                                density="compact",
                                variant="outlined",
                                hide_details=True,
                            )
                        with v3.VCol(cols=4, classes="px-1"):
                            v3.VTextField(
                                label="BEMT floor g",
                                v_model=("prop_bemt_floor",),
                                type="number",
                                density="compact",
                                variant="outlined",
                                hide_details=True,
                            )
                        with v3.VCol(cols=4, classes="pl-1"):
                            v3.VBtn(
                                "CFD refine",
                                color="warning",
                                size="small",
                                block=True,
                                click=(getattr(ctx, "refine_prop_cfd"),),
                                loading=("prop_refine_busy",),
                                disabled=(
                                    "prop_busy || prop_refine_busy || !prop_has_front || !(prop_cfd_top > 0)",
                                ),
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
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div("{{ line }}", v_for="line in prop_readout", classes="text-body-2")
                with v3.VCard(style="height:360px;", classes="mb-2"):
                    prop_view = plotter_ui(prop_plotter)
                    ctrl.prop_view_update = prop_view.update
                with v3.VCard(classes="pa-2 mb-2"):
                    v3.VSelect(
                        label="Previous runs",
                        v_model=("prop_sel_idx",),
                        items=("prop_trial_items",),
                        density="compact", variant="outlined", hide_details=True,
                        update_modelValue=(getattr(ctx, "load_prop_row"), "[$event]"),
                    )
                with v3.VCard(style="height:360px;", classes="pa-1 mb-2"):
                    prop_fig_widget = plotly_widgets.Figure(
                        figure=prop_scatter_figure(prop_pareto_store, prop_user_store),
                        click=(
                            getattr(ctx, "load_prop_row"),
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
                            click=(getattr(ctx, "load_prop_row"), "[row.idx]"),
                        ):
                            v3.VListItemTitle(
                                "{{ row.thrust }} g  ·  {{ row.eff }} g/W  "
                                "·  🔉 {{ row.noise }}  ·  {{ row.power }} W  "
                                "·  {{ row.nb }}-blade  {{ row.pitch }} in"
                            )
