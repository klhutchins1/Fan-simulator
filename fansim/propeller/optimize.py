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


def run_prop_study(spec: PropSpec, n_trials: int = 200, seed: int = 0,
                   max_power_w: float | None = None,
                   out_dir=None, prop_model: str | None = None):
    """NSGA-II over the prop blade, maximizing (thrust_g, efficiency_g_per_w)."""
    from pathlib import Path

    storage = None
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        storage = f"sqlite:///{(out / 'study.db').as_posix()}"
        study = optuna.create_study(
            directions=["maximize", "maximize"],
            sampler=optuna.samplers.NSGAIISampler(seed=seed),
            storage=storage,
            study_name="prop",
            load_if_exists=True,
        )
    else:
        study = optuna.create_study(directions=["maximize", "maximize"],
                                    sampler=optuna.samplers.NSGAIISampler(seed=seed))

    def objective(trial):
        params = suggest_prop(trial, spec)
        perf = evaluate_prop(params, spec)
        if max_power_w is not None and perf.power_w > max_power_w:
            return 0.0, 0.0
        trial.set_user_attr("thrust_g", perf.thrust_g)
        trial.set_user_attr("eff", perf.efficiency_g_per_w)
        trial.set_user_attr("power_w", perf.power_w)
        trial.set_user_attr("fm", perf.figure_of_merit)
        trial.set_user_attr("n_blades", params.n_blades)
        noise = estimate_prop_noise(params, spec.rpm_max, perf)
        trial.set_user_attr("rel_dba", noise["rel_dba"])
        trial.set_user_attr("tip_mach", noise["tip_mach"])
        return perf.thrust_g, perf.efficiency_g_per_w

    study.optimize(objective, n_trials=n_trials)
    pareto = [{"thrust_g": t.values[0], "eff_g_per_w": t.values[1],
               "power_w": t.user_attrs.get("power_w"), "fm": t.user_attrs.get("fm"),
               "n_blades": t.user_attrs.get("n_blades"), "rel_dba": t.user_attrs.get("rel_dba"),
               "tip_mach": t.user_attrs.get("tip_mach"), "params": t.params}
              for t in study.best_trials]
    pareto.sort(key=lambda r: -r["thrust_g"])
    if out_dir is not None:
        from fansim.propeller.persist import save_prop_pareto
        save_prop_pareto(Path(out_dir), pareto, prop_model=prop_model or getattr(spec, "name", None))
    return study, pareto
