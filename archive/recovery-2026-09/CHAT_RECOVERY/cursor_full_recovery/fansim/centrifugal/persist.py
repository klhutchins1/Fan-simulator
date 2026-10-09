"""Persist / reload mixed-flow Assess + Optimize results for the cockpit scatter (§8.6).

Assess workdirs are ``runs/cockpit_mf_*``; each successful score writes ``design.json``
next to ``impeller.stl`` (same shape as axial cockpit_assess). Optimize fronts live under
``runs/cockpit_mf_opt_*/pareto.json`` (+ Optuna ``study.db``).
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

_log = logging.getLogger(__name__)

MIXED_RUN_GLOB = "cockpit_mf_*"
MIXED_OPT_GLOB = "cockpit_mf_opt_*"
PARETO_FILENAME = "pareto.json"
STUDY_DB_NAME = "study.db"
MIXED_OPT_TRIAL_OFFSET = 20000  # Optuna trial ids → cockpit scatter (miss Assess 9xxx)


def mixed_design_payload(
    *,
    trial: int,
    params: dict,
    objectives: dict,
    feasible: bool = True,
    reason: str = "",
    extra: dict | None = None,
) -> dict[str, Any]:
    return {
        "kind": "mixed_flow",
        "trial": int(trial),
        "params": dict(params),
        "objectives": {
            "cfm_free": objectives.get("cfm_free"),
            "cfm_load": objectives.get("cfm_load"),
            "efficiency": objectives.get("efficiency"),
        },
        "feasible": bool(feasible),
        "reason": reason or "",
        "extra": dict(extra or {}),
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def save_mixed_design_json(
    workdir: str | Path,
    *,
    trial: int,
    params: dict,
    objectives: dict,
    feasible: bool = True,
    reason: str = "",
    extra: dict | None = None,
) -> Path:
    """Write ``design.json`` into an Assess workdir."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    payload = mixed_design_payload(
        trial=trial,
        params=params,
        objectives=objectives,
        feasible=feasible,
        reason=reason,
        extra=extra,
    )
    path = workdir / "design.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_mixed_design(path_or_dir: str | Path) -> dict | None:
    """Load one mixed Assess record from ``design.json`` or its parent dir."""
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / "design.json"
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "skip corrupt mixed design.json %s: %s: %s",
            p, type(exc).__name__, exc)
        return None
    if not isinstance(d, dict) or "objectives" not in d:
        return None
    objs = d.get("objectives") or {}
    if objs.get("cfm_free") is None:
        return None
    stl = p.parent / "impeller.stl"
    extra = dict(d.get("extra") or {})
    extra.setdefault("source", "mixed_assess")
    extra.setdefault("source_run", p.parent.name)
    return {
        "trial": int(d.get("trial", 9000)),
        "params": dict(d.get("params") or {}),
        "objectives": {
            "cfm_free": float(objs["cfm_free"]),
            "cfm_load": float(objs.get("cfm_load") or 0.0),
            "efficiency": float(objs.get("efficiency") or 0.0),
        },
        "feasible": bool(d.get("feasible", True)),
        "reason": d.get("reason", ""),
        "extra": extra,
        "stl_path": str(stl) if stl.exists() else None,
        "workdir": str(p.parent),
    }


