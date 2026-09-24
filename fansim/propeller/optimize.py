"""Propeller optimizer — auto-design a prop's blade for a size/RPM envelope.

Because BEMT is instant (no CFD), a full multi-objective search runs in SECONDS. It fixes the envelope
(diameter, RPM, hub from the PropSpec) and searches the BLADE: pitch, planform (chord distribution),
blade count, camber, thickness, and light 3-D shape — maximizing THRUST and EFFICIENCY (g/W).
"""

from __future__ import annotations

import dataclasses

import optuna

from fansim.geometry.blade import BladeParams
from fansim.prop_spec import PropSpec
from fansim.propeller.bemt import PropPerf, analyze
from fansim.propeller.noise import estimate_prop_noise
from fansim.propeller.params_io import prop_params_from_flat, spec_with_flat

optuna.logging.set_verbosity(optuna.logging.WARNING)


def suggest_prop(trial, spec: PropSpec) -> BladeParams:
    """Sample a prop blade for ``spec``'s envelope (§14.1 Design keys)."""
    n_blades = trial.suggest_int("n_blades", 2, 4)
    pitch_in = trial.suggest_float("pitch_in", spec.pitch_in * 0.6, spec.pitch_in * 1.4)
    flat = {
        "n_blades": n_blades,
        "pitch_in": pitch_in,
        "chord_root": trial.suggest_float("chord_root", 0.10, 0.26),
        "chord_mid": trial.suggest_float("chord_mid", 0.14, 0.30),
        "chord_tip": trial.suggest_float("chord_tip", 0.05, 0.16),
        "camber_root": trial.suggest_float("camber_root", 0.02, 0.055),
        "camber_mid": trial.suggest_float("camber_mid", 0.02, 0.055),
        "camber_tip": trial.suggest_float("camber_tip", 0.02, 0.055),
        "thickness_root": trial.suggest_float("thickness_root", 0.06, 0.12),
        "thickness_mid": trial.suggest_float("thickness_mid", 0.04, 0.09),
        "thickness_tip": trial.suggest_float("thickness_tip", 0.03, 0.07),
        "sweep_mid": trial.suggest_float("sweep_mid", 0.0, 6.0),
        "sweep_tip": trial.suggest_float("sweep_tip", 0.0, 10.0),
        "le_skew_mid": trial.suggest_float("le_skew_mid", 0.0, 6.0),
        "le_skew_tip": trial.suggest_float("le_skew_tip", 0.0, 12.0),
        "lean_tip": trial.suggest_float("lean_tip", 0.0, 15.0),
        "tip_round": trial.suggest_float("tip_round", 0.0, 0.6),
        "cylindrical_tip": True,
        "thick_mode": "tapered",
    }
    # Keep a legacy ``camber`` stamp = mid for older consumers.
    flat["camber"] = flat["camber_mid"]
    s2 = dataclasses.replace(spec, n_blades=n_blades, pitch_in=pitch_in)
    return prop_params_from_flat(s2, flat)


def evaluate_prop(params: BladeParams, spec: PropSpec) -> PropPerf:
    return analyze(params, rpm=spec.rpm_max)


def bemt_thrust_g(params: BladeParams, spec: PropSpec, *, rpm: float | None = None) -> float:
    """Static BEMT thrust in grams at ``rpm`` (default ``spec.rpm_max``)."""
    perf = analyze(params, rpm=float(spec.rpm_max if rpm is None else rpm))
    return float(perf.thrust_g)


def blade_params_from_trial_params(spec: PropSpec, p: dict) -> BladeParams:
    """Rebuild a prop BladeParams from an Optuna / Pareto flat params dict."""
    s2 = spec_with_flat(spec, p)
    return prop_params_from_flat(s2, p)


def refine_pareto_cfd(spec: PropSpec, pareto: list[dict], out_dir,
                      *, n_top: int = 1, bemt_floor_g: float = 0.0, **eval_kw) -> list[dict]:
    """Run CFD on the top-N Pareto rows (mocked in unit tests)."""
    from pathlib import Path

    from fansim.propeller.cfd import evaluate_prop_cfd

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for i, row in enumerate(list(pareto)[: max(0, int(n_top))]):
        params = blade_params_from_trial_params(spec, row["params"])
        workdir = out_dir / f"cfd_{i:02d}"
        result = evaluate_prop_cfd(
            spec, workdir, params=params, bemt_floor_g=float(bemt_floor_g), **eval_kw)
        rows.append({
            "rank": i,
            "workdir": str(workdir),
            "bemt_thrust_g": result.get("bemt_thrust_g"),
            "cfd_thrust_g": result.get("thrust_g"),
            "skipped": bool(result.get("skipped")),
            "reason": result.get("reason"),
            "params": row.get("params"),
        })
    return rows


_MISSIONS = ("thrust_efficiency", "quiet_thrust", "hover_endurance", "range")
_WORST_MIN = 1.0e6


def _mission_directions(mission: str) -> list[str]:
    if mission == "quiet_thrust":
        return ["maximize", "minimize"]
    if mission in ("thrust_efficiency", "hover_endurance", "range"):
        return ["maximize", "maximize"]
    raise ValueError(
        f"unknown mission {mission!r}; known: {', '.join(_MISSIONS)}"
    )


