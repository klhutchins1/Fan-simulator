"""Load an optimization study's designs (params, objectives, STL) for the cockpit."""

from __future__ import annotations

from pathlib import Path

import optuna

# Canonical Design lives in optimize/ (Cursor 09-11 move). Re-export for cockpit callers.
from fansim.cfd.metrics import CFD_VERSION
from fansim.optimize.design import Design
from fansim.optimize.search_space import OBJECTIVE_NAMES
from fansim.optimize.trial_attrs import trial_flat


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


ASSESS_BASE_CELL_M = 0.006   # the Assess background cell the legacy floor was applied to


def coarse_mesh_stale(extra: dict | None, params: dict | None) -> bool:
    """True when an axial score was meshed below the current Assess floor (§23.39).

    New scores carry ``surf_max``. Older ones were floored at level 3, so they are coarse exactly
    when the design's thinnest wall maps to a level below the floor (thick walls, > ~2.25 mm),
    which scored 3-7 % high vs level 4. Thin designs were already at 4 and stay current.
    """
    from fansim.cfd.openfoam_case import ASSESS_SURF_MAX_FLOOR, surface_level_for_wall

    extra = extra or {}
    if extra.get("surf_max") is not None:
        return int(extra["surf_max"]) < ASSESS_SURF_MAX_FLOOR
    try:
        from fansim.geometry.blade import min_blade_wall_mm
        from fansim.optimize.search_space import blade_from_flat

        wall = min_blade_wall_mm(blade_from_flat(dict(params or {})))
    except Exception:  # noqa: BLE001 — not an axial flat dict: nothing to judge
        return False
    return surface_level_for_wall(ASSESS_BASE_CELL_M, wall) < ASSESS_SURF_MAX_FLOOR


HUB_CLIP_TOL_MM = 0.05


def below_hub_stale(extra: dict | None, params: dict | None) -> bool:
    """True when a score was computed on blades that reached below the hub face (pre-clip rule).

    Since 2026-10-09 fan blades are cut at the hub's motor face (the frame struts sit there); a
    design that hung lower now builds differently from what was scored. New scores stamp
    ``hub_clip``.
    """
    extra = extra or {}
    if extra.get("hub_clip"):
        return False
    if extra.get("hub_overhang_mm") is not None:   # exact, from scripts/stamp_hub_overhang.py
        return float(extra["hub_overhang_mm"]) > HUB_CLIP_TOL_MM
    try:  # section-point estimate (misses the loft's realised chords on 'measured' designs)
        from fansim.cockpit.placement import blade_overhang_below_hub_mm
        from fansim.optimize.search_space import blade_from_flat

        return blade_overhang_below_hub_mm(blade_from_flat(dict(params or {}))) > HUB_CLIP_TOL_MM
    except Exception:  # noqa: BLE001 — not an axial flat dict: nothing to judge
        return False


def scored_case_dir(d) -> Path | None:
    """The CFD case that produced a design's saved score.

    ``scripts/refresh_stale_designs.py`` re-scores a design in another run and records it as
    ``extra.case_dir`` (relative to ``runs/``), while the design folder keeps the OLD case's fields.
    Airflow pictures must come from the run behind the score, so use ``case_dir`` when it still
    exists, else the design's own folder.
    """
    stl = getattr(d, "stl_path", None)
    if not stl:
        return None
    own = Path(stl).parent
    rel = (getattr(d, "extra", None) or {}).get("case_dir")
    if rel:
        cand = Path(rel) if Path(rel).is_absolute() else own.parents[2] / rel
        if cand.is_dir():
            return cand
    return own


def stale_reason(extra: dict | None, params: dict | None) -> str:
    """'' when the score is current, else why it must be re-run ('old solver' / 'coarse mesh')."""
    extra = extra or {}
    if cfd_is_stale(extra.get("cfd_version")):
        return "old solver"
    if coarse_mesh_stale(extra, params):
        return "coarse mesh"
    if below_hub_stale(extra, params):
        return "blade below hub"
    if extra.get("motor_model_stale"):  # refine_op score made at the old motor derate (2026-10-10)
        return "old motor model"
    return ""


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
        params = trial_flat(t)
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
                   "source_run": out_dir.name,
                   "completed": (t.datetime_complete.strftime("%Y-%m-%d %H:%M")
                                 if t.datetime_complete else None),
                   "runtime_s": t.user_attrs.get("runtime_s"),
                   "cfd_version": t.user_attrs.get("cfd_version"),
                   "surf_max": t.user_attrs.get("surf_max"),
                   "converged": t.user_attrs.get("converged"),  # QA-65; None on old studies
                   "cfd_stale": bool(_reason := stale_reason(
                       {"cfd_version": t.user_attrs.get("cfd_version"),
                        "surf_max": t.user_attrs.get("surf_max"),
                        "hub_clip": t.user_attrs.get("hub_clip")}, params)),
                   "stale_reason": _reason},
        ))
    return designs


def load_saved_opt_designs(runs_root: str | Path, *, exclude: str | Path | None,
                           existing_keys: set[tuple[str, int]]) -> list[Design]:
    """Plottable trials from every saved ``runs/cockpit_opt_*`` study, merged for the cockpit.

    Lets Optimize results survive a cockpit restart. Each run keeps its own id block
    (``opt_trial_offset``). ``exclude`` is the opened run (already on the plot as the study);
    ``existing_keys`` is updated so live Optimize polling does not re-add these.
    """
    from fansim.optimize.cli_argv import cockpit_opt_dirs, merge_opt_designs, opt_trial_offset

    skip = Path(exclude).resolve() if exclude is not None else None
    out: list[Design] = []
    for run in cockpit_opt_dirs(runs_root):
        if skip is not None and run.resolve() == skip:
            continue
        if not (run / "study.db").is_file():
            continue
        try:
            loaded = load_designs(run)
        except Exception:  # noqa: BLE001 - a corrupt/empty study just stays off the plot
            continue
        out += merge_opt_designs(loaded, source_run=run.name, existing_keys=existing_keys,
                                 offset=opt_trial_offset(run.name, runs_root))
    return out


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
