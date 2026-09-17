"""Volute NSGA screen via a geometry proxy (roadmap §14.4b).

No BEM exists for radial blowers here. Objectives are **ranking-only** proxies
(``capacity_proxy``, ``head_proxy``) stamped ``volute_proxy=geometry`` — never claim
calibrated CFM. CFD Assess remains the honest score; Optimize is a Design search aid.
"""

from __future__ import annotations

import math
from pathlib import Path

import optuna

from fansim.volute.geometry import VoluteParams
from fansim.volute.params_io import volute_params_to_flat

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Fixed Optuna bounds (static space = resume-safe). Matches cockpit slider envelope.
_N_BLADES = (5, 11)
_R_HUB = (12.0, 28.0)
_R_TIP = (35.0, 60.0)
_BLADE_H = (12.0, 32.0)
_BLADE_THICK = (0.6, 2.5)
_BACKPLATE = (1.0, 4.0)
_SPIRAL = (10.0, 40.0)
_CLEARANCE = (1.0, 8.0)
_WALL = (1.0, 4.0)
_TONGUE_ANGLE = (2.0, 15.0)
_TONGUE_CLEAR = (0.5, 4.0)
_TONGUE_FILLET = (0.0, 4.0)
_OUT_W = (20.0, 50.0)
_OUT_L = (20.0, 60.0)
_OUT_H = (12.0, 40.0)

VOLUTE_PROXY_STAMP = "geometry"


def suggest_volute(trial) -> VoluteParams:
    """Sample Design knobs within the cockpit slider envelope (§14.4b)."""
    r_hub = float(trial.suggest_float("r_hub_mm", *_R_HUB))
    r_tip_lo = min(max(r_hub + 5.0, _R_TIP[0]), _R_TIP[1] - 0.5)
    r_tip = float(trial.suggest_float("r_tip_mm", r_tip_lo, _R_TIP[1]))
    return VoluteParams(
        n_blades=int(trial.suggest_int("n_blades", *_N_BLADES)),
        r_hub_mm=r_hub,
        r_tip_mm=r_tip,
        blade_height_mm=float(trial.suggest_float("blade_height_mm", *_BLADE_H)),
        blade_thick_mm=float(trial.suggest_float("blade_thick_mm", *_BLADE_THICK)),
        backplate_thick_mm=float(trial.suggest_float("backplate_thick_mm", *_BACKPLATE)),
        spiral_growth_mm=float(trial.suggest_float("spiral_growth_mm", *_SPIRAL)),
        volute_clearance_mm=float(trial.suggest_float("volute_clearance_mm", *_CLEARANCE)),
        volute_wall_mm=float(trial.suggest_float("volute_wall_mm", *_WALL)),
        tongue_angle_deg=float(trial.suggest_float("tongue_angle_deg", *_TONGUE_ANGLE)),
        tongue_tip_clearance_mm=float(
            trial.suggest_float("tongue_tip_clearance_mm", *_TONGUE_CLEAR)),
        tongue_fillet_mm=float(trial.suggest_float("tongue_fillet_mm", *_TONGUE_FILLET)),
        outlet_width_mm=float(trial.suggest_float("outlet_width_mm", *_OUT_W)),
        outlet_length_mm=float(trial.suggest_float("outlet_length_mm", *_OUT_L)),
        outlet_height_mm=float(trial.suggest_float("outlet_height_mm", *_OUT_H)),
    )


def volute_proxy_scores(params: VoluteParams, *, rpm: float) -> tuple[float, float]:
    """Return (capacity_proxy, head_proxy) — relative rank only, not CFM/Pa.

    Capacity ~ blade count × height × radial extent × tip speed.
    Head ~ spiral growth / tip clearance (collector diffusion stand-in).
    """
    omega = float(rpm) * (2.0 * math.pi / 60.0)
    tip_u = omega * (float(params.r_tip_mm) * 1e-3)  # m/s
    span = max(0.0, float(params.r_tip_mm) - float(params.r_hub_mm))
    capacity = (
        float(params.n_blades)
        * float(params.blade_height_mm)
        * span
        * max(tip_u, 1e-6)
    )
    head = float(params.spiral_growth_mm) / max(float(params.volute_clearance_mm), 0.5)
    return float(capacity), float(head)


def run_volute_study(
    *,
    n_trials: int = 80,
    seed: int = 0,
    rpm: float = 3000.0,
    out_dir: str | Path | None = None,
    study_name: str = "volute",
):
    """NSGA-II maximizing (capacity_proxy, head_proxy). Persists when ``out_dir`` is set.

    Returns (study, pareto_rows).
    """
    from fansim.volute.persist import save_volute_pareto, volute_opt_rows_from_study

    if out_dir is not None:
        from fansim.optimize.storage import make_sqlite_storage

        storage = make_sqlite_storage(out_dir)
        study = optuna.create_study(
            directions=["maximize", "maximize"],
            sampler=optuna.samplers.NSGAIISampler(seed=seed),
            storage=storage,
            study_name=study_name,
            load_if_exists=True,
        )
    else:
        study = optuna.create_study(
            directions=["maximize", "maximize"],
            sampler=optuna.samplers.NSGAIISampler(seed=seed),
        )

    def objective(trial):
        try:
            params = suggest_volute(trial)
            cap, head = volute_proxy_scores(params, rpm=float(rpm))
        except Exception as exc:  # noqa: BLE001
            trial.set_user_attr("feasible", False)
            trial.set_user_attr("reason", f"proxy failed: {type(exc).__name__}: {exc}")
            raise
        flat = volute_params_to_flat(params)
        trial.set_user_attr("feasible", True)
        trial.set_user_attr("reason", "")
        trial.set_user_attr("capacity_proxy", cap)
        trial.set_user_attr("head_proxy", head)
        trial.set_user_attr("params", flat)
        trial.set_user_attr("volute_proxy", VOLUTE_PROXY_STAMP)
        trial.set_user_attr("rpm", float(rpm))
        return cap, head

    study.optimize(objective, n_trials=int(n_trials), catch=(Exception,))
    pareto = volute_opt_rows_from_study(study)
    if out_dir is not None:
        save_volute_pareto(
            out_dir, pareto,
            meta={"n_trials": int(n_trials), "rpm": float(rpm),
                  "volute_proxy": VOLUTE_PROXY_STAMP},
        )
    return study, pareto
