## patch 0 line 726
### OLD
`
from fansim.fan_bem import CFM_PER_M3S
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    intersect_fan_line,
    k_from_pa,
    score_operating_point,
)
`
### NEW
`
from fansim.fan_bem import CFM_PER_M3S, FanCurve, FanPoint, pq_curve
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_load_cfm,
    intersect_fan_line,
    k_from_pa,
    probe_flow_cfm,
    score_operating_point,
)
`

## patch 1 line 726
### OLD
`
            ) in text
`
### NEW
`
            ) in text
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen")[1].split("add_argument")[0] or True
`

## patch 2 line 728
### OLD
`
    assert ("system-curve Pa at 50 CFM (sets k on dP = k Q^2). Default 1.0 or the --preset value."
            ) in text
`
### NEW
`
    assert ("system-curve Pa at 50 CFM (sets k on dP = k Q^2). Default 1.0 or the --preset value."
            ) in text
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
`

## patch 3 line 729
### OLD
`
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
`
### NEW
`
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]


def _fake_curve() -> FanCurve:
    def pt(cfm, pa):
        return FanPoint(flow_cfm=cfm, flow_m3s=0.0, dp_static_pa=pa,
                        dp_total_pa=pa, efficiency=0.3, power_w=1.0)
    return FanCurve(
        points=[pt(10.0, 20.0), pt(40.0, 8.0), pt(80.0, 0.0)],
        free_delivery_cfm=80.0, shutoff_dp_pa=20.0,
        peak_efficiency=0.3, peak_eff_cfm=40.0,
    )


def test_probe_flow_interpolates_bem_pq():
    c = _fake_curve()
    assert probe_flow_cfm(c, 8.0) == pytest.approx(40.0)
    assert probe_flow_cfm(c, 14.0) == pytest.approx(25.0)


def test_bem_shutoff_below_probe_raises():
    with pytest.raises(SystemCurveError):
        probe_flow_cfm(_fake_curve(), 50.0)


def test_bem_load_cfm_sits_between_probe_and_free():
    from fansim.geometry.blade import BladeParams
    p = BladeParams()
    curve = pq_curve(p, rpm=2000, tip_gap_mm=0.5)
    q1 = probe_flow_cfm(curve, 8.0)
    q_op = bem_load_cfm(p, 2000.0, 8.0, tip_gap_mm=0.5)
    assert q1 < q_op < curve.free_delivery_cfm
`

## patch 4 line 731
### OLD
`
    return OperatingPoint(
        q_op_cfm=q_op_cfm,
        p_op_pa=p_op_pa,
        eta=eta,
        k=k,
    )
`
### NEW
`
    return OperatingPoint(
        q_op_cfm=q_op_cfm,
        p_op_pa=p_op_pa,
        eta=eta,
        k=k,
    )


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


def bem_load_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> float:
    """BEM 2-point fan line ∩ ΔP = k Q² — same operating point CFD uses for cfm_load."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q_op


def bem_screen_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve operating CFM)."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op
`

## patch 5 line 732
### OLD
`
def bem_load_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> float:
    """BEM 2-point fan line ∩ ΔP = k Q² — same operating point CFD uses for cfm_load."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q_op


def bem_screen_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve operating CFM)."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op
`
### NEW
`
def bem_screen_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve operating CFM)."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op


def bem_load_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> float:
    """BEM 2-point fan line ∩ ΔP = k Q² — same operating point CFD uses for cfm_load."""
    return bem_screen_cfm(params, rpm, load_pa, tip_gap_mm)[1]
`

