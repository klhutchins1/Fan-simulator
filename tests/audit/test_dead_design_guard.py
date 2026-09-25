"""A design that does not deliver air must be rejected, never scored (spec: optimizer guard)."""

from __future__ import annotations

import pytest

from fansim.optimize.system_curve import SystemCurveError, score_operating_point


@pytest.mark.parametrize("q_free, q_probe", [(-12.0, -20.0), (0.0, -5.0), (-3.0, 4.0)])
def test_non_delivering_free_air_is_rejected(q_free, q_probe):
    with pytest.raises(SystemCurveError):
        score_operating_point(q_free_cfm=q_free, q_probe_cfm=q_probe, p_probe_pa=5.0,
                              eta_free=0.1, eta_load=0.1, load_pa=5.0)


def test_delivering_design_still_scores():
    op = score_operating_point(q_free_cfm=50.0, q_probe_cfm=30.0, p_probe_pa=5.0,
                               eta_free=0.2, eta_load=0.3, load_pa=5.0)
    assert op.q_op_cfm > 0
