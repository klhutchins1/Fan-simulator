"""Persist / reload propeller Optimize + Analyze points for the cockpit scatter (§8.5).

Mirrors axial ``design.json`` / ``study.db`` reload: Optimize fronts live under
``runs/cockpit_prop_*/pareto.json`` (and optional Optuna ``study.db``); Analyze points
under ``runs/cockpit_prop_assess/design_*/design.json``.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

_log = logging.getLogger(__name__)

PARETO_FILENAME = "pareto.json"
PROP_RUN_GLOB = "cockpit_prop_*"
PROP_ASSESS_DIRNAME = "cockpit_prop_assess"
STUDY_DB_NAME = "study.db"


def prop_out_path(
    *,
    resume: bool,
    last_dir: str | Path | None,
    stamp: str | None = None,
    runs_root: str | Path = "runs",
) -> Path:
    """Where Prop Optimize writes: new ``cockpit_prop_*`` folder, or ``last_dir`` when resuming."""
    if resume and last_dir is not None:
        p = Path(last_dir)
        if p.is_dir() and (p / STUDY_DB_NAME).exists():
            return p
    tag = stamp if stamp is not None else datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(runs_root) / f"cockpit_prop_{tag}"


def latest_prop_study_dir(runs_root: str | Path) -> Path | None:
    """Most recently modified ``cockpit_prop_*`` folder that has an Optuna ``study.db``."""
    root = Path(runs_root)
    if not root.exists():
        return None
    candidates = [
        d for d in root.glob(PROP_RUN_GLOB)
        if d.is_dir() and (d / STUDY_DB_NAME).exists()
    ]
    if not candidates:
        return None
    # Directory mtimes are not reliably bumped by file writes on some platforms (notably Windows).
    # Use the study database mtime instead, since resuming appends trials into that file.
    return max(candidates, key=lambda d: (d / STUDY_DB_NAME).stat().st_mtime)


def pareto_rows_from_study(study) -> list[dict]:
    """Extract the NSGA front the same way ``run_prop_study`` returns it."""
    pareto = [
        {
            "thrust_g": t.values[0],
            "eff_g_per_w": t.values[1],
            "power_w": t.user_attrs.get("power_w"),
            "fm": t.user_attrs.get("fm"),
            "n_blades": t.user_attrs.get("n_blades"),
            "rel_dba": t.user_attrs.get("rel_dba"),
            "tip_mach": t.user_attrs.get("tip_mach"),
            "params": dict(t.params),
            "source": "optimize",
            "trial": int(t.number),
        }
        for t in study.best_trials
        if t.values is not None
    ]
    pareto.sort(key=lambda r: -float(r["thrust_g"]))
    return pareto


def save_prop_pareto(
    out_dir: str | Path,
    pareto: list[dict],
    *,
    prop_model: str = "",
    meta: dict | None = None,
) -> Path:
    """Write ``pareto.json`` under ``out_dir`` (creates the directory)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in pareto:
        row = dict(r)
        row.setdefault("source", "optimize")
        rows.append(row)
    payload = {
        "kind": "prop_pareto",
        "prop_model": prop_model,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n": len(rows),
        "meta": dict(meta or {}),
        "pareto": rows,
    }
    path = out_dir / PARETO_FILENAME
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_prop_pareto(path_or_dir: str | Path) -> list[dict]:
    """Load a single Optimize front from a ``pareto.json`` path or its parent dir."""
    p = Path(path_or_dir)
    if p.is_dir():
        p = p / PARETO_FILENAME
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "skip corrupt prop pareto.json %s: %s: %s",
            p, type(exc).__name__, exc)
        return []
    rows = data.get("pareto") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    run_name = p.parent.name
    model = data.get("prop_model", "") if isinstance(data, dict) else ""
    for r in rows:
        if not isinstance(r, dict) or "params" not in r:
            continue
        row = dict(r)
        row.setdefault("source", "optimize")
        row.setdefault("source_run", run_name)
        if model and "prop_model" not in row:
            row["prop_model"] = model
        out.append(row)
    return out


