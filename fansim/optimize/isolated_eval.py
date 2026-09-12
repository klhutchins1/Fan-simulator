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
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path

from fansim.fan_spec import A12X25, FanSpec, fan_spec_to_dict
from fansim.optimize.objectives import ObjectiveResult

# Wall-clock budget for one Assess (geometry + mesh + free+load simpleFoam, optional refine-op).
# Successful Windows/Docker runs already take ~16–18 min; the old 1200s default killed in-progress
# load solves (~21 min). Override with env FANSIM_CFD_EVAL_TIMEOUT (seconds).
DEFAULT_CFD_EVAL_TIMEOUT_S = 3600.0
ENV_CFD_EVAL_TIMEOUT = "FANSIM_CFD_EVAL_TIMEOUT"


def cfd_eval_timeout(override: float | None = None) -> float:
    """Resolve CFD subprocess timeout: explicit override > env > default."""
    if override is not None:
        return float(override)
    raw = os.environ.get(ENV_CFD_EVAL_TIMEOUT)
    if raw not in (None, ""):
        try:
            return max(60.0, float(raw))
        except ValueError:
            pass
    return float(DEFAULT_CFD_EVAL_TIMEOUT_S)


def _terminate_worker(proc: subprocess.Popen) -> None:
    """Kill an eval worker and its children (Windows needs taskkill /T for the Docker tree)."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True, text=True,
        )
    else:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


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
    }
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
) -> ObjectiveResult:
    """Run evaluate_candidate in a subprocess and return its ObjectiveResult.

    ``flat`` may be a merged geometry+feature dict (feature keys are ignored by blade_from_flat).
    ``features`` is a Features dataclass or a plain dict. Raises TimeoutError if the evaluation
    exceeds ``timeout`` (default ``DEFAULT_CFD_EVAL_TIMEOUT_S`` / ``FANSIM_CFD_EVAL_TIMEOUT``),
    or RuntimeError if the worker process fails / crashes natively (non-zero exit) -- the caller
    shows the message instead of dying.

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
    )
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
        jobfile = jf.name
    proc: subprocess.Popen | None = None
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "fansim.optimize._eval_worker", jobfile],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if proc_holder is not None:
            if len(proc_holder) == 0:
                proc_holder.append(proc)
            else:
                proc_holder[0] = proc
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            _terminate_worker(proc)
            try:
                from fansim.cfd.runner import kill_cfd_containers
                kill_cfd_containers()
            except Exception:  # noqa: BLE001
                pass
            raise TimeoutError(
                f"CFD evaluation exceeded {timeout_s:.0f}s "
                f"(free+load often needs 15–40 min on Windows/Docker; "
                f"set {ENV_CFD_EVAL_TIMEOUT}=SECONDS to raise)"
            ) from exc
        returncode = proc.returncode
    finally:
        if proc_holder is not None and proc_holder and proc_holder[0] is proc:
            proc_holder[0] = None
        Path(jobfile).unlink(missing_ok=True)
    if returncode != 0 or not out.exists():
        tail = (stderr or "").strip()[-300:] or "native crash (no output)"
        raise RuntimeError(f"CFD evaluation failed (exit {returncode}): {tail}")
    data = json.loads(out.read_text())
    return ObjectiveResult(**data)
