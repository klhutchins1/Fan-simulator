"""Isolated (subprocess) CFD evaluation -- a crash/hang in OCP or OpenFOAM can't kill the caller.

The cockpit's Assess runs evaluate_candidate() (OCP impeller build + OpenFOAM CFD). Run directly in a
worker THREAD of the live-VTK trame process, a native OCP build crash bypasses try/except and takes
the whole cockpit server down -- the same crash class already isolated for the live preview build.
Running the evaluation in a short-lived subprocess turns those into a caught error instead of a dead
server. Mirrors fansim.geometry.isolated.build_stl_isolated.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path

from fansim.fan_spec import A12X25, FanSpec, fan_spec_to_dict
from fansim.isolated_job import run_watched, stall_timeout
from fansim.optimize.objectives import PARTIAL_FREE_FILE, ObjectiveResult

# HARD CAP for one Assess (geometry + mesh + free+load simpleFoam, optional refine-op). The real
# guard is the no-progress watchdog (fansim.isolated_job.stall_timeout, 15 min): a run that keeps
# writing output may finish even when a busy desktop slows it 2-3x (measured 2026-10-07: the same
# 1.07M-cell solve varied 69-140 s per 60 iters). The old flat 3600 s killed such runs near the end.
# Override with env FANSIM_CFD_EVAL_TIMEOUT (seconds).
DEFAULT_CFD_EVAL_TIMEOUT_S = 3.0 * 3600.0
ENV_CFD_EVAL_TIMEOUT = "FANSIM_CFD_EVAL_TIMEOUT"


def partial_free_note(workdir: str | Path) -> str:
    """Salvage text for a killed eval whose free-air solve had already finished ('' if none)."""
    try:
        m = json.loads((Path(workdir) / PARTIAL_FREE_FILE).read_text(encoding="utf-8"))
        return (f"; the free-air solve had finished: {float(m['cfm']):.1f} CFM raw CFD "
                f"(before motor derate / print penalty, "
                f"{'converged' if m.get('converged') else 'UNCONVERGED'})")
    except Exception:  # noqa: BLE001 — salvage is best-effort
        return ""


def cfd_eval_timeout(override: float | None = None) -> float:
    """Resolve the CFD subprocess hard cap: explicit override > env > default."""
    if override is not None:
        return float(override)
    raw = os.environ.get(ENV_CFD_EVAL_TIMEOUT)
    if raw not in (None, ""):
        try:
            return max(60.0, float(raw))
        except ValueError:
            pass
    return float(DEFAULT_CFD_EVAL_TIMEOUT_S)


def eval_job_dict(
    flat: dict,
    features,
    workdir: str | Path,
    spec: FanSpec,
    *,
    procs: int,
    base_cell: float,
    iters: int,
    out: str,
    load_pa: float = 1.0,
    refine_op: bool = False,
    material: str = "PETG",
    wall_ks_mm: float | None = None,
    parallel_mesh: bool = False,
    surf_max_floor: int | None = None,
) -> dict:
    """JSON payload for ``_eval_worker`` (includes the Assess/optimizer hose)."""
    feat = asdict(features) if is_dataclass(features) else dict(features or {})
    job = {
        "flat": flat, "features": feat, "workdir": str(workdir),
        "spec": fan_spec_to_dict(spec), "procs": int(procs),
        "base_cell": float(base_cell), "iters": int(iters), "out": str(out),
        "load_pa": float(load_pa),
        "refine_op": bool(refine_op),
        "material": str(material or "PETG"),
        "parallel_mesh": bool(parallel_mesh),
    }
    if surf_max_floor is not None:
        job["surf_max_floor"] = int(surf_max_floor)
    if wall_ks_mm is not None and float(wall_ks_mm) > 0:
        job["wall_ks_mm"] = float(wall_ks_mm)
    return job


def evaluate_candidate_isolated(
    flat: dict,
    features,
    workdir: str | Path,
    spec: FanSpec = A12X25,
    *,
    procs: int = 8,
    base_cell: float = 0.006,
    iters: int = 500,
    timeout: float | None = None,
    load_pa: float = 1.0,
    refine_op: bool = False,
    material: str = "PETG",
    wall_ks_mm: float | None = None,
    proc_holder: list | None = None,
    parallel_mesh: bool = False,
    surf_max_floor: int | None = None,
) -> ObjectiveResult:
    """Run evaluate_candidate in a subprocess and return its ObjectiveResult.

    ``flat`` may be a merged geometry+feature dict (feature keys are ignored by blade_from_flat).
    ``features`` is a Features dataclass or a plain dict. Raises TimeoutError if the evaluation
    exceeds ``timeout`` (default ``DEFAULT_CFD_EVAL_TIMEOUT_S`` / ``FANSIM_CFD_EVAL_TIMEOUT``)
    or stalls (no new case output for ``stall_timeout()``) -- the message carries the free-air
    result if that solve had finished -- or RuntimeError if the worker process fails / crashes
    natively (non-zero exit). The caller shows the message instead of dying.

    ``proc_holder``, when provided as a one-slot list, receives the live ``Popen`` so the cockpit
    Cancel button can terminate the worker mid-solve.
    """
    timeout_s = cfd_eval_timeout(timeout)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "_eval_result.json"
    job = eval_job_dict(
        flat, features, workdir, spec,
        procs=procs, base_cell=base_cell, iters=iters, out=str(out),
        load_pa=load_pa,
        refine_op=refine_op,
        material=material,
        wall_ks_mm=wall_ks_mm,
        parallel_mesh=parallel_mesh,
        surf_max_floor=surf_max_floor,
    )
    job["parent_pid"] = os.getpid()  # the worker stops (and kills its containers) if we die (29.4)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
        jobfile = jf.name
    (workdir / PARTIAL_FREE_FILE).unlink(missing_ok=True)
    try:
        try:
            returncode, _stdout, stderr = run_watched(
                [sys.executable, "-m", "fansim.optimize._eval_worker", jobfile],
                watch_dir=workdir, hard_timeout_s=timeout_s, stall_s=stall_timeout(),
                label="CFD evaluation", proc_holder=proc_holder,
            )
        except TimeoutError as exc:
            raise TimeoutError(f"{exc}{partial_free_note(workdir)}") from exc
    finally:
        Path(jobfile).unlink(missing_ok=True)
    if returncode != 0 or not out.exists():
        tail = (stderr or "").strip()[-300:] or "native crash (no output)"
        raise RuntimeError(f"CFD evaluation failed (exit {returncode}): {tail}")
    data = json.loads(out.read_text())
    return ObjectiveResult(**data)
