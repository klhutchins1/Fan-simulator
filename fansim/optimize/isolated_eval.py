# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Isolated (subprocess) CFD evaluation -- a crash/hang in OCP or OpenFOAM can't kill the caller.

The cockpit's Assess runs evaluate_candidate() (OCP impeller build + OpenFOAM CFD). Run directly in a
worker THREAD of the live-VTK trame process, a native OCP build crash bypasses try/except and takes
the whole cockpit server down -- the same crash class already isolated for the live preview build.
Running the evaluation in a short-lived subprocess turns those into a caught error instead of a dead
server. Mirrors fansim.geometry.isolated.build_stl_isolated.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path

from fansim.fan_spec import A12X25, FanSpec, fan_spec_to_dict
from fansim.optimize.objectives import ObjectiveResult


def evaluate_candidate_isolated(
    flat: dict,
    features,
    workdir: str | Path,
    spec: FanSpec = A12X25,
    *,
    procs: int = 8,
    base_cell: float = 0.006,
    iters: int = 500,
    timeout: float = 1200.0,
) -> ObjectiveResult:
    """Run evaluate_candidate in a subprocess and return its ObjectiveResult.

    ``flat`` may be a merged geometry+feature dict (feature keys are ignored by blade_from_flat).
    ``features`` is a Features dataclass or a plain dict. Raises TimeoutError if the evaluation
    exceeds ``timeout`` (CFD is minutes-long, so keep this generous), or RuntimeError if the worker
    process fails / crashes natively (non-zero exit) -- the caller shows the message instead of dying.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "_eval_result.json"
    feat = asdict(features) if is_dataclass(features) else dict(features or {})
    job = {
        "flat": flat, "features": feat, "workdir": str(workdir),
        "spec": fan_spec_to_dict(spec), "procs": int(procs),
        "base_cell": float(base_cell), "iters": int(iters), "out": str(out),
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
        jobfile = jf.name
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "fansim.optimize._eval_worker", jobfile],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"CFD evaluation exceeded {timeout:.0f}s") from exc
    finally:
        Path(jobfile).unlink(missing_ok=True)
    if proc.returncode != 0 or not out.exists():
        tail = (proc.stderr or "").strip()[-300:] or "native crash (no output)"
        raise RuntimeError(f"CFD evaluation failed (exit {proc.returncode}): {tail}")
    data = json.loads(out.read_text())
    return ObjectiveResult(**data)
