"""CROR depth helpers + fast NSGA screen (roadmap §4.2 leftovers, stage 1).

Dual-MRF CFD stays the honesty path. This module (1) thins the stack toward a 25 mm
frame envelope and (2) runs an Optuna NSGA on geometry using a **crude BEM proxy**
(front+rear axial ``fan_bem``-style via prop BEMT on each rotor) so hundreds of trials
are cheap. CFD refine remains separate.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import optuna

from fansim.cror.geometry import CrorParams, cror_axial_layout_mm
from fansim.geometry.blade import BladeParams, RadialStation
from fansim.propeller.bemt import analyze

optuna.logging.set_verbosity(optuna.logging.WARNING)


def cror_stack_depth_mm(params: CrorParams | None = None) -> float:
    layout = cror_axial_layout_mm(params)
    return float(layout["hub_z1_mm"] - layout["hub_z0_mm"])


def _scale_blade_chords(blade: BladeParams, scale: float) -> BladeParams:
    stations = [
        RadialStation(
            s.r_frac,
            float(s.chord) * scale,
            s.stagger_deg,
            thickness=s.thickness,
            max_camber=s.max_camber,
        )
        for s in blade.stations
    ]
    return replace(blade, stations=stations)


def thin_cror_for_frame(
    params: CrorParams | None = None,
    *,
    max_depth_mm: float = 25.0,
    min_gap_mm: float = 2.0,
) -> CrorParams:
    """Shrink chords + gap until stack depth ≤ ``max_depth_mm`` (25 mm A12x25 class)."""
    p = deepcopy(params or CrorParams())
    for _ in range(24):
        depth = cror_stack_depth_mm(p)
        if depth <= float(max_depth_mm) + 1e-6:
            return p
        scale = max(0.55, float(max_depth_mm) / max(depth, 1e-6))
        p.front = _scale_blade_chords(p.front, scale)
        p.rear = _scale_blade_chords(p.rear, scale)
        p.axial_gap_mm = max(float(min_gap_mm), float(p.axial_gap_mm) * scale)
        # re-apply opposite swirl policy
        for s in p.rear.stations:
            s.stagger_deg = -abs(float(s.stagger_deg))
        for s in p.front.stations:
            s.stagger_deg = abs(float(s.stagger_deg))
    return p


def _proxy_perf(params: CrorParams, rpm: float) -> dict:
    """Crude dual-rotor screen: BEMT each rotor at ``rpm``; sum thrust, sum power."""
    front = analyze(params.front, rpm=rpm)
    rear = analyze(params.rear, rpm=rpm)
    thrust_g = front.thrust_g + rear.thrust_g
    power_w = front.power_w + rear.power_w
    eff = thrust_g / power_w if power_w > 0 else 0.0
    return {
        "thrust_g": thrust_g,
        "power_w": power_w,
        "eff_g_per_w": eff,
        "depth_mm": cror_stack_depth_mm(params),
    }


def suggest_cror(trial, *, tip_radius: float = 55.0, hub_radius: float = 18.0) -> CrorParams:
    gap = trial.suggest_float("axial_gap_mm", 2.0, 10.0)
    n_f = trial.suggest_int("n_front", 5, 9)
    n_r = trial.suggest_int("n_rear", 5, 11)
    stag = trial.suggest_float("stagger_deg", 28.0, 48.0)
    chord = trial.suggest_float("chord_mm", 10.0, 18.0)

    def stations(sign: float) -> list[RadialStation]:
        s = sign * stag
        return [
            RadialStation(0.0, chord, s, thickness=0.10, max_camber=0.04),
            RadialStation(0.5, chord, s * 0.9, thickness=0.08, max_camber=0.04),
            RadialStation(1.0, chord * 0.75, s * 0.8, thickness=0.06, max_camber=0.04),
        ]

    front = BladeParams(
        n_blades=n_f, hub_radius=hub_radius, tip_radius=tip_radius,
        stations=stations(+1.0),
    )
    rear = BladeParams(
        n_blades=n_r, hub_radius=hub_radius, tip_radius=tip_radius,
        stations=stations(-1.0),
    )
    return CrorParams(front=front, rear=rear, axial_gap_mm=gap)


def run_cror_study(
    n_trials: int = 80,
    *,
    rpm: float = 2000.0,
    max_depth_mm: float = 25.0,
    seed: int = 0,
    tip_radius: float = 55.0,
):
    """NSGA-II: maximize (thrust_g, eff) subject to depth ≤ ``max_depth_mm`` via soft gate."""
    study = optuna.create_study(
        directions=["maximize", "maximize"],
        sampler=optuna.samplers.NSGAIISampler(seed=seed),
    )

    def objective(trial):
        params = suggest_cror(trial, tip_radius=tip_radius)
        params = thin_cror_for_frame(params, max_depth_mm=max_depth_mm)
        perf = _proxy_perf(params, rpm)
        if perf["depth_mm"] > max_depth_mm + 0.5:
            trial.set_user_attr("feasible", False)
            trial.set_user_attr(
                "reason",
                f"depth {perf['depth_mm']:.1f} mm > max {max_depth_mm:.1f} mm",
            )
            raise optuna.TrialPruned()  # §11.5 — never invent a (0, 0) NSGA point
        trial.set_user_attr("feasible", True)
        trial.set_user_attr("thrust_g", perf["thrust_g"])
        trial.set_user_attr("eff", perf["eff_g_per_w"])
        trial.set_user_attr("depth_mm", perf["depth_mm"])
        trial.set_user_attr("power_w", perf["power_w"])
        return perf["thrust_g"], perf["eff_g_per_w"]

    study.optimize(objective, n_trials=n_trials)
    pareto = [
        {
            "thrust_g": t.values[0],
            "eff_g_per_w": t.values[1],
            "depth_mm": t.user_attrs.get("depth_mm"),
            "power_w": t.user_attrs.get("power_w"),
            "params": t.params,
        }
        for t in study.best_trials
    ]
    pareto.sort(key=lambda r: -r["thrust_g"])
    return study, pareto


def cror_params_from_trial_params(
    p: dict,
    *,
    tip_radius: float = 55.0,
    hub_radius: float = 18.0,
) -> CrorParams:
    """Rebuild ``CrorParams`` from Optuna trial params (same keys as ``suggest_cror``)."""
    gap = float(p["axial_gap_mm"])
    n_f = int(p["n_front"])
    n_r = int(p["n_rear"])
    stag = float(p["stagger_deg"])
    chord = float(p["chord_mm"])

    def stations(sign: float) -> list:
        from fansim.geometry.blade import RadialStation
        s = sign * stag
        return [
            RadialStation(0.0, chord, s, thickness=0.10, max_camber=0.04),
            RadialStation(0.5, chord, s * 0.9, thickness=0.08, max_camber=0.04),
            RadialStation(1.0, chord * 0.75, s * 0.8, thickness=0.06, max_camber=0.04),
        ]

    from fansim.geometry.blade import BladeParams
    front = BladeParams(
        n_blades=n_f, hub_radius=hub_radius, tip_radius=tip_radius,
        stations=stations(+1.0),
    )
    rear = BladeParams(
        n_blades=n_r, hub_radius=hub_radius, tip_radius=tip_radius,
        stations=stations(-1.0),
    )
    return thin_cror_for_frame(
        CrorParams(front=front, rear=rear, axial_gap_mm=gap),
    )


def refine_pareto_cfd(
    pareto: list[dict],
    out_dir: str | Path,
    *,
    n_top: int,
    tip_radius: float = 55.0,
    **eval_kw,
) -> list[dict]:
    """Dual-MRF CFD-refine the top N CROR Pareto rows (proxy screen → honesty check).

    Monkeypatch ``fansim.cror.evaluate.evaluate_cror`` in tests to avoid Docker.
    """
    from pathlib import Path

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for i, row in enumerate(pareto[: int(n_top)]):
        params = cror_params_from_trial_params(row["params"], tip_radius=tip_radius)
        workdir = out_dir / f"rank_{i:02d}"
        from fansim.cror.evaluate import evaluate_cror

        res = evaluate_cror(params, workdir, **eval_kw)
        rec = {
            "rank": int(i),
            "workdir": str(workdir),
            "feasible": bool(getattr(res, "feasible", False)),
            "bemt_proxy_thrust_g": row.get("thrust_g"),
            "depth_mm": row.get("depth_mm"),
            "reason": getattr(res, "reason", "") or "",
        }
        if getattr(res, "feasible", False):
            rec["cfm_free"] = float(res.cfm_free)
            rec["cfm_load"] = float(res.cfm_load)
            rec["efficiency"] = float(res.efficiency)
        rows.append(rec)
    return rows
