"""Load an optimization study's designs (params, objectives, STL) for the cockpit."""

from __future__ import annotations

import time
from pathlib import Path

import optuna

from fansim.optimize.design import Design
from fansim.optimize.search_space import OBJECTIVE_NAMES
from fansim.optimize.storage import make_sqlite_storage
from fansim.optimize.study import with_shroud_attr

__all__ = ["Design", "load_designs", "feasible_designs"]


def _study_storage(out_dir: Path):
    return make_sqlite_storage(out_dir)


def load_designs(out_dir: str | Path, study_name: str | None = None) -> list[Design]:
    """Read all completed trials from a run directory's Optuna study + trial STLs.

    Retries briefly on SQLite locks (cockpit poll vs Optimize writer).
    """
    out_dir = Path(out_dir)
    last_exc: Exception | None = None
    study = None
    for attempt in range(8):
        try:
            storage = _study_storage(out_dir)
            if study_name is None:
                names = optuna.get_all_study_names(storage=storage)
                if not names:
                    return []
                study_name = names[0]
            study = optuna.load_study(study_name=study_name, storage=storage)
            # Touch trials once inside the retry loop so lock errors surface here.
            _ = study.trials
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            msg = str(exc).lower()
            if "locked" not in msg and "e3q8" not in msg:
                raise
            time.sleep(0.25 * (attempt + 1))
    else:
        if last_exc is not None:
            raise last_exc
        return []

    assert study is not None
    try:
        pareto_numbers = {t.number for t in study.best_trials
                          if t.user_attrs.get("feasible", False)}
    except Exception:  # noqa: BLE001 — locked mid-read; skip Pareto stars
        pareto_numbers = set()

    designs: list[Design] = []
    for t in study.trials:
        if t.state != optuna.trial.TrialState.COMPLETE or t.values is None:
            continue
        feasible = bool(t.user_attrs.get("feasible", False))
        objectives = {name: float(v) for name, v in zip(OBJECTIVE_NAMES, t.values)}
        stl = out_dir / "trials" / f"trial_{t.number:04d}" / "impeller.stl"
        tip_gap = t.user_attrs.get("tip_gap_mm", None)
        casing_id = t.user_attrs.get("casing_id_mm", None)
        tip_gap_floor = t.user_attrs.get("tip_gap_floor_mm", None)
        frame_stl = t.user_attrs.get("frame_stl", None)
        duct = t.user_attrs.get("duct", None)
        k = t.user_attrs.get("k", None)
        dp_op_pa = t.user_attrs.get("dp_op_pa", None)
        q_ref_cfm = t.user_attrs.get("q_ref_cfm", None)
        designs.append(Design(
            trial=t.number,
            params=with_shroud_attr(t),
            objectives=objectives,
            feasible=feasible,
            is_pareto=t.number in pareto_numbers,
            stl_path=stl if stl.exists() else None,
            reason=t.user_attrs.get("reason", ""),
            extra={"n_blades": t.user_attrs.get("n_blades"),
                   "runtime_s": t.user_attrs.get("runtime_s"),
                   "tip_gap_mm": float(tip_gap) if tip_gap is not None else None,
                   "casing_id_mm": float(casing_id) if casing_id is not None else None,
                   "tip_gap_floor_mm": (
                       float(tip_gap_floor) if tip_gap_floor is not None else None),
                   "frame_stl": (bool(frame_stl) if frame_stl is not None else None),
                   "duct": (str(duct) if duct is not None else None),
                   "k": float(k) if k is not None else None,
                   "dp_op_pa": float(dp_op_pa) if dp_op_pa is not None else None,
                   "q_ref_cfm": float(q_ref_cfm) if q_ref_cfm is not None else None},
        ))
    return designs


def feasible_designs(designs: list[Design]) -> list[Design]:
    return [d for d in designs if d.feasible and d.objectives[OBJECTIVE_NAMES[0]] > -1e5]
