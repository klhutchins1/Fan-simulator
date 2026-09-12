"""Build ``scripts/run_optimization.py`` argv for the cockpit (roadmap §8.3)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

OPT_TRIAL_OFFSET = 20000  # cockpit-merged trial ids, so they miss the opened study


def _script() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "run_optimization.py"


def opt_out_path(*, resume: bool, run_dir: str | Path, stamp: str | None = None) -> Path:
    """Where Optimize writes: new cockpit_opt_* folder, or the opened run when resuming."""
    if resume:
        return Path(run_dir)
    tag = stamp if stamp is not None else datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("runs") / f"cockpit_opt_{tag}"


def merge_opt_designs(
    loaded,
    *,
    source_run: str,
    existing_keys: set[tuple[str, int]],
    offset: int = OPT_TRIAL_OFFSET,
    plottable_only: bool = True,
) -> list:
    """Return NEW designs with trial += offset; skip keys already in ``existing_keys``.

    Mutates ``existing_keys`` by adding accepted (source_run, orig_trial) pairs.
    Each returned design gets ``extra`` stamps for merge provenance.

    When ``plottable_only`` (default), skip infeasible / sentinel CFM (-1e6) rows so they
    never land on the cockpit scatter and blow up the axes.
    """
    from fansim.optimize.design import Design
    from fansim.optimize.search_space import OBJECTIVE_NAMES

    out: list = []
    for d in loaded:
        orig = int(d.trial)
        key = (source_run, orig)
        if key in existing_keys:
            continue
        if plottable_only:
            cfm0 = float(d.objectives.get(OBJECTIVE_NAMES[0], -1e9))
            if (not d.feasible) or cfm0 <= -1e5:
                existing_keys.add(key)  # don't revisit
                continue
        existing_keys.add(key)
        nd = Design(
            trial=orig + offset,
            params=dict(d.params),
            objectives=dict(d.objectives),
            feasible=d.feasible,
            is_pareto=d.is_pareto,
            stl_path=d.stl_path,
            reason=d.reason,
            extra=dict(d.extra or {}),
        )
        nd.extra["orig_trial"] = orig
        nd.extra["source_run"] = source_run
        nd.extra["source"] = "cockpit_opt"
        out.append(nd)
    return out


def optimization_argv(
    *,
    trials: int,
    out: str | Path,
    fan_model: str,
    preset: str,
    refine_op: bool,
    shroud: bool,
    bem_floor: float,
    gp_floor: float,
    space: str = "guided",
    mountable: bool = True,
    study_name: str | None = None,
    gp_boost: bool = False,
    stator: bool = False,
    stator_stack: bool = False,
    sickle: bool = False,
    stepped_inlet: bool = False,
    notched_tips: bool = False,
) -> list[str]:
    """CLI vector for a fan NSGA-II study. No Docker; the caller spawns this."""
    if stator and stator_stack:
        raise ValueError("cannot combine stator and stator_stack")
    argv = [
        sys.executable,
        str(_script()),
        "--trials", str(int(trials)),
        "--out", str(out),
        "--fan-model", str(fan_model),
        "--space", str(space),
    ]
    if mountable:
        argv.append("--mountable")
    if preset and preset != "legacy":
        argv.extend(["--preset", str(preset)])
    if refine_op:
        argv.append("--refine-op")
    if shroud:
        argv.append("--shroud")
    if float(bem_floor) > 0:
        argv.extend(["--bem-prescreen", f"{float(bem_floor):g}"])
    if float(gp_floor) > 0:
        argv.extend(["--surrogate-prescreen", f"{float(gp_floor):g}"])
        if gp_boost:
            argv.append("--surrogate-boost")
    if study_name:
        argv.extend(["--study-name", str(study_name)])
    if stator_stack:
        argv.append("--stator-stack")
    elif stator:
        argv.append("--stator")
    if sickle:
        argv.append("--sickle")
    if stepped_inlet:
        argv.append("--stepped-inlet")
    if notched_tips:
        argv.append("--notched-tips")
    return argv
