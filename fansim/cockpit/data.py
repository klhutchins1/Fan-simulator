"""Load an optimization study's designs (params, objectives, STL) for the cockpit."""

from __future__ import annotations

from pathlib import Path

import optuna

# Canonical Design lives in optimize/ (Cursor 09-11 move). Re-export for cockpit callers.
from fansim.cfd.metrics import CFD_VERSION
from fansim.optimize.design import Design
from fansim.optimize.search_space import OBJECTIVE_NAMES


def _study_storage(out_dir: Path) -> str:
    return f"sqlite:///{(out_dir / 'study.db').as_posix()}"


def cfd_is_stale(cfd_version) -> bool:
    """True when a stored score predates the current solver generation (CFD_VERSION).

    Unstamped (None) trials are pre-2026-09-18 (final-sample metrics + coarse mesh) → stale.
    """
    try:
        return int(cfd_version) < CFD_VERSION
    except (TypeError, ValueError):
        return True


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
                   "runtime_s": t.user_attrs.get("runtime_s"),
                   "cfd_version": t.user_attrs.get("cfd_version"),
                   "cfd_stale": cfd_is_stale(t.user_attrs.get("cfd_version"))},
        ))
    return designs


def feasible_designs(designs: list[Design]) -> list[Design]:
    return [d for d in designs if d.feasible and d.objectives[OBJECTIVE_NAMES[0]] > -1e5]


def design_dropdown_items(rows, *, by_index: bool = False) -> list[dict]:
    """Build ``[{title, value}]`` for an archetype Results "previous runs" dropdown.

    ``rows`` are the tab's design-store dicts (``trial`` + ``objectives`` + optional ``extra``).
    ``value`` is the trial number (mixed/volute load by trial) or the list index when
    ``by_index`` (cror/prop load by click index). Marks stale (old-solver) scores with ⧗.
    """
    items: list[dict] = []
    for i, r in enumerate(rows or []):
        obj = r.get("objectives") or {}
        bits = []
        for key, lab in (("cfm_free", "free"), ("cfm_load", "load"), ("efficiency", "η"),
                         ("fm", "FM"), ("thrust_n", "T"), ("swl_dba", "dBA")):
            v = obj.get(key)
            if isinstance(v, (int, float)):
                bits.append(f"{lab} {v:.1f}")
        t = r.get("trial")
        head = f"#{t}" if t is not None else f"#{i}"
        stale = " ⧗" if (r.get("extra") or {}).get("cfd_stale") else ""
        title = head + stale + (" · " + " · ".join(bits) if bits else "")
        value = i if by_index else (int(t) if t is not None else i)
        items.append({"title": title, "value": value})
    return items
