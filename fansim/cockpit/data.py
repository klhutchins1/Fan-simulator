"""Load an optimization study's designs (params, objectives, STL) for the cockpit."""

from __future__ import annotations

from pathlib import Path

import optuna

# Canonical Design lives in optimize/ (Cursor 09-11 move). Re-export for cockpit callers.
from fansim.optimize.design import Design
from fansim.optimize.search_space import OBJECTIVE_NAMES


def _study_storage(out_dir: Path) -> str:
    return f"sqlite:///{(out_dir / 'study.db').as_posix()}"


def load_designs(out_dir: str | Path, study_name: str | None = None) -> list[Design]:
    """Read all completed trials from a run directory's Optuna study + trial STLs."""
    out_dir = Path(out_dir)
    storage = _study_storage(out_dir)
    if study_name is None:
        names = optuna.get_all_study_names(storage=storage)
        if not names:
            return []
        study_name = names[0]
    study = optuna.load_study(study_name=study_name, storage=storage)

    pareto_numbers = {t.number for t in study.best_trials
                      if t.user_attrs.get("feasible", False)}

    designs: list[Design] = []
    for t in study.trials:
        if t.state != optuna.trial.TrialState.COMPLETE or t.values is None:
            continue
        feasible = bool(t.user_attrs.get("feasible", False))
        objectives = {name: float(v) for name, v in zip(OBJECTIVE_NAMES, t.values)}
        stl = out_dir / "trials" / f"trial_{t.number:04d}" / "impeller.stl"
        params = dict(t.params)
        # --shroud stamps after Optuna sampling; carry into params for cockpit round-trip
        shroud = float(t.user_attrs.get("shroud_thick_mm", 0.0) or 0.0)
        params.setdefault("shroud_thick_mm", shroud)
        designs.append(Design(
            trial=t.number,
            params=params,
            objectives=objectives,
            feasible=feasible,
            is_pareto=t.number in pareto_numbers,
            stl_path=stl if stl.exists() else None,
            reason=t.user_attrs.get("reason", ""),
            extra={"n_blades": t.user_attrs.get("n_blades"),
                   "runtime_s": t.user_attrs.get("runtime_s")},
        ))
    return designs


def feasible_designs(designs: list[Design]) -> list[Design]:
    return [d for d in designs if d.feasible and d.objectives[OBJECTIVE_NAMES[0]] > -1e5]
