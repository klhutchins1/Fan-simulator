"""Axial-fan BEM screening model (fansim/fan_bem.py) — physics sanity + reference calibration.

A screening model, so tests check SHAPE + that the reference geometry lands near the CFD-validated
P-Q, not tight absolute accuracy (that needs the CFD tier / the §7.2-7.3 loss upgrades)."""

from __future__ import annotations

from fansim.fan_bem import operating_point, pq_curve
from fansim.geometry.blade import BladeParams


def test_reference_free_delivery_in_band():
    # default = the wrapped high-solidity a12x25 approximation; CFD gives ~65 CFM free, Noctua real 60.
    c = pq_curve(BladeParams(), rpm=2000)
    assert 50.0 < c.free_delivery_cfm < 80.0        # calibrated to the CFD reference
    assert c.shutoff_dp_pa > c.points[len(c.points) // 2].dp_static_pa  # pressure falls with flow
    assert 0.15 < c.peak_efficiency < 0.55          # realistic fan efficiency band (not inviscid ~0.8)


def test_pq_curve_declines_and_crosses_zero():
    c = pq_curve(BladeParams(), rpm=2000)
    dps = [p.dp_static_pa for p in c.points]
    assert dps[0] > dps[-1]                          # low flow = high pressure, high flow = low/neg
    assert dps[-1] <= 0.0 < dps[0]                   # free delivery (ΔP=0) is bracketed
    assert c.free_delivery_cfm > c.peak_eff_cfm      # peak efficiency sits below free delivery


def test_faster_rpm_more_pressure_and_flow():
    lo = pq_curve(BladeParams(), rpm=1000)
    hi = pq_curve(BladeParams(), rpm=2000)
    assert hi.shutoff_dp_pa > lo.shutoff_dp_pa       # ~rpm^2 pressure
    assert hi.free_delivery_cfm > lo.free_delivery_cfm


def test_operating_point_types():
    p = operating_point(BladeParams(), rpm=2000, flow_m3s=0.02)
    assert p.power_w > 0 and p.dp_total_pa >= p.dp_static_pa   # total >= static (swirl loss)