def load_all_mixed_designs(runs_root: str | Path) -> list[dict]:
    """Merge Assess (``cockpit_mf_*``) + Optimize fronts (``cockpit_mf_opt_*``)."""
    runs_root = Path(runs_root)
    out: list[dict] = []
    used: set[int] = set()

    def _fresh() -> int:
        i = 9000
        while i in used:
            i += 1
        used.add(i)
        return i

    if not runs_root.exists():
        return out
    for d in sorted(runs_root.glob(MIXED_RUN_GLOB)):
        if not d.is_dir() or d.name.startswith("cockpit_mf_opt"):
            continue
        row = load_mixed_design(d)
        if row is None or not row.get("feasible", True):
            continue
        orig = int(row["trial"])
        if orig in used:
            tid = _fresh()
            row["extra"] = dict(row.get("extra") or {})
            row["extra"]["orig_trial"] = orig
            row["trial"] = tid
        else:
            used.add(orig)
        out.append(row)
    for d in sorted(runs_root.glob(MIXED_OPT_GLOB)):
        if not d.is_dir():
            continue
        for row in load_mixed_pareto(d):
            tid = int(row.get("trial", _fresh()))
            if tid in used:
                row = dict(row)
                row["extra"] = dict(row.get("extra") or {})
                row["extra"]["orig_trial"] = tid
                tid = _fresh()
                row["trial"] = tid
            else:
                used.add(tid)
            out.append(row)
    out.sort(key=lambda r: -float(r["objectives"]["cfm_free"]))
    return out


def next_mixed_trial(existing: Iterable[dict], start: int = 9000) -> int:
    used = {int(r["trial"]) for r in existing if "trial" in r}
    i = int(start)
    while i in used:
        i += 1
    return i


def mixed_opt_out_path(
    *,
    resume: bool,
    last_dir: str | Path | None,
    stamp: str | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    """New ``cockpit_mf_opt_*`` folder, or ``last_dir`` when resuming a study with ``study.db``."""
    if resume and last_dir is not None:
        p = Path(last_dir)
        if p.is_dir() and (p / STUDY_DB_NAME).exists():
            return p
    tag = stamp if stamp is not None else datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(runs_root) / f"cockpit_mf_opt_{tag}"


def latest_mixed_opt_dir(runs_root: str | Path) -> Path | None:
    root = Path(runs_root)
    if not root.exists():
        return None
    candidates = [
        d for d in root.glob(MIXED_OPT_GLOB)
        if d.is_dir() and (d / STUDY_DB_NAME).exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.stat().st_mtime)


def mixed_opt_rows_from_study(study) -> list[dict]:
    """Pareto front as cockpit scatter rows (BEM proxy objectives)."""
    rows: list[dict] = []
    for t in study.best_trials:
        if t.values is None:
            continue
        if t.user_attrs.get("feasible") is False:
            continue
        params = t.user_attrs.get("params") or dict(t.params)
        tid = int(t.number) + MIXED_OPT_TRIAL_OFFSET
        rows.append({
            "trial": tid,
            "params": dict(params),
            "objectives": {
                "cfm_free": float(t.values[0]),
                "cfm_load": float(t.values[1]),
                "efficiency": float(t.user_attrs.get("efficiency") or 0.0),
            },
            "feasible": True,
            "reason": "",
            "extra": {
                "source": "mixed_optimize",
                "bem_adapter": t.user_attrs.get("bem_adapter", "axial"),
                "hose": t.user_attrs.get("hose", ""),
                "load_pa": t.user_attrs.get("load_pa"),
                "orig_trial": int(t.number),
            },
            "stl_path": None,
            "workdir": None,
        })
    rows.sort(key=lambda r: -float(r["objectives"]["cfm_free"]))
    return rows


def save_mixed_pareto(
    out_dir: str | Path,
    pareto: list[dict],
    *,
    meta: dict | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "mixed_pareto",
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": len(pareto),
        "meta": dict(meta or {}),
        "pareto": pareto,
    }
    path = out_dir / PARETO_FILENAME
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_mixed_pareto(path_or_dir: str | Path) -> list[dict]:
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / PARETO_FILENAME
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "skip corrupt mixed pareto.json %s: %s: %s",
            p, type(exc).__name__, exc)
        return []
    rows = data.get("pareto") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    run_name = p.parent.name
    for r in rows:
        if not isinstance(r, dict) or "objectives" not in r:
            continue
        row = dict(r)
        extra = dict(row.get("extra") or {})
        extra.setdefault("source", "mixed_optimize")
        extra.setdefault("source_run", run_name)
        extra.setdefault("bem_adapter", "axial")
        row["extra"] = extra
        row.setdefault("feasible", True)
        out.append(row)
    return out
