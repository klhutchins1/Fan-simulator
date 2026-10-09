"""Isolated (subprocess) impeller build — a crash/hang in OCP can't kill the caller.

The cockpit's live preview builds featured geometry, which is heavy (high-resolution lofts) and can
occasionally crash OCP natively or run for minutes under load. Running the build in a short-lived
subprocess with a timeout turns those into a caught error instead of a dead server.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path

from fansim.isolated_job import run_worker_module


def write_progress(path: str | Path | None, stage: int, of: int, label: str) -> None:
    """Worker side: record the build stage (atomic replace, so a reader never sees half a file)."""
    if not path:
        return
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps({"stage": int(stage), "of": int(of), "label": str(label)}),
                   encoding="utf-8")
    os.replace(tmp, path)


def read_progress(path: str | Path | None) -> dict | None:
    """Caller side: the worker's last reported stage, or None (not started / no file)."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if int(d["of"]) > 0 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


STARTING_PCT = 2   # bar value before the worker's first stage lands (a sliver, not the sweep)


def progress_caption(p: dict | None, prev_pct: int = 0) -> tuple[int, str]:
    """(percent for a determinate bar, 'stage 3/5 · realising chords').

    Before the worker reports anything: a small fixed value and "starting build process". The bar
    shows completed stages and never goes below ``prev_pct``, so it only moves forward; it never
    falls back to the indeterminate sweep, which read as a bar jumping 65 % → 50 % (QA UI-4).
    """
    if not p:
        return max(prev_pct, STARTING_PCT), "starting build process"
    k, n = int(p["stage"]), int(p["of"])
    return max(prev_pct, STARTING_PCT, int(100 * (k - 1) / n)), f"stage {k}/{n} · {p['label']}"


def build_stl_isolated(flat: dict, features, out_path: str | Path, timeout: float = 300.0,
                       preview: bool = False, motor_mount: dict | None = None,
                       *, preview_dense: bool = False,
                       progress_path: str | Path | None = None) -> Path:
    """Build an impeller STL from a flat param dict + features, in a subprocess with a timeout.

    ``features`` may be a Features dataclass or a plain dict. ``preview=True`` builds the FAST
    non-fused visual mesh (skips the ~140s boolean fuse that dominates featured builds; see
    build_impeller_preview) and writes a ``<out>.meta.json`` volume sidecar — for the live preview,
    which only needs to look right. ``preview_dense=True`` keeps recipe ``n_span``/``n_chord``
    (smoother LE; still non-fused). ``preview=False`` builds the real fused watertight solid.
    When ``motor_mount`` is a MotorMount field dict and ``preview`` is False, the motor cup (+ grips)
    is carved into the hub so the preview/export shows the commercial hub opening.
    Returns the STL path on success; raises TimeoutError if the build exceeds ``timeout``, or
    RuntimeError if the build process fails/crashes (e.g. an OCP native crash -> non-zero exit).
    """
    out_path = Path(out_path)
    feat = asdict(features) if is_dataclass(features) else dict(features or {})
    job = {
        "flat": flat,
        "features": feat,
        "out": str(out_path),
        "preview": preview,
        "preview_dense": bool(preview_dense),
    }
    if motor_mount is not None and not preview:
        job["motor_mount"] = dict(motor_mount)
    if progress_path is not None:
        # Stage 1 is the worker's interpreter + CadQuery/OCP import (~2 s; ~30 s on a slow box),
        # which happens before any worker code can run, so the parent records it (QA UI-4 r3).
        write_progress(progress_path, 1, 4, "loading CAD kernel")
        job["progress"] = str(progress_path)
    run_worker_module(
        "fansim.geometry._build_worker",
        job,
        timeout=timeout,
        label="geometry build",
        require_paths=[out_path],
    )
    return out_path
