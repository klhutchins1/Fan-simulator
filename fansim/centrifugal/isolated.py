"""Isolated mixed-flow preview build and CFD evaluate (subprocess)."""

from __future__ import annotations

from pathlib import Path

from fansim.fan_spec import A12X25, FanSpec, fan_spec_to_dict
from fansim.isolated_job import load_objective_result, run_worker_module
from fansim.optimize.isolated_eval import cfd_eval_timeout
from fansim.optimize.objectives import ObjectiveResult


def mixed_eval_job_dict(
    flat: dict,
    workdir: str | Path,
    spec: FanSpec,
    *,
    procs: int,
    base_cell: float,
    iters: int,
    out: str,
    load_pa: float = 1.0,
    refine_op: bool = False,
) -> dict:
    """JSON payload for ``fansim.centrifugal._eval_worker``."""
    return {
        "kind": "mixed_flow",
        "flat": dict(flat),
        "workdir": str(workdir),
        "spec": fan_spec_to_dict(spec),
        "procs": int(procs),
        "base_cell": float(base_cell),
        "iters": int(iters),
        "out": str(out),
        "load_pa": float(load_pa),
        "refine_op": bool(refine_op),
    }


def build_mixed_stl_isolated(
    flat: dict,
    out_path: str | Path,
    timeout: float = 300.0,
    *,
    preview: bool = False,
) -> Path:
    """Export mixed-flow STL in a subprocess (CadQuery crash isolation).

    ``preview=True`` builds the non-fused rotate-copy mesh (§13.23) and writes a
    ``<out>.meta.json`` volume sidecar. ``preview=False`` builds the fused + cup carve solid.
    """
    out_path = Path(out_path)
    job = {"flat": flat, "out": str(out_path), "preview": bool(preview)}
    require = [out_path]
    run_worker_module(
        "fansim.centrifugal._build_worker",
        job,
        timeout=timeout,
        label="mixed-flow preview" if preview else "mixed-flow build",
        require_paths=require,
    )
    return out_path


def evaluate_mixed_flow_isolated(
    flat: dict,
    workdir: str | Path,
    spec: FanSpec = A12X25,
    *,
    procs: int = 8,
    base_cell: float = 0.006,
    iters: int = 500,
    timeout: float | None = None,
    load_pa: float = 1.0,
    refine_op: bool = False,
) -> ObjectiveResult:
    """Run ``evaluate_mixed_flow`` in a subprocess; return ``ObjectiveResult``.

    Default timeout matches axial Assess (``cfd_eval_timeout`` / env ``FANSIM_CFD_EVAL_TIMEOUT``).
    """
    timeout_s = cfd_eval_timeout(timeout)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "_eval_result.json"
    job = mixed_eval_job_dict(
        flat, workdir, spec,
        procs=procs, base_cell=base_cell, iters=iters, out=str(out),
        load_pa=load_pa, refine_op=refine_op,
    )
    run_worker_module(
        "fansim.centrifugal._eval_worker",
        job,
        timeout=timeout_s,
        label="mixed-flow evaluate",
        require_paths=[out],
        stderr_tail=200,
    )
    return load_objective_result(out)
