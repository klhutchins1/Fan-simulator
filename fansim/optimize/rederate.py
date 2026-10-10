"""Re-derate saved fan scores when the motor power budget changes (no CFD).

The scorer (``fansim.optimize.objectives``) slows a design the motor can't power to
lambda = min(1, (budget / P_shaft)^(1/3)) of rated speed, and scales flow by lambda and pressure by
lambda^2 (affinity laws). On the quadratic hose line the operating point scales with lambda too, and
the straight-line efficiency is unchanged. So a saved score re-derates by lambda_new / lambda_old,
which is recoverable from the saved RPM alone. ``rescore_from_raw`` reruns the post-CFD scoring from
a saved ``_eval_result.json`` raw dict, to check that shortcut
(docs/validation/audits/2026-10-10-motor-efficiency.md).
"""

from __future__ import annotations

from fansim.optimize.system_curve import derated_probe_pa, score_operating_point


def derate_factor(budget_w: float, shaft_w: float) -> float:
    return min(1.0, (float(budget_w) / max(float(shaft_w), 1e-9)) ** (1.0 / 3.0))


def rederate_scale(actual_rpm: float, target_rpm: float, budget_old_w: float, budget_new_w: float) -> float:
    """lambda_new / lambda_old for a score saved at ``actual_rpm`` under ``budget_old_w``."""
    lam_old = min(1.0, float(actual_rpm) / float(target_rpm))
    if lam_old <= 0.0:
        return 1.0
    lam_new = min(1.0, lam_old * (float(budget_new_w) / float(budget_old_w)) ** (1.0 / 3.0))
    return lam_new / lam_old


def rescore_from_raw(raw: dict, *, budget_w: float, target_rpm: float, load_pa: float) -> dict | None:
    """Post-CFD score from saved free/load metrics, or None when that isn't reproducible here
    (``refine_op`` ran extra CFD at the derated point, or the metrics are missing)."""
    if raw.get("op_cfd") or raw.get("cfm_op_alg") is not None:
        return None
    free, load = raw.get("free") or {}, raw.get("load") or {}
    try:
        shaft = max(float(free["shaft_power_w"]), float(load["shaft_power_w"]), 1e-9)
        lam = derate_factor(budget_w, shaft)
        cfm_free = float(free["cfm"]) * lam
        cfm_probe = max(float(load["cfm"]), 0.0) * lam
        p_free = max(0.0, float(free["static_pressure_rise_pa"])) * lam * lam
        op = score_operating_point(
            q_free_cfm=cfm_free, q_probe_cfm=cfm_probe,
            p_probe_pa=derated_probe_pa(load_pa, lam),
            eta_free=float(free["efficiency"]), eta_load=float(load["efficiency"]),
            load_pa=float(load_pa), p_free_pa=p_free)
    except (KeyError, TypeError, ValueError):
        return None
    k_cfm = float(raw.get("print_k_cfm") or 1.0)
    k_eta = float(raw.get("print_k_eta") or 1.0)
    return {"cfm_free": cfm_free * k_cfm, "cfm_load": op.q_op_cfm * k_cfm,
            "efficiency": max(op.eta * 100.0, 0.0) * k_eta,
            "actual_rpm": float(target_rpm) * lam, "derate": lam}
