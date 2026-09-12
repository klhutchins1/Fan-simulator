"""Mixed-flow NSGA screen via axial-adapter BEM (cockpit Optimize after §8.6).

Instant (no CFD). Objectives are BEM free-delivery CFM and system-curve op CFM —
same axes as the mixed Assess scatter. Stamp ``bem_adapter=axial``; do not claim
calibrated mixed-flow CFM. CFD Assess remains the honest score.
"""

from __future__ import annotations

from pathlib import Path

import optuna

from fansim.centrifugal.bem import mixed_to_blade_params
from fansim.centrifugal.geometry import MixedFlowParams
from fansim.centrifugal.params_io import mixed_flat_from_params
from fansim.fan_bem import DEFAULT_TIP_GAP_MM, pq_curve
from fansim.fan_spec import A12X25
from fansim.optimize.system_curve import bem_screen_cfm

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Fixed Optuna bounds (static space = resume-safe). Matches cockpit slider envelope
# with eye/back split so eye < back always holds.
_N_BLADES = (5, 13)
_R_EYE = (12.0, 22.0)
_R_BACK = (24.0, 35.0)
_R_TIP = (48.0, 54.5)
_Z_SPAN = (12.0, 22.0)
_CHORD = (14.0, 28.0)
_STAGGER = (20.0, 50.0)


def suggest_mixed(trial) -> MixedFlowParams:
    """Sample core mixed-flow knobs within the cockpit slider envelope."""
    return MixedFlowParams(
        n_blades=int(trial.suggest_int("n_blades", *_N_BLADES)),
        r_eye_mm=float(trial.suggest_float("r_eye_mm", *_R_EYE)),
        r_back_mm=float(trial.suggest_float("r_back_mm", *_R_BACK)),
        r_tip_mm=float(trial.suggest_float("r_tip_mm", *_R_TIP)),
        z_span_mm=float(trial.suggest_float("z_span_mm", *_Z_SPAN)),
        chord_mm=float(trial.suggest_float("chord_mm", *_CHORD)),
        stagger_deg=float(trial.suggest_float("stagger_deg", *_STAGGER)),
    )


def evaluate_mixed_bem(
    params: MixedFlowParams,
    *,
    rpm: float,
    load_pa: float,
    tip_gap_mm: float = DEFAULT_TIP_GAP_MM,
) -> tuple[float, float, float]:
    """Return (cfm_free, cfm_load, peak_efficiency_pct) via the axial BEM adapter."""
    blade = mixed_to_blade_params(params)
    q0, q_op = bem_screen_cfm(blade, rpm, load_pa, tip_gap_mm, stator=False)
    curve = pq_curve(blade, rpm, tip_gap_mm=tip_gap_mm, stator=False)
    eta_pct = float(curve.peak_efficiency) * 100.0
    return float(q0), float(q_op), eta_pct


def run_mixed_study(
    *,
    n_trials: int = 120,
    seed: int = 0,
    load_pa: float = 8.0,
    rpm: float | None = None,
    tip_gap_mm: float = DEFAULT_TIP_GAP_MM,
    out_dir: str | Path | None = None,
    study_name: str = "mixed",
    hose: str = "case",
):
    """NSGA-II maximizing (BEM cfm_free, BEM cfm_load). Persists when ``out_dir`` is set.

    Returns (study, pareto_rows) where rows match the mixed cockpit scatter shape.
    """
    from fansim.centrifugal.persist import (
        mixed_opt_rows_from_study,
        save_mixed_pareto,
    )

    run_rpm = float(A12X25.rpm if rpm is None else rpm)
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
            params = suggest_mixed(trial)
            q0, q_op, eta_pct = evaluate_mixed_bem(
                params, rpm=run_rpm, load_pa=float(load_pa), tip_gap_mm=tip_gap_mm)
        except Exception as exc:  # noqa: BLE001 — mark FAIL; never invent a (0, 0) point (§9.7)
            trial.set_user_attr("feasible", False)
            trial.set_user_attr(
                "reason", f"bem failed: {type(exc).__name__}: {exc}")
            raise
        flat = mixed_flat_from_params(params)
        trial.set_user_attr("feasible", True)
        trial.set_user_attr("reason", "")
        trial.set_user_attr("cfm_free", q0)
        trial.set_user_attr("cfm_load", q_op)
        trial.set_user_attr("efficiency", eta_pct)
        trial.set_user_attr("params", flat)
        trial.set_user_attr("bem_adapter", "axial")
        trial.set_user_attr("hose", hose)
        trial.set_user_attr("load_pa", float(load_pa))
        return q0, q_op

    study.optimize(objective, n_trials=int(n_trials), catch=(Exception,))
    pareto = mixed_opt_rows_from_study(study)
    if out_dir is not None:
        save_mixed_pareto(
            out_dir,
            pareto,
            meta={
                "n_trials": int(n_trials),
                "load_pa": float(load_pa),
                "rpm": run_rpm,
                "hose": hose,
                "seed": int(seed),
                "bem_adapter": "axial",
            },
        )
    return study, pareto


def refine_pareto_cfd(
    pareto: list[dict],
    out_dir: str | Path,
    *,
    n_top: int,
    load_pa: float = 8.0,
    bem_prescreen_cfm: float = 0.0,
    **eval_kw,
) -> list[dict]:
    """CFD-score the top-N mixed BEM Pareto rows (mirrors prop/CROR refine).

    Monkeypatch ``fansim.centrifugal.evaluate.evaluate_mixed_flow`` in tests.
    Writes ``cfd_refine.json`` under ``out_dir``. Does not claim the BEM front
    is calibrated — CFD is the honest score.
    """
    from fansim.centrifugal.params_io import mixed_params_from_flat

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    n = max(0, int(n_top))
    for i, row in enumerate(pareto[:n]):
        workdir = out_dir / f"rank_{i:02d}"
        flat = dict(row.get("params") or {})
        try:
            params = mixed_params_from_flat(flat)
        except Exception as exc:  # noqa: BLE001
            rows.append({
                "rank": int(i),
                "workdir": str(workdir),
                "skipped": True,
                "reason": f"bad params: {type(exc).__name__}: {exc}",
                "bem_cfm_free": row.get("objectives", {}).get("cfm_free"),
                "bem_cfm_load": row.get("objectives", {}).get("cfm_load"),
            })
            continue

        from fansim.centrifugal.evaluate import evaluate_mixed_flow

        res = evaluate_mixed_flow(
            params,
            workdir,
            load_pa=float(load_pa),
            bem_prescreen_cfm=float(bem_prescreen_cfm),
            **eval_kw,
        )
        rec = {
            "rank": int(i),
            "workdir": str(workdir),
            "skipped": not bool(res.feasible),
            "bem_cfm_free": float((row.get("objectives") or {}).get("cfm_free") or 0.0),
            "bem_cfm_load": float((row.get("objectives") or {}).get("cfm_load") or 0.0),
            "params": flat,
        }
        if not res.feasible:
            rec["reason"] = res.reason
        else:
            rec["cfd_cfm_free"] = float(res.cfm_free)
            rec["cfd_cfm_load"] = float(res.cfm_load)
            rec["cfd_efficiency"] = float(res.efficiency)
        rows.append(rec)

    import json
    import time

    payload = {
        "kind": "mixed_cfd_refine",
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "n_top": n,
        "load_pa": float(load_pa),
        "rows": rows,
    }
    (out_dir / "cfd_refine.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    return rows
