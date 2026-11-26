"""Audit #4: axial-fan BEM pre-screen (fansim.fan_bem) -- verification + Stock v1/v2 ordering.

Tolerances were pre-registered in docs/validation/audits/2026-09-29-audit-04-fan-bem.md before any
comparison to CFD: (a) v2 free-air within +-25% of CFD, P-Q slope sign/order right; (b) Spearman >= 0.6
over >= 5 designs (fewer -> INCONCLUSIVE); (c) BEM orders Stock v1 above Stock v2 in free-air flow.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from fansim import fan_bem as FB
from fansim.cfd import metrics as M
from fansim.fan_bem import operating_point, pq_curve
from fansim.geometry.config import load_blade_params
from fansim.physics import air

CFG = Path(__file__).resolve().parents[2] / "config" / "problems"
CFD_V2 = {0: 56.5, 5: 49.8, 10: 40.2}      # CFD v5 complete setup, converged
CFD_V1_FREE = 77.4                          # CFD v5 complete setup, free air only
ABS_TOL = 0.25                              # pre-registered
SPEARMAN_MIN, MIN_DESIGNS = 0.6, 5          # pre-registered


@pytest.fixture(scope="module")
def v2():
    return load_blade_params(CFG / "a12x25_reference.yaml")


@pytest.fixture(scope="module")
def v1():
    return load_blade_params(CFG / "a12x25_reference_v1.yaml")


def _flow_at(curve, dp):
    for a, b in zip(curve.points, curve.points[1:]):
        if a.dp_static_pa >= dp > b.dp_static_pa:
            t = (a.dp_static_pa - dp) / (a.dp_static_pa - b.dp_static_pa)
            return a.flow_cfm + t * (b.flow_cfm - a.flow_cfm)
    return None


def ranking_verdict(n_designs: int, rho: float) -> str:
    if n_designs < MIN_DESIGNS:
        return "INCONCLUSIVE"
    return "PASS" if rho >= SPEARMAN_MIN else "FAIL"


# ------------------------------------------------------------------ verification
def test_units_and_dimensions(v2):
    q = 0.0123                                   # m^3/s
    p = operating_point(v2, 2000, q)
    assert p.flow_cfm == pytest.approx(q * M.CFM_PER_M3S, rel=1e-12)
    assert p.flow_m3s == q and p.power_w > 0
    u_tip = 2000 * 2 * math.pi / 60 * v2.tip_radius / 1000
    assert 0 < p.dp_total_pa <= 0.95 * FB.RHO_AIR * u_tip**2     # Euler bound with vth <= 0.95 U
    assert p.dp_static_pa <= p.dp_total_pa                       # static never exceeds total


@pytest.mark.parametrize("rpm", [1000, 2000, 3500])
@pytest.mark.parametrize("cfg", ["a12x25_reference.yaml", "a12x25_reference_v1.yaml"])
def test_momentum_bound_air_power_below_shaft_power(cfg, rpm):
    bp = load_blade_params(CFG / cfg)
    c = pq_curve(bp, rpm)
    for p in c.points:
        assert p.flow_m3s * p.dp_total_pa <= p.power_w * (1.0 + 1e-12), p   # ideal-actuator limit
        assert 0.0 <= p.efficiency <= 1.0
        assert p.flow_m3s * max(p.dp_static_pa, 0.0) <= p.power_w * (1.0 + 1e-12)


def test_pressure_rise_is_zero_at_free_delivery(v2, v1):
    for bp in (v2, v1):
        c = pq_curve(bp, 2000)
        assert c.points[-1].dp_static_pa < 0, "free delivery not bracketed by the sweep"
        q = c.free_delivery_cfm / M.CFM_PER_M3S
        assert abs(operating_point(bp, 2000, q).dp_static_pa) < 1.5   # sweep-interpolation error only


def test_pq_monotone_on_unstalled_branch(v2, v1):
    for bp in (v2, v1):
        pts = pq_curve(bp, 2000).points
        i0 = max(range(len(pts)), key=lambda i: pts[i].dp_static_pa)
        for a, b in zip(pts[i0:], pts[i0 + 1:]):
            assert b.dp_static_pa <= a.dp_static_pa + 1e-6


def test_swirl_iteration_converges_up_to_free_delivery(v2, v1):
    for bp in (v2, v1):
        assert pq_curve(bp, 2000).converged
    # the flag is live: forcing a 1-iteration cap must trip it
    old = FB.N_ITER_MAX
    try:
        FB.N_ITER_MAX = 1
        assert not operating_point(v2, 2000, 0.02).converged
    finally:
        FB.N_ITER_MAX = old


def test_constants_single_source():
    assert FB.CFM_PER_M3S is M.CFM_PER_M3S
    assert FB.RHO_AIR is air.RHO_AMCA and FB.RHO_AIR == M.RHO_AIR
    assert FB.MU_AIR is air.MU_AIR
    assert FB.NU_AIR is air.NU_AIR


# ------------------------------------------------------------------ validation (Stock, complete-setup CFD)
def test_stock_v2_free_air_within_pre_registered_tolerance(v2):
    c = pq_curve(v2, 2000)
    assert abs(c.free_delivery_cfm / CFD_V2[0] - 1.0) <= ABS_TOL


def test_stock_v2_pq_slope_sign_and_order(v2):
    c = pq_curve(v2, 2000)
    q0, q5, q10 = (_flow_at(c, d) for d in (0, 5, 10))
    assert q0 > q5 > q10                       # flow falls as backpressure rises, as in CFD
    assert CFD_V2[0] > CFD_V2[5] > CFD_V2[10]


def test_bem_orders_stock_v1_above_stock_v2(v1, v2):
    b1, b2 = pq_curve(v1, 2000).free_delivery_cfm, pq_curve(v2, 2000).free_delivery_cfm
    assert CFD_V1_FREE > CFD_V2[0]
    assert b1 > b2


def test_ranking_verdict_rule():
    assert ranking_verdict(3, 1.0) == "INCONCLUSIVE"
    assert ranking_verdict(5, 0.59) == "FAIL"
    assert ranking_verdict(5, 0.6) == "PASS"
