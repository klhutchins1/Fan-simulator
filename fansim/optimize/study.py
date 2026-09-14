# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Optuna multi-objective study (NSGA-II) over the blade design vector.

Each trial: sample a design -> evaluate_candidate (gates + CFD at two operating points) ->
report (cfm_free, cfm_load, efficiency). Infeasible designs return large-negative objectives
so the sampler learns to avoid them. The study is backed by SQLite so it is resumable.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import optuna

from fansim.geometry.blade import BladeParams
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import (
    OBJECTIVE_DIRECTIONS,
    OBJECTIVE_NAMES,
    suggest_features,
    suggest_params,
)

optuna.logging.set_verbosity(optuna.logging.WARNING)


def make_study(study_name: str, storage: str, seed: int | None = 42,
               directions=None) -> optuna.Study:
    sampler = optuna.samplers.NSGAIISampler(seed=seed, population_size=16)
    return optuna.create_study(
        study_name=study_name,
        storage=storage,
        sampler=sampler,
        directions=list(directions) if directions is not None else list(OBJECTIVE_DIRECTIONS),
        load_if_exists=True,
    )


def run_study(
    n_trials: int,
    out_dir: str | Path,
    study_name: str = "fansim",
    procs: int = 8,
    base_cell: float = 0.005,
    iters: int = 1000,
    load_pa: float = 1.0,
    with_features: bool = False,
    base_params: BladeParams | None = None,
    space: str = "open",
    with_spacing: bool = False,
    with_extended: bool = False,
    min_sol_mid: float | None = None,
    min_sol_tip: float | None = None,
    with_noise: bool = False,
    noise_model: str = "loading",
    fan_model: str = "a12x25",
    mountable: bool = False,
    with_winglet: bool = False,
    bem_prescreen_cfm: float = 0.0,
    tip_gap_mm: float | None = None,
    surrogate_prescreen_cfm: float = 0.0,
    surrogate_db: str | Path | None = None,
    surrogate_boost: bool = False,
    on_trial=None,
) -> optuna.Study:
    from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
    spec = get_fan_spec(fan_model)
    # Frame-aware blade length: the built tip dia bulges ~4 mm past 2*tip_radius, so cap the sampled
    # tip_radius at frame_max/2 - 4 so designs land INSIDE the frame instead of getting gated on dia.
    max_tip_radius = spec.tip_dia_mm[1] / 2.0 - 4.0
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    storage = f"sqlite:///{(out_dir / 'study.db').as_posix()}"
    directions = list(OBJECTIVE_DIRECTIONS) + (["minimize"] if with_noise else [])
    study = make_study(study_name, storage, directions=directions)

    # --mountable: sample the hub radius in [motor-mount minimum, hub-diameter max/2] so every design
    # can actually house the motor (and gate any that slip through). Needs a fan model with a motor_mount.
    hub_range = None
    if mountable:
        lo = mount_min_hub_radius(spec)
        if lo is None:
            raise SystemExit(f"--mountable: fan model '{fan_model}' has no motor_mount defined.")
        hi = max(lo + 0.1, spec.hub_dia_mm[1] / 2.0)
        hub_range = (lo, hi)

    surrogate = None
    surrogate_load = None
    surr_free_xy: list = [None, None]
    surr_load_xy: list = [None, None]
    # Mutable cells so the trial closure can rebind models after online refit.
    surr_models: list = [None, None]  # [free, load]
    if surrogate_prescreen_cfm > 0.0:
        from fansim.catalog import CATALOG_DB
        from fansim.surrogate.catalog import prescreen_fit
        db = Path(surrogate_db) if surrogate_db is not None else CATALOG_DB
        surrogate, Xf, yf, why = prescreen_fit(db, boost=surrogate_boost)
        if surrogate is None:
            print(f"surrogate-prescreen: free off ({why})")
        else:
            surr_free_xy[0], surr_free_xy[1] = Xf, yf
            surr_models[0] = surrogate
            if why:
                print(f"surrogate-prescreen: free ({why})")
            elif surrogate_boost:
                print("surrogate-prescreen: free boost+GP ensemble")
        surrogate_load, Xl, yl, why_load = prescreen_fit(
            db, y_attr="cfm_load", require_k=True, boost=surrogate_boost)
        if surrogate_load is None:
            print(f"surrogate-prescreen: load off ({why_load})")
        else:
            surr_load_xy[0], surr_load_xy[1] = Xl, yl
            surr_models[1] = surrogate_load
            if why_load:
                print(f"surrogate-prescreen: load ({why_load})")
            elif surrogate_boost:
                print("surrogate-prescreen: load boost+GP ensemble")

    def objective(trial: optuna.Trial):
        if base_params is not None:
            # Feature-isolation study: fix the base geometry, vary only the feature layer.
            params = copy.deepcopy(base_params)
            params.features = suggest_features(trial)
        else:
            params = suggest_params(trial, with_features=with_features, space=space,
                                    with_spacing=with_spacing, with_extended=with_extended,
                                    hub_radius_range=hub_range, with_winglet=with_winglet,
                                    max_tip_radius=max_tip_radius)
        workdir = out_dir / "trials" / f"trial_{trial.number:04d}"
        result = evaluate_candidate(params, workdir, procs=procs, base_cell=base_cell,
                                    iters=iters, load_pa=load_pa,
                                    min_sol_mid=min_sol_mid, min_sol_tip=min_sol_tip,
                                    with_noise=with_noise, noise_model=noise_model, spec=spec,
                                    require_mountable=mountable, bem_prescreen_cfm=bem_prescreen_cfm,
                                    tip_gap_mm=tip_gap_mm,
                                    surrogate_prescreen_cfm=surrogate_prescreen_cfm,
                                    surrogate=surr_models[0], surrogate_load=surr_models[1])
        # Online GP update (§7.4): teach the in-memory screen from this study's CFD.
        if result.feasible and surrogate_prescreen_cfm > 0.0:
            try:
                from fansim.surrogate.catalog import append_and_refit
                from fansim.surrogate.features import feature_vector
                x = feature_vector(params)
                if (surr_models[0] is not None and surr_free_xy[0] is not None
                        and result.cfm_free > -1e5):
                    surr_models[0], surr_free_xy[0], surr_free_xy[1] = append_and_refit(
                        surr_models[0], surr_free_xy[0], surr_free_xy[1], x, result.cfm_free)
                if (surr_models[1] is not None and surr_load_xy[0] is not None
                        and result.raw.get("k") is not None
                        and result.cfm_load > -1e5):
                    surr_models[1], surr_load_xy[0], surr_load_xy[1] = append_and_refit(
                        surr_models[1], surr_load_xy[0], surr_load_xy[1],
                        x, result.cfm_load)
            except Exception:  # noqa: BLE001 - online update must never break the study
                pass
        trial.set_user_attr("feasible", result.feasible)
        trial.set_user_attr("reason", result.reason)
        trial.set_user_attr("n_blades", params.n_blades)
        trial.set_user_attr("runtime_s", result.runtime_s)
        if with_noise:
            trial.set_user_attr("noise_swl", result.noise_swl)
        if result.raw:
            (workdir / "result.json").write_text(
                json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        if on_trial:
            on_trial(trial, params, result)
        return result.as_tuple(with_noise=with_noise)

    study.optimize(objective, n_trials=n_trials)
    return study


def pareto_summary(study: optuna.Study) -> list[dict]:
    """Feasible best-trials on the Pareto front, as plain dicts."""
    rows = []
    for t in study.best_trials:
        if not t.user_attrs.get("feasible", False):
            continue
        names = OBJECTIVE_NAMES + (("noise_swl",) if len(t.values) == 4 else ())
        shroud = float(t.user_attrs.get("shroud_thick_mm", 0.0) or 0.0)
        params = dict(t.params)
        params.setdefault("shroud_thick_mm", shroud)  # --shroud stamps after sampling; carry it in params
        rows.append({
            "trial": t.number,
            "n_blades": t.user_attrs.get("n_blades"),
            **{name: round(val, 2) for name, val in zip(names, t.values)},
            "shroud_thick_mm": shroud,
            "params": params,
        })
    return rows
