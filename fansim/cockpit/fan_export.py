"""Fan-tab export binder: write a print-ready STL (+ README / fit gauge) for the editor design (§13.9).

Fits the editor flat to the frame, rebuilds the solid, and writes the STL asynchronously so
the busy indicator shows during the (up to ~3 min) build. Cross-domain: reads the editor flat
and model fit-readouts through ``session``.
"""

from __future__ import annotations

import re

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace

from fansim.cockpit import fan_runtime
from fansim.cockpit.errors import log_caught
from fansim.cockpit.paths import exports_dir
from fansim.cockpit.placement import prepare_export_flat, preview_changes
from fansim.geometry.blade import validate_blade_params

_log = logging.getLogger(__name__)



def export_basename(trial, by_trial) -> str:
    """Readable export file stem: the design's F-name, ``a12x25_stock_reference`` or ``fan``.

    Was ``design_<trial>``, so the Stock reference exported as ``design_100000`` (§23.19).
    """
    if trial is None:
        return "fan"
    d = (by_trial or {}).get(int(trial))
    extra = getattr(d, "extra", None) or {}
    if extra.get("is_reference"):
        return f"{extra.get('fan_model') or 'a12x25'}_stock_reference"
    name = str(extra.get("display_name") or f"design_{int(trial)}")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "fan"


def do_export(params, out, spec, also_mirror: bool = False, *,
              print_id: str | None = None, design_id: str = "") -> dict:
    """Build + write the print-ready STL and sidecars; return a JSON-able summary.

    Runs in ``fansim.cockpit._export_worker`` (its own process) so the multi-minute OCP build
    no longer holds the cockpit's GIL — the busy caption froze and a native crash could take
    the server down (roadmap §23.17 / §23.19).
    """
    out = Path(out)
    mount = spec.motor_mount
    from fansim.manufacturability.mount_gauge import write_print_fit_sidecars
    from fansim.manufacturability.print_export import (
        balance_summary,
        export_handedness_pair,
        export_print_ready,
        print_readme,
        recommend_print_settings,
    )
    from fansim.manufacturability.print_id import git_head, recipe_hash, record_export

    rep = export_print_ready(params, out, mount=mount)
    mirror_note = ""
    if also_mirror:
        try:
            paths = export_handedness_pair(
                params, out.parent, stem=out.stem, mount=mount, as_designed_stl=out,
            )
            mirror_note = (
                f"\n↳ Opposite-hand pair: {paths['mirrored_stl'].name} "
                f"+ {paths['mirrored_meta'].name} (spin travels with geometry — §19.4)"
            )
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "handedness mirror export", exc)
            mirror_note = f"\n⚠ Mirror export failed: {type(exc).__name__}: {exc}"
    try:
        settings = recommend_print_settings(spec.material)
        bal = balance_summary(params, spec.rpm)
        (out.with_suffix(".md")).write_text(
            print_readme(out.stem, params, spec.material, rep, bal, settings, None,
                         print_id=print_id),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 - README sidecar is best-effort
        log_caught(_log, "export print README", exc)
    gauge = None
    if mount is not None:
        try:
            extra = None
            if print_id:
                extra = {
                    "print_id": print_id,
                    "design_id": design_id,
                    "section_wrap": str(getattr(params, "section_wrap", "") or ""),
                    "recipe_hash": recipe_hash(params),
                    "git": git_head(),
                    "material": str(getattr(spec, "material", "") or ""),
                }
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
                extra=extra,
            )
        except Exception as exc:  # noqa: BLE001
            log_caught(_log, "print fit sidecars", exc, level=logging.DEBUG)
            gauge = None
    if print_id and mount is None:
        import json
        sidecar = {
            "print_id": print_id,
            "design_id": design_id,
            "section_wrap": str(getattr(params, "section_wrap", "") or ""),
            "recipe_hash": recipe_hash(params),
            "git": git_head(),
            "material": str(getattr(spec, "material", "") or ""),
            "stl": str(out),
        }
        out.with_name(out.stem + "_print_fit.json").write_text(
            json.dumps(sidecar, indent=2), encoding="utf-8")
    if print_id:
        record_export(
            print_id=print_id,
            design_id=design_id,
            recipe_hash=recipe_hash(params),
            section_wrap=str(getattr(params, "section_wrap", "") or ""),
            git=git_head(),
            material=str(getattr(spec, "material", "") or ""),
            stl=str(out),
        )
    summary = {
        "ok": bool(rep.ok), "mount_fits": rep.mount_fits, "mount_msg": rep.mount_msg or "",
        "mirror_note": mirror_note, "gauge": None, "print_id": print_id,
    }
    if gauge is not None:
        summary["gauge"] = {
            "mount_ok": bool(gauge.mount_ok), "frame_ok": bool(gauge.frame_ok),
            "tip_od_mm": float(gauge.tip_od_mm), "notes": [str(n) for n in gauge.notes],
        }
    return summary

