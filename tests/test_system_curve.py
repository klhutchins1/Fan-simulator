"""Smoke tests for system-curve math (fixtures from 2026-09-02 design spec)."""

from __future__ import annotations

import pytest

from fansim.fan_bem import CFM_PER_M3S
from fansim.optimize.system_curve import (
    REF_CFM,
    SystemCurveError,
    derated_probe_pa,
    intersect_fan_line,
    k_from_pa,
    score_operating_point,
)


def test_ref_cfm():
    assert REF_CFM == 50.0


def test_k_from_pa_eight_at_fifty():
    q_ref = REF_CFM / CFM_PER_M3S
    assert k_from_pa(8.0) == pytest.approx(8.0 / (q_ref * q_ref))


def test_probe_on_hose_is_exact_op():
    # Q0=80, Q1=50, P1=8, k from 8 Pa @ 50 CFM → op is 50 CFM, 8 Pa
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 50.0, 8.0, k)
    assert q_op == pytest.approx(50.0)
    assert p_op == pytest.approx(8.0)


def test_weaker_probe_raises_op_above_probe():
    k = k_from_pa(8.0)
    q_op, p_op = intersect_fan_line(80.0, 40.0, 8.0, k)
    assert q_op > 40.0
    assert p_op < 8.0


def test_inverted_probe_raises():
    with pytest.raises(SystemCurveError):
        intersect_fan_line(50.0, 60.0, 8.0, k_from_pa(8.0))


def test_score_clamps_efficiency_past_probe_point():
    # Hard hose relative to a weak probe → q_op can sit *below* probe CFM
    # (toward shutoff). Without clamp, t>1 would extrapolate eta above eta_load.
    op = score_operating_point(
        q_free_cfm=80.0, q_probe_cfm=60.0, p_probe_pa=8.0,
        eta_free=0.20, eta_load=0.35, load_pa=35.0,
    )
    assert op.q_op_cfm < 60.0
    assert op.eta == pytest.approx(0.35)


def test_derated_probe_pa_is_load_times_lambda_squared():
    assert derated_probe_pa(8.0, 1.0) == pytest.approx(8.0)
    assert derated_probe_pa(8.0, 0.5) == pytest.approx(2.0)
