"""Algebraic intersection of a 2-point fan line with ΔP = k Q²."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.fan_bem import CFM_PER_M3S

REF_CFM = 50.0


def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


def rated_op_back_pressure(p_op_pa: float, derate: float) -> float:
    """Rated-RPM boundary Pa that matches hose pressure at actual RPM (P ∝ RPM²)."""
    lam = float(derate)
    if lam <= 0.0:
        raise SystemCurveError("derate must be positive")
    return float(p_op_pa) / lam ** 2


OP_REUSE_PA = 0.05


@dataclass(frozen=True)
class RefinedOp:
    q_op_cfm: float
    eta: float
    op_cfd: str
    cfm_op_alg: float


def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


def rated_op_back_pressure(p_op_pa: float, derate: float) -> float:
    """Rated-RPM boundary Pa that matches hose pressure at actual RPM (P ∝ RPM²)."""
    lam = float(derate)
    if lam <= 0.0:
        raise SystemCurveError("derate must be positive")
    return float(p_op_pa) / lam ** 2


OP_REUSE_PA = 0.05


@dataclass(frozen=True)
class RefinedOp:
    q_op_cfm: float
    eta: float
    op_cfd: str
    cfm_op_alg: float


class SystemCurveError(ValueError):
    """Infeasible fan line / system-curve intersection."""


def k_from_pa(load_pa: float, ref_cfm: float = REF_CFM) -> float:
    q_ref_m3s = ref_cfm / CFM_PER_M3S
    return load_pa / q_ref_m3s**2


def intersect_fan_line(
    q_free_cfm: float,
    q_probe_cfm: float,
    p_probe_pa: float,
    k: float,
) -> tuple[float, float]:
    q0_m3s = q_free_cfm / CFM_PER_M3S
    q1_m3s = q_probe_cfm / CFM_PER_M3S
    p1 = p_probe_pa

    if q0_m3s <= 0:
        raise SystemCurveError("free-delivery flow must be positive")
    if q1_m3s <= 0:
        raise SystemCurveError("probe flow must be positive")
    if q1_m3s >= q0_m3s:
        raise SystemCurveError("probe flow must be below free delivery")
    if p1 <= 0:
        raise SystemCurveError("probe pressure must be positive")
    if k <= 0:
        raise SystemCurveError("system-curve k must be positive")

    a = k * (q0_m3s - q1_m3s)
    b = p1
    c = -p1 * q0_m3s

    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        raise SystemCurveError("no real intersection")

    sqrt_d = math.sqrt(discriminant)
    roots = [(-b + sqrt_d) / (2 * a), (-b - sqrt_d) / (2 * a)]
    valid = [root for root in roots if 0 < root < q0_m3s]
    if len(valid) != 1:
        raise SystemCurveError("no unique root in (0, Q0)")

    q_op_m3s = valid[0]
    p_op = k * q_op_m3s**2
    return q_op_m3s * CFM_PER_M3S, p_op


@dataclass(frozen=True)
class OperatingPoint:
    q_op_cfm: float
    p_op_pa: float
    eta: float
    k: float


def score_operating_point(
    q_free_cfm: float,
    q_probe_cfm: float,
    p_probe_pa: float,
    eta_free: float,
    eta_load: float,
    load_pa: float,
) -> OperatingPoint:
    k = k_from_pa(load_pa)
    q_op_cfm, p_op_pa = intersect_fan_line(
        q_free_cfm, q_probe_cfm, p_probe_pa, k
    )
    t = (q_op_cfm - q_free_cfm) / (q_probe_cfm - q_free_cfm)
    t = min(1.0, max(0.0, t))
    eta = eta_free + t * (eta_load - eta_free)
    return OperatingPoint(
        q_op_cfm=q_op_cfm,
        p_op_pa=p_op_pa,
        eta=eta,
        k=k,
    )


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
