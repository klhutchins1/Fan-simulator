"""Fan-tab assess/sweep binder: run CFD on the editor design (§13.9).

Assess evaluates the live editor geometry (or re-scores a stale selected design) through the
isolated CFD path and adds the result to Results. Sweep runs Assess across one parameter.
Also owns the spec-status caption and the assess-settings staleness check. Cross-domain: reads
the editor flat, model spec, and refreshes Results through ``session``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

from fansim.cfd.cockpit_viz import bake_cockpit_viz_core
from fansim.cfd.runner import kill_cfd_containers
from fansim.cockpit import fan_runtime, run_settings
from fansim.cockpit.busy import busy_caption, cfd_stage_hint
from fansim.cockpit.data import Design
from fansim.cockpit.errors import log_caught
from fansim.cockpit.fan_helpers import (
    _blade_max_dia,
    append_user_designs,
    upsert_by_trial,
)
from fansim.cockpit.figures import reject_hint
from fansim.cockpit.placement import frame_gap_note, impeller_z_extent
from fansim.cockpit.run_settings import RunSettings
from fansim.cockpit.score_caption import score_caption
from fansim.fan_spec import (
    check_build,
    estimate_weight_g,
    get_fan_spec,
    over_spec_flags,
)
from fansim.geometry.features import Features
from fansim.isolated_job import stall_timeout
from fansim.manufacturability import check_printability
from fansim.optimize.isolated_eval import cfd_eval_timeout, evaluate_candidate_isolated
from fansim.optimize.search_space import blade_from_flat

_log = logging.getLogger(__name__)

# Each sweep step is a full ~4-min CFD run, so this lists the params that actually move the CFD
# objectives (flow/eff) — the high-value levers from the design-rules study — grouped like the
# editor. Deliberately omitted: LE-curve/skew/thickness/camber-pos (minor aero or structural) and
# UNEVEN SPACING (a tonal-NOISE lever a flow/eff CFD sweep can't see — the Preview shows it live).
SWEEP_OPTIONS = [
    # planform / solidity — biggest flow + pressure levers
    ("blades", "flat", "n_blades", 5.0, 11.0),
    ("chord mid", "flat", "chord_mid", 14.0, 60.0),
    ("chord tip", "flat", "chord_tip", 14.0, 70.0),
    # pitch / twist (stagger mid = the win-win-win lever from the design rules)
    ("stagger root", "flat", "stagger_root", 15.0, 55.0),
    ("stagger mid", "flat", "stagger_mid", 15.0, 55.0),
    ("stagger tip", "flat", "stagger_tip", 15.0, 55.0),
    # airfoil
    ("camber", "flat", "max_camber", 0.0, 0.06),
    ("camber position", "flat", "camber_pos", 0.2, 0.6),
    # 3-D shape
    ("sweep mid", "flat", "sweep_mid", -3.0, 8.0),
    ("sweep tip", "flat", "sweep_tip", 0.0, 15.0),
    ("wrap tip", "flat", "lean_tip", 0.0, 45.0),
    # winglet (mild CFD effect ~+4% flow; near the screening noise floor)
    ("winglet sweep", "flat", "winglet_sweep", 0.0, 15.0),
    # size / hub (blade length + flow annulus / mountability)
    ("tip radius (length)", "flat", "tip_radius", 45.0, 59.0),
    ("hub radius", "flat", "hub_radius", 15.0, 35.0),
    # bio-inspired features
    ("tubercle amp", "tub", "tubercle_amp", 0.0, 0.10),
    ("serration amp", "ser", "serration_amp", 0.0, 0.06),
    ("dimple depth", "dim", "dimple_amp", 0.0, 0.35),
]


def bind(session) -> None:
    state = session.state
    run_dir = session.run_dir
    assess_dir = session.assess_dir
    user_designs = session.user_designs
    by_trial = session.by_trial
    next_id = session.next_id
    designs_lock = session.designs_lock
    assess_proc = session.assess_proc
    sel_sig = session.sel_sig

    state.sweep_items = [o[0] for o in SWEEP_OPTIONS]

    def spec_status(stl_path, params, flat=None, spec=None):
        spec = spec or session.active_spec()
        try:
            import trimesh

            m = trimesh.load(str(stl_path))
            (xmin, ymin, zmin), (xmax, ymax, zmax) = m.bounds
            dia = 2.0 * max(abs(xmin), abs(xmax), abs(ymin), abs(ymax))
            depth = zmax - zmin
            vol = abs(float(m.volume))
            meta = Path(str(stl_path) + ".meta.json")
            if meta.exists():
                try:
                    vol = float(json.loads(meta.read_text()).get("volume_mm3", vol))
                except Exception as exc:  # noqa: BLE001
                    log_caught(_log, "preview volume sidecar", exc, level=logging.DEBUG)
            weight = estimate_weight_g(vol, spec.material)
        except Exception:  # noqa: BLE001
            return True, ""
        ok, reason = check_build(spec, dia, 2.0 * params.hub_radius, depth, weight)
        depth_msg = session._depth_driver_msg(flat) if (flat and "depth" in reason.lower()) else ""
        if not ok:
            return (
                False,
                f"⚠ Out of spec — Assess will reject: {reason}. {reject_hint(reason)}{depth_msg}",
            )
        gap = frame_gap_note(dia, spec)
        if gap:
            return False, f"⚠ Out of spec — Assess will reject: {gap}. {reject_hint(gap)}"
        over = over_spec_flags(spec, dia, depth, weight)
        if over:
            dm = session._depth_driver_msg(flat) if (flat and any("depth" in o for o in over)) else ""
            return True, "⚠ OVER-SPEC (allowed via leeway): " + "; ".join(over) + dm
        return True, f"✓ fits {spec.name} (dia {dia:.0f} mm, depth {depth:.0f} mm, {weight:.0f} g)"

    def _blocking_eval(flat, features, workdir, rs: RunSettings):
        """Run the CFD with the settings captured when Run was pressed (25.11), never live state."""
        from fansim.cfd.wall_roughness import FDM_WALL_KS_MM

        ks = FDM_WALL_KS_MM if rs.wall_ks else None
        return evaluate_candidate_isolated(
            flat,
            features,
            workdir,
            spec=rs.spec,
            procs=8,
            base_cell=0.006,
            iters=500,
            timeout=cfd_eval_timeout(),
            load_pa=rs.load_pa,
            refine_op=rs.refine_op,
            material=rs.material,
            wall_ks_mm=ks,
            proc_holder=assess_proc,
            # Stock A/B 2026-10-07: same objectives within 0.15%, mesh 4 min faster.
            parallel_mesh=True,
        )

    def _cfd_progress_hint(workdir: Path | None) -> str:
        return cfd_stage_hint(workdir)

    async def _assess_progress_ticker(
        t0: float, workdir_holder, *, note: str = "", stop=None, stall_hint=None,
    ):
        # ``stop[0]`` ends the ticker once the result is written: the picture bake after "Done"
        # awaits, and a ticker still looping on ``assess_busy`` overwrote the result (QA-29, 27.6).
        while state.assess_busy and not state.assess_cancel and not (stop and stop[0]):
            if state.sweep_active or state.opt_running:
                await asyncio.sleep(5.0)
                continue
            wd = workdir_holder[0] if workdir_holder else None
            hint = _cfd_progress_hint(wd)
            warn = (stall_hint or [""])[0]
            if warn:
                hint = f"{warn}\n{hint}" if hint else warn
            state.assess_msg = busy_caption(
                "Assess",
                time.time() - t0,
                hint=hint,
                note=note,
            )
            state.flush()
            await asyncio.sleep(2.0)

    def _stamp_assess_extra(extra, result, rs: RunSettings):
        run_settings.stamp(extra, result.raw, rs)  # hose/load/refine from the click, + cfd_version

    async def _bake_viz_for_design(d: Design | None) -> None:
        """Warm midplane + glyphs before Results select (§22.6 / §22.10). Fail-soft."""
        if d is None or not d.has_model or d.stl_path is None:
            return
        case = Path(d.stl_path).parent
        if not case.is_dir():
            return
        if state.assess_cancel:
            return
        prev = state.assess_msg or ""
        state.assess_msg = (prev + "\nWarming airflow viz (midplane + arrows)…").strip()
        state.flush()
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, bake_cockpit_viz_core, case)
        except Exception as exc:  # noqa: BLE001 — never fail Assess on viz bake
            log_caught(_log, "bake_cockpit_viz_core", exc)

    async def _assess(params, flat, label, rs: RunSettings, workdir_holder=None):
        tid = next_id[0]
        next_id[0] += 1
        workdir = assess_dir / f"design_{tid}"
        if workdir_holder is not None:
            workdir_holder[0] = workdir
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir, rs)
        if state.assess_cancel:
            raise RuntimeError("Assess cancelled")
        if not result.feasible:
            hint = reject_hint(result.reason)
            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
            state.flush()
            return None
        stl = workdir / "impeller.stl"
        extra = {
            "n_blades": params.n_blades,
            "source": "user",
            "source_run": run_dir.name,
            "over_spec": list(result.over_spec),
            "actual_rpm": round(result.actual_rpm),
            **run_settings.identity_extra(rs),  # fan model, material, library parent: from the click
        }
        _stamp_assess_extra(extra, result, rs)
        d = Design(
            trial=tid,
            params=dict(flat),
            objectives={
                "cfm_free": result.cfm_free,
                "cfm_load": result.cfm_load,
                "efficiency": result.efficiency,
            },
            feasible=True,
            is_pareto=False,
            stl_path=stl if stl.exists() else None,
            extra=extra,
        )
        try:
            (workdir / "design.json").write_text(
                json.dumps(
                    {
                        "trial": d.trial,
                        "params": d.params,
                        "objectives": d.objectives,
                        "feasible": True,
                        "reason": d.reason,
                        "extra": d.extra,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "skip assess design.json write %s: %s: %s",
                workdir / "design.json", type(exc).__name__, exc)
        append_user_designs(designs_lock, user_designs, by_trial, d)
        session.refresh_items()
        session.refresh_figure()
        state.flush()
        return d

    async def _assess_existing(d: Design, params, flat, label, rs: RunSettings, workdir_holder=None):
        tid = int(d.trial)
        workdir = assess_dir / f"design_{tid}"
        if workdir_holder is not None:
            workdir_holder[0] = workdir
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _blocking_eval, flat, params.features, workdir, rs)
        if state.assess_cancel:
            raise RuntimeError("Assess cancelled")
        if not result.feasible:
            hint = reject_hint(result.reason)
            state.assess_msg = f"{label}: rejected — {result.reason}" + (f"\n{hint}" if hint else "")
            state.flush()
            return None
        stl = workdir / "impeller.stl"
        d.params = dict(flat)
        d.objectives = {
            "cfm_free": result.cfm_free,
            "cfm_load": result.cfm_load,
            "efficiency": result.efficiency,
        }
        d.feasible = True
        d.is_pareto = False
        d.stl_path = stl if stl.exists() else None
        d.reason = ""
        d.extra.update(
            {
                "source": d.extra.get("source", "user"),
                "source_run": run_dir.name,
                "over_spec": list(result.over_spec),
                "fan_model": rs.fan_model,
                "material": rs.material,
                "actual_rpm": round(result.actual_rpm),
                "cfd_stale": False,
            }
        )
        _stamp_assess_extra(d.extra, result, rs)
        try:
            workdir.mkdir(parents=True, exist_ok=True)
            (workdir / "design.json").write_text(
                json.dumps(
                    {
                        "trial": d.trial,
                        "params": d.params,
                        "objectives": d.objectives,
                        "feasible": True,
                        "reason": d.reason,
                        "extra": d.extra,
                    },
                    indent=2,
                )
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "skip assess design.json write %s: %s: %s",
                workdir / "design.json", type(exc).__name__, exc)
        upsert_by_trial(designs_lock, by_trial, d)
        session.refresh_items()
        session.refresh_figure()
        state.flush()
        return d

    def on_assess():
        if state.assess_busy:
            return
        params, flat = session.build_edit_params(), {**session.edit_flat(), **session._feat_dict()}
        rs = run_settings.capture(state, session.active_spec)  # 25.11: settings as of this click

        async def task():
            state.assess_busy = True
            state.assess_cancel = False
            t0 = time.time()
            note = (f"typically 30–40 min free+load; stops only if stalled "
                    f"{stall_timeout() / 60:.0f} min (cap {cfd_eval_timeout() / 3600:.0f} h)")
            wd_holder: list = [None]
            ns_line = [""]
            try:
                from fansim.optimize.near_stall import near_stall_caption, near_stall_report

                ns_line[0] = near_stall_caption(
                    near_stall_report(
                        params,
                        rpm=float(getattr(rs.spec, "rpm", 2000.0) or 2000.0),
                        load_pa=rs.load_pa,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — warning must never block Assess
                log_caught(_log, "near-stall flag", exc)
            state.assess_msg = busy_caption("Assess", 0, note=note, hint=ns_line[0])
            state.flush()
            ticker_stop = [False]
            ticker = fan_runtime.asynchronous.create_task(
                _assess_progress_ticker(
                    t0, wd_holder, note=note, stop=ticker_stop, stall_hint=ns_line,
                )
            )
            try:
                try:
                    # Always gate on LIVE editor geometry — never orphan Preview STL bounds
                    # (edit-after-Preview used to false-reject or skip the gate).
                    spec = rs.spec
                    dia = _blade_max_dia(params)
                    depth = impeller_z_extent(params)
                    ok_prev, reason_prev = check_build(
                        spec, dia, 2.0 * float(params.hub_radius), depth, None,
                    )
                    if ok_prev:
                        gap = frame_gap_note(dia, spec)
                        if gap:
                            ok_prev, reason_prev = False, gap
                    if not ok_prev:
                        hint = reject_hint(reason_prev)
                        state.assess_msg = (
                            f"Assess: rejected — {reason_prev}"
                            + (f"\n{hint}" if hint else "")
                        )
                        return
                except Exception as exc:  # noqa: BLE001 — never block Assess on readout failure
                    log_caught(_log, "Assess preflight readout", exc)
                cur = by_trial.get(rs.selected_trial) if rs.selected_trial is not None else None
                if cur is not None and cur.extra.get("cfd_stale"):
                    d = await _assess_existing(cur, params, flat, "Assess", rs, wd_holder)
                else:
                    d = await _assess(params, flat, "Assess", rs, wd_holder)
                if state.assess_cancel:
                    state.assess_msg = "⏹ Assess cancelled."
                    return
                if d:
                    ticker_stop[0] = True
                    ticker.cancel()
                    o = d.objectives
                    over = d.extra.get("over_spec") or []
                    tag = ("  ⚠ OVER-SPEC: " + "; ".join(over)) if over else ""
                    spec = get_fan_spec(d.extra.get("fan_model", "a12x25"))
                    rpm = d.extra.get("actual_rpm", 0)
                    rpm_tag = (
                        f"  ⚙ motor-limited: {rpm:.0f} RPM ({100*rpm/spec.rpm:.0f}%)"
                        if rpm and rpm < spec.rpm * 0.995
                        else ""
                    )
                    state.assess_msg = (
                        f"Done ◆#{d.trial}: free {o['cfm_free']:.1f}  "
                        f"load {o['cfm_load']:.1f}  eff {o['efficiency']:.1f}%"
                        f"  (added to Results plot){rpm_tag}{tag}"
                    )
                    ref_cfm = getattr(spec, "ref_cfm", None)
                    if ref_cfm:
                        pct = 100.0 * (float(o["cfm_free"]) - float(ref_cfm)) / float(ref_cfm)
                        state.assess_msg += (
                            f"\nvs stock free {float(ref_cfm):.0f} CFM: {pct:+.0f}% "
                            f"({'better' if pct >= 0 else 'lower'} free-air)"
                        )
                    cap = score_caption(d.extra)
                    if cap:
                        state.assess_msg += f"\n{cap}"
                    await _bake_viz_for_design(d)
                    if state.assess_cancel:
                        state.assess_msg = "⏹ Assess cancelled."
                        return
                    # QA-26 / 27.5: don't yank the 3-D view if the user picked another design
                    # while this run was in flight.
                    if state.selected_trial == rs.selected_trial:
                        session.select(d.trial)
                        state.fan_subtab = "results"
                        session._set_baseline()
            except Exception as exc:  # noqa: BLE001
                if state.assess_cancel or "cancelled" in str(exc).lower():
                    state.assess_msg = "⏹ Assess cancelled."
                else:
                    state.assess_msg = f"Assess failed: {type(exc).__name__}: {exc}"
            finally:
                state.assess_busy = False
                state.assess_cancel = False
                assess_proc[0] = None
                ticker.cancel()
                state.flush()

        fan_runtime.asynchronous.create_task(task())

    def on_sweep():
        if state.assess_busy:
            return
        import numpy as np

        opt = next((o for o in SWEEP_OPTIONS if o[0] == state.sweep_param), SWEEP_OPTIONS[0])
        label, kind, field, mn, mx = opt
        base_flat, base_feat = session.edit_flat(), session._feat_dict()
        rs = run_settings.capture(state, session.active_spec)  # 25.11: one snapshot for every step
        steps = max(2, int(state.sweep_steps))
        raw = list(np.linspace(mn, mx, steps))
        values = sorted(set(int(round(v)) for v in raw)) if field == "n_blades" else raw

        async def task():
            state.assess_busy = True
            state.assess_cancel = False
            state.sweep_active = True
            state.sweep_cancel = False
            state.sweep_progress = 0
            done = 0
            n = len(values)
            try:
                for i, val in enumerate(values):
                    if state.sweep_cancel or state.assess_cancel:
                        state.assess_msg = (
                            f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
                        )
                        break
                    flat, feat = dict(base_flat), dict(base_feat)
                    if kind == "flat":
                        flat[field] = int(val) if field == "n_blades" else float(val)
                    else:
                        feat[field] = float(val)
                        if kind == "tub" and feat["tubercle_waves"] == 0:
                            feat["tubercle_waves"] = 6
                        if kind == "ser" and feat["serration_waves"] == 0:
                            feat["serration_waves"] = 8
                        if kind == "dim":
                            feat["dimple_rows"] = feat["dimple_rows"] or 5
                            feat["dimple_cols"] = feat["dimple_cols"] or 5
                    params = blade_from_flat(flat, Features(**feat))
                    state.assess_msg = (
                        f"Sweep {label} {i+1}/{n} = {val:g}: running CFD… "
                        f"(~15–30 min/step; {done} added so far)"
                    )
                    state.sweep_progress = int(100 * i / n)
                    state.flush()
                    if not check_printability(params).printable:
                        continue
                    try:
                        if await _assess(params, flat, f"sweep {label}={val:g}", rs):
                            done += 1
                    except Exception as exc:  # noqa: BLE001
                        if state.assess_cancel or "cancelled" in str(exc).lower():
                            state.assess_msg = (
                                f"Sweep of {label} cancelled: {done}/{n} done ({done} ◆ added)."
                            )
                            break
                        state.assess_msg = f"Sweep {label}={val:g} failed: {type(exc).__name__}: {exc}"
                        state.flush()
                else:
                    if done == 0:
                        state.assess_msg = (
                            f"Sweep of {label} done: 0 ◆ added — every design was rejected before CFD "
                            "(not a crash). Usually the base design is out of spec or too close to the "
                            "frame: Preview shows the exact verdict, or click Fit envelope first."
                        )
                    else:
                        state.assess_msg = f"Sweep of {label} done: {done} ◆ runs added to the plot."
                state.sweep_progress = 100
            finally:
                state.assess_busy = False
                state.assess_cancel = False
                state.sweep_active = False
                state.sweep_cancel = False
                assess_proc[0] = None
                state.flush()

        fan_runtime.asynchronous.create_task(task())

    def _kill_assess_proc():
        p = assess_proc[0]
        if p is not None and getattr(p, "poll", lambda: 0)() is None:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    capture_output=True,
                    text=True,
                )
            else:
                p.terminate()
        assess_proc[0] = None
        kill_cfd_containers()

    def cancel_sweep():
        if state.sweep_active or (state.assess_busy and not state.opt_running):
            state.sweep_cancel = True
            state.assess_cancel = True
            _kill_assess_proc()
            state.assess_msg = "⏹ Cancelling…"
            state.flush()

    def cancel_assess():
        if not state.assess_busy or state.opt_running:
            return
        state.assess_cancel = True
        if state.sweep_active:
            state.sweep_cancel = True
        _kill_assess_proc()
        state.assess_msg = "⏹ Cancelling Assess…"
        state.flush()

    @state.change("assess_preset", "assess_refine_op", "assess_wall_ks")
    def _on_assess_score_settings(
        assess_preset=None, assess_refine_op=None, assess_wall_ks=None, **_
    ):
        if sel_sig[0] is None:
            return
        cur = None
        if state.selected_trial is not None:
            cur = by_trial.get(int(state.selected_trial))
        scored_preset = (cur.extra.get("preset") if cur else None) or "legacy"
        scored_refine = bool(cur.extra.get("refine_op")) if cur else False
        scored_ks = float((cur.extra.get("wall_ks_mm") if cur else None) or 0) > 0
        preset = str(
            assess_preset if assess_preset is not None else state.assess_preset or "case"
        )
        refine = bool(state.assess_refine_op) if assess_refine_op is None else bool(assess_refine_op)
        wall_ks = bool(state.assess_wall_ks) if assess_wall_ks is None else bool(assess_wall_ks)
        if preset != str(scored_preset) or refine != scored_refine or wall_ks != scored_ks:
            state.edited_stale = True
            state.stale_msg = (
                "⚠ Assess settings changed — the shown load CFM is for the "
                "previous hose / refine-op / wall-ks. Press Assess to rescore."
            )
        else:
            session._recompute_stale()

    session.spec_status = spec_status
    session.on_assess = on_assess
    session.on_sweep = on_sweep
    session.cancel_sweep = cancel_sweep
    session.cancel_assess = cancel_assess

    def score_multi_point_bem():
        """§20.6: instant BEM duty-cycle score for the editor blade (no CFD)."""
        try:
            from fansim.cfd.domain import OPTIMIZER_TIP_GAP_MM
            from fansim.optimize.multi_point import (
                cfm_at_matched_noise,
                format_multi_point,
                score_multi_point,
            )

            params = session.build_edit_params()
            tip = float(OPTIMIZER_TIP_GAP_MM)
            score = score_multi_point(params, tip_gap_mm=tip)
            lines = format_multi_point(score)
            mid_noise = score.points[1].rel_noise_db if len(score.points) > 1 else score.weighted_rel_noise_db
            matched = cfm_at_matched_noise(params, mid_noise, tip_gap_mm=tip)
            if matched.get("cfm_free") is not None:
                lines.append(
                    f"CFM at matched rel noise {mid_noise:.0f}: "
                    f"{matched['cfm_free']:.0f} CFM @ {matched['duty_pct']:.0f}% PWM "
                    f"({matched['rpm']:.0f} RPM)"
                )
            state.multi_point_msg = "\n".join(lines)
        except Exception as exc:  # noqa: BLE001
            state.multi_point_msg = f"⚠ Multi-point score failed: {type(exc).__name__}: {exc}"
        state.flush()

    session.score_multi_point_bem = score_multi_point_bem
