"""Volute cockpit tab (radial impeller + sealed volute casing).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from fansim.cockpit.airflow_panel import pick_airflow_uri, render_airflow_pack
from fansim.cockpit.paths import exports_dir
from fansim.cockpit.busy import cfd_stage_hint
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_widgets import slider as _shared_slider
from fansim.cockpit.data import design_dropdown_items
from fansim.cockpit.figures import volute_scatter_figure
from fansim.cockpit.plotters import ensure_plotter
from fansim.cockpit.tab_shell import (
    SCATTER_HEIGHT_PX,
    VTK_VIEW_STYLE,
    render_action_row,
    render_left_shell,
)
from fansim.volute.optimize import run_volute_study
from fansim.volute.persist import (
    latest_volute_opt_dir,
    load_all_volute_pareto,
    volute_opt_out_path,
)

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    plotter_ui = None  # type: ignore[assignment]
    asynchronous = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from pyvista.trame.ui import plotter_ui
    from trame.app import asynchronous
    from trame.widgets import html
    from trame.widgets import plotly as plotly_widgets
    from trame.widgets import vuetify3 as v3




def split_volute_preview(mesh):
    """(casing, [rotor parts]) from the two-body preview STL; (None, []) if it doesn't split.

    The casing encloses the impeller, so it is the body with the largest bounding box.
    """
    try:
        bodies = list(mesh.split_bodies())
    except Exception:  # noqa: BLE001 — viz only
        return None, []
    if len(bodies) < 2:
        return None, []

    def _extent(b):
        x0, x1, y0, y1, z0, z1 = b.bounds
        return (x1 - x0) * (y1 - y0) * (z1 - z0)

    bodies.sort(key=_extent, reverse=True)
    return bodies[0].extract_surface(), [b.extract_surface() for b in bodies[1:]]

def volute_export_rows(exports: Path, limit: int = 24) -> list[dict]:
    """Newest-first ``{title, value}`` rows for volute STLs under ``exports``.

    (The inline version had ``len(rel := ...).parts`` — ``len()`` of a Path — so every Export after
    the first reported "Export failed: object of type 'PosixPath' has no len()" even though the
    STLs were written. QA 2026-10-08, roadmap §23.2.)
    """
    rows: list[dict] = []
    if not exports.is_dir():
        return rows
    candidates: list[Path] = []
    for path in exports.rglob("*.stl"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(exports)
        except ValueError:
            continue
        if path.name.lower().startswith("volute") or (
            rel.parts and rel.parts[0].lower().startswith("volute")
        ):
            candidates.append(path)
    for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
        rel = path.relative_to(exports)
        title = f"{rel.parts[0]}/{path.name}" if len(rel.parts) > 1 else path.name
        rows.append({"title": title, "value": str(path.resolve())})
        if len(rows) >= limit:
            break
    return rows

def setup_volute_tab(ctx: CockpitCtx) -> None:
    """Init volute_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    runs_root = ctx.runs_root
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # ---- Volute tab (90° radial + casing scaffold, §4.1 leftover) --------------------------
    from fansim.volute.domain import DEFAULT_VOLUTE_RPM as _VOLUTE_RPM
    from fansim.volute.geometry import VoluteParams as _VoluteDefaults
    from fansim.volute.isolated import (
        build_volute_preview_isolated,
        build_volute_stls_isolated,
        evaluate_volute_isolated,
    )
    from fansim.volute.params_io import volute_params_from_flat

    _v0 = _VoluteDefaults()
    volute_preview_stl = Path(tempfile.gettempdir()) / "fansim_volute_preview.stl"
    _volute_runs = runs_root if runs_root.exists() else Path("runs")
    volute_design_store: list[dict] = load_all_volute_pareto(_volute_runs)

    # Shared objects for render + callbacks (kept per-session).
    ctx.volute_preview_stl = volute_preview_stl  # type: ignore[attr-defined]
    ctx.volute_design_store = volute_design_store  # type: ignore[attr-defined]

    state.volute_n_blades = int(_v0.n_blades)
    state.volute_r_hub = float(_v0.r_hub_mm)
    state.volute_r_tip = float(_v0.r_tip_mm)
    state.volute_blade_h = float(_v0.blade_height_mm)
    state.volute_blade_thick = float(_v0.blade_thick_mm)
    state.volute_backplate = float(_v0.backplate_thick_mm)
    state.volute_spiral = float(_v0.spiral_growth_mm)
    state.volute_clearance = float(_v0.volute_clearance_mm)
    state.volute_wall = float(_v0.volute_wall_mm)
    state.volute_tongue_angle = float(_v0.tongue_angle_deg)
    state.volute_tongue_clear = float(_v0.tongue_tip_clearance_mm)
    state.volute_tongue_fillet = float(_v0.tongue_fillet_mm)
    state.volute_out_w = float(_v0.outlet_width_mm)
    state.volute_out_l = float(_v0.outlet_length_mm)
    state.volute_out_h = float(_v0.outlet_height_mm)
    state.volute_rpm = float(_VOLUTE_RPM)
    state.volute_load_pa = 50.0
    state.volute_subtab = "design"
    state.volute_export_items = []
    state.volute_preview_busy = False
    state.volute_export_busy = False
    state.volute_assess_busy = False
    state.volute_opt_busy = False
    state.volute_trials = 80
    state.volute_resume = False
    state.volute_geo_ready = False
    _volute_last = latest_volute_opt_dir(_volute_runs)
    state.volute_last_opt = str(_volute_last) if _volute_last else ""
    state.volute_has_front = bool(_volute_last) or bool(volute_design_store)
    state.volute_msg = (
        "Radial impeller + sealed volute enclosure (smooth Archimedean scroll). "
        "Assess runs radial MRF; Optimize is a geometry proxy (not CFM)."
    )
    state.volute_readout = [
        "Preview / Export: impeller + sealed casing STLs.",
        "Assess: free+load CFD in the radial MRF domain (OpenFOAM Docker).",
        "Optimize: NSGA geometry proxy — ranking only; Assess for honest CFD.",
    ]
    if volute_design_store:
        state.volute_msg = (
            f"Loaded {len(volute_design_store)} Optimize proxy point(s) onto the volute scatter."
        )

    state.volute_sel_trial = None  # previous-runs dropdown (loads by trial)
    state.volute_trial_items = design_dropdown_items(volute_design_store)
    state.volute_airflow_field = "U"
    state.volute_airflow_img_uri = ""
    state.volute_airflow_caption = "Run Assess to see scroll-section airflow for a solved case."
    state.volute_airflow_busy = False
    state.volute_last_assess = ""

    def _refresh_volute_figure():
        state.volute_trial_items = design_dropdown_items(volute_design_store)
        if hasattr(ctrl, "volute_fig_update"):
            ctrl.volute_fig_update(volute_scatter_figure(volute_design_store))

    def _refresh_volute_export_items():
        rows = volute_export_rows(exports_dir())
        state.volute_export_items = rows

    _refresh_volute_export_items()

    # --- Scroll-section airflow (§17.3 Volute): Y=0 full section, not axial wake crop ------
    _volute_airflow = {"uris": {}, "gen": 0}

    def _apply_volute_airflow_field():
        uri, cap = pick_airflow_uri(
            _volute_airflow["uris"], state.volute_airflow_field or "U", layout="scroll",
        )
        state.volute_airflow_img_uri = uri
        if uri:
            state.volute_airflow_caption = cap
        elif not state.volute_airflow_busy:
            state.volute_airflow_caption = "Run Assess to see scroll-section airflow for a solved case."

    def _render_volute_airflow(case_dir):
        if not case_dir or asynchronous is None:
            _volute_airflow["uris"] = {}
            state.volute_airflow_img_uri = ""
            state.volute_airflow_caption = "Run Assess to see scroll-section airflow for a solved case."
            return
        _volute_airflow["gen"] += 1
        gen = _volute_airflow["gen"]
        state.volute_airflow_busy = True
        state.volute_airflow_img_uri = ""
        state.volute_airflow_caption = "Rendering scroll-section airflow…"
        state.flush()

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(
                    None,
                    lambda: render_airflow_pack(str(case_dir), layout="scroll"),
                )
                if _volute_airflow["gen"] != gen:
                    return
                _volute_airflow["uris"] = pack["uris"]
                state.volute_airflow_busy = False
                _apply_volute_airflow_field()
            except Exception:  # noqa: BLE001 — viz must never break the tab
                if _volute_airflow["gen"] == gen:
                    _volute_airflow["uris"] = {}
                    state.volute_airflow_busy = False
                    state.volute_airflow_img_uri = ""
                    state.volute_airflow_caption = "Airflow not available for this design"
            finally:
                try:
                    state.flush()
                    ctrl.volute_view_update()
                except Exception:  # noqa: BLE001
                    pass

        asynchronous.create_task(task())

    @state.change("volute_airflow_field")
    def _on_volute_airflow_field(**_):
        _apply_volute_airflow_field()
        try:
            state.flush()
        except Exception:  # noqa: BLE001
            pass

    def _volute_flat_from_state() -> dict:
        return {
            "n_blades": int(state.volute_n_blades),
            "r_hub_mm": float(state.volute_r_hub),
            "r_tip_mm": float(state.volute_r_tip),
            "blade_height_mm": float(state.volute_blade_h),
            "blade_thick_mm": float(state.volute_blade_thick),
            "backplate_thick_mm": float(state.volute_backplate),
            "spiral_growth_mm": float(state.volute_spiral),
            "volute_clearance_mm": float(state.volute_clearance),
            "volute_wall_mm": float(state.volute_wall),
            "tongue_angle_deg": float(state.volute_tongue_angle),
            "tongue_tip_clearance_mm": float(state.volute_tongue_clear),
            "tongue_fillet_mm": float(state.volute_tongue_fillet),
            "outlet_width_mm": float(state.volute_out_w),
            "outlet_length_mm": float(state.volute_out_l),
            "outlet_height_mm": float(state.volute_out_h),
        }

    def _volute_busy() -> bool:
        return bool(
            state.volute_preview_busy
            or state.volute_export_busy
            or state.volute_assess_busy
            or state.volute_opt_busy
        )

    def _show_volute_stl(path: Path):
        volute_plotter = ensure_plotter(ctx, "volute_plotter")
        if volute_plotter is None:
            return
        # clear_actors, not clear(): clear() also removes every light, so previews rendered as a
        # flat unlit silhouette (§23.25). Axes stay from make_white_plotter.
        volute_plotter.clear_actors()
        mesh = pv.read(str(path))
        casing, rotor = split_volute_preview(mesh)
        if casing is None:
            volute_plotter.add_mesh(mesh, color="lightsteelblue", smooth_shading=True)
        else:
            # The opaque casing hid the impeller (§23.23): casing translucent, impeller solid.
            volute_plotter.add_mesh(casing, color="lightgray", opacity=0.25, smooth_shading=True)
            for part in rotor:
                volute_plotter.add_mesh(part, color="cadetblue", smooth_shading=True)
        volute_plotter.reset_camera()
        ctrl.volute_view_update()

    async def volute_preview(**_):
        if _volute_busy():
            return
        try:
            flat = _volute_flat_from_state()
            volute_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        state.volute_preview_busy = True
        ticker, _t0 = spawn_busy_ticker(
            action="Preview",
            msg_attr="volute_msg",
            busy_attr="volute_preview_busy",
            note="impeller + casing",
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: build_volute_preview_isolated(
                    flat, volute_preview_stl, timeout=300.0
                ),
            )
            _show_volute_stl(volute_preview_stl)
            state.volute_geo_ready = True
            state.volute_msg = "✓ Preview ready (impeller + casing; no CFD)."
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Preview failed: {type(exc).__name__}: {exc}"
        finally:
            state.volute_preview_busy = False
            ticker.cancel()
            state.flush()

    async def volute_export(**_):
        if _volute_busy():
            return
        try:
            flat = _volute_flat_from_state()
            volute_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = exports_dir() / f"volute_{stamp}"
        state.volute_export_busy = True
        ticker, _t0 = spawn_busy_ticker(
            action="Export",
            msg_attr="volute_msg",
            busy_attr="volute_export_busy",
            note="impeller + casing STLs",
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            imp, cas = await loop.run_in_executor(
                None,
                lambda: build_volute_stls_isolated(flat, out_dir, timeout=300.0),
            )
            state.volute_msg = f"✓ Saved {imp.resolve()}\n✓ Saved {cas.resolve()}"
            _refresh_volute_export_items()
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
        finally:
            state.volute_export_busy = False
            ticker.cancel()
            state.flush()

    async def volute_assess(**_):
        if _volute_busy():
            return
        try:
            flat = _volute_flat_from_state()
            volute_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        workdir = Path("runs") / f"cockpit_volute_{stamp}"
        load_pa = float(state.volute_load_pa or 50.0)
        rpm = float(state.volute_rpm or _VOLUTE_RPM)
        state.volute_assess_busy = True
        wd_holder: list = [workdir]
        ticker, _t0 = spawn_busy_ticker(
            action="Assess",
            msg_attr="volute_msg",
            busy_attr="volute_assess_busy",
            note=f"radial MRF, {rpm:.0f} RPM, {load_pa:g} Pa",
            hint_fn=lambda: cfd_stage_hint(wd_holder[0]),
            interval=2.0,
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(
                None,
                lambda: evaluate_volute_isolated(
                    flat,
                    workdir,
                    load_pa=load_pa,
                    rpm=rpm,
                    procs=8,
                    base_cell=0.006,
                    iters=500,
                    timeout=1800.0,
                ),
            )
            if res.feasible:
                state.volute_msg = (
                    f"✓ Assess OK → {workdir}\n"
                    f"CFM free={res.cfm_free:.1f}  load={res.cfm_load:.1f}  "
                    f"η={res.efficiency:.1f}%  ({res.runtime_s:.0f}s)"
                )
                state.volute_readout = [
                    f"CFM free {res.cfm_free:.1f} · load {res.cfm_load:.1f} · "
                    f"η {res.efficiency:.1f}% · {rpm:.0f} RPM",
                    f"Domain: radial MRF stage 1 ({res.raw.get('honesty', '')}).",
                    f"Workdir: {workdir}",
                ]
                state.volute_last_assess = str(workdir)
                _render_volute_airflow(workdir)
            else:
                state.volute_msg = (
                    f"⚠ Assess infeasible: {res.reason or 'unknown'}\n"
                    f"workdir={workdir}"
                )
                state.volute_readout = [
                    f"Infeasible: {res.reason}",
                    f"topology={res.raw.get('topology')} honesty={res.raw.get('honesty')}",
                    f"Workdir: {workdir}",
                ]
        except Exception as exc:  # noqa: BLE001
            state.volute_msg = f"⚠ Assess failed: {type(exc).__name__}: {exc}"
        finally:
            state.volute_assess_busy = False
            ticker.cancel()
            state.flush()

    def optimize_volute():
        """Geometry-proxy NSGA for volute Design (§14.4b) — not CFD / not CFM."""
        if _volute_busy():
            return
        try:
            trials = max(40, int(float(state.volute_trials)))
        except (TypeError, ValueError):
            trials = 80
        try:
            rpm = float(state.volute_rpm)
        except (TypeError, ValueError):
            rpm = float(_VOLUTE_RPM)
        resume = bool(state.volute_resume)
        root = runs_root if runs_root.exists() else Path("runs")
        last = state.volute_last_opt or None
        if resume and not last:
            found = latest_volute_opt_dir(root)
            last = str(found) if found else None
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = volute_opt_out_path(
            resume=resume, last_dir=last, stamp=stamp, runs_root=root)
        mode = "resume" if resume and out_dir == Path(last or "") else "new"

        async def task():
            state.volute_opt_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Optimize",
                msg_attr="volute_msg",
                busy_attr="volute_opt_busy",
                note=f"{trials} proxy trials @ {rpm:.0f} rpm, {mode}",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                _, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_volute_study(
                        n_trials=trials,
                        rpm=rpm,
                        out_dir=out_dir,
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.volute_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.volute_opt_busy = False
                ticker.cancel()
                state.flush()
                return
            state.volute_last_opt = str(out_dir)
            state.volute_has_front = True
            volute_design_store.clear()
            volute_design_store.extend(load_all_volute_pareto(root))
            _refresh_volute_figure()
            state.volute_msg = (
                f"✓ {len(pareto)} proxy front design(s) → {out_dir.name} "
                f"(geometry ranking — Assess for CFD). Click a ● point to load knobs."
            )
            state.volute_opt_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def load_volute_trial(trial=None, **_):
        """Load a volute Optimize point into the editor from the scatter click."""
        if trial is None:
            return
        tid = int(trial)
        row = next((r for r in volute_design_store if int(r["trial"]) == tid), None)
        if row is None:
            return
        p = row.get("params") or {}
        if "n_blades" in p:
            state.volute_n_blades = int(p["n_blades"])
        if "r_hub_mm" in p:
            state.volute_r_hub = float(p["r_hub_mm"])
        if "r_tip_mm" in p:
            state.volute_r_tip = float(p["r_tip_mm"])
        if "blade_height_mm" in p:
            state.volute_blade_h = float(p["blade_height_mm"])
        if "blade_thick_mm" in p:
            state.volute_blade_thick = float(p["blade_thick_mm"])
        if "backplate_thick_mm" in p:
            state.volute_backplate = float(p["backplate_thick_mm"])
        if "spiral_growth_mm" in p:
            state.volute_spiral = float(p["spiral_growth_mm"])
        if "volute_clearance_mm" in p:
            state.volute_clearance = float(p["volute_clearance_mm"])
        if "volute_wall_mm" in p:
            state.volute_wall = float(p["volute_wall_mm"])
        if "tongue_angle_deg" in p:
            state.volute_tongue_angle = float(p["tongue_angle_deg"])
        if "tongue_tip_clearance_mm" in p:
            state.volute_tongue_clear = float(p["tongue_tip_clearance_mm"])
        if "tongue_fillet_mm" in p:
            state.volute_tongue_fillet = float(p["tongue_fillet_mm"])
        if "outlet_width_mm" in p:
            state.volute_out_w = float(p["outlet_width_mm"])
        if "outlet_length_mm" in p:
            state.volute_out_l = float(p["outlet_length_mm"])
        if "outlet_height_mm" in p:
            state.volute_out_h = float(p["outlet_height_mm"])
        o = row.get("objectives") or {}
        state.volute_readout = [
            f"#{tid}  capacity {o.get('capacity_proxy', 0):.1f}  ·  "
            f"head {o.get('head_proxy', 0):.2f}  (proxy — not CFM)",
            f"Loaded from {row.get('extra', {}).get('source_run', '')}",
        ]
        state.volute_geo_ready = False
        state.volute_msg = f"Loaded #{tid} into Design — Preview to refresh STL."
        workdir = row.get("workdir") or state.volute_last_assess or None
        if workdir:
            _render_volute_airflow(workdir)
        state.flush()

    # Expose callbacks for the UI renderer.
    ctx.volute_preview = volute_preview  # type: ignore[attr-defined]
    ctx.volute_export = volute_export  # type: ignore[attr-defined]
    ctx.volute_assess = volute_assess  # type: ignore[attr-defined]
    ctx.optimize_volute = optimize_volute  # type: ignore[attr-defined]
    ctx.load_volute_trial = load_volute_trial  # type: ignore[attr-defined]


def render_volute_tab(ctx: CockpitCtx) -> None:
    """Build Volute UI (call inside layout content)."""
    state, ctrl = ctx.state, ctx.ctrl
    volute_plotter = ensure_plotter(ctx, "volute_plotter")
    volute_design_store = getattr(ctx, "volute_design_store", [])

    def _slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None, **_kw):
        # Shared slider: label + exact value always visible (these tabs showed no numbers; §23.24).
        _shared_slider(label, model, mn, mx, step, disabled=disabled)

    _volute_busy_expr = (
        "volute_preview_busy || volute_export_busy || volute_assess_busy || volute_opt_busy"
    )

    # ---- VOLUTE TAB ---------------------------------------------------------------
    with html.Div(v_show="active_tab === 'volute'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):

                def _volute_design():
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div(
                            "Radial impeller + sealed volute (radial MRF Assess)",
                            classes="text-subtitle-2 mb-1",
                        )
                        html.Div(
                            "90° discharge collector — not an A12x25 drop-in. "
                            "Assess uses sealed-enclosure radial MRF (+Z inlet / +X outlet). "
                            "Optimize is a geometry proxy (ranking only — not CFM).",
                            classes="text-caption mb-2",
                            style="white-space: pre-line",
                        )
                        _slider("Blades", "volute_n_blades", 5, 11, 1)
                        _slider("Hub R (mm)", "volute_r_hub", 12.0, 28.0, 0.5)
                        _slider("Tip R (mm)", "volute_r_tip", 35.0, 60.0, 0.5)
                        _slider("Blade height (mm)", "volute_blade_h", 12.0, 32.0, 0.5)
                        _slider("Blade thick (mm)", "volute_blade_thick", 0.6, 2.5, 0.1)
                        _slider("Backplate (mm)", "volute_backplate", 1.0, 4.0, 0.1)
                        with v3.VExpansionPanels(variant="accordion", class_="mb-2"):
                            with v3.VExpansionPanel(title="Scroll & tongue"):
                                with v3.VExpansionPanelText():
                                    _slider("Spiral growth (mm)", "volute_spiral", 10.0, 40.0, 1.0)
                                    _slider("Tip clearance (mm)", "volute_clearance", 1.0, 8.0, 0.5)
                                    _slider("Wall (mm)", "volute_wall", 1.0, 4.0, 0.1)
                                    _slider("Tongue angle (°)", "volute_tongue_angle", 2.0, 15.0, 0.5)
                                    _slider("Tongue clear (mm)", "volute_tongue_clear", 0.5, 4.0, 0.1)
                                    _slider("Tongue fillet (mm)", "volute_tongue_fillet", 0.0, 4.0, 0.1)
                            with v3.VExpansionPanel(title="Outlet"):
                                with v3.VExpansionPanelText():
                                    _slider("Outlet width (mm)", "volute_out_w", 20.0, 50.0, 1.0)
                                    _slider("Outlet length (mm)", "volute_out_l", 20.0, 60.0, 1.0)
                                    _slider("Outlet height (mm)", "volute_out_h", 12.0, 40.0, 1.0)
                        # mt-4: outlined labels float above the border and were clipped by the panels (§23.23)
                        with v3.VRow(no_gutters=True, classes="mt-4"):
                            with v3.VCol(cols=6, classes="pr-1"):
                                v3.VTextField(
                                    label="RPM",
                                    v_model=("volute_rpm",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                            with v3.VCol(cols=6, classes="pl-1"):
                                v3.VTextField(
                                    label="Load Pa@50CFM",
                                    v_model=("volute_load_pa",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                    with v3.VCard(classes="mb-2 pa-3"):
                        render_action_row(
                            v3,
                            {
                                "preview": {
                                    "label": "Preview",
                                    "color": "primary",
                                    "size": "small",
                                    "click": (getattr(ctx, "volute_preview"),),
                                    "loading": ("volute_preview_busy",),
                                    "disabled": (_volute_busy_expr,),
                                },
                                "score": {
                                    "label": "Assess",
                                    "color": "success",
                                    "size": "small",
                                    "click": (getattr(ctx, "volute_assess"),),
                                    "loading": ("volute_assess_busy",),
                                    "disabled": (f"{_volute_busy_expr} || !volute_geo_ready",),
                                },
                                "export": {
                                    "label": "Export STLs",
                                    "size": "small",
                                    "variant": "tonal",
                                    "color": "primary",
                                    "click": (getattr(ctx, "volute_export"),),
                                    "loading": ("volute_export_busy",),
                                    "disabled": (f"{_volute_busy_expr} || !volute_geo_ready",),
                                },
                                "optimize": {
                                    "label": "Optimize",
                                    "color": "success",
                                    "size": "small",
                                    "click": (getattr(ctx, "optimize_volute"),),
                                    "loading": ("volute_opt_busy",),
                                    "disabled": (_volute_busy_expr,),
                                },
                            },
                        )
                        html.Div(
                            "{{ volute_msg }}",
                            classes="text-caption mt-2",
                            style="white-space: pre-line",
                        )
                        ctx.busy_bar(
                            "volute_preview_busy",
                            "volute_export_busy",
                            "volute_assess_busy",
                            "volute_opt_busy",
                            color="success",
                        )
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div(
                            "Optimize (geometry proxy) — not CFM",
                            classes="text-subtitle-2 mb-1",
                        )
                        html.Div(
                            "NSGA ranks impeller + scroll geometry. Assess for honest radial MRF CFD. "
                            "Resume continues the last cockpit_volute_opt_* study.",
                            classes="text-caption mb-2",
                            style="white-space: pre-line",
                        )
                        v3.VTextField(
                            label="Trials",
                            v_model=("volute_trials",),
                            type="number",
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            classes="mb-2",
                        )
                        v3.VCheckbox(
                            label="Resume last Optimize front",
                            v_model=("volute_resume",),
                            density="compact",
                            hide_details=True,
                        )

                def _volute_results():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("volute_sel_trial",),
                            items=("volute_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_volute_trial"), "[$event]"),
                        )
                    with v3.VCard(style=f"height:{SCATTER_HEIGHT_PX}px;", classes="pa-1 mb-2"):
                        volute_fig_widget = plotly_widgets.Figure(
                            figure=volute_scatter_figure(volute_design_store),
                            click=(
                                getattr(ctx, "load_volute_trial"),
                                "[$event?.points?.[0]?.customdata]",
                            ),
                            style="width:100%;",
                        )
                        ctrl.volute_fig_update = volute_fig_widget.update

                def _volute_library():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("volute_sel_trial",),
                            items=("volute_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_volute_trial"), "[$event]"),
                        )
                    with v3.VCard(classes="pa-2"):
                        html.Div(
                            "Exported volute STLs under exports/ (volute_* folders).",
                            classes="text-caption mb-2",
                        )
                        with v3.VList(density="compact", lines="one"):
                            with v3.VListItem(v_for="it in volute_export_items", key="it.value"):
                                v3.VListItemTitle("{{ it.title }}")
                        html.Div(
                            "No exports yet — use Export STLs on Design.",
                            classes="text-caption text-medium-emphasis",
                            v_if="!volute_export_items.length",
                        )

                render_left_shell(
                    v3,
                    html,
                    state_key="volute_subtab",
                    design=_volute_design,
                    results=_volute_results,
                    library=_volute_library,
                )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "{{ line }}",
                        v_for="line in volute_readout",
                        classes="text-body-2",
                    )
                with v3.VCard(style=VTK_VIEW_STYLE, classes="mb-2"):
                    volute_view = plotter_ui(volute_plotter)
                    ctrl.volute_view_update = volute_view.update
                with v3.VCard(classes="mb-2 pa-2", v_show="volute_subtab === 'results'"):
                    html.Div(
                        "Scroll-section airflow — last Assess",
                        classes="text-subtitle-2 mb-1",
                    )
                    html.Div(
                        "Y=0 meridional cut of the sealed scroll (not the axial-duct wake crop). "
                        "|U| and pressure only — outlet is +X, inlet is +Z. Axial-Uz is omitted "
                        "because this is a radial machine.",
                        classes="text-caption text-medium-emphasis mb-2",
                    )
                    with v3.VBtnToggle(
                        v_model=("volute_airflow_field",),
                        density="compact",
                        color="primary",
                        classes="mb-2",
                        mandatory=True,
                    ):
                        v3.VBtn("|U| scroll", value="U", size="small")
                        v3.VBtn("pressure scroll", value="p", size="small")
                    html.Div(
                        "{{ volute_airflow_caption }}",
                        classes="text-caption text-medium-emphasis mb-1",
                    )
                    html.Img(
                        src=("volute_airflow_img_uri",),
                        v_show="volute_airflow_img_uri",
                        style=(
                            "width:100%;max-height:520px;object-fit:contain;"
                            "display:block;background:#fafafa;border-radius:4px;"
                        ),
                    )
