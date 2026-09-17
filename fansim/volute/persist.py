"""Persist / reload Volute Optimize fronts for the cockpit (§14.4b)."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

VOLUTE_OPT_GLOB = "cockpit_volute_opt_*"
PARETO_FILENAME = "pareto.json"
STUDY_DB_NAME = "study.db"
VOLUTE_OPT_TRIAL_OFFSET = 30000


def volute_opt_out_path(
    *,
    resume: bool = False,
    last_dir: str | Path | None = None,
    stamp: str | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    if resume and last_dir is not None:
        p = Path(last_dir)
        if p.is_dir() and (p / STUDY_DB_NAME).exists():
            return p
    tag = stamp if stamp is not None else datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(runs_root) / f"cockpit_volute_opt_{tag}"


def latest_volute_opt_dir(runs_root: str | Path) -> Path | None:
    root = Path(runs_root)
    if not root.exists():
        return None
    candidates = [
        d for d in root.glob(VOLUTE_OPT_GLOB)
        if d.is_dir() and (d / STUDY_DB_NAME).exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.stat().st_mtime)


def volute_opt_rows_from_study(study) -> list[dict]:
    rows: list[dict] = []
    for t in study.best_trials:
        if t.values is None:
            continue
        if t.user_attrs.get("feasible") is False:
            continue
        params = t.user_attrs.get("params") or dict(t.params)
        tid = int(t.number) + VOLUTE_OPT_TRIAL_OFFSET
        rows.append({
            "trial": tid,
            "params": dict(params),
            "objectives": {
                "capacity_proxy": float(t.values[0]),
                "head_proxy": float(t.values[1]),
            },
            "feasible": True,
            "reason": "",
            "extra": {
                "source": "volute_optimize",
                "volute_proxy": t.user_attrs.get("volute_proxy", "geometry"),
                "rpm": t.user_attrs.get("rpm"),
                "orig_trial": int(t.number),
            },
            "stl_path": None,
            "workdir": None,
        })
    rows.sort(key=lambda r: -float(r["objectives"]["capacity_proxy"]))
    return rows


def save_volute_pareto(
    out_dir: str | Path,
    pareto: list[dict],
    *,
    meta: dict | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "kind": "volute_pareto",
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": len(pareto),
        "meta": dict(meta or {}),
        "pareto": pareto,
    }
    path = out_dir / PARETO_FILENAME
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_volute_pareto(path_or_dir: str | Path) -> list[dict]:
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / PARETO_FILENAME
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _log.warning("skip corrupt volute pareto %s: %s: %s", p, type(exc).__name__, exc)
        return []
    rows = data.get("pareto") if isinstance(data, dict) else None
    return list(rows) if isinstance(rows, list) else []


def load_all_volute_pareto(runs_root: str | Path = "runs") -> list[dict]:
    root = Path(runs_root)
    if not root.exists():
        return []
    dirs = sorted(
        (p for p in root.glob(VOLUTE_OPT_GLOB) if p.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    out: list[dict] = []
    for d in dirs:
        for row in load_volute_pareto(d):
            extra = dict(row.get("extra") or {})
            extra.setdefault("source_run", d.name)
            row = dict(row, extra=extra)
            out.append(row)
    return out