def bind(session) -> None:
    state = session.state
    spawn_busy_ticker = session.spawn_busy_ticker

    def _export_isolated(flat, features, out, spec, also_mirror, print_id="", design_id=""):
        """Run do_export in a worker process; return its summary dict."""
        from dataclasses import asdict

        from fansim.fan_spec import fan_spec_to_dict
        from fansim.isolated_job import run_worker_module

        result = Path(out).with_suffix(".export.json")
        run_worker_module(
            "fansim.cockpit._export_worker",
            {"flat": flat, "features": asdict(features), "out": str(out),
             "spec": fan_spec_to_dict(spec), "also_mirror": bool(also_mirror),
             "print_id": print_id, "design_id": design_id,
             "result": str(result)},
            timeout=900.0, label="STL export", require_paths=[result], stderr_tail=400,
        )
        import json

        summary = json.loads(result.read_text(encoding="utf-8"))
        result.unlink(missing_ok=True)
        return summary

    def export_stl_current():
        if state.export_busy or state.preview_busy or state.assess_busy:
            return
        from fansim.cockpit.fan_core import refresh_memory_tier

        refresh_memory_tier(state)
        if not state.cup_build_ok:
            # The print-ready STL fuses the carved hub + blades: ~4.5 GB even on the leanest path.
            state.export_msg = (
                "⚠ Not enough free memory for a print-ready export (needs about 5 GB free). "
                "Close other programs and try again.")
            state.flush()
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
        try:
            validate_blade_params(params)
        except ValueError as exc:
            state.export_msg = f"⚠ {exc}"
            state.flush()
            return
        hub_r_export = float(params.hub_radius)
        hub_h_export = float(params.hub_height_mm) if params.hub_height_mm is not None else None
        also_mirror = bool(state.export_also_mirror)
        # Settings from the click (24.4): the finished message must describe this export, not the
        # switches/sliders as they are when the worker returns.
        fit_hub_click = bool(state.export_fit_hub)
        hub_h_click = float(state.e_hub_height or 0.0)
        flat_x, feat_x = session.edit_flat(), session.edit_features()
        exports = exports_dir()
        exports.mkdir(exist_ok=True)
        base = export_basename(state.selected_trial, session.by_trial)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        from fansim.manufacturability.print_id import export_stem, issue_print_id
        print_id = issue_print_id()
        design_id = base
        out = exports / f"{export_stem(print_id, base, stamp)}.stl"

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
                summary = await loop.run_in_executor(
                    None,
                    _export_isolated,
                    flat_x,
                    feat_x,
                    out,
                    spec,
                    also_mirror,
                    print_id,
                    design_id,
                )
                rep = SimpleNamespace(ok=summary["ok"], mount_fits=summary["mount_fits"],
                                      mount_msg=summary["mount_msg"])
                mirror_note = summary["mirror_note"]
                gauge = SimpleNamespace(**summary["gauge"]) if summary["gauge"] else None
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
                if not fit_hub_click:
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
                    f"\n↳ Hub widened {grew_from:.1f} → {hub_r_export:.1f} mm to fit the "
                    f"{spec.motor_mount.cavity_dia_mm:.1f} mm motor hub."
                )
            if grew_h_from is not None:
                h_txt = f"{hub_h_export:.0f}" if hub_h_export is not None else f"{hub_h_click:.0f}"
                extra += (
                    f"\n↳ Hub height set to {h_txt} mm so the cup has a cap and "
                    f"clears the frame spokes."
                )
            if extra:
                extra += (
                    " Press Preview to see it; the CFM/eff shown were for the original geometry, so "
                    "they're now approximate — re-Assess for exact numbers."
                )
            pid_txt = f"\n↳ Print-id `{print_id}` — Sharpie that on the hub (+Z). Same code in the README."
            state.export_msg = (
                f"✓ Saved {out.resolve()} (+ .step)  ({wt}{mnt})"
                f"{mirror_note}{gauge_txt}{pid_txt}{extra}"
            )
            state.export_download = f"fansim_exports/{out.name}"   # served by app.py (§23.19)
            state.export_busy = False
            ticker.cancel()
            state.flush()

        fan_runtime.asynchronous.create_task(task())

    session._export_isolated = _export_isolated
    session.export_stl_current = export_stl_current
