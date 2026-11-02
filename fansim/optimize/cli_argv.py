"""Build ``scripts/run_optimization.py`` argv for the cockpit (roadmap §8.3)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

OPT_TRIAL_OFFSET = 20000  # cockpit-merged trial ids, so they miss the opened study
OPT_RUN_STRIDE = 1000     # each cockpit_opt_* run gets its own id block (cockpit caps trials at 40)
OPT_RUN_PREFIX = "cockpit_opt_"


def cockpit_opt_dirs(runs_root: str | Path) -> list[Path]:
    """All ``runs/cockpit_opt_*`` folders, oldest first (folder names carry the start stamp)."""
    root = Path(runs_root)
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob(f"{OPT_RUN_PREFIX}*") if p.is_dir())


def opt_trial_offset(run_name: str, runs_root: str | Path) -> int:
    """Stable trial-id offset for one cockpit Optimize run.

    Runs are numbered by start stamp, so ids survive restarts and a new run (always the newest)
    never shifts the older ones. Two runs' trial 4 no longer collide on #20004.
    """
    names = sorted({p.name for p in cockpit_opt_dirs(runs_root)} | {str(run_name)})
    return OPT_TRIAL_OFFSET + names.index(str(run_name)) * OPT_RUN_STRIDE


def run_label(run_name: str) -> str:
    """Short human label: ``cockpit_opt_20261001-100133`` -> ``Opt 2026-10-01 10:01``."""
    name = str(run_name or "")
    if name.startswith(OPT_RUN_PREFIX):
        try:
            dt = datetime.strptime(name[len(OPT_RUN_PREFIX):], "%Y%m%d-%H%M%S")
            return f"Opt {dt:%Y-%m-%d %H:%M}"
        except ValueError:
            pass
    return name


def latest_opt_run(runs_root: str | Path) -> Path | None:
    """Newest cockpit Optimize run that has a study to continue, or None."""
    for p in reversed(cockpit_opt_dirs(runs_root)):
        if (p / "study.db").is_file():
            return p
    return None


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
        nd.extra["run_label"] = run_label(source_run)
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
    gp_nn: bool = False,
    stator: bool = False,
    stator_stack: bool = False,
    sickle: bool = False,
    stepped_inlet: bool = False,
    notched_tips: bool = False,
    search_rpm: bool = False,
    rpm_min: float | None = None,
    rpm_max: float | None = None,
    wall_ks_mm: float | None = None,
    material: str | None = None,
    surrogate_guided: bool = False,
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
        if gp_nn:
            argv.append("--surrogate-nn")
    if surrogate_guided:
        argv.append("--surrogate-guided")
        # Reuse boost/nn toggles for the guided loop even without a prescreen floor.
        if gp_boost and float(gp_floor) <= 0:
            argv.append("--surrogate-boost")
        if gp_nn and float(gp_floor) <= 0:
            argv.append("--surrogate-nn")
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
    if search_rpm:
        argv.append("--search-rpm")
        if rpm_min is not None:
            argv.extend(["--rpm-min", f"{float(rpm_min):g}"])
        if rpm_max is not None:
            argv.extend(["--rpm-max", f"{float(rpm_max):g}"])
    if wall_ks_mm is not None and float(wall_ks_mm) > 0:
        argv.extend(["--wall-ks-mm", f"{float(wall_ks_mm):g}"])
    if material:
        argv.extend(["--material", str(material)])
    return argv


def surrogate_guided_cli_error(*, guided: bool, verify_cfd: bool, stub_labels: bool) -> str | None:
    """Refuse an ungated stub rank. R1.11: synthetic labels are not CFD."""
    if guided and not verify_cfd and not stub_labels:
        return (
            "ERROR: --surrogate-guided needs --verify-cfd or --stub-labels "
            "(synthetic labels, not CFD)."
        )
    return None
