# EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12
# source: agent-transcripts/9f43d5b7...jsonl write@3337 + 0 later StrReplace
# NOT verified against lost E: tree — re-check before deleting RECOVERED-FROM-CHAT peers.

"""Shared JSON-job subprocess runner for CadQuery/CFD workers.

Build/eval callers write a temp job file and run ``python -m <module> <job.json>``.
A crash or hang in OCP/OpenFOAM stays in the child process.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from fansim.optimize.objectives import ObjectiveResult


def run_worker_module(
    module: str,
    job: dict,
    *,
    timeout: float,
    label: str,
    require_paths: Sequence[Path] | None = None,
    stderr_tail: int = 160,
) -> subprocess.CompletedProcess:
    """Run ``python -m module <job.json>``; delete the job file afterward.

    Raises ``TimeoutError`` if the worker exceeds ``timeout``, or ``RuntimeError`` if
    the exit code is non-zero or any ``require_paths`` is missing.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump(job, jf)
        jobfile = jf.name
    try:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", module, jobfile],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"{label} exceeded {timeout:.0f}s") from exc
    finally:
        Path(jobfile).unlink(missing_ok=True)

    missing = [p for p in (require_paths or ()) if not Path(p).exists()]
    if proc.returncode != 0 or missing:
        tail = (proc.stderr or "").strip()[-stderr_tail:] or "native crash"
        raise RuntimeError(f"{label} failed (exit {proc.returncode}): {tail}")
    return proc


def load_objective_result(path: Path | str) -> ObjectiveResult:
    """Load an ``ObjectiveResult`` written by an eval worker."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ObjectiveResult(**data)
