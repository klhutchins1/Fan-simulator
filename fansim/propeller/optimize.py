# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Propeller optimizer — auto-design a prop's blade for a size/RPM envelope.

Because BEMT is instant (no CFD), a full multi-objective search runs in SECONDS. It fixes the envelope
(diameter, RPM, hub from the PropSpec) and searches the BLADE: pitch, planform (chord distribution),
blade count, camber — maximizing THRUST and EFFICIENCY (g/W) at once. Those two fight (aggressive
high-pitch wide blades push more air but sip more watts), so the result is a Pareto front: pick the
point that suits the mission (punchy freestyle vs efficient long-range).
"""

from __future__ import annotations

import dataclasses

import optuna

from fansim.geometry.blade import BladeParams
from fansim.prop_spec import PropSpec
from fansim.propeller.bemt import PropPerf, analyze
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.noise import estimate_prop_noise

optuna.logging.set_verbosity(optuna.logging.WARNING)


def suggest_prop(trial, spec: PropSpec) -> BladeParams:
    """Sample a prop blade for ``spec``'s envelope: blade count, pitch, planform, camber."""
    n_blades = trial.suggest_int("n_blades", 2, 4)
    pitch_in = trial.suggest_float("pitch_in", spec.pitch_in * 0.6, spec.pitch_in * 1.4)
    cr = trial.suggest_float("chord_root", 0.10, 0.26)
    cm = trial.suggest_float("chord_mid", 0.14, 0.30)
    ct = trial.suggest_float("chord_tip", 0.05, 0.16)
    camber = trial.suggest_float("camber", 0.02, 0.055)
    s2 = dataclasses.replace(spec, n_blades=n_blades, pitch_in=pitch_in)
    return prop_blade_params(s2, chord_frac=(cr, cm, ct), camber=camber)


def evaluate_prop(params: BladeParams, spec: PropSpec) -> PropPerf:
    return analyze(params, rpm=spec.rpm_max)


def bemt_thrust_g(params: BladeParams, spec: PropSpec, *, rpm: float | None = None) -> float:
    """Static BEMT thrust in grams at ``rpm`` (default ``spec.rpm_max``)."""
    perf = analyze(params, rpm=float(spec.rpm_max if rpm is None else rpm))
    return float(perf.thrust_g)


def blade_params_from_trial_params(spec: PropSpec, p: dict) -> BladeParams:
    """Rebuild a prop BladeParams from an Optuna / Pareto flat params dict."""
    s2 = dataclasses.replace(spec, n_blades=int(p["n_blades"]), pitch_in=float(p["pitch_in"]))
    return prop_blade_params(
        s2,
        chord_frac=(float(p["chord_root"]), float(p["chord_mid"]), float(p["chord_tip"])),
        camber=float(p["camber"]),
    )


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
    """NSGA-II over the prop blade, maximizing (thrust_g, efficiency_g_per_w). ``max_power_w`` (the
    motor's budget) gates designs that draw more than the motor can give, so the front is realistic.
    Returns (study, pareto). Optional ``out_dir`` persists Optuna SQLite + ``pareto.json``."""
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
            return 0.0, 0.0                       # over the motor budget -> not a real option
        trial.set_user_attr("thrust_g", perf.thrust_g)
        trial.set_user_attr("eff", perf.efficiency_g_per_w)
        trial.set_user_attr("power_w", perf.power_w)
        trial.set_user_attr("fm", perf.figure_of_merit)
        trial.set_user_attr("n_blades", params.n_blades)
        noise = estimate_prop_noise(params, spec.rpm_max, perf)   # relative noise (for thrust-vs-noise)
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