## patch 6 line 736
### OLD
`
def test_bem_load_cfm_sits_between_probe_and_free():
    from fansim.geometry.blade import BladeParams
    p = BladeParams()
    curve = pq_curve(p, rpm=2000, tip_gap_mm=0.5)
    q1 = probe_flow_cfm(curve, 8.0)
    q_op = bem_load_cfm(p, 2000.0, 8.0, tip_gap_mm=0.5)
    assert q1 < q_op < curve.free_delivery_cfm
`
### NEW
`
def test_bem_load_cfm_sits_between_probe_and_free():
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.fan_spec import A12X25
    from fansim.geometry.blade import RadialStation

    p = BladeParams(
        tip_radius=50.0,
        stations=[
            RadialStation(0.0, 18.0, 40.0, thickness=0.12, max_camber=0.04),
            RadialStation(0.5, 18.0, 40.0, thickness=0.10, max_camber=0.04),
            RadialStation(1.0, 14.0, 40.0, thickness=0.08, max_camber=0.04),
        ],
    )
    gap = remaining_tip_gap_mm(p, A12X25.tip_dia_mm[1])
    curve = pq_curve(p, rpm=A12X25.rpm, tip_gap_mm=gap)
    q1 = probe_flow_cfm(curve, 8.0)
    q_op = bem_load_cfm(p, A12X25.rpm, 8.0, tip_gap_mm=gap)
    assert q1 < q_op < curve.free_delivery_cfm
`

## patch 7 line 737
### OLD
`
    from fansim.geometry.blade import RadialStation
`
### NEW
`
    from fansim.geometry.blade import BladeParams, RadialStation
`

## patch 8 line 748
### OLD
`
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_load_cfm,
    intersect_fan_line,
    k_from_pa,
    probe_flow_cfm,
    score_operating_point,
)
`
### NEW
`
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_load_cfm,
    derated_probe_pa,
    intersect_fan_line,
    k_from_pa,
    probe_flow_cfm,
    score_operating_point,
)
`

## patch 9 line 748
### OLD
`
    assert op.k == pytest.approx(k_from_pa(8.0))


def test_score_clamps_efficiency_past_probe_point():
`
### NEW
`
    assert op.k == pytest.approx(k_from_pa(8.0))


def test_derated_probe_pa_is_load_times_lambda_squared():
    assert derated_probe_pa(8.0, 1.0) == pytest.approx(8.0)
    assert derated_probe_pa(8.0, 0.5) == pytest.approx(2.0)


def test_scaled_probe_pressure_lowers_operating_point():
    full = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    weak = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=derated_probe_pa(8.0, 0.8),
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    assert weak.q_op_cfm < full.q_op_cfm
    assert weak.p_op_pa < full.p_op_pa
    assert weak.k == pytest.approx(full.k)


def test_score_clamps_efficiency_past_probe_point():
`

## patch 10 line 750
### OLD
`
class SystemCurveError(ValueError):
`
### NEW
`
def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


class SystemCurveError(ValueError):
`

## patch 11 line 764
### OLD
`
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_load_cfm,
    derated_probe_pa,
    intersect_fan_line,
    k_from_pa,
    probe_flow_cfm,
    score_operating_point,
)
`
### NEW
`
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    bem_load_cfm,
    derated_probe_pa,
    intersect_fan_line,
    k_from_pa,
    probe_flow_cfm,
    rated_op_back_pressure,
    refine_operating_metrics,
    score_operating_point,
)
`

## patch 12 line 764
### OLD
`
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
`
### NEW
`
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
    assert "--refine-op" in text
`

