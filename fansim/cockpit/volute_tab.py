"""Volute cockpit tab (radial impeller + sealed volute casing).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

from fansim.cockpit.busy import cfd_stage_hint
from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.plotters import ensure_plotter

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    plotter_ui = None  # type: ignore[assignment]
    asynchronous = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
    import pyvista as pv
    from pyvista.trame.ui import plotter_ui
    from trame.app import asynchronous
    from trame.widgets import html
    from trame.widgets import vuetify3 as v3


def setup_volute_tab(ctx: CockpitCtx) -> None:
    """Init volute_* state and controllers (call before SinglePageLayout)."""
    state, ctrl = ctx.state, ctx.ctrl
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

    # Shared objects for render + callbacks (kept per-session).
    ctx.volute_preview_stl = volute_preview_stl  # type: ignore[attr-defined]

    state.volute_n_blades = int(_v0.n_blades)
    state.volute_r_hub = float(_v0.r_hub_mm)
    state.volute_r_tip = float(_v0.r_tip_mm)
    state.volute_blade_h = float(_v0.blade_height_mm)
    state.volute_spiral = float(_v0.spiral_growth_mm)
    state.volute_clearance = float(_v0.volute_clearance_mm)
    state.volute_rpm = float(_VOLUTE_RPM)
    state.volute_load_pa = 50.0
    state.volute_preview_busy = False
    state.volute_export_busy = False
    state.volute_assess_busy = False
    state.volute_geo_ready = False
    state.volute_msg = (
        "Radial impeller + sealed volute enclosure (smooth Archimedean scroll). "
        "Assess runs radial MRF (+Z inlet / +X outlet; stage3_smooth_scroll honesty)."
    )
    state.volute_readout = [
        "Preview / Export: impeller + sealed casing STLs.",
        "Assess: free+load CFD in the radial MRF domain (OpenFOAM Docker).",
    ]

    def _volute_flat_from_state() -> dict:
        return {
            "n_blades": int(state.volute_n_blades),
            "r_hub_mm": float(state.volute_r_hub),
            "r_tip_mm": float(state.volute_r_tip),
            "blade_height_mm": float(state.volute_blade_h),
            "spiral_growth_mm": float(state.volute_spiral),
            "volute_clearance_mm": float(state.volute_clearance),
        }

    def _volute_busy() -> bool:
        return bool(
            state.volute_preview_busy
            or state.volute_export_busy
            or state.volute_assess_busy
        )

    def _show_volute_stl(path: Path):
        volute_plotter = ensure_plotter(ctx, "volute_plotter")
        if volute_plotter is None:
            return
        volute_plotter.clear()
        volute_plotter.add_axes()
        mesh = pv.read(str(path))
        volute_plotter.add_mesh(mesh, color="lightsteelblue")
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
        out_dir = Path("exports") / f"volute_{stamp}"
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

    # Expose callbacks for the UI renderer.
    ctx.volute_preview = volute_preview  # type: ignore[attr-defined]
    ctx.volute_export = volute_export  # type: ignore[attr-defined]
    ctx.volute_assess = volute_assess  # type: ignore[attr-defined]


def render_volute_tab(ctx: CockpitCtx) -> None:
    """Build Volute UI (call inside layout content)."""
    state, ctrl = ctx.state, ctx.ctrl
    volute_plotter = ensure_plotter(ctx, "volute_plotter")

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

    # ---- VOLUTE TAB ---------------------------------------------------------------
    with html.Div(v_show="active_tab === 'volute'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "Radial impeller + sealed volute (radial MRF Assess)",
                        classes="text-subtitle-2 mb-1",
                    )
                    html.Div(
                        "90° discharge collector — not an A12x25 drop-in. "
                        "Assess uses sealed-enclosure radial MRF (+Z inlet / +X outlet). "
                        "Tongue is a discrete cutwater on a segmented spiral.",
                        classes="text-caption mb-2",
                        style="white-space: pre-line",
                    )
                    _slider("Blades", "volute_n_blades", 5, 11, 1)
                    _slider("Hub R (mm)", "volute_r_hub", 12.0, 28.0, 0.5)
                    _slider("Tip R (mm)", "volute_r_tip", 35.0, 60.0, 0.5)
                    _slider("Blade height (mm)", "volute_blade_h", 12.0, 32.0, 0.5)
                    _slider("Spiral growth (mm)", "volute_spiral", 10.0, 40.0, 1.0)
                    _slider("Tip clearance (mm)", "volute_clearance", 1.0, 8.0, 0.5)
                    with v3.VRow(no_gutters=True, classes="mt-1"):
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
                    with v3.VRow(no_gutters=True):
                        v3.VBtn(
                            "Preview",
                            color="primary",
                            size="small",
                            click=(getattr(ctx, "volute_preview"),),
                            classes="mr-2",
                            loading=("volute_preview_busy",),
                            disabled=(
                                "volute_preview_busy || volute_export_busy || volute_assess_busy",
                            ),
                        )
                        v3.VBtn(
                            "Assess",
                            color="success",
                            size="small",
                            click=(getattr(ctx, "volute_assess"),),
                            classes="mr-2",
                            loading=("volute_assess_busy",),
                            disabled=(
                                "volute_preview_busy || volute_export_busy || volute_assess_busy || "
                                "!volute_geo_ready",
                            ),
                        )
                        v3.VBtn(
                            "Export STLs",
                            size="small",
                            variant="tonal",
                            color="primary",
                            click=(getattr(ctx, "volute_export"),),
                            loading=("volute_export_busy",),
                            disabled=(
                                "volute_preview_busy || volute_export_busy || volute_assess_busy || "
                                "!volute_geo_ready",
                            ),
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
                        color="success",
                    )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "{{ line }}",
                        v_for="line in volute_readout",
                        classes="text-body-2",
                    )
                with v3.VCard(style="height:480px;", classes="mb-2"):
                    volute_view = plotter_ui(volute_plotter)
                    ctrl.volute_view_update = volute_view.update