def _require_vehicle(mission: str, all_up_weight_n, n_rotors, battery_wh, cruise_mps, min_hover_minutes):
    if min_hover_minutes is not None and mission != "quiet_thrust":
        raise ValueError("min_hover_minutes is only valid for quiet_thrust")
    needs_vehicle = mission in ("hover_endurance", "range") or (
        mission == "quiet_thrust" and min_hover_minutes is not None
    )
    if not needs_vehicle:
        return
    if all_up_weight_n is None or float(all_up_weight_n) <= 0.0:
        raise ValueError(f"{mission} requires all_up_weight_n > 0")
    if n_rotors is None or int(n_rotors) < 1:
        raise ValueError(f"{mission} requires n_rotors >= 1")
    if battery_wh is None or float(battery_wh) <= 0.0:
        raise ValueError(f"{mission} requires battery_wh > 0")
    if mission == "range" and (cruise_mps is None or float(cruise_mps) <= 0.0):
        raise ValueError("range requires cruise_mps > 0")


def _worst(directions: list[str]) -> tuple[float, float]:
    return tuple(_WORST_MIN if d == "minimize" else 0.0 for d in directions)


def run_prop_study(spec: PropSpec, n_trials: int = 200, seed: int = 0,
                   max_power_w: float | None = None,
                   out_dir=None, prop_model: str | None = None,
                   mission: str = "thrust_efficiency",
                   all_up_weight_n: float | None = None,
                   n_rotors: int | None = None,
                   battery_wh: float | None = None,
                   cruise_mps: float | None = None,
                   min_hover_minutes: float | None = None):
    """NSGA-II over the prop blade. ``mission`` picks the two objectives."""
    from pathlib import Path

    from fansim.propeller.persist import pareto_rows_from_study

    _require_vehicle(mission, all_up_weight_n, n_rotors, battery_wh, cruise_mps, min_hover_minutes)
    directions = _mission_directions(mission)
    study_name = "prop" if mission == "thrust_efficiency" else f"prop_{mission}"
    worst = _worst(directions)

    storage = None
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        storage = f"sqlite:///{(out / 'study.db').as_posix()}"
        study = optuna.create_study(
            directions=directions,
            sampler=optuna.samplers.NSGAIISampler(seed=seed),
            storage=storage,
            study_name=study_name,
            load_if_exists=True,
        )
    else:
        study = optuna.create_study(
            directions=directions, sampler=optuna.samplers.NSGAIISampler(seed=seed))

    def _budget_minutes(shaft_power_w: float, tip_radius_mm: float) -> float:
        from fansim.propeller.power import hover_power_budget
        budget = hover_power_budget(
            all_up_weight_n=float(all_up_weight_n),
            n_rotors=int(n_rotors),
            tip_radius_m=float(tip_radius_mm) / 1000.0,
            figure_of_merit=0.7,
            battery_wh=float(battery_wh),
            shaft_power_w=float(shaft_power_w),
        )
        return float(budget["hover_minutes"])

    def objective(trial):
        params = suggest_prop(trial, spec)
        perf = evaluate_prop(params, spec)
        noise = estimate_prop_noise(params, spec.rpm_max, perf)
        hover_minutes = None
        range_km = None
        feasible = True
        if max_power_w is not None and perf.power_w > max_power_w:
            feasible = False
        lifts = True
        if mission in ("hover_endurance", "range") or min_hover_minutes is not None:
            lifts = perf.thrust_n * int(n_rotors) >= float(all_up_weight_n)
            if not lifts:
                feasible = False
            else:
                hover_minutes = _budget_minutes(perf.power_w, params.tip_radius)
                if min_hover_minutes is not None and hover_minutes < float(min_hover_minutes):
                    feasible = False
        if feasible and mission == "range":
            cruise = analyze(params, rpm=spec.rpm_max, v_forward=float(cruise_mps))
            range_km = float(cruise_mps) * _budget_minutes(cruise.power_w, params.tip_radius) * 0.06
        trial.set_user_attr("feasible", feasible)
        trial.set_user_attr("thrust_g", perf.thrust_g)
        trial.set_user_attr("eff", perf.efficiency_g_per_w)
        trial.set_user_attr("power_w", perf.power_w)
        trial.set_user_attr("fm", perf.figure_of_merit)
        trial.set_user_attr("n_blades", params.n_blades)
        trial.set_user_attr("rel_dba", noise["rel_dba"])
        trial.set_user_attr("tip_mach", noise["tip_mach"])
        trial.set_user_attr("hover_minutes", hover_minutes)
        trial.set_user_attr("range_km", range_km)
        trial.set_user_attr("mission", mission)
        if not feasible:
            return worst
        if mission == "quiet_thrust":
            return perf.thrust_g, noise["rel_dba"]
        if mission == "hover_endurance":
            return hover_minutes, perf.thrust_g
        if mission == "range":
            return range_km, perf.thrust_g
        return perf.thrust_g, perf.efficiency_g_per_w

    study.optimize(objective, n_trials=n_trials)
    pareto = pareto_rows_from_study(study)
    if out_dir is not None:
        from fansim.propeller.persist import save_prop_pareto
        save_prop_pareto(Path(out_dir), pareto, prop_model=prop_model or getattr(spec, "name", None))
    return study, pareto
