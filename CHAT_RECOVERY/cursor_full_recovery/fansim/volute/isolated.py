"""Isolated volute CadQuery builds + CFD evaluate (subprocess)."""

from __future__ import annotations

from pathlib import Path

from fansim.isolated_job import load_objective_result, run_worker_module
from fansim.optimize.objectives import ObjectiveResult
from fansim.volute.domain import DEFAULT_VOLUTE_RPM


def volute_eval_job_dict(
    flat: dict,
    workdir: str | Path,
    *,
    procs: int,
    base_cell: float,
    iters: int,
    out: str,
    load_pa: float = 50.0,
    rpm: float = DEFAULT_VOLUTE_RPM,
    mesh_only: bool = False,
) -> dict:
    """JSON payload for ``fansim.volute._eval_worker``."""
    return {
        "kind": "volute",
        "flat": dict(flat),
        "workdir": str(workdir),
        "procs": int(procs),
        "base_cell": float(base_cell),
        "iters": int(iters),
        "out": str(out),
        "load_pa": float(load_pa),
        "rpm": float(rpm),
        "mesh_only": bool(mesh_only),
    }


def build_volute_preview_isolated(
    flat: dict,
    out_path: str | Path,
    timeout: float = 300.0,
) -> Path:
    """Export multi-body preview STL in a subprocess."""
    out_path = Path(out_path)
    run_worker_module(
        "fansim.volute._build_worker",
        {"flat": flat, "out": str(out_path), "kind": "preview"},
        timeout=timeout,
        label="volute preview build",
        require_paths=[out_path],
    )
    return out_path


def build_volute_stls_isolated(
    flat: dict,
    out_dir: str | Path,
    timeout: float = 300.0,
) -> tuple[Path, Path]:
    """Export impeller.stl + casing.stl in a subprocess."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    imp = out_dir / "impeller.stl"
    cas = out_dir / "casing.stl"
    run_worker_module(
        "fansim.volute._build_worker",
        {"flat": flat, "out_dir": str(out_dir), "kind": "stls"},
        timeout=timeout,
        label="volute STL export",
        require_paths=[imp, cas],
    )
    return imp, cas


def evaluate_volute_isolated(
    flat: dict,
    workdir: str | Path,
    *,
    procs: int = 8,
    base_cell: float = 0.006,
    iters: int = 500,
    timeout: float = 1800.0,
    load_pa: float = 50.0,
    rpm: float = DEFAULT_VOLUTE_RPM,
    mesh_only: bool = False,
) -> ObjectiveResult:
    """Run ``evaluate_volute`` in a subprocess; return ``ObjectiveResult``."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "_eval_result.json"
    job = volute_eval_job_dict(
        flat, workdir,
        procs=procs, base_cell=base_cell, iters=iters, out=str(out),
        load_pa=load_pa, rpm=rpm, mesh_only=mesh_only,
    )
    run_worker_module(
        "fansim.volute._eval_worker",
        job,
        timeout=timeout,
        label="volute evaluate",
        require_paths=[out],
        stderr_tail=200,
    )
    return load_objective_result(out)
