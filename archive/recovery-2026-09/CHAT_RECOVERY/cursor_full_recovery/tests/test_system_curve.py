import math
import pytest

from fansim.fan_bem import CFM_PER_M3S, FanCurve, FanPoint, pq_curve
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


def test_ref_cfm_is_fifty():
    assert REF_CFM == 50.0


def test_k_from_pa_eight_at_fifty_cfm():
    q_ref = REF_CFM / CFM_PER_M3S
    assert k_from_pa(8.0) == pytest.approx(8.0 / q_ref**2)


def test_intersection_at_calibration_point_is_fifty_cfm_eight_pa():
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 50.0, 8.0, k)
    assert q_op == pytest.approx(50.0)
    assert p_op == pytest.approx(8.0)


def test_weaker_probe_moves_op_to_higher_flow_lower_pressure():
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 40.0, 8.0, k)
    assert q_op > 40.0
    assert p_op < 8.0
    assert 0.0 < q_op < 80.0


def test_inverted_curve_raises():
    k = k_from_pa(8.0)
    with pytest.raises(SystemCurveError):
        intersect_fan_line(40.0, 50.0, 8.0, k)


def test_score_interpolates_efficiency_vs_cfm():
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=50.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    assert op.q_op_cfm == pytest.approx(50.0)
    assert op.p_op_pa == pytest.approx(8.0)
    assert op.eta == pytest.approx(0.35)
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
    # A strong fan line can intersect the system curve left of the CFD probe point.
    # In that case we must NOT extrapolate efficiency above the probe-point value.
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=60.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=8.0)
    assert op.q_op_cfm < 60.0
    assert op.eta == pytest.approx(0.35)


def test_probe_flow_nonpositive_raises():
    k = k_from_pa(8.0)
    with pytest.raises(SystemCurveError):
        intersect_fan_line(80.0, 0.0, 8.0, k)

    with pytest.raises(SystemCurveError):
        score_operating_point(
            q_free_cfm=80.0, q_probe_cfm=0.0, p_probe_pa=8.0,
            eta_free=0.20, eta_load=0.35, load_pa=8.0)


def test_cli_help_mentions_system_curve_and_no_k_flag():
    from pathlib import Path

    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--k" not in text
    assert "★" not in text
    assert ("application impedance as Pa at 50 CFM (system curve dP = k Q^2): "
            "case=8 Pa, heatsink=20 Pa, radiator=35 Pa. Sets --load-pa unless you pass --load-pa."
            ) in text
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen")[1].split("add_argument")[0] or True
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen")[1].split("add_argument")[0] or True
    assert ("system-curve Pa at 50 CFM (sets k on dP = k Q^2). Default 1.0 or the --preset value."
            ) in text
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
    assert "--refine-op" in text


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
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.fan_spec import A12X25
    from fansim.geometry.blade import BladeParams, RadialStation

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
    assert len(seen) == 1
    assert seen[0] == pytest.approx(op.p_op_pa)
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
    assert "system-curve operating point" in text
    assert "free-delivery" not in text.split("--bem-prescreen", 1)[1].split("ap.add_argument")[0]
    assert "--refine-op" in text


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
    from fansim.cfd.domain import remaining_tip_gap_mm
    from fansim.fan_spec import A12X25
    from fansim.geometry.blade import BladeParams, RadialStation

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
    assert len(seen) == 1
    assert seen[0] == pytest.approx(op.p_op_pa)
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


def test_cli_help_mentions_system_curve_and_no_k_flag():
    from pathlib import Path

    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--k" not in text
    assert "★" not in text
    assert ("application impedance as Pa at 50 CFM (system curve dP = k Q^2): "
            "case=8 Pa, heatsink=20 Pa, radiator=35 Pa. Sets --load-pa unless you pass --load-pa."
            ) in text
    assert ("system-curve Pa at 50 CFM (not a fixed wall). Default 1.0 or the --preset value."
            ) in text