def save_prop_analyze_point(
    assess_root: str | Path,
    row: dict,
    *,
    trial: int | None = None,
) -> Path:
    """Persist one Analyze (BEMT) point as ``design_<trial>/design.json``."""
    assess_root = Path(assess_root)
    assess_root.mkdir(parents=True, exist_ok=True)
    tid = int(trial if trial is not None else _next_assess_trial(assess_root))
    workdir = assess_root / f"design_{tid}"
    workdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": "prop_analyze",
        "trial": tid,
        "params": dict(row.get("params") or {}),
        "objectives": {
            "thrust_g": row.get("thrust_g"),
            "eff_g_per_w": row.get("eff_g_per_w"),
            "power_w": row.get("power_w"),
            "fm": row.get("fm"),
            "rel_dba": row.get("rel_dba"),
            "tip_mach": row.get("tip_mach"),
        },
        "feasible": True,
        "extra": {
            "source": "analyze",
            "n_blades": row.get("n_blades"),
            "prop_model": row.get("prop_model", ""),
            **dict(row.get("extra") or {}),
        },
    }
    path = workdir / "design.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_prop_analyze_points(assess_dirs: str | Path | Iterable[str | Path]) -> list[dict]:
    """Reload Analyze points from one or more ``cockpit_prop_assess`` trees."""
    if isinstance(assess_dirs, (str, Path)):
        assess_dirs = [assess_dirs]
    out: list[dict] = []
    used: set[int] = set()

    def _fresh() -> int:
        i = 9000
        while i in used:
            i += 1
        used.add(i)
        return i

    for assess_dir in assess_dirs:
        assess_dir = Path(assess_dir)
        if not assess_dir.exists():
            continue
        for jf in sorted(assess_dir.glob("design_*/design.json")):
            try:
                d = json.loads(jf.read_text(encoding="utf-8"))
                orig = int(d.get("trial", 9000))
                if orig in used:
                    tid = _fresh()
                else:
                    tid = orig
                    used.add(tid)
                objs = d.get("objectives") or {}
                extra = dict(d.get("extra") or {})
                params = dict(d.get("params") or {})
                row = {
                    "thrust_g": objs.get("thrust_g"),
                    "eff_g_per_w": objs.get("eff_g_per_w"),
                    "power_w": objs.get("power_w"),
                    "fm": objs.get("fm"),
                    "n_blades": extra.get("n_blades") or params.get("n_blades"),
                    "rel_dba": objs.get("rel_dba"),
                    "tip_mach": objs.get("tip_mach"),
                    "params": params,
                    "source": "analyze",
                    "source_run": assess_dir.name,
                    "trial": tid,
                    "prop_model": extra.get("prop_model", ""),
                }
                if tid != orig:
                    row["orig_trial"] = orig
                out.append(row)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "skip corrupt prop assess design.json %s: %s: %s",
                    jf, type(exc).__name__, exc)
                continue
    return out


def load_all_prop_results(runs_root: str | Path) -> list[dict]:
    """Merge Optimize fronts + Analyze points under ``runs/`` for the prop scatter."""
    runs_root = Path(runs_root)
    merged: list[dict] = []
    if runs_root.exists():
        for d in sorted(runs_root.glob(PROP_RUN_GLOB)):
            if d.is_dir():
                merged.extend(load_prop_pareto(d))
        assess = runs_root / PROP_ASSESS_DIRNAME
        if assess.exists():
            merged.extend(load_prop_analyze_points(assess))
    return merge_prop_rows(merged)


def merge_prop_rows(rows: Iterable[dict]) -> list[dict]:
    """Dedupe by (source, params fingerprint); keep first occurrence; sort by thrust desc."""
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        if not isinstance(r, dict) or r.get("thrust_g") is None:
            continue
        key = _row_key(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(r))
    out.sort(key=lambda r: -float(r["thrust_g"]))
    return out


def prop_row_from_bemt(
    *,
    params_flat: dict,
    thrust_g: float,
    eff_g_per_w: float,
    power_w: float,
    fm: float,
    rel_dba: float | None = None,
    tip_mach: float | None = None,
    prop_model: str = "",
    n_blades: int | None = None,
) -> dict[str, Any]:
    """Build one scatter row from an Analyze BEMT readout."""
    return {
        "thrust_g": float(thrust_g),
        "eff_g_per_w": float(eff_g_per_w),
        "power_w": float(power_w),
        "fm": float(fm),
        "n_blades": int(n_blades if n_blades is not None else params_flat.get("n_blades", 0)),
        "rel_dba": None if rel_dba is None else float(rel_dba),
        "tip_mach": None if tip_mach is None else float(tip_mach),
        "params": dict(params_flat),
        "source": "analyze",
        "prop_model": prop_model,
    }


def _next_assess_trial(assess_root: Path) -> int:
    used = set()
    for p in assess_root.glob("design_*"):
        try:
            used.add(int(p.name.split("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    i = 9000
    while i in used:
        i += 1
    return i


def _row_key(r: dict) -> str:
    src = str(r.get("source") or "")
    p = r.get("params") or {}
    try:
        blob = json.dumps(p, sort_keys=True, default=str)
    except Exception:  # noqa: BLE001
        blob = str(p)
    return f"{src}|{blob}"
