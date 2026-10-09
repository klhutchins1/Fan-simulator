"""Persist / reload CROR Optimize fronts for the cockpit scatter.

Optimize fronts live under ``runs/cockpit_cror_*/pareto.json``.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

CROR_OPT_GLOB = "cockpit_cror_*"
PARETO_FILENAME = "pareto.json"


def cror_opt_out_path(
    *,
    stamp: str | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    root = Path(runs_root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return root / f"cockpit_cror_{stamp}"


def latest_cror_opt_dir(runs_root: str | Path = "runs") -> Path | None:
    root = Path(runs_root)
    if not root.exists():
        return None
    dirs = sorted(
        (p for p in root.glob(CROR_OPT_GLOB) if p.is_dir() and (p / PARETO_FILENAME).exists()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return dirs[0] if dirs else None


def save_cror_pareto(
    out_dir: str | Path,
    pareto: list[dict],
    *,
    meta: dict | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "kind": "cror",
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "meta": dict(meta or {}),
        "pareto": list(pareto),
    }
    path = out_dir / PARETO_FILENAME
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_cror_pareto(path_or_dir: str | Path) -> list[dict]:
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / PARETO_FILENAME
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return []
    rows = data.get("pareto") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict) and "params" in r]


def load_all_cror_pareto(runs_root: str | Path = "runs") -> list[dict]:
    """Flatten all cockpit_cror_* fronts (newest first), tagging source_run."""
    root = Path(runs_root)
    if not root.exists():
        return []
    dirs = sorted(
        (p for p in root.glob(CROR_OPT_GLOB) if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    out: list[dict] = []
    for d in dirs:
        for row in load_cror_pareto(d):
            r = dict(row)
            r.setdefault("source_run", d.name)
            out.append(r)
    return out
