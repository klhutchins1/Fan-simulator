"""Isolated (subprocess) impeller build — a crash/hang in OCP can't kill the caller.

The cockpit's live preview builds featured geometry, which is heavy (high-resolution lofts) and can
occasionally crash OCP natively or run for minutes under load. Running the build in a short-lived
subprocess with a timeout turns those into a caught error instead of a dead server.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

from fansim.isolated_job import run_worker_module


def build_stl_isolated(flat: dict, features, out_path: str | Path, timeout: float = 300.0,
                       preview: bool = False, motor_mount: dict | None = None,
                       *, preview_dense: bool = False) -> Path:
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
    run_worker_module(
        "fansim.geometry._build_worker",
        job,
        timeout=timeout,
        label="geometry build",
        require_paths=[out_path],
    )
    return out_path
