"""CROR cockpit tab (counter-rotating stacked rotors).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from fansim.cockpit.airflow_panel import pick_airflow_uri, render_airflow_pack
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_widgets import slider as _shared_slider
from fansim.cockpit.data import design_dropdown_items
from fansim.cockpit.tab_shell import (
    SCATTER_HEIGHT_PX,
    VTK_HEIGHT_PX,
    render_action_row,
    render_left_shell,
)
from fansim.cockpit.figures import cror_scatter_figure
from fansim.cockpit.plotters import ensure_plotter
from fansim.cror.geometry import CrorParams, export_cror_stl
from fansim.cror.noise import estimate_cror_noise
from fansim.cockpit.paths import exports_dir
from fansim.cror.optimize import (
    cror_stack_depth_mm,
    refine_pareto_cfd as refine_cror_pareto_cfd,
    run_cror_study,
    thin_cror_for_frame,
)
from fansim.cror.persist import (
    cror_opt_out_path,
    latest_cror_opt_dir,
    load_all_cror_pareto,
    load_cror_pareto,
    save_cror_pareto,
)

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


def setup_cror_tab(ctx: CockpitCtx) -> None:
    """Init cror_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    runs_root = ctx.runs_root
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # ---- CROR tab (counter-rotating stacked rotors, §4.2) ---------------------------------
    cror_pareto_store: list[dict] = []
    cror_preview_stl = Path(tempfile.gettempdir()) / "fansim_cror_preview.stl"

    # Shared objects for render + callbacks (kept per-session).
    ctx.cror_pareto_store = cror_pareto_store  # type: ignore[attr-defined]
    ctx.cror_preview_stl = cror_preview_stl  # type: ignore[attr-defined]

    state.cror_subtab = "design"
    state.cror_export_items = []
    state.cror_trials = 60
    state.cror_rpm = 2000.0
    state.cror_max_depth = 25.0
    state.cror_cfd_top = 0
    state.cror_opt_busy = False
    state.cror_refine_busy = False
    state.cror_thin_busy = False
    state.cror_export_busy = False
    state.cror_preview_busy = False
    state.cror_geo_ready = False
    # Duct-airflow viz (§17.3): rendered from the top CFD-refined design (dual counter-rotating
    # AXIAL rotors, so the axial slices apply). |U|/p midplane + axial-Uz + streamlines.
    state.cror_airflow_field = "U"
    state.cror_airflow_img_uri = ""
    state.cror_airflow_caption = "Run CFD refine to see duct airflow for the top design."
    state.cror_airflow_busy = False
    state.cror_sel_idx = None  # previous-runs dropdown (loads by click index)
    state.cror_trial_items = design_dropdown_items(cror_pareto_store, by_index=True)
    state.cror_msg = ""
    state.cror_readout = [
        "CROR: edit front/rear blades, Preview the stack, Thin to ≤25 mm, Optimize (BEMT proxy), "
        "CFD refine top-N. Relative noise only."
    ]
    # Design defaults (§14.5)
    _c0 = CrorParams()
    state.cror_hub_r = float(_c0.front.hub_radius)
    state.cror_tip_r = float(_c0.front.tip_radius)
    state.cror_gap = float(_c0.axial_gap_mm)
    state.cror_f_n = int(_c0.front.n_blades)
    state.cror_r_n = int(_c0.rear.n_blades)
    from fansim.cockpit.blade_editor import init_shape_state
    from fansim.cror.params_io import cror_flat_from_params

    _flat0 = cror_flat_from_params(_c0)
    state.cror_f_chord_root = float(_flat0["f_chord_root"])
    state.cror_f_chord_mid = float(_flat0["f_chord_mid"])
    state.cror_f_chord_tip = float(_flat0["f_chord_tip"])
    state.cror_f_stagger = float(_flat0["f_stagger"])
    state.cror_r_chord_root = float(_flat0["r_chord_root"])
    state.cror_r_chord_mid = float(_flat0["r_chord_mid"])
    state.cror_r_chord_tip = float(_flat0["r_chord_tip"])
    state.cror_r_stagger = float(_flat0["r_stagger"])
    # Map f_/r_ shape keys onto cror_f_ / cror_r_ state prefixes.
    init_shape_state(state, "cror_f_", {k[2:]: v for k, v in _flat0.items() if k.startswith("f_")})
    init_shape_state(state, "cror_r_", {k[2:]: v for k, v in _flat0.items() if k.startswith("r_")})
    _cror_runs = runs_root if runs_root.exists() else Path("runs")
    _cror_last = latest_cror_opt_dir(_cror_runs)
    state.cror_last_opt = str(_cror_last) if _cror_last else ""
    cror_pareto_store.extend(load_all_cror_pareto(_cror_runs))
    state.cror_has_front = bool(cror_pareto_store) or bool(_cror_last)

    def _refresh_cror_figure():
        if hasattr(ctrl, "cror_fig_update"):
            ctrl.cror_fig_update(cror_scatter_figure(cror_pareto_store))
        state.cror_trial_items = design_dropdown_items(cror_pareto_store, by_index=True)

    def _refresh_cror_export_items():
        rows: list[dict] = []
        exports = exports_dir()
        if exports.is_dir():
            candidates = [
                p
                for p in exports.iterdir()
                if p.is_file() and p.name.lower().startswith("cror")
            ]
            for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
                rows.append({"title": path.name, "value": str(path.resolve())})
                if len(rows) >= 24:
                    break
        state.cror_export_items = rows

    _refresh_cror_export_items()

    # --- Duct-airflow viz (§17.3): render a CFD-refined CROR case (shared renderers) ---------
    _cror_airflow = {"uris": {}, "gen": 0}

    def _apply_cror_airflow_field():
        uri, cap = pick_airflow_uri(_cror_airflow["uris"], state.cror_airflow_field or "U")
        state.cror_airflow_img_uri = uri
        if uri:
            state.cror_airflow_caption = cap
        elif not state.cror_airflow_busy:
            state.cror_airflow_caption = "Airflow not available for this design"

    def _render_cror_airflow(case_dir):
        if not case_dir or asynchronous is None:
            _cror_airflow["uris"] = {}
            state.cror_airflow_img_uri = ""
            state.cror_airflow_caption = "Airflow not available for this design"
            return
        _cror_airflow["gen"] += 1
        gen = _cror_airflow["gen"]
        state.cror_airflow_busy = True
        state.cror_airflow_img_uri = ""
        state.cror_airflow_caption = "Rendering duct airflow…"
        state.flush()

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(
                    None, lambda: render_airflow_pack(str(case_dir)))
                if _cror_airflow["gen"] != gen:
                    return
                _cror_airflow["uris"] = pack["uris"]
                state.cror_airflow_busy = False
                _apply_cror_airflow_field()
            except Exception:  # noqa: BLE001 — viz must never break the tab
                if _cror_airflow["gen"] == gen:
                    _cror_airflow["uris"] = {}
                    state.cror_airflow_busy = False
                    state.cror_airflow_img_uri = ""
                    state.cror_airflow_caption = "Airflow not available for this design"
            finally:
                try:
                    state.flush()
                    ctrl.cror_view_update()
                except Exception:  # noqa: BLE001
                    pass

        asynchronous.create_task(task())

    @state.change("cror_airflow_field")
    def _on_cror_airflow_field(**_):
        _apply_cror_airflow_field()
        try:
            state.flush()
        except Exception:  # noqa: BLE001
            pass

    def _cror_busy():
        return bool(
            state.cror_opt_busy
            or state.cror_refine_busy
            or state.cror_thin_busy
            or state.cror_export_busy
            or state.cror_preview_busy
        )

    def _draw_cror(path: Path) -> None:
        cror_plotter = ensure_plotter(ctx, "cror_plotter")
        if cror_plotter is None:
            return
        cror_plotter.clear_actors()
        try:
            cror_plotter.add_mesh(pv.read(str(path)), color="cadetblue", smooth_shading=True)
            cror_plotter.reset_camera()
        except Exception:  # noqa: BLE001 - nothing to show
            pass
        try:
            ctrl.cror_view_update()
        except Exception:  # noqa: BLE001
            pass

    def preview_cror(**_):
        """Build thinned CROR stack STL and show it in the tab plotter (§14.6)."""
        if _cror_busy() or asynchronous is None:
            return

        async def task():
            state.cror_preview_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Preview",
                msg_attr="cror_msg",
                busy_attr="cror_preview_busy",
                note="building CROR stack",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                params = await loop.run_in_executor(None, _cror_params_from_editor)
                await loop.run_in_executor(
                    None,
                    lambda: export_cror_stl(params, cror_preview_stl),
                )
                _draw_cror(cror_preview_stl)
                depth = cror_stack_depth_mm(params)
                nz = estimate_cror_noise(params, float(state.cror_rpm))
                state.cror_geo_ready = True
                state.cror_readout = [
                    f"Stack depth {depth:.1f} mm · gap {params.axial_gap_mm:.1f} mm · "
                    f"{params.front.n_blades}+{params.rear.n_blades} blades",
                    f"Proxy noise {nz['rel_dba']:.0f} (rel) · front BPF {nz['front_bpf_hz']:.0f} Hz · "
                    f"rear {nz['rear_bpf_hz']:.0f} Hz",
                ]
                state.cror_msg = "✓ Preview ready (thinned to depth cap)."
            except Exception as exc:  # noqa: BLE001
                state.cror_msg = f"⚠ Preview failed: {type(exc).__name__}: {exc}"
            finally:
                state.cror_preview_busy = False
                ticker.cancel()
                state.flush()

        asynchronous.create_task(task())

    def _cror_flat_from_state() -> dict:
        from fansim.cockpit.blade_editor import shape_flat_from_state

        f_shape = shape_flat_from_state(state, "cror_f_")
        r_shape = shape_flat_from_state(state, "cror_r_")
        flat = {
            "axial_gap_mm": float(state.cror_gap),
            "hub_radius": float(state.cror_hub_r),
            "tip_radius": float(state.cror_tip_r),
            "n_front": int(state.cror_f_n),
            "n_rear": int(state.cror_r_n),
            "f_chord_root": float(state.cror_f_chord_root),
            "f_chord_mid": float(state.cror_f_chord_mid),
            "f_chord_tip": float(state.cror_f_chord_tip),
            "f_stagger": float(state.cror_f_stagger),
            "r_chord_root": float(state.cror_r_chord_root),
            "r_chord_mid": float(state.cror_r_chord_mid),
            "r_chord_tip": float(state.cror_r_chord_tip),
            "r_stagger": float(state.cror_r_stagger),
        }
        for k, v in f_shape.items():
            flat[f"f_{k}"] = v
        for k, v in r_shape.items():
            flat[f"r_{k}"] = v
        return flat

    def _cror_params_from_editor() -> CrorParams:
        from fansim.cror.params_io import cror_params_from_flat

        raw = cror_params_from_flat(_cror_flat_from_state())
        return thin_cror_for_frame(raw, max_depth_mm=float(state.cror_max_depth))

    def thin_cror_now():
        if _cror_busy() or asynchronous is None:
            return

        async def task():
            state.cror_thin_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Thin",
                msg_attr="cror_msg",
                busy_attr="cror_thin_busy",
                note="default CROR stack",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                from fansim.cror.params_io import cror_params_from_flat

                flat = _cror_flat_from_state()
                raw = await loop.run_in_executor(None, lambda: cror_params_from_flat(flat))
                thin = await loop.run_in_executor(
                    None,
                    lambda: thin_cror_for_frame(raw, max_depth_mm=float(state.cror_max_depth)),
                )
                d0 = cror_stack_depth_mm(raw)
                d1 = cror_stack_depth_mm(thin)
                nz = estimate_cror_noise(thin, float(state.cror_rpm))
                state.cror_readout = [
                    f"Default depth {d0:.1f} mm → thinned {d1:.1f} mm "
                    f"(cap {float(state.cror_max_depth):.0f} mm, gap {thin.axial_gap_mm:.1f} mm)",
                    f"Proxy noise {nz['rel_dba']:.0f} (rel) · front BPF {nz['front_bpf_hz']:.0f} Hz · "
                    f"rear {nz['rear_bpf_hz']:.0f} Hz",
                ]
                state.cror_msg = f"✓ Thinned stack depth {d1:.1f} mm"
            except Exception as exc:  # noqa: BLE001
                state.cror_msg = f"⚠ Thin failed: {type(exc).__name__}: {exc}"
            finally:
                state.cror_thin_busy = False
                ticker.cancel()
                state.flush()

        asynchronous.create_task(task())

    def optimize_cror():
        if _cror_busy() or asynchronous is None:
            return
        try:
            trials = max(20, int(float(state.cror_trials)))
        except (TypeError, ValueError):
            trials = 60
        root = runs_root if runs_root.exists() else Path("runs")
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = cror_opt_out_path(stamp=stamp, runs_root=root)

        async def task():
            state.cror_opt_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Optimize",
                msg_attr="cror_msg",
                busy_attr="cror_opt_busy",
                note=(f"{trials} BEMT-proxy trials, " f"≤{float(state.cror_max_depth):.0f} mm"),
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                _, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_cror_study(
                        trials,
                        rpm=float(state.cror_rpm),
                        max_depth_mm=float(state.cror_max_depth),
                    ),
                )
                save_cror_pareto(
                    out_dir,
                    pareto,
                    meta={
                        "n_trials": trials,
                        "rpm": float(state.cror_rpm),
                        "max_depth_mm": float(state.cror_max_depth),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                state.cror_msg = f"⚠ CROR Optimize failed: {type(exc).__name__}: {exc}"
                state.cror_opt_busy = False
                ticker.cancel()
                state.flush()
                return
            state.cror_last_opt = str(out_dir)
            state.cror_has_front = True
            cror_pareto_store.clear()
            cror_pareto_store.extend(load_all_cror_pareto(root))
            _refresh_cror_figure()
            top = pareto[0] if pareto else None
            extra = ""
            if top:
                extra = (
                    f" Top: {top.get('thrust_g', 0):.0f} g · "
                    f"{top.get('eff_g_per_w', 0):.2f} g/W · "
                    f"noise {top.get('rel_dba', 0):.0f}"
                )
            state.cror_msg = (
                f"✓ {len(pareto)} CROR proxy front → {out_dir.name}.{extra} "
                f"Click a point to inspect params."
            )
            state.cror_opt_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def refine_cror_cfd():
        if _cror_busy() or asynchronous is None:
            return
        try:
            n_top = int(float(state.cror_cfd_top))
        except (TypeError, ValueError):
            n_top = 0
        n_top = max(0, min(8, n_top))
        if n_top <= 0:
            state.cror_msg = "Set CFD refine top N ≥ 1 (uses last CROR Optimize front)."
            state.flush()
            return
        root = runs_root if runs_root.exists() else Path("runs")
        last = state.cror_last_opt or None
        if not last:
            found = latest_cror_opt_dir(root)
            last = str(found) if found else None
        if not last:
            state.cror_msg = "⚠ No CROR Optimize front yet — run Optimize first."
            state.flush()
            return
        pareto_dir = Path(last)
        pareto = load_cror_pareto(pareto_dir)
        if not pareto:
            state.cror_msg = f"⚠ No pareto.json in {pareto_dir.name}"
            state.flush()
            return
        out = pareto_dir / "cfd_refine"

        async def task():
            state.cror_refine_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="CFD refine",
                msg_attr="cror_msg",
                busy_attr="cror_refine_busy",
                note=f"dual-MRF top {n_top} of {len(pareto)}",
                interval=2.0,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                rows = await loop.run_in_executor(
                    None,
                    lambda: refine_cror_pareto_cfd(
                        pareto,
                        out,
                        n_top=n_top,
                        load_pa=8.0,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.cror_msg = f"⚠ CROR CFD refine failed: {type(exc).__name__}: {exc}"
                state.cror_refine_busy = False
                ticker.cancel()
                state.flush()
                return
            ok = sum(1 for r in rows if r.get("feasible"))
            state.cror_msg = (
                f"✓ CROR CFD refine {ok}/{len(rows)} feasible → {out} "
                f"(summary.json; proxy ● points unchanged)"
            )
            state.cror_refine_busy = False
            ticker.cancel()
            # Show the airflow for the best refined (feasible) design.
            best = next((r for r in rows if r.get("feasible")), rows[0] if rows else None)
            if best and best.get("workdir"):
                _render_cror_airflow(best["workdir"])
            state.flush()

        asynchronous.create_task(task())

    def load_cror_row(idx=None, **_):
        if idx is None or not (0 <= int(idx) < len(cror_pareto_store)):
            return
        row = cror_pareto_store[int(idx)]
        p = row.get("params") or {}
        from fansim.cockpit.blade_editor import apply_shape_flat_to_state
        from fansim.cror.params_io import cror_flat_from_params, cror_params_from_flat

        params = cror_params_from_flat(p)
        flat = cror_flat_from_params(params)
        state.cror_hub_r = float(flat["hub_radius"])
        state.cror_tip_r = float(flat["tip_radius"])
        state.cror_gap = float(flat["axial_gap_mm"])
        state.cror_f_n = int(flat["n_front"])
        state.cror_r_n = int(flat["n_rear"])
        state.cror_f_chord_root = float(flat["f_chord_root"])
        state.cror_f_chord_mid = float(flat["f_chord_mid"])
        state.cror_f_chord_tip = float(flat["f_chord_tip"])
        state.cror_f_stagger = float(flat["f_stagger"])
        state.cror_r_chord_root = float(flat["r_chord_root"])
        state.cror_r_chord_mid = float(flat["r_chord_mid"])
        state.cror_r_chord_tip = float(flat["r_chord_tip"])
        state.cror_r_stagger = float(flat["r_stagger"])
        apply_shape_flat_to_state(
            state, "cror_f_", {k[2:]: v for k, v in flat.items() if k.startswith("f_")})
        apply_shape_flat_to_state(
            state, "cror_r_", {k[2:]: v for k, v in flat.items() if k.startswith("r_")})
        state.cror_readout = [
            f"#{idx}  thrust {row.get('thrust_g', 0):.0f} g  ·  "
            f"{row.get('eff_g_per_w', 0):.2f} g/W  ·  "
            f"depth {row.get('depth_mm', 0):.1f} mm  ·  "
            f"noise {row.get('rel_dba', 0):.0f} (rel)",
            f"Loaded front/rear Design from {row.get('source_run', 'front')}",
        ]
        state.cror_msg = f"Loaded CROR front row #{idx} into the editor."
        state.flush()

    def export_cror_now():
        if _cror_busy() or asynchronous is None:
            return

        async def task():
            state.cror_export_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Export",
                msg_attr="cror_msg",
                busy_attr="cror_export_busy",
                note="thinned CROR STL",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            exports = exports_dir()
            exports.mkdir(exist_ok=True)
            out = exports / "cror_cockpit.stl"
            try:
                params = await loop.run_in_executor(None, _cror_params_from_editor)
                await loop.run_in_executor(None, lambda: export_cror_stl(params, out))
                depth = cror_stack_depth_mm(params)
                state.cror_msg = f"✓ Saved {out.resolve()} (depth {depth:.1f} mm)"
                _refresh_cror_export_items()
            except Exception as exc:  # noqa: BLE001
                state.cror_msg = f"⚠ CROR export failed: {type(exc).__name__}: {exc}"
            finally:
                state.cror_export_busy = False
                ticker.cancel()
                state.flush()

        asynchronous.create_task(task())

    # Expose callbacks for the UI renderer.
    ctx.thin_cror_now = thin_cror_now  # type: ignore[attr-defined]
    ctx.export_cror_now = export_cror_now  # type: ignore[attr-defined]
    ctx.preview_cror = preview_cror  # type: ignore[attr-defined]
    ctx.optimize_cror = optimize_cror  # type: ignore[attr-defined]
    ctx.refine_cror_cfd = refine_cror_cfd  # type: ignore[attr-defined]
    ctx.load_cror_row = load_cror_row  # type: ignore[attr-defined]


def render_cror_tab(ctx: CockpitCtx) -> None:
    """Build CROR UI (call inside layout content)."""
    if html is None or v3 is None or plotly_widgets is None or plotter_ui is None:
        return

    state, ctrl = ctx.state, ctx.ctrl
    cror_pareto_store = getattr(ctx, "cror_pareto_store")  # set by setup_cror_tab
    cror_plotter = ensure_plotter(ctx, "cror_plotter")

    def _slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None, **_kw):
        # Shared slider: label + exact value always visible (these tabs showed no numbers; §23.24).
        _shared_slider(label, model, mn, mx, step, disabled=disabled)

    _cror_busy_expr = (
        "cror_preview_busy || cror_opt_busy || cror_refine_busy || "
        "cror_thin_busy || cror_export_busy"
    )

    # ---- CROR TAB -----------------------------------------------------------------
    with html.Div(v_show="active_tab === 'cror'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):

                def _cror_design():
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div(
                            "Counter-rotating stacked rotors — Design + BEMT proxy Optimize",
                            classes="text-subtitle-2 mb-1",
                        )
                        html.Div(
                            "Edit front/rear planform, then Preview / Export / Optimize. "
                            "Optimize is BEMT-proxy NSGA (not dual-MRF). Relative noise only.",
                            classes="text-caption mb-2",
                            style="white-space: pre-line",
                        )
                        _slider("Hub R (mm)", "cror_hub_r", 14.0, 28.0, 0.5)
                        _slider("Tip R (mm)", "cror_tip_r", 45.0, 58.0, 0.5)
                        _slider("Axial gap (mm)", "cror_gap", 2.0, 12.0, 0.5)
                        with v3.VExpansionPanels(variant="accordion", class_="mb-2"):
                            with v3.VExpansionPanel(title="Front rotor"):
                                with v3.VExpansionPanelText():
                                    _slider("Front blades", "cror_f_n", 5, 11, 1)
                                    _slider(
                                        "Chord root", "cror_f_chord_root", 8.0, 20.0, 0.5, unit="mm")
                                    _slider(
                                        "Chord mid", "cror_f_chord_mid", 8.0, 20.0, 0.5, unit="mm")
                                    _slider(
                                        "Chord tip", "cror_f_chord_tip", 6.0, 16.0, 0.5, unit="mm")
                                    _slider(
                                        "Stagger", "cror_f_stagger", 25.0, 50.0, 1.0, unit="deg")
                                    from fansim.cockpit.blade_editor import render_shape_panels
                                    from fansim.cockpit.fan_widgets import help_switch as _hs
                                    render_shape_panels(
                                        prefix="cror_f_",
                                        slider=_slider,
                                        help_switch=_hs,
                                        v3=v3,
                                        html=html,
                                        title_thick="Front thickness/camber",
                                        title_3d="Front 3-D",
                                        title_tip="Front tip",
                                    )
                            with v3.VExpansionPanel(title="Rear rotor"):
                                with v3.VExpansionPanelText():
                                    _slider("Rear blades", "cror_r_n", 5, 13, 1)
                                    _slider(
                                        "Chord root", "cror_r_chord_root", 8.0, 20.0, 0.5, unit="mm")
                                    _slider(
                                        "Chord mid", "cror_r_chord_mid", 8.0, 20.0, 0.5, unit="mm")
                                    _slider(
                                        "Chord tip", "cror_r_chord_tip", 6.0, 16.0, 0.5, unit="mm")
                                    _slider(
                                        "Stagger", "cror_r_stagger", 25.0, 50.0, 1.0, unit="deg")
                                    from fansim.cockpit.blade_editor import render_shape_panels
                                    from fansim.cockpit.fan_widgets import help_switch as _hs
                                    render_shape_panels(
                                        prefix="cror_r_",
                                        slider=_slider,
                                        help_switch=_hs,
                                        v3=v3,
                                        html=html,
                                        title_thick="Rear thickness/camber",
                                        title_3d="Rear 3-D",
                                        title_tip="Rear tip",
                                    )
                        v3.VBtn(
                            "Thin to depth",
                            size="small",
                            variant="tonal",
                            color="primary",
                            click=(getattr(ctx, "thin_cror_now"),),
                            classes="mb-2",
                            loading=("cror_thin_busy",),
                            disabled=(_cror_busy_expr,),
                        )
                        render_action_row(
                            v3,
                            {
                                "preview": {
                                    "label": "Preview",
                                    "size": "small",
                                    "variant": "tonal",
                                    "color": "primary",
                                    "click": (getattr(ctx, "preview_cror"),),
                                    "loading": ("cror_preview_busy",),
                                    "disabled": (_cror_busy_expr,),
                                },
                                "export": {
                                    "label": "Export STL",
                                    "size": "small",
                                    "variant": "tonal",
                                    "color": "primary",
                                    "click": (getattr(ctx, "export_cror_now"),),
                                    "loading": ("cror_export_busy",),
                                    "disabled": (_cror_busy_expr,),
                                },
                                "optimize": {
                                    "label": "Optimize",
                                    "color": "success",
                                    "size": "small",
                                    "click": (getattr(ctx, "optimize_cror"),),
                                    "loading": ("cror_opt_busy",),
                                    "disabled": (_cror_busy_expr,),
                                },
                            },
                        )
                        html.Div(
                            "{{ cror_msg }}",
                            classes="text-caption mt-2",
                            style="white-space: pre-line",
                        )
                        ctx.busy_bar(
                            "cror_preview_busy",
                            "cror_opt_busy",
                            "cror_refine_busy",
                            "cror_thin_busy",
                            "cror_export_busy",
                            color="success",
                        )
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div(
                            "Optimize (BEMT proxy NSGA)",
                            classes="text-subtitle-2 mb-1",
                        )
                        html.Div(
                            "Screen counter-rotating stacks for thrust, efficiency, and relative "
                            "noise. Optional CFD refine scores top-N finalists (dual-MRF).",
                            classes="text-caption mb-2",
                            style="white-space: pre-line",
                        )
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=4, classes="pr-1"):
                                v3.VTextField(
                                    label="Trials",
                                    v_model=("cror_trials",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                            with v3.VCol(cols=4, classes="px-1"):
                                v3.VTextField(
                                    label="RPM",
                                    v_model=("cror_rpm",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                            with v3.VCol(cols=4, classes="pl-1"):
                                v3.VTextField(
                                    label="Max depth mm",
                                    v_model=("cror_max_depth",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                        with v3.VRow(no_gutters=True, classes="mt-2 align-center"):
                            with v3.VCol(cols=5, classes="pr-1"):
                                v3.VTextField(
                                    label="CFD refine top N",
                                    v_model=("cror_cfd_top",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                            with v3.VCol(cols=7, classes="pl-1"):
                                v3.VBtn(
                                    "CFD refine",
                                    color="warning",
                                    variant="tonal",  # solid orange looked enabled while disabled (§23.26)
                                    size="small",
                                    block=True,
                                    click=(getattr(ctx, "refine_cror_cfd"),),
                                    loading=("cror_refine_busy",),
                                    disabled=(
                                        f"{_cror_busy_expr} || !cror_has_front || !(cror_cfd_top > 0)",
                                    ),
                                )

                def _cror_results():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("cror_sel_idx",),
                            items=("cror_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_cror_row"), "[$event]"),
                        )
                    with v3.VCard(style=f"height:{SCATTER_HEIGHT_PX}px;", classes="pa-1 mb-2"):
                        cror_fig_widget = plotly_widgets.Figure(
                            figure=cror_scatter_figure(cror_pareto_store),
                            click=(
                                getattr(ctx, "load_cror_row"),
                                "[$event?.points?.[0]?.customdata]",
                            ),
                            style="width:100%;",
                        )
                        ctrl.cror_fig_update = cror_fig_widget.update

                def _cror_library():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("cror_sel_idx",),
                            items=("cror_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_cror_row"), "[$event]"),
                        )
                    with v3.VCard(classes="pa-2"):
                        html.Div(
                            "Exported CROR files under exports/ (cror*).",
                            classes="text-caption mb-2",
                        )
                        with v3.VList(density="compact", lines="one"):
                            with v3.VListItem(v_for="it in cror_export_items", key="it.value"):
                                v3.VListItemTitle("{{ it.title }}")
                        html.Div(
                            "No exports yet — use Export STL on Design.",
                            classes="text-caption text-medium-emphasis",
                            v_if="!cror_export_items.length",
                        )

                render_left_shell(
                    v3,
                    html,
                    state_key="cror_subtab",
                    design=_cror_design,
                    results=_cror_results,
                    library=_cror_library,
                )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "{{ line }}",
                        v_for="line in cror_readout",
                        classes="text-body-2",
                    )
                with v3.VCard(style=f"height:{VTK_HEIGHT_PX}px;", classes="mb-2"):
                    cror_view = plotter_ui(cror_plotter)
                    ctrl.cror_view_update = cror_view.update
                with v3.VCard(classes="mb-2 pa-2", v_show="cror_subtab === 'results'"):
                    html.Div(
                        "Duct airflow — top CFD-refined design",
                        classes="text-subtitle-2 mb-1",
                    )
                    html.Div(
                        "From the best design of the last CFD refine (dual-MRF). |U|/pressure "
                        "midplane; axial Uz (blue = delivery, red = reverse); streamlines by |U|. "
                        "Counter-rotating rotors cancel much of the net swirl.",
                        classes="text-caption text-medium-emphasis mb-2",
                    )
                    with v3.VBtnToggle(
                        v_model=("cror_airflow_field",),
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
                        "{{ cror_airflow_caption }}",
                        classes="text-caption text-medium-emphasis mb-1",
                    )
                    html.Img(
                        src=("cror_airflow_img_uri",),
                        v_show="cror_airflow_img_uri",
                        style=(
                            "width:100%;max-height:520px;object-fit:contain;"
                            "display:block;background:#fafafa;border-radius:4px;"
                        ),
                    )
