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


def run_prop_study(spec: PropSpec, n_trials: int = 200, seed: int = 0,
                   max_power_w: float | None = None):
    """NSGA-II over the prop blade, maximizing (thrust_g, efficiency_g_per_w). ``max_power_w`` (the
    motor's budget) gates designs that draw more than the motor can give, so the front is realistic.
    Returns (study, pareto)."""
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
    return study, pareto
