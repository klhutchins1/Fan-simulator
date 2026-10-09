"""CROR cockpit tab (counter-rotating stacked rotors).

Extracted from `fansim.cockpit.app` as part of cockpit tab-split (Approach B).
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from fansim.cockpit.context import CockpitCtx
from fansim.cockpit.figures import cror_scatter_figure
from fansim.cror.geometry import CrorParams, export_cror_stl
from fansim.cror.noise import estimate_cror_noise
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
    asynchronous = None  # type: ignore[assignment]
    html = None  # type: ignore[assignment]
    plotly_widgets = None  # type: ignore[assignment]
    v3 = None  # type: ignore[assignment]
else:
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

    # Shared objects for render + callbacks (kept per-session).
    ctx.cror_pareto_store = cror_pareto_store  # type: ignore[attr-defined]

    state.cror_trials = 60
    state.cror_rpm = 2000.0
    state.cror_max_depth = 25.0
    state.cror_cfd_top = 0
    state.cror_opt_busy = False
    state.cror_refine_busy = False
    state.cror_thin_busy = False
    state.cror_export_busy = False
    state.cror_geo_ready = False
    state.cror_msg = ""
    state.cror_readout = [
        "CROR: BEMT-proxy Optimize (not dual-MRF). Thin packs the stack into ≤25 mm. "
        "CFD refine runs dual-MRF on top-N finalists. Relative noise only."
    ]
    _cror_runs = runs_root if runs_root.exists() else Path("runs")
    _cror_last = latest_cror_opt_dir(_cror_runs)
    state.cror_last_opt = str(_cror_last) if _cror_last else ""
    cror_pareto_store.extend(load_all_cror_pareto(_cror_runs))
    state.cror_has_front = bool(cror_pareto_store) or bool(_cror_last)

    def _refresh_cror_figure():
        if hasattr(ctrl, "cror_fig_update"):
            ctrl.cror_fig_update(cror_scatter_figure(cror_pareto_store))

    def _cror_busy():
        return bool(
            state.cror_opt_busy
            or state.cror_refine_busy
            or state.cror_thin_busy
            or state.cror_export_busy
        )

    def _cror_params_from_editor() -> CrorParams:
        return thin_cror_for_frame(CrorParams(), max_depth_mm=float(state.cror_max_depth))

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
                raw = CrorParams()
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
            state.flush()

        asynchronous.create_task(task())

    def load_cror_row(idx=None, **_):
        if idx is None or not (0 <= int(idx) < len(cror_pareto_store)):
            return
        row = cror_pareto_store[int(idx)]
        p = row.get("params") or {}
        state.cror_readout = [
            f"#{idx}  thrust {row.get('thrust_g', 0):.0f} g  ·  "
            f"{row.get('eff_g_per_w', 0):.2f} g/W  ·  "
            f"depth {row.get('depth_mm', 0):.1f} mm  ·  "
            f"noise {row.get('rel_dba', 0):.0f} (rel)",
            f"params: n_front={p.get('n_front')} n_rear={p.get('n_rear')} "
            f"gap={p.get('axial_gap_mm')} stagger={p.get('stagger_deg')} "
            f"chord={p.get('chord_mm')}  ·  {row.get('source_run', '')}",
        ]
        state.cror_msg = f"Loaded CROR front row #{idx}."
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
            exports = Path("exports")
            exports.mkdir(exist_ok=True)
            out = exports / "cror_cockpit.stl"
            try:
                params = await loop.run_in_executor(None, _cror_params_from_editor)
                await loop.run_in_executor(None, lambda: export_cror_stl(params, out))
                depth = cror_stack_depth_mm(params)
                state.cror_msg = f"✓ Saved {out.resolve()} (depth {depth:.1f} mm)"
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
    ctx.optimize_cror = optimize_cror  # type: ignore[attr-defined]
    ctx.refine_cror_cfd = refine_cror_cfd  # type: ignore[attr-defined]
    ctx.load_cror_row = load_cror_row  # type: ignore[attr-defined]


def render_cror_tab(ctx: CockpitCtx) -> None:
    """Build CROR UI (call inside layout content)."""
    if html is None or v3 is None or plotly_widgets is None:
        return

    state, ctrl = ctx.state, ctx.ctrl
    cror_pareto_store = getattr(ctx, "cror_pareto_store")  # set by setup_cror_tab

    # ---- CROR TAB -----------------------------------------------------------------
    with html.Div(v_show="active_tab === 'cror'"):
        with v3.VRow(no_gutters=True):
            with v3.VCol(cols=5, classes="pr-2"):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "Counter-rotating stacked rotors (BEMT proxy + dual-MRF refine)",
                        classes="text-subtitle-2 mb-1",
                    )
                    html.Div(
                        "Optimize is a coarse BEMT-proxy NSGA (not dual-MRF physics). "
                        "Thin packs default geometry into the depth cap. "
                        "Relative noise only — not calibrated dB(A). "
                        "CFD refine needs OpenFOAM Docker.",
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
                    with v3.VRow(no_gutters=True, classes="mt-2"):
                        v3.VBtn(
                            "Thin default",
                            size="small",
                            variant="tonal",
                            color="primary",
                            click=(getattr(ctx, "thin_cror_now"),),
                            classes="mr-2",
                            loading=("cror_thin_busy",),
                            disabled=(
                                "cror_opt_busy || cror_refine_busy || cror_thin_busy || cror_export_busy",
                            ),
                        )
                        v3.VBtn(
                            "Export STL",
                            size="small",
                            variant="tonal",
                            color="primary",
                            click=(getattr(ctx, "export_cror_now"),),
                            classes="mr-2",
                            loading=("cror_export_busy",),
                            disabled=(
                                "cror_opt_busy || cror_refine_busy || cror_thin_busy || cror_export_busy",
                            ),
                        )
                        v3.VBtn(
                            "Optimize",
                            color="success",
                            size="small",
                            click=(getattr(ctx, "optimize_cror"),),
                            loading=("cror_opt_busy",),
                            disabled=(
                                "cror_opt_busy || cror_refine_busy || cror_thin_busy || cror_export_busy",
                            ),
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
                                size="small",
                                block=True,
                                click=(getattr(ctx, "refine_cror_cfd"),),
                                loading=("cror_refine_busy",),
                                disabled=(
                                    "cror_opt_busy || cror_refine_busy || cror_thin_busy || "
                                    "cror_export_busy || !cror_has_front || !(cror_cfd_top > 0)",
                                ),
                            )
                    html.Div(
                        "{{ cror_msg }}",
                        classes="text-caption mt-2",
                        style="white-space: pre-line",
                    )
                    ctx.busy_bar(
                        "cror_opt_busy",
                        "cror_refine_busy",
                        "cror_thin_busy",
                        "cror_export_busy",
                        color="success",
                    )
            with v3.VCol(cols=7):
                with v3.VCard(classes="mb-2 pa-3"):
                    html.Div(
                        "{{ line }}",
                        v_for="line in cror_readout",
                        classes="text-body-2",
                    )
                with v3.VCard(classes="mb-2 pa-4", style="height:200px;"):
                    html.Div("Proxy-only — no mesh viewer yet", classes="text-subtitle-2 mb-1")
                    html.Div(
                        "CROR Optimize is a BEMT proxy (no dual-MRF mesh in the cockpit). "
                        "Use Export STL for printable geometry; Thin packs the default "
                        "stack into the depth cap. 3-D preview deferred.",
                        classes="text-caption text-medium-emphasis",
                        style="white-space: pre-line",
                    )
                with v3.VCard(style="height:360px;", classes="pa-1 mb-2"):
                    cror_fig_widget = plotly_widgets.Figure(
                        figure=cror_scatter_figure(cror_pareto_store),
                        click=(
                            getattr(ctx, "load_cror_row"),
                            "[$event?.points?.[0]?.customdata]",
                        ),
                        style="width:100%;",
                    )
                    ctrl.cror_fig_update = cror_fig_widget.update
