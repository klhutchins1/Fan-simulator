"""Shared busy-caption / elapsed helpers for the cockpit action strips.

Long-running Preview / Assess / Optimize / Export / CFD-refine paths use the same
caption language everywhere: ``Running <Action>… M:SS`` plus an optional note and
stage hint. True percent is rare (sweep only); everything else is honest-indeterminate.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
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
    max_t = 0
    p0 = wd / "processor0"
    if p0.is_dir():
        for child in p0.iterdir():
            if child.is_dir() and child.name.isdigit():
                max_t = max(max_t, int(child.name))
    if max_t <= 0 and not (wd / "logs" / "decomposePar.log").exists():
        return "meshing done — starting free delivery…"
    if max_t < 500:
        return f"solving… time={max_t}/500 (free or load)"
    return f"solving… time={max_t}/500 (finishing / second hose point)"


async def run_busy_ticker(
    *,
    is_active: Callable[[], bool],
    set_msg: Callable[[str], None],
    action: str,
    t0: float,
    note: str = "",
    hint_fn: Callable[[], str] | None = None,
    interval: float = 1.0,
    flush: Callable[[], None] | None = None,
) -> None:
    """Refresh a busy caption with live elapsed (and optional stage hint) until inactive."""
    while is_active():
        hint = hint_fn() if hint_fn else ""
        set_msg(busy_caption(action, time.time() - t0, hint=hint, note=note))
        if flush is not None:
            flush()
        await asyncio.sleep(interval)
