# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Isolated (subprocess) impeller build — a crash/hang in OCP can't kill the caller.

The cockpit's live preview builds featured geometry, which is heavy (high-resolution lofts) and can
occasionally crash OCP natively or run for minutes under load. Running the build in a short-lived
subprocess with a timeout turns those into a caught error instead of a dead server.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path


def build_stl_isolated(flat: dict, features, out_path: str | Path, timeout: float = 300.0,
                       preview: bool = False) -> Path:
    """Build an impeller STL from a flat param dict + features, in a subprocess with a timeout.

    ``features`` may be a Features dataclass or a plain dict. ``preview=True`` builds the FAST
    non-fused visual mesh (skips the ~140s boolean fuse that dominates featured builds; see
    build_impeller_preview) and writes a ``<out>.meta.json`` volume sidecar — for the live preview,
    which only needs to look right. ``preview=False`` builds the real fused watertight solid.
    Returns the STL path on success; raises TimeoutError if the build exceeds ``timeout``, or
    RuntimeError if the build process fails/crashes (e.g. an OCP native crash -> non-zero exit).
    """
    out_path = Path(out_path)
    feat = asdict(features) if is_dataclass(features) else dict(features or {})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as jf:
        json.dump({"flat": flat, "features": feat, "out": str(out_path), "preview": preview}, jf)
        job = jf.name
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "fansim.geometry._build_worker", job],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"geometry build exceeded {timeout:.0f}s (features are heavy)") from exc
    finally:
        Path(job).unlink(missing_ok=True)
    if proc.returncode != 0 or not out_path.exists():
        raise RuntimeError(f"geometry build failed (exit {proc.returncode}): "
                           f"{(proc.stderr or '').strip()[-160:] or 'native crash'}")
    return out_path
