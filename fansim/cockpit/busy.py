"""Shared busy-caption / elapsed helpers for the cockpit action strips.

Long-running Preview / Assess / Optimize / Export / CFD-refine paths use the same
caption language everywhere: ``Running <Action>… M:SS`` plus an optional note and
stage hint. True percent is rare (sweep only); everything else is honest-indeterminate.
"""

from __future__ import annotations

import re
from pathlib import Path


def format_elapsed(seconds: float | int) -> str:
    """Format elapsed seconds as ``M:SS`` (or ``H:MM:SS`` if ≥ 1 h)."""
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def busy_caption(
    action: str,
    elapsed_s: float | int,
    *,
    hint: str = "",
    note: str = "",
) -> str:
    """Cohesive busy line: ``Running Preview… 0:12`` (+ optional note / stage)."""
    base = f"Running {action}… {format_elapsed(elapsed_s)}"
    if note:
        base = f"{base}  ({note})"
    if hint:
        return f"{base}\n{hint}"
    return base


def cfd_stage_hint(workdir: Path | None) -> str:
    """Best-effort stage string from an in-flight CFD workdir (mesh vs free/load iters)."""
    if workdir is None:
        return ""
    wd = Path(workdir)
    if not wd.exists():
        return "building geometry…"
    if not (wd / "logs" / "checkMesh.log").exists():
        if (wd / "impeller.stl").exists():
            return "meshing…"
        return "building geometry…"
    # simpleFoam.log streams live (fansim.cfd.runner), so the hint shows the actual iteration.
    # Axial evals drop _partial_free.json once free-air is done; other archetypes don't, so the
    # phase is only named when known.
    phase = "load solve (free-air done)" if (wd / "_partial_free.json").exists() else "solve"
    it = _live_iteration(wd / "logs" / "simpleFoam.log")
    if it is None:
        if not (wd / "logs" / "decomposePar.log").exists():
            return "meshing done — starting solve…"
        return f"{phase}: starting…"
    return f"{phase}: iteration {it}"


_TIME_RE = re.compile(r"^Time = (\d+)\s*$", re.MULTILINE)


def _live_iteration(log: Path) -> int | None:
    """Last ``Time = N`` in a (possibly still growing) simpleFoam log; reads only the tail."""
    try:
        with open(log, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 16384))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    hits = _TIME_RE.findall(tail)
    return int(hits[-1]) if hits else None
