# Provenance: docs/superpowers/specs/2026-09-02-system-curve-design.md + StrReplace
# patches in agent-transcripts/9f43d5b7...jsonl (initial Write was via subagent; body rebuilt).
# Later additions: probe_flow_cfm / bem_* / derated_probe_pa / eta clamp.
"""Hose system curve ΔP = k Q² and 2-point fan-line intersection (roadmap §1.2)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.metrics import CFM_PER_M3S

REF_CFM = 50.0


def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


class SystemCurveError(ValueError):
    """Infeasible system-curve inputs or no intersection in (0, Q_free)."""


def rated_op_back_pressure(p_op_pa: float, derate: float) -> float:
    """Rated-RPM boundary Pa that matches hose pressure at actual RPM (P ∝ RPM²).

    Inverse of ``derated_probe_pa``: if the fan is running at ``derate`` × rated RPM,
    the hose ΔP seen in the derated solve is ``p_op``; the equivalent rated-RPM
    back-pressure for a third CFD is ``p_op / derate²``.
    """
    lam = float(derate)
    if lam <= 0.0:
        raise SystemCurveError("derate must be positive")
    return float(p_op_pa) / (lam * lam)


OP_REUSE_PA = 0.05  # Pa — skip third CFD if p_rated ≈ hose load_pa


@dataclass(frozen=True)
class RefinedOp:
    """Result of optional third CFD at the rated-RPM hose operating pressure."""

    q_op_cfm: float
    eta: float
    op_cfd: str  # "reused-probe" | "solved" | "failed"
    cfm_op_alg: float


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
    *,
    p_free_pa: float = 0.0,
) -> tuple[float, float]:
    """Intersect fan line (Q0,P0)–(Q1,P1) with ΔP = k Q².

    ``p_free_pa`` defaults to 0 (AMCA free delivery / BEM zero-crossing). CFD free
    (zero back-pressure) often measures a small positive static rise — pass that as
    ``p_free_pa`` so the hose operating point matches the measured free endpoint.

    Returns ``(q_op_cfm, p_op_pa)``. Raises ``SystemCurveError`` on bad inputs
    or no root in ``(0, Q0)``.
    """
    q0_cfm = float(q_free_cfm)
    q1_cfm = float(q_probe_cfm)
    p0 = float(p_free_pa)
    p1 = float(p_probe_pa)
    kk = float(k)
    if q0_cfm <= 0.0:
        raise SystemCurveError("free-delivery CFM must be positive")
    if q1_cfm <= 0.0:
        raise SystemCurveError("probe CFM must be positive")
    if q1_cfm >= q0_cfm:
        raise SystemCurveError("probe CFM must be below free-delivery")
    if p1 <= p0:
        raise SystemCurveError("probe Pa must exceed free-endpoint Pa")
    if kk <= 0.0:
        raise SystemCurveError("system-curve k must be positive")
    if p0 < 0.0:
        raise SystemCurveError("free-endpoint Pa must be non-negative")

    q0 = q0_cfm / CFM_PER_M3S
    q1 = q1_cfm / CFM_PER_M3S
    # Fan line: P = [(q1-Q)*p0 + (Q-q0)*p1] / (q1-q0)
    # Set = k Q² → k(q1-q0) Q² - (p1-p0) Q - (q1 p0 - q0 p1) = 0
    dq = q1 - q0
    a = kk * dq
    b = -(p1 - p0)
    c = -(q1 * p0 - q0 * p1)
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
    *,
    p_free_pa: float = 0.0,
) -> OperatingPoint:
    """Hose k from ``load_pa`` @ REF_CFM; fan line uses free/probe pressures (may be derated)."""
    k = k_from_pa(load_pa)
    q_op_cfm, p_op_pa = intersect_fan_line(
        q_free_cfm, q_probe_cfm, p_probe_pa, k, p_free_pa=p_free_pa,
    )
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
    if q0 <= 0.0:                     # no pressure rise at all (pq_curve free_status "no_rise")
        return 0.0, 0.0
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op


# A design whose axial-force BEM peak efficiency is below this does not pump air, it churns it (QA
# paddle: 0.9 %). Lowest of 93 real designs (CFD-scored, saved, both QA shortlists): 28.8 %.
EXPLOIT_MIN_PEAK_EFF = 0.05


def bem_exploit_reason(params, rpm: float, tip_gap_mm: float | None = None) -> str:
    """Why the axial-force BEM says these blades are not a fan ('' when they are).

    The Euler BEM can be exploited: drag-driven swirl from a paddle (stagger near 90°) or a
    wrong-hand blade counts as useful pressure, so such designs scored as good fans (QA-4). The
    axial-force model takes the static rise from the blades' axial push, which drag and negative
    lift reduce. Used only to refuse a design before CFD, never to rank (it ranks no better than
    Euler: ρ 0.809 vs 0.827 on 16 CFD designs).
    """
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm, pressure_model="axial_force")
    if curve.free_status == "no_rise":
        return "blades make no pressure (wrong hand or fully stalled?)"
    if float(curve.peak_efficiency) < EXPLOIT_MIN_PEAK_EFF:
        return (f"blades churn air instead of pumping it (peak efficiency "
                f"{100.0 * float(curve.peak_efficiency):.1f} % < {100 * EXPLOIT_MIN_PEAK_EFF:.0f} %; paddle-like?)")
    return ""


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
