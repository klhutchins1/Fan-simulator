"""Pilot-run timing: mesh cell counts, solve rate, and full-run ETA for CFD scripts.

A full validation / ladder / direction-audit run can take hours to days. ``--pilot`` (added to
``scripts/run_a12x25_validation.py``, ``scripts/audit_direction_cfd.py`` and
``scripts/run_loaded_ladder.py``) meshes once, solves a single point at a fraction of the
requested iterations, measures the achieved rate, and estimates the full run's wall time
before committing to it -- see ``.superpowers/sdd/ring-duct-brief.md`` Part B.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_CELLS_RE = re.compile(r"cells:\s*(\d+)")


def mesh_cells(case_dir: str | Path) -> int | None:
    """Parse the ``cells:`` count from ``<case_dir>/logs/checkMesh.log``. ``None`` if missing."""
    path = Path(case_dir) / "logs" / "checkMesh.log"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    m = _CELLS_RE.search(text)
    return int(m.group(1)) if m else None


@dataclass
class SolveTiming:
    """One measured (or estimated) solve's timing."""

    cells: int | None
    iters: int
    wall_s: float
    sec_per_iter: float


def pilot_iters(iters: int, *, min_iters: int = 50, fraction: int = 10) -> int:
    """Iteration count for the pilot solve: ``max(min_iters, iters // fraction)``."""
    return max(int(min_iters), int(iters) // int(fraction))


def estimate_run(
    mesh_s: float, sec_per_iter: float, iters: int, points: int, margin: float = 1.2,
) -> float:
    """Estimated wall time (s) for a full run: meshing plus ``points`` solves of ``iters``.

    ``mesh_s`` is the total meshing cost for the run (a script meshing more than once, e.g.
    the direction audit's 2 orientations, passes the summed meshing cost). ``margin`` (default
    1.2 = +20%) pads the pilot's short-sample rate for overhead a brief pilot under-samples
    (potentialFoam seeding, decomposePar, I/O, iteration-to-iteration variance).
    """
    return float(margin) * (float(mesh_s) + float(sec_per_iter) * float(iters) * float(points))


def estimate_urans_wall_s(*, sim_s_per_wall_s: float, revs: float, rpm: float) -> float:
    """Wall time (s) for a URANS run, from the pilot's simulated-time rate.

    ``sim_s_per_wall_s`` is simulated seconds advanced per wall-clock second, measured from a
    short pilot ``pimpleFoam`` run. The full run needs ``revs * 60 / rpm`` simulated seconds
    (``revs`` rotor revolutions at ``rpm``).
    """
    if sim_s_per_wall_s <= 0:
        raise ValueError(f"sim_s_per_wall_s must be > 0, got {sim_s_per_wall_s!r}")
    sim_time_s = float(revs) * 60.0 / float(rpm)
    return sim_time_s / float(sim_s_per_wall_s)


def format_eta(seconds: float) -> str:
    """Human-readable ETA, e.g. ``"3 h 20 min"``, ``"45 min"``, or ``"12 s"``."""
    seconds = max(0.0, float(seconds))
    if seconds < 60.0:
        return f"{round(seconds)} s"
    total_min = round(seconds / 60.0)
    h, m = divmod(total_min, 60)
    if h > 0:
        return f"{h} h {m} min"
    return f"{m} min"


def write_pilot_json(
    path: str | Path,
    *,
    cells: int | None,
    mesh_s: float,
    sec_per_iter: float,
    iters: int,
    points: int,
    margin: float = 1.2,
    extra: dict | None = None,
) -> dict:
    """Compute the full-run estimate and write ``pilot.json``. Returns the payload written."""
    est_s = estimate_run(mesh_s, sec_per_iter, iters, points, margin=margin)
    payload: dict = {
        "cells": cells,
        "mesh_s": mesh_s,
        "sec_per_iter": sec_per_iter,
        "iters": iters,
        "points": points,
        "margin": margin,
        "estimated_full_run_s": est_s,
        "estimated_full_run_eta": format_eta(est_s),
    }
    if extra:
        payload.update(extra)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