## patch 13 line 766
### OLD
`
    q1 = probe_flow_cfm(curve, 8.0)
    q_op = bem_load_cfm(p, A12X25.rpm, 8.0, tip_gap_mm=gap)
    assert q1 < q_op < curve.free_delivery_cfm
`
### NEW
`
    q1 = probe_flow_cfm(curve, 8.0)
    q_op = bem_load_cfm(p, A12X25.rpm, 8.0, tip_gap_mm=gap)
    assert q1 < q_op < curve.free_delivery_cfm


def test_rated_op_back_pressure_undoes_affinity():
    assert rated_op_back_pressure(8.0, 1.0) == pytest.approx(8.0)
    assert rated_op_back_pressure(5.12, 0.8) == pytest.approx(8.0)
    with pytest.raises(SystemCurveError):
        rated_op_back_pressure(8.0, 0.0)


def test_refine_op_calls_solve_at_rated_pressure():
    from types import SimpleNamespace
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    seen = []

    def solve_at(pa):
        seen.append(pa)
        return SimpleNamespace(cfm=44.0, efficiency=0.31)

    m_load = SimpleNamespace(cfm=50.0, efficiency=0.35)
    got = refine_operating_metrics(op, derate=1.0, load_pa=20.0, m_load=m_load, solve_at=solve_at)
    assert seen == [pytest.approx(op.p_op_pa)]
    assert got.op_cfd == "solved"
    assert got.q_op_cfm == pytest.approx(44.0)
    assert got.eta == pytest.approx(0.31)
    assert got.cfm_op_alg == pytest.approx(op.q_op_cfm)


def test_refine_op_reuses_probe_when_pressure_matches():
    from types import SimpleNamespace
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    calls = []
    m_load = SimpleNamespace(cfm=50.0, efficiency=0.35)
    got = refine_operating_metrics(
        op, derate=1.0, load_pa=op.p_op_pa, m_load=m_load,
        solve_at=lambda pa: calls.append(pa) or SimpleNamespace(cfm=1.0, efficiency=0.0))
    assert calls == []
    assert got.op_cfd == "reused-probe"
    assert got.q_op_cfm == pytest.approx(50.0)
    assert got.eta == pytest.approx(0.35)


def test_refine_op_keeps_algebraic_when_solve_raises():
    from types import SimpleNamespace
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)

    def boom(_pa):
        raise RuntimeError("cfd")

    got = refine_operating_metrics(
        op, derate=1.0, load_pa=20.0,
        m_load=SimpleNamespace(cfm=50.0, efficiency=0.35), solve_at=boom)
    assert got.op_cfd == "failed"
    assert got.q_op_cfm == pytest.approx(op.q_op_cfm)
    assert got.eta == pytest.approx(op.eta)
`

## patch 14 line 767
### OLD
`
    assert seen == [pytest.approx(op.p_op_pa)]
`
### NEW
`
    assert len(seen) == 1
    assert seen[0] == pytest.approx(op.p_op_pa)
`

## patch 15 line 768
### OLD
`
def derated_probe_pa(load_pa: float, derate: float) -> float:
    """Fan-line probe pressure after motor derate: P ∝ RPM². Hose k is unchanged."""
    return float(load_pa) * float(derate) ** 2


class SystemCurveError(ValueError):
`
### NEW
`
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
`

## patch 16 line 770
### OLD
`
    return OperatingPoint(
        q_op_cfm=q_op_cfm,
        p_op_pa=p_op_pa,
        eta=eta,
        k=k,
    )
`
### NEW
`
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
`

## patch 17 line 1633
### OLD
`
def bem_screen_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> tuple[float, float]:
    """(BEM free-delivery CFM, BEM system-curve operating CFM)."""
    from fansim.fan_bem import pq_curve

    curve = pq_curve(params, rpm, tip_gap_mm=tip_gap_mm)
    q0 = float(curve.free_delivery_cfm)
    if float(load_pa) <= 0.0:
        return q0, q0
    q1 = probe_flow_cfm(curve, load_pa)
    if q1 >= q0:
        q1 = 0.999 * q0
    q_op, _p_op = intersect_fan_line(q0, q1, float(load_pa), k_from_pa(load_pa))
    return q0, q_op


def bem_load_cfm(params, rpm: float, load_pa: float, tip_gap_mm: float) -> float:
    """BEM 2-point fan line ∩ ΔP = k Q² — same operating point CFD uses for cfm_load."""
    return bem_screen_cfm(params, rpm, load_pa, tip_gap_mm)[1]
`
### NEW
`
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
`
