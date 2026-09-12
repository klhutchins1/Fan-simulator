# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Load an optimization study's designs (params, objectives, STL) for the cockpit."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import optuna

from fansim.optimize.search_space import OBJECTIVE_NAMES


@dataclass
class Design:
    """One evaluated design: its parameters, objectives, and geometry file."""

    trial: int
    params: dict
    objectives: dict  # cfm_free, cfm_load, efficiency
    feasible: bool
    is_pareto: bool
    stl_path: Path | None
    reason: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def has_model(self) -> bool:
        return self.stl_path is not None and self.stl_path.exists()


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
        designs.append(Design(
            trial=t.number,
            params=dict(t.params),
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
