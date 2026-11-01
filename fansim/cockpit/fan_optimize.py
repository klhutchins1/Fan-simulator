"""Fan-tab optimize binder: launch the Optuna study as a subprocess and merge live (§13.9).

Runs ``optimization_argv`` as a child process, streams its log into the Optimize panel, and
polls the study DB every few seconds to merge new trials onto the Results plot. Cross-domain:
merges into the shared design tables and refreshes Results through ``session``.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from fansim.cfd.runner import kill_cfd_containers
from fansim.cockpit import fan_runtime
from fansim.cockpit.busy import busy_caption, format_elapsed
from fansim.cockpit.data import load_designs
from fansim.cockpit.fan_helpers import append_user_designs
from fansim.optimize.cli_argv import (
    latest_opt_run,
    merge_opt_designs,
    opt_out_path,
    opt_trial_offset,
    optimization_argv,
    run_label,
)

_log = logging.getLogger(__name__)


def bind(session) -> None:
    state = session.state
    run_dir = session.run_dir
    study_name = session.study_name
    user_designs = session.user_designs
    by_trial = session.by_trial
    designs_lock = session.designs_lock
    opt_proc = session.opt_proc

    def _kill_opt_proc():
        p = opt_proc[0]
        if p is None or p.poll() is not None:
            return
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                capture_output=True,
                text=True,
            )
        else:
            p.terminate()
        kill_cfd_containers()

    def refresh_resume_caption(*, default_on: bool = False) -> None:
        """Say which run "Continue" would add to; optionally switch it on when one exists."""
        target = latest_opt_run(session.runs_root)
        if target is None:
            state.opt_resume_caption = (
                "No earlier Optimize run yet — this starts a new one in runs/cockpit_opt_*."
            )
            return
        n = sum(1 for d in user_designs
                if d.extra.get("source") == "cockpit_opt"
                and d.extra.get("source_run") == target.name)
        state.opt_resume_caption = (
            f"On: adds trials to {run_label(target.name)} ({n} plotted so far) so the search keeps "
            "learning from them. Off: starts a fresh run (random warm-up again)."
        )
        if default_on:
            state.opt_resume = True

    refresh_resume_caption(default_on=True)

    def cancel_optimize():
        if not state.opt_running:
            return
        state.opt_cancel = True
        _kill_opt_proc()
        state.opt_msg = "⏹ Cancelling optimize…"
        state.flush()

    def on_optimize_fan():
        if state.assess_busy or state.preview_busy or state.export_busy or state.opt_running:
            return
        try:
            trials = int(float(state.opt_trials))
        except (TypeError, ValueError):
            trials = 8
        trials = max(2, min(40, trials))
        resume = bool(state.opt_resume)
        # "Continue" adds trials to the latest cockpit Optimize run so the sampler keeps learning
        # from earlier batches; with none on disk it falls back to the opened run.
        target = latest_opt_run(session.runs_root) if resume else None
        if resume and target is None:
            target = run_dir
        out = opt_out_path(resume=resume, run_dir=target or run_dir)
        is_opened = resume and Path(target).resolve() == Path(run_dir).resolve()
        resume_study = None
        if resume:
            resume_study = (study_name or "fansim") if is_opened else "fansim"
        resync_opened = is_opened
        offset = opt_trial_offset(out.name, session.runs_root)
        search_rpm = bool(state.opt_search_rpm)
        rpm_min = rpm_max = None
        if search_rpm:
            from fansim.optimize.pwm_table import pwm_caption, resolve_pwm_table

            try:
                lo = float(state.opt_rpm_min)
                hi = float(state.opt_rpm_max)
            except (TypeError, ValueError):
                lo, hi = 450.0, 2000.0
            try:
                tab = resolve_pwm_table(lo, hi)
            except ValueError as exc:
                state.opt_msg = f"⚠ PWM band invalid: {exc}"
                state.flush()
                return
            rpm_min, rpm_max = tab.rpm_min, tab.rpm_max
            state.opt_rpm_min = rpm_min
            state.opt_rpm_max = rpm_max
            state.opt_pwm_caption = pwm_caption(tab)
        from fansim.cfd.wall_roughness import FDM_WALL_KS_MM

        argv = optimization_argv(
            trials=trials,
            out=out,
            fan_model=str(state.fan_model or "a12x25"),
            preset=str(state.assess_preset or "case"),
            refine_op=bool(state.assess_refine_op),
            shroud=bool(state.opt_shroud),
            bem_floor=32.0 if state.opt_bem else 0.0,
            gp_floor=40.0 if state.opt_gp else 0.0,
            gp_boost=bool(state.opt_gp_boost),
            gp_nn=bool(state.opt_gp_nn),
            surrogate_guided=False,  # R1.11 / UI-31: never rank with synthetic_label

            study_name=resume_study,
            stator=bool(state.opt_stator) and not bool(state.opt_stator_stack),
            stator_stack=bool(state.opt_stator_stack),
            sickle=bool(state.opt_sickle),
            stepped_inlet=bool(state.opt_stepped),
            notched_tips=bool(state.opt_notched),
            search_rpm=search_rpm,
            rpm_min=rpm_min,
            rpm_max=rpm_max,
            wall_ks_mm=FDM_WALL_KS_MM if state.assess_wall_ks else None,
            material=str(state.assess_material or "PETG"),
        )

        async def task():
            state.assess_busy = True
            state.opt_running = True
            state.opt_cancel = False
            mode = "resume" if resume else "new"
            t0 = time.time()
            note = f"{trials} trials, guided, mountable, {mode}"
            state.opt_msg = busy_caption("Optimize", 0, note=note)
            state.flush()
            kwargs = dict(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            try:
                proc = subprocess.Popen(argv, **kwargs)
            except Exception as exc:  # noqa: BLE001
                state.opt_msg = f"⚠ Optimize failed to start: {type(exc).__name__}: {exc}"
                state.assess_busy = False
                state.opt_running = False
                state.flush()
                return
            opt_proc[0] = proc
            lines: list[str] = []
            log_q: queue.Queue = queue.Queue()
            with designs_lock:
                seen_keys: set[tuple[str, int]] = {
                    (str(d.extra.get("source_run") or ""), int(d.extra.get("orig_trial", d.trial)))
                    for d in user_designs
                    if d.extra.get("source") == "cockpit_opt"
                }
            last_poll = 0.0

            def reader():
                try:
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        log_q.put(line.rstrip())
                finally:
                    log_q.put(None)

            def poll_merge() -> int:
                try:
                    loaded = load_designs(out, resume_study)
                except Exception:  # noqa: BLE001
                    return 0
                fresh = merge_opt_designs(
                    loaded, source_run=out.name, existing_keys=seen_keys, offset=offset
                )
                append_user_designs(designs_lock, user_designs, by_trial, fresh)
                if fresh:
                    session.refresh_items()
                    session.refresh_figure()
                return len(fresh)

            def _opt_busy_body(extra: str = "") -> str:
                head = busy_caption("Optimize", time.time() - t0, note=note)
                body = "\n".join(lines[-18:])
                if extra:
                    body = f"{body}\n{extra}" if body else extra
                return f"{head}\n{body}" if body else head

            threading.Thread(target=reader, daemon=True).start()
            loop = asyncio.get_running_loop()

            def get_item():
                try:
                    return log_q.get(timeout=0.25)
                except queue.Empty:
                    return Ellipsis

            while True:
                item = await loop.run_in_executor(None, get_item)
                now = time.time()
                if now - last_poll >= 5.0:
                    last_poll = now
                    n_new = await loop.run_in_executor(None, poll_merge)
                    if n_new:
                        state.opt_msg = _opt_busy_body(
                            f"… live: +{n_new} trial(s) on plot ({len(seen_keys)} from this run)"
                        )
                        state.flush()
                    elif item is Ellipsis:
                        state.opt_msg = _opt_busy_body()
                        state.flush()
                if item is Ellipsis:
                    continue
                if item is None:
                    break
                lines.append(str(item))
                state.opt_msg = _opt_busy_body()
                state.flush()
            rc = proc.wait()
            opt_proc[0] = None
            if state.opt_cancel or rc not in (0, None):
                if state.opt_cancel:
                    state.opt_msg = (
                        f"{state.opt_msg}\n⏹ Cancelled." if state.opt_msg else "⏹ Cancelled."
                    )
                else:
                    tail = "\n".join(lines[-8:])
                    state.opt_msg = f"⚠ Optimize exited {rc}\n{tail}"
                await loop.run_in_executor(None, poll_merge)
                if resync_opened:
                    await loop.run_in_executor(None, session._resync_study_from_disk)
                session.refresh_items()
                session.refresh_figure()
                state.assess_busy = False
                state.opt_running = False
                state.opt_cancel = False
                state.flush()
                return
            n = await loop.run_in_executor(None, poll_merge)
            n_study = 0
            if resync_opened:
                n_study = await loop.run_in_executor(None, session._resync_study_from_disk)
            session.refresh_items()
            session.refresh_figure()
            state.opt_msg = (
                f"✓ Optimize finished → {run_label(out.name)} ({out.name}). "
                f"Its points are on the plot as #{offset}+trial; +{n} on final merge"
                + (f"; opened study now {n_study} feasible" if resync_opened else "")
                + f"  · elapsed {format_elapsed(time.time() - t0)}"
                + ". Open Results and click a ◆ diamond for the 3-D impeller "
                "+ velocity arrows + duct midplane airflow when case fields are still on disk."
            )
            state.fan_subtab = "results"
            refresh_resume_caption(default_on=True)  # next Optimize builds on this run
            state.assess_busy = False
            state.opt_running = False
            state.flush()

        fan_runtime.asynchronous.create_task(task())

    session.cancel_optimize = cancel_optimize
    session.on_optimize_fan = on_optimize_fan
