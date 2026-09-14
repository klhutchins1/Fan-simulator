# RECONSTRUCTED-FROM-CURSOR-TRANSCRIPT 2026-09-12
# Provenance: docs/superpowers/specs/2026-09-02-system-curve-design.md + StrReplace
# patches in agent-transcripts/9f43d5b7...jsonl (initial Write was via subagent; body rebuilt).
# Later additions: probe_flow_cfm / bem_* / derated_probe_pa / eta clamp.
"""Hose system curve ΔP = k Q² and 2-point fan-line intersection (roadmap §1.2)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.fan_bem import CFM_PER_M3S

REF_CFM = 50.0


def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


class SystemCurveError(ValueError):
    """Infeasible system-curve inputs or no intersection in (0, Q_free)."""


def k_from_pa(load_pa: float, ref_cfm: float = REF_CFM) -> float:
    """Pa at ``ref_cfm`` → k for ΔP = k Q² with Q in m³/s."""
    q_ref = float(ref_cfm) / CFM_PER_M3S
    if q_ref <= 0.0:
        raise SystemCurveError("ref CFM must be positive")
    return float(load_pa) / (q_ref * q_ref)


def intersect_fan_line(
    q_free_cfm: float,
    q_probe_cfm: float,
    p_probe_pa: float,
    k: float,
) -> tuple[float, float]:
    """Intersect fan line (Q0,0)–(Q1,P1) with ΔP = k Q².

    Returns ``(q_op_cfm, p_op_pa)``. Raises ``SystemCurveError`` on bad inputs
    or no root in ``(0, Q0)``.
    """
    q0_cfm = float(q_free_cfm)
    q1_cfm = float(q_probe_cfm)
    p1 = float(p_probe_pa)
    kk = float(k)
    if q0_cfm <= 0.0:
        raise SystemCurveError("free-delivery CFM must be positive")
    if q1_cfm <= 0.0:
        raise SystemCurveError("probe CFM must be positive")
    if q1_cfm >= q0_cfm:
        raise SystemCurveError("probe CFM must be below free-delivery")
    if p1 <= 0.0:
        raise SystemCurveError("probe Pa must be positive")
    if kk <= 0.0:
        raise SystemCurveError("system-curve k must be positive")

    q0 = q0_cfm / CFM_PER_M3S
    q1 = q1_cfm / CFM_PER_M3S
    # a Q² + b Q + c = 0  (Q in m³/s); see 2026-09-02-system-curve-design.md
    a = kk * (q0 - q1)
    b = p1
    c = -p1 * q0
    if abs(a) < 1e-30:
        raise SystemCurveError("degenerate fan-line / k")
    disc = b * b - 4.0 * a * c
    if disc < 0.0:
        raise SystemCurveError("no real intersection")
    sqrt_disc = math.sqrt(disc)
    roots = [(-b + sqrt_disc) / (2.0 * a), (-b - sqrt_disc) / (2.0 * a)]
    in_range = [q for q in roots if 0.0 < q < q0]
    if not in_range:
        raise SystemCurveError("no intersection in (0, Q_free)")
    q_op = in_range[0] if len(in_range) == 1 else min(in_range, key=lambda q: abs(q - q1))
    p_op = kk * q_op * q_op
    return q_op * CFM_PER_M3S, p_op


@dataclass(frozen=True)
class OperatingPoint:
    q_op_cfm: float
    p_op_pa: float
    eta: float  # 0–1 fraction
    k: float


def score_operating_point(
    q_free_cfm: float,
    q_probe_cfm: float,
    p_probe_pa: float,
    eta_free: float,
    eta_load: float,
    load_pa: float,
) -> OperatingPoint:
    """Hose k from ``load_pa`` @ REF_CFM; fan line uses ``p_probe_pa`` (may be derated)."""
    k = k_from_pa(load_pa)
    q_op_cfm, p_op_pa = intersect_fan_line(q_free_cfm, q_probe_cfm, p_probe_pa, k)
    denom = float(q_probe_cfm) - float(q_free_cfm)
    if abs(denom) < 1e-12:
        raise SystemCurveError("free and probe CFM coincide")
    t = (q_op_cfm - float(q_free_cfm)) / denom
    t = min(1.0, max(0.0, t))  # clamp: past-probe ops keep probe eta (not extrapolate)
    eta = float(eta_free) + t * (float(eta_load) - float(eta_free))
    return OperatingPoint(q_op_cfm=q_op_cfm, p_op_pa=p_op_pa, eta=eta, k=k)


def probe_flow_cfm(curve, load_pa: float) -> float:
    """Linear-interpolate BEM flow at static pressure ``load_pa``.

    ``FanCurve.points`` run low flow (high static) → high flow (low static).
    """
    p1 = float(load_pa)
    if p1 >= float(curve.shutoff_dp_pa):
        raise SystemCurveError("BEM shutoff below probe Pa")
    pts = list(curve.points)
    for a, b in zip(pts, pts[1:]):
        pa, pb = float(a.dp_static_pa), float(b.dp_static_pa)
        if pa >= p1 >= pb or pb >= p1 >= pa:
            if pa == pb:
                return float(a.flow_cfm)
            t = (p1 - pa) / (pb - pa)
            return float(a.flow_cfm) + t * (float(b.flow_cfm) - float(a.flow_cfm))
    raise SystemCurveError("probe Pa is not on the BEM curve")


def bem_screen_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float,
                   *, stator: bool = False) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve operating CFM)."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm, stator=stator)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op


def bem_load_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float,
                 *, stator: bool = False) -> float:
    """BEM 2-point fan line ∩ ΔP = k Q² — same operating point CFD uses for cfm_load."""
    return bem_screen_cfm(params, rpm, load_pa, tip_gap_mm, stator=stator)[1]


# --- spliced from transcript edit-history (recovery 2026-09-12) ---
def refine_operating_metrics(op, derate: float, load_pa: float, m_load, solve_at) -> RefinedOp:
    """Optional third CFD at the rated-RPM equivalent of the algebraic hose pressure."""
    alg_q = float(op.q_op_cfm)
    alg_eta = float(op.eta)
    lam = float(derate)
    p_rated = rated_op_back_pressure(op.p_op_pa, lam)
    if abs(p_rated - float(load_pa)) < OP_REUSE_PA:
        return RefinedOp(
            q_op_cfm=max(float(m_load.cfm), 0.0) * lam,
            eta=float(m_load.efficiency),
            op_cfd="reused-probe",
            cfm_op_alg=alg_q,
        )
    try:
        m_op = solve_at(p_rated)
        return RefinedOp(
            q_op_cfm=max(float(m_op.cfm), 0.0) * lam,
            eta=float(m_op.efficiency),
            op_cfd="solved",
            cfm_op_alg=alg_q,
        )
    except Exception:  # noqa: BLE001 - refinement miss must not fail the trial
        return RefinedOp(alg_q, alg_eta, "failed", alg_q)
