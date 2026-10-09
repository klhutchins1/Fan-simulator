"""Mixed-flow cockpit tab (Assess CFD + BEM Optimize).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
import time
from pathlib import Path

_log = logging.getLogger(__name__)

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.fan_widgets import slider as _shared_slider
from fansim.cockpit.airflow_panel import pick_airflow_uri, render_airflow_pack
from fansim.cockpit.data import design_dropdown_items
from fansim.cockpit.figures import mf_scatter_figure
from fansim.cockpit.plotters import ensure_plotter
from fansim.cockpit.tab_shell import (
    SCATTER_HEIGHT_PX,
    VTK_HEIGHT_PX,
    render_action_row,
    render_left_shell,
)
from fansim.fan_spec import A12X25
from fansim.isolated_job import stall_timeout
from fansim.optimize.isolated_eval import cfd_eval_timeout
from fansim.optimize.presets import assess_load

from fansim.centrifugal.optimize import (
    refine_pareto_cfd as refine_mixed_pareto_cfd,
    run_mixed_study,
)
from fansim.centrifugal.persist import (
    latest_mixed_opt_dir,
    load_all_mixed_designs,
    load_mixed_pareto,
    mixed_opt_out_path,
    next_mixed_trial,
    save_mixed_design_json,
)
from fansim.cockpit.busy import cfd_stage_hint

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    plotter_ui = None  # type: ignore[assignment]
    asynchronous = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from pyvista.trame.ui import plotter_ui
    from trame.app import asynchronous
    from trame.widgets import html
    from trame.widgets import plotly as plotly_widgets
    from trame.widgets import vuetify3 as v3


def setup_mixed_tab(ctx: CockpitCtx) -> None:
    """Init mf_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
    runs_root = ctx.runs_root
    spawn_busy_ticker = ctx.spawn_busy_ticker

    # ---- Mixed-flow tab (drop-in impeller; axial-duct Assess) --------------------------------
    from fansim.centrifugal.geometry import MixedFlowParams as _MFDefaults
    from fansim.centrifugal.isolated import (
        build_mixed_stl_isolated,
        evaluate_mixed_flow_isolated,
    )
    from fansim.centrifugal.params_io import mixed_params_from_flat

    _mf0 = _MFDefaults()
    mf_preview_stl = Path(tempfile.gettempdir()) / "fansim_mf_preview.stl"
    mf_design_store: list[dict] = load_all_mixed_designs(
        runs_root if runs_root.exists() else Path("runs")
    )

    # Shared objects for render + callbacks (kept per-session).
    ctx.mf_preview_stl = mf_preview_stl  # type: ignore[attr-defined]
    ctx.mf_design_store = mf_design_store  # type: ignore[attr-defined]

    state.mf_n_blades = int(_mf0.n_blades)
    state.mf_r_eye = float(_mf0.r_eye_mm)
    state.mf_r_back = float(_mf0.r_back_mm)
    state.mf_r_tip = float(_mf0.r_tip_mm)
    state.mf_z_span = float(_mf0.z_span_mm)
    state.mf_chord = float(_mf0.chord_mm)
    state.mf_chord_root = float(_mf0.chord_root)
    state.mf_chord_tip = float(_mf0.chord_tip)
    state.mf_stagger = float(_mf0.stagger_deg)
    state.mf_stagger_root = float(_mf0.stagger_root)
    state.mf_stagger_tip = float(_mf0.stagger_tip)
    state.mf_thickness = float(_mf0.thickness)
    state.mf_camber = float(_mf0.max_camber)
    state.mf_camber_pos = float(_mf0.camber_pos)
    state.mf_assess_preset = "case"
    state.mf_refine_op = False
    state.mf_subtab = "design"
    state.mf_export_items = []
    state.mf_preview_busy = False
    state.mf_export_busy = False
    state.mf_assess_busy = False
    state.mf_opt_busy = False
    state.mf_refine_busy = False
    state.mf_trials = 120
    state.mf_resume = False
    state.mf_cfd_top = 0
    state.mf_geo_ready = False
    # Duct-airflow viz (shared with the Fan tab; §17.3): |U|/p midplane + axial-Uz + streamlines
    state.mf_airflow_field = "U"
    state.mf_airflow_img_uri = ""
    state.mf_airflow_caption = "Assess or load a mixed design to see duct airflow."
    state.mf_airflow_busy = False
    state.mf_sel_trial = None  # previous-runs dropdown selection (loads by trial)
    state.mf_trial_items = design_dropdown_items(mf_design_store)
    _mf_runs = runs_root if runs_root.exists() else Path("runs")
    _mf_last = latest_mixed_opt_dir(_mf_runs)
    state.mf_last_opt = str(_mf_last) if _mf_last else ""
    state.mf_has_front = bool(_mf_last) or any(
        str(r.get("source") or "").startswith("cockpit_mf_opt") for r in mf_design_store
    )
    state.mf_msg = "Tune the cone and tip, then Preview → Assess → Export → Optimize (BEM)."
    state.mf_readout = [
        "Assess uses the axial MRF duct (approximate for mixed-flow).",
        "Optimize is a BEM screen (axial adapter) — not CFD.",
    ]
    if mf_design_store:
        n_opt = sum(
            1
            for r in mf_design_store
            if str((r.get("extra") or {}).get("source", "")) == "mixed_optimize"
        )
        n_as = len(mf_design_store) - n_opt
        state.mf_msg = f"Loaded {n_as} Assess + {n_opt} Optimize point(s) onto the mixed scatter."

    def _refresh_mf_figure():
        if hasattr(ctrl, "mf_fig_update"):
            ctrl.mf_fig_update(mf_scatter_figure(mf_design_store))
        state.mf_trial_items = design_dropdown_items(mf_design_store)

    def _refresh_mf_export_items():
        rows: list[dict] = []
        exports = Path("exports")
        if exports.is_dir():
            candidates = [
                p
                for p in exports.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".stl"
                and (
                    p.name.lower().startswith("mixed")
                    or "mixed" in p.name.lower()
                )
            ]
            for path in sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True):
                rows.append({"title": path.name, "value": str(path.resolve())})
                if len(rows) >= 24:
                    break
        state.mf_export_items = rows

    _refresh_mf_export_items()

    # --- Duct-airflow viz (§17.3): render a solved mixed case with the shared renderers -------
    _mf_airflow = {"uris": {}, "gen": 0}

    def _apply_mf_airflow_field():
        uri, cap = pick_airflow_uri(_mf_airflow["uris"], state.mf_airflow_field or "U")
        state.mf_airflow_img_uri = uri
        if uri:
            state.mf_airflow_caption = cap
        elif not state.mf_airflow_busy:
            state.mf_airflow_caption = "Airflow not available for this design"

    def _render_mf_airflow(case_dir):
        """Render the four airflow views from a solved mixed case dir (off-screen, fail-soft)."""
        if not case_dir or asynchronous is None:
            _mf_airflow["uris"] = {}
            state.mf_airflow_img_uri = ""
            state.mf_airflow_caption = "Airflow not available for this design"
            return
        _mf_airflow["gen"] += 1
        gen = _mf_airflow["gen"]
        state.mf_airflow_busy = True
        state.mf_airflow_img_uri = ""
        state.mf_airflow_caption = "Rendering duct airflow…"
        state.flush()

        async def task():
            try:
                loop = asyncio.get_running_loop()
                pack = await loop.run_in_executor(
                    None, lambda: render_airflow_pack(str(case_dir)))
                if _mf_airflow["gen"] != gen:
                    return
                _mf_airflow["uris"] = pack["uris"]
                state.mf_airflow_busy = False
                _apply_mf_airflow_field()
            except Exception:  # noqa: BLE001 — viz must never break the tab
                if _mf_airflow["gen"] == gen:
                    _mf_airflow["uris"] = {}
                    state.mf_airflow_busy = False
                    state.mf_airflow_img_uri = ""
                    state.mf_airflow_caption = "Airflow not available for this design"
            finally:
                try:
                    state.flush()
                    ctrl.mf_view_update()
                except Exception:  # noqa: BLE001
                    pass

        asynchronous.create_task(task())

    @state.change("mf_airflow_field")
    def _on_mf_airflow_field(**_):
        _apply_mf_airflow_field()
        try:
            state.flush()
        except Exception:  # noqa: BLE001
            pass

    def _mf_flat_from_state() -> dict:
        return {
            "n_blades": int(state.mf_n_blades),
            "r_eye_mm": float(state.mf_r_eye),
            "r_back_mm": float(state.mf_r_back),
            "r_tip_mm": float(state.mf_r_tip),
            "z_span_mm": float(state.mf_z_span),
            "chord_root": float(state.mf_chord_root),
            "chord_mm": float(state.mf_chord),
            "chord_tip": float(state.mf_chord_tip),
            "stagger_root": float(state.mf_stagger_root),
            "stagger_deg": float(state.mf_stagger),
            "stagger_tip": float(state.mf_stagger_tip),
            "thickness": float(state.mf_thickness),
            "max_camber": float(state.mf_camber),
            "camber_pos": float(state.mf_camber_pos),
        }

    def _mf_busy() -> bool:
        return bool(
            state.mf_preview_busy
            or state.mf_export_busy
            or state.mf_assess_busy
            or state.mf_opt_busy
            or state.mf_refine_busy
        )

    def _show_mf_stl(path: Path):
        mf_plotter = ensure_plotter(ctx, "mf_plotter")
        if mf_plotter is None:
            return
        # clear_actors, not clear(): clear() also removes every light, so previews rendered as a
        # flat unlit silhouette (§23.25). Axes stay from make_white_plotter.
        mf_plotter.clear_actors()
        mesh = pv.read(str(path))
        # smooth shading like Prop/CROR — without it the preview read as a flat silhouette (§23.25)
        mf_plotter.add_mesh(mesh, color="lightsteelblue", smooth_shading=True)
        mf_plotter.reset_camera()
        ctrl.mf_view_update()

    async def mf_preview(**_):
        if _mf_busy():
            return
        try:
            flat = _mf_flat_from_state()
            mixed_params_from_flat(flat)  # validate early
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        state.mf_preview_busy = True
        ticker, _t0 = spawn_busy_ticker(
            action="Preview",
            msg_attr="mf_msg",
            busy_attr="mf_preview_busy",
            note="mixed-flow geometry",
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: build_mixed_stl_isolated(
                    flat, mf_preview_stl, timeout=300.0, preview=True,
                ),
            )
            _show_mf_stl(mf_preview_stl)
            state.mf_geo_ready = True
            state.mf_msg = "✓ Preview ready (non-fused visual mesh)."
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Preview failed: {type(exc).__name__}: {exc}"
        finally:
            state.mf_preview_busy = False
            ticker.cancel()
            state.flush()

    async def mf_export(**_):
        if _mf_busy():
            return
        try:
            flat = _mf_flat_from_state()
            params = mixed_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        exports = Path("exports")
        exports.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = exports / f"mixed_flow_{stamp}.stl"
        state.mf_export_busy = True
        ticker, _t0 = spawn_busy_ticker(
            action="Export",
            msg_attr="mf_msg",
            busy_attr="mf_export_busy",
            note="mixed-flow STL",
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            from fansim.centrifugal.geometry import export_mixed_flow_stl

            def _do():
                return export_mixed_flow_stl(params, out)

            path = await loop.run_in_executor(None, _do)
            state.mf_msg = f"✓ Saved {Path(path).resolve()}"
            _refresh_mf_export_items()
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Export failed: {type(exc).__name__}: {exc}"
        finally:
            state.mf_export_busy = False
            ticker.cancel()
            state.flush()

    async def mf_assess(**_):
        if _mf_busy():
            return
        try:
            flat = _mf_flat_from_state()
            mixed_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Invalid params: {exc}"
            state.flush()
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        workdir = Path("runs") / f"cockpit_mf_{stamp}"
        load_pa, _ = assess_load(str(state.mf_assess_preset or "case"))
        state.mf_assess_busy = True
        wd_holder: list = [workdir]
        note = (f"hose {state.mf_assess_preset}; typically 15–30 min; stops only if stalled "
                f"{stall_timeout() / 60:.0f} min (cap {cfd_eval_timeout() / 3600:.0f} h)")
        ticker, _t0 = spawn_busy_ticker(
            action="Assess",
            msg_attr="mf_msg",
            busy_attr="mf_assess_busy",
            note=note,
            hint_fn=lambda: cfd_stage_hint(wd_holder[0]),
            interval=2.0,
        )
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda flat=flat, workdir=workdir, load_pa=load_pa: evaluate_mixed_flow_isolated(
                    flat,
                    workdir,
                    spec=A12X25,
                    procs=8,
                    base_cell=0.006,
                    iters=500,
                    load_pa=load_pa,
                    refine_op=bool(state.mf_refine_op),
                ),
            )
            if not result.feasible:
                state.mf_msg = f"Rejected — {result.reason}"
                state.mf_readout = [f"infeasible: {result.reason}"]
            else:
                tid = next_mixed_trial(mf_design_store)
                extra = {
                    "source": "mixed_assess",
                    "source_run": workdir.name,
                    "hose": str(state.mf_assess_preset or "case"),
                    "refine_op": bool(state.mf_refine_op),
                    "n_blades": int(flat.get("n_blades", 0)),
                }
                try:
                    save_mixed_design_json(
                        workdir,
                        trial=tid,
                        params=dict(flat),
                        objectives={
                            "cfm_free": result.cfm_free,
                            "cfm_load": result.cfm_load,
                            "efficiency": result.efficiency,
                        },
                        feasible=True,
                        extra=extra,
                    )
                except Exception as exc:  # noqa: BLE001 — keep in-memory even if disk write fails
                    _log.warning(
                        "skip mixed assess design.json write %s: %s: %s",
                        workdir, type(exc).__name__, exc)
                row = {
                    "trial": tid,
                    "params": dict(flat),
                    "objectives": {
                        "cfm_free": float(result.cfm_free),
                        "cfm_load": float(result.cfm_load),
                        "efficiency": float(result.efficiency),
                    },
                    "feasible": True,
                    "reason": "",
                    "extra": extra,
                    "stl_path": str(workdir / "impeller.stl")
                    if (workdir / "impeller.stl").exists()
                    else None,
                    "workdir": str(workdir),
                }
                mf_design_store.append(row)
                _refresh_mf_figure()
                _render_mf_airflow(workdir)  # duct-airflow viz from the just-solved case
                state.mf_msg = (
                    f"✓ free {result.cfm_free:.1f} CFM  ·  load {result.cfm_load:.1f} CFM  ·  "
                    f"η {result.efficiency:.1f}%  ({workdir.name}) — saved to scatter"
                )
                state.mf_readout = [
                    f"cfm_free {result.cfm_free:.1f}  ·  cfm_load {result.cfm_load:.1f}  ·  "
                    f"efficiency {result.efficiency:.1f}%",
                    "Domain: axial MRF duct (approximate for mixed-flow).",
                    f"workdir {workdir}",
                ]
                stl = workdir / "impeller.stl"
                if stl.exists():
                    _show_mf_stl(stl)
        except Exception as exc:  # noqa: BLE001
            state.mf_msg = f"⚠ Assess failed: {type(exc).__name__}: {exc}"
        finally:
            state.mf_assess_busy = False
            ticker.cancel()
            state.flush()

    def optimize_mixed():
        """BEM NSGA screen for mixed-flow (instant; axial-adapter CFM — not CFD)."""
        if _mf_busy():
            return
        try:
            trials = max(40, int(float(state.mf_trials)))
        except (TypeError, ValueError):
            trials = 120
        load_pa, _ = assess_load(str(state.mf_assess_preset or "case"))
        resume = bool(state.mf_resume)
        root = runs_root if runs_root.exists() else Path("runs")
        last = state.mf_last_opt or None
        if resume and not last:
            found = latest_mixed_opt_dir(root)
            last = str(found) if found else None
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out_dir = mixed_opt_out_path(resume=resume, last_dir=last, stamp=stamp, runs_root=root)
        mode = "resume" if resume and out_dir == Path(last or "") else "new"

        async def task():
            state.mf_opt_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="Optimize",
                msg_attr="mf_msg",
                busy_attr="mf_opt_busy",
                note=f"{trials} BEM trials, hose {state.mf_assess_preset}, {mode}",
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                _, pareto = await loop.run_in_executor(
                    None,
                    lambda: run_mixed_study(
                        n_trials=trials,
                        load_pa=float(load_pa),
                        out_dir=out_dir,
                        hose=str(state.mf_assess_preset or "case"),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.mf_msg = f"⚠ Optimize failed: {type(exc).__name__}: {exc}"
                state.mf_opt_busy = False
                ticker.cancel()
                state.flush()
                return
            state.mf_last_opt = str(out_dir)
            state.mf_has_front = True
            # Reload disk so prior Assess + Optimize fronts stay on the graph.
            mf_design_store.clear()
            mf_design_store.extend(load_all_mixed_designs(root))
            _refresh_mf_figure()
            state.mf_msg = (
                f"✓ {len(pareto)} BEM front design(s) → {out_dir.name} "
                f"(axial adapter — Assess for CFD). Click a ● point to load knobs."
            )
            state.mf_opt_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def refine_mixed_cfd():
        """CFD-score top-N rows from the last mixed BEM Optimize front."""
        if _mf_busy():
            return
        try:
            n_top = int(float(state.mf_cfd_top))
        except (TypeError, ValueError):
            n_top = 0
        n_top = max(0, min(8, n_top))
        if n_top <= 0:
            state.mf_msg = "Set CFD refine top N ≥ 1 (uses last BEM Optimize front)."
            state.flush()
            return
        root = runs_root if runs_root.exists() else Path("runs")
        last = state.mf_last_opt or None
        if not last:
            found = latest_mixed_opt_dir(root)
            last = str(found) if found else None
        if not last:
            state.mf_msg = "⚠ No mixed Optimize front yet — run Optimize first."
            state.flush()
            return
        pareto_dir = Path(last)
        pareto = load_mixed_pareto(pareto_dir)
        if not pareto:
            state.mf_msg = f"⚠ No pareto.json in {pareto_dir.name}"
            state.flush()
            return
        load_pa, _ = assess_load(str(state.mf_assess_preset or "case"))
        out = pareto_dir / "cfd_refine"

        async def task():
            state.mf_refine_busy = True
            ticker, _t0 = spawn_busy_ticker(
                action="CFD refine",
                msg_attr="mf_msg",
                busy_attr="mf_refine_busy",
                note=f"top {n_top} of {len(pareto)} from {pareto_dir.name}",
                interval=2.0,
            )
            state.flush()
            loop = asyncio.get_running_loop()
            try:
                rows = await loop.run_in_executor(
                    None,
                    lambda: refine_mixed_pareto_cfd(
                        pareto,
                        out,
                        n_top=n_top,
                        load_pa=float(load_pa),
                        refine_op=bool(state.mf_refine_op),
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                state.mf_msg = f"⚠ CFD refine failed: {type(exc).__name__}: {exc}"
                state.mf_refine_busy = False
                ticker.cancel()
                state.flush()
                return
            ok = sum(1 for r in rows if not r.get("skipped"))
            state.mf_msg = (
                f"✓ CFD refine {ok}/{len(rows)} feasible → {out} "
                f"(see cfd_refine.json; BEM ● points unchanged)"
            )
            state.mf_refine_busy = False
            ticker.cancel()
            state.flush()

        asynchronous.create_task(task())

    def load_mf_trial(trial=None, **_):
        """Load a mixed Assess point into the editor from the scatter click."""
        if trial is None:
            return
        tid = int(trial)
        row = next((r for r in mf_design_store if int(r["trial"]) == tid), None)
        if row is None:
            return
        p = row.get("params") or {}
        if "n_blades" in p:
            state.mf_n_blades = int(p["n_blades"])
        if "r_eye_mm" in p:
            state.mf_r_eye = float(p["r_eye_mm"])
        if "r_back_mm" in p:
            state.mf_r_back = float(p["r_back_mm"])
        if "r_tip_mm" in p:
            state.mf_r_tip = float(p["r_tip_mm"])
        if "z_span_mm" in p:
            state.mf_z_span = float(p["z_span_mm"])
        if "chord_mm" in p or "chord_root" in p or "chord_tip" in p:
            mid = float(p.get("chord_mm", state.mf_chord))
            state.mf_chord = mid
            state.mf_chord_root = float(p.get("chord_root", mid))
            state.mf_chord_tip = float(p.get("chord_tip", mid))
        if "stagger_deg" in p or "stagger_root" in p or "stagger_tip" in p:
            mid_s = float(p.get("stagger_deg", state.mf_stagger))
            state.mf_stagger = mid_s
            state.mf_stagger_root = float(p.get("stagger_root", mid_s))
            state.mf_stagger_tip = float(p.get("stagger_tip", mid_s))
        if "thickness" in p:
            state.mf_thickness = float(p["thickness"])
        if "max_camber" in p:
            state.mf_camber = float(p["max_camber"])
        if "camber_pos" in p:
            state.mf_camber_pos = float(p["camber_pos"])
        o = row.get("objectives") or {}
        state.mf_readout = [
            f"#{tid}  cfm_free {o.get('cfm_free', 0):.1f}  ·  cfm_load {o.get('cfm_load', 0):.1f}  ·  "
            f"efficiency {o.get('efficiency', 0):.1f}%",
            f"Loaded from {row.get('extra', {}).get('source_run', row.get('workdir', ''))}",
        ]
        stl = row.get("stl_path")
        if stl and Path(stl).exists():
            try:
                _show_mf_stl(Path(stl))
            except Exception:  # noqa: BLE001
                pass
        state.mf_msg = f"Loaded Assess #{tid} into the editor."
        _render_mf_airflow(row.get("workdir"))  # duct-airflow viz from the loaded case (if kept)
        state.flush()

    # Expose callbacks for the UI renderer.
    ctx.mf_preview = mf_preview  # type: ignore[attr-defined]
    ctx.mf_export = mf_export  # type: ignore[attr-defined]
    ctx.mf_assess = mf_assess  # type: ignore[attr-defined]
    ctx.optimize_mixed = optimize_mixed  # type: ignore[attr-defined]
    ctx.refine_mixed_cfd = refine_mixed_cfd  # type: ignore[attr-defined]
    ctx.load_mf_trial = load_mf_trial  # type: ignore[attr-defined]


def render_mixed_tab(ctx: CockpitCtx) -> None:
    """Build Mixed UI (call inside layout content)."""
    state, ctrl = ctx.state, ctx.ctrl
    mf_plotter = ensure_plotter(ctx, "mf_plotter")
    mf_design_store = getattr(ctx, "mf_design_store")  # set by setup_mixed_tab

    def _slider(label: str, model: str, mn: float, mx: float, step: float, disabled=None, **_kw):
        # Shared slider: label + exact value always visible (these tabs showed no numbers; §23.24).
        _shared_slider(label, model, mn, mx, step, disabled=disabled)

    _mf_busy_expr = (
        "mf_preview_busy || mf_export_busy || mf_assess_busy || "
        "mf_opt_busy || mf_refine_busy"
    )

    # ---- MIXED-FLOW TAB -----------------------------------------------------------
    with html.Div(v_show="active_tab === 'mixed'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):

                def _mf_design():
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div("Core geometry (A12x25 envelope)", classes="text-subtitle-2 mb-2")
                        _slider("Blades", "mf_n_blades", 5, 13, 1)
                        _slider("Eye hub R (mm)", "mf_r_eye", 12.0, 24.0, 0.5)
                        _slider("Back hub R (mm)", "mf_r_back", 20.0, 35.0, 0.5)
                        _slider("Tip R (mm)", "mf_r_tip", 48.0, 54.5, 0.5)
                        _slider("Z span (mm)", "mf_z_span", 12.0, 22.0, 0.5)
                        html.Div("Planform (root → tip)", classes="text-subtitle-2 mt-3 mb-1")
                        _slider("Chord root (mm)", "mf_chord_root", 14.0, 28.0, 0.5)
                        _slider("Chord mid (mm)", "mf_chord", 14.0, 28.0, 0.5)
                        _slider("Chord tip (mm)", "mf_chord_tip", 14.0, 28.0, 0.5)
                        _slider("Stagger root (°)", "mf_stagger_root", 20.0, 50.0, 1.0)
                        _slider("Stagger mid (°)", "mf_stagger", 20.0, 50.0, 1.0)
                        _slider("Stagger tip (°)", "mf_stagger_tip", 20.0, 50.0, 1.0)
                        html.Div("Section aero", classes="text-subtitle-2 mt-3 mb-1")
                        _slider("Thickness t/c", "mf_thickness", 0.04, 0.14, 0.005)
                        _slider("Camber", "mf_camber", 0.0, 0.08, 0.005)
                        _slider("Camber pos", "mf_camber_pos", 0.25, 0.55, 0.01)
                    with v3.VCard(classes="mb-2 pa-3"):
                        v3.VSelect(
                            label="Application",
                            v_model=("mf_assess_preset",),
                            items=("assess_preset_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            classes="mb-2",
                        )
                        v3.VSwitch(
                            v_model=("mf_refine_op",),
                            density="compact",
                            hide_details=True,
                            color="primary",
                            inset=True,
                            label="Third CFD at operating point",
                            classes="mb-2",
                        )
                        render_action_row(
                            v3,
                            {
                                "preview": {
                                    "label": "Preview",
                                    "color": "primary",
                                    "size": "small",
                                    "click": (getattr(ctx, "mf_preview"),),
                                    "loading": ("mf_preview_busy",),
                                    "disabled": (_mf_busy_expr,),
                                },
                                "score": {
                                    "label": "Assess",
                                    "color": "success",
                                    "size": "small",
                                    "click": (getattr(ctx, "mf_assess"),),
                                    "loading": ("mf_assess_busy",),
                                    "disabled": (f"{_mf_busy_expr} || !mf_geo_ready",),
                                },
                                "export": {
                                    "label": "Export STL",
                                    "size": "small",
                                    "variant": "tonal",
                                    "color": "primary",
                                    "click": (getattr(ctx, "mf_export"),),
                                    "loading": ("mf_export_busy",),
                                    "disabled": (f"{_mf_busy_expr} || !mf_geo_ready",),
                                },
                                "optimize": {
                                    "label": "Optimize",
                                    "color": "success",
                                    "size": "small",
                                    "click": (getattr(ctx, "optimize_mixed"),),
                                    "loading": ("mf_opt_busy",),
                                    "disabled": (_mf_busy_expr,),
                                },
                            },
                        )
                        html.Div(
                            "{{ mf_msg }}",
                            classes="text-caption mt-2",
                            style="white-space: pre-line",
                        )
                        ctx.busy_bar(
                            "mf_preview_busy",
                            "mf_export_busy",
                            "mf_assess_busy",
                            "mf_opt_busy",
                            "mf_refine_busy",
                            color="success",
                        )
                    with v3.VCard(classes="mb-2 pa-3"):
                        html.Div(
                            "Optimize (BEM screen, ~1 s) — axial adapter CFM",
                            classes="text-subtitle-2 mb-1",
                        )
                        html.Div(
                            "NSGA on free↔load CFM via the axial BEM stand-in. Not CFD. "
                            "Assess still scores the honest MRF duct. Continue last "
                            "appends into the newest cockpit_mf_opt_* study. "
                            "Optional CFD refine scores the top-N BEM finalists "
                            "(same hose as Assess; writes cfd_refine.json).",
                            classes="text-caption mb-2",
                            style="white-space: pre-line",
                        )
                        v3.VTextField(
                            label="Trials",
                            v_model=("mf_trials",),
                            type="number",
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            classes="mb-2",
                        )
                        v3.VSwitch(
                            v_model=("mf_resume",),
                            density="compact",
                            hide_details=True,
                            color="primary",
                            inset=True,
                            label="Continue last",
                            classes="mb-2",
                        )
                        with v3.VRow(no_gutters=True, classes="align-center"):
                            with v3.VCol(cols=5, classes="pr-1"):
                                v3.VTextField(
                                    label="CFD refine top N",
                                    v_model=("mf_cfd_top",),
                                    type="number",
                                    density="compact",
                                    variant="outlined",
                                    hide_details=True,
                                )
                            with v3.VCol(cols=7, classes="pl-1"):
                                v3.VBtn(
                                    "CFD refine",
                                    color="warning",
                                    size="small",
                                    block=True,
                                    click=(getattr(ctx, "refine_mixed_cfd"),),
                                    loading=("mf_refine_busy",),
                                    disabled=(
                                        f"{_mf_busy_expr} || !mf_has_front || !(mf_cfd_top > 0)",
                                    ),
                                )

                def _mf_results():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("mf_sel_trial",),
                            items=("mf_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_mf_trial"), "[$event]"),
                        )
                    with v3.VCard(style=f"height:{SCATTER_HEIGHT_PX}px;", classes="pa-1 mb-2"):
                        mf_fig_widget = plotly_widgets.Figure(
                            figure=mf_scatter_figure(mf_design_store),
                            click=(
                                getattr(ctx, "load_mf_trial"),
                                "[$event?.points?.[0]?.customdata]",
                            ),
                            style="width:100%;",
                        )
                        ctrl.mf_fig_update = mf_fig_widget.update

                def _mf_library():
                    with v3.VCard(classes="pa-2 mb-2"):
                        v3.VSelect(
                            label="Previous runs",
                            v_model=("mf_sel_trial",),
                            items=("mf_trial_items",),
                            density="compact",
                            variant="outlined",
                            hide_details=True,
                            update_modelValue=(getattr(ctx, "load_mf_trial"), "[$event]"),
                        )
                    with v3.VCard(classes="pa-2"):
                        html.Div(
                            "Exported mixed-flow STL files under exports/.",
                            classes="text-caption mb-2",
                        )
                        with v3.VList(density="compact", lines="one"):
                            with v3.VListItem(v_for="it in mf_export_items", key="it.value"):
                                v3.VListItemTitle("{{ it.title }}")
                        html.Div(
                            "No exports yet — use Export STL on Design.",
                            classes="text-caption text-medium-emphasis",
                            v_if="!mf_export_items.length",
                        )

                render_left_shell(
                    v3,
                    html,
                    state_key="mf_subtab",
                    design=_mf_design,
                    results=_mf_results,
                    library=_mf_library,
                )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div("{{ line }}", v_for="line in mf_readout", classes="text-body-2")
                with v3.VCard(style=f"height:{VTK_HEIGHT_PX}px;", classes="mb-2"):
                    mf_view = plotter_ui(mf_plotter)
                    ctrl.mf_view_update = mf_view.update
                with v3.VCard(classes="mb-2 pa-2", v_show="mf_subtab === 'results'"):
                    html.Div("Duct airflow — slices & streamlines", classes="text-subtitle-2 mb-1")
                    html.Div(
                        "From the last Assess (axial MRF duct, approximate for mixed-flow). "
                        "|U|/pressure midplane; axial Uz (blue = delivery, red = reverse); "
                        "streamlines colored by |U|.",
                        classes="text-caption text-medium-emphasis mb-2",
                    )
                    with v3.VBtnToggle(
                        v_model=("mf_airflow_field",),
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
                        "{{ mf_airflow_caption }}",
                        classes="text-caption text-medium-emphasis mb-1",
                    )
                    html.Img(
                        src=("mf_airflow_img_uri",),
                        v_show="mf_airflow_img_uri",
                        style=(
                            "width:100%;max-height:520px;object-fit:contain;"
                            "display:block;background:#fafafa;border-radius:4px;"
                        ),
                    )
