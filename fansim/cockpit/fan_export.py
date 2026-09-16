"""Fan-tab export binder: write a print-ready STL (+ README / fit gauge) for the editor design (§13.9).

Fits the editor flat to the frame, rebuilds the solid, and writes the STL asynchronously so
the busy indicator shows during the (up to ~3 min) build. Cross-domain: reads the editor flat
and model fit-readouts through ``session``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fansim.cockpit import fan_runtime
from fansim.cockpit.errors import log_caught
from fansim.cockpit.placement import prepare_export_flat, preview_changes

_log = logging.getLogger(__name__)


def bind(session) -> None:
    state = session.state
    spawn_busy_ticker = session.spawn_busy_ticker

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
        except Exception as exc:  # noqa: BLE001 - README sidecar is best-effort
            log_caught(_log, "export print README", exc)
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
            except Exception as exc:  # noqa: BLE001
                log_caught(_log, "print fit sidecars", exc, level=logging.DEBUG)
                gauge = None
        return rep, gauge

    def export_stl_current():
        if state.export_busy or state.preview_busy or state.assess_busy:
            return
        from datetime import datetime

        spec = session.active_spec()
        fitted, frame_changes = prepare_export_flat(
            session.edit_flat(),
            spec,
            fit_frame=bool(state.export_fit_frame),
            features=session.edit_features(),
            fit_hub=bool(state.export_fit_hub),
        )
        session._apply_editor_flat(fitted)
        session._hub_fit_readout()
        session._tip_fit_readout()
        session._depth_fit_readout()
        if frame_changes:
            state.edited_stale = True
        grew_from = None
        grew_h_from = None
        for ch in frame_changes:
            if ch.field == "hub_radius" and ch.after > ch.before:
                grew_from = ch.before
            if ch.field == "hub_height" and ch.after > ch.before:
                grew_h_from = ch.before
        params = session.build_edit_params()
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

        fan_runtime.asynchronous.create_task(task())

    session._do_export = _do_export
    session.export_stl_current = export_stl_current
