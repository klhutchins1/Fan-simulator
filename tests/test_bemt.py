# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""BEMT propeller performance (fansim/propeller/bemt.py) — physics sanity on synthetic + real props."""

from __future__ import annotations

from fansim.prop_spec import get_prop_spec
from fansim.propeller import prop_blade_params
from fansim.propeller.bemt import analyze


def test_static_thrust_positive_and_realistic():
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    r = analyze(p, rpm=30000)
    assert r.thrust_g > 500 and r.thrust_n > 0
    assert r.power_w > 0
    assert 1.0 < r.efficiency_g_per_w < 8.0        # realistic static hover efficiency band
    assert 0.4 < r.figure_of_merit <= 1.0          # physical figure of merit (ideal/actual)


def test_thrust_scales_with_rpm_squared():
    # prop affinity: thrust ~ rpm^2. Doubling rpm should ~quadruple thrust.
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    t1 = analyze(p, rpm=15000).thrust_n
    t2 = analyze(p, rpm=30000).thrust_n
    # ~4x from rpm^2. 30000 RPM is tip Mach ~0.58. The stall cap keeps
    # post-stall Cl at the polar value, so the high-RPM point is no longer
    # inflated. Measured ratio is 4.47.
    assert 3.3 < t2 / t1 < 4.57


def test_power_scales_faster_than_thrust():
    # power ~ rpm^3 grows faster than thrust ~ rpm^2 -> g/W drops at higher rpm
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    lo = analyze(p, rpm=12000)
    hi = analyze(p, rpm=30000)
    assert hi.power_w / lo.power_w > hi.thrust_n / lo.thrust_n
    assert hi.efficiency_g_per_w < lo.efficiency_g_per_w


def test_all_registry_props_produce_sane_numbers():
    for k in ("fpv_5inch", "cine_3inch", "longrange_7inch", "micro_2inch"):
        spec = get_prop_spec(k)
        r = analyze(prop_blade_params(spec), rpm=spec.rpm_max)
        assert r.thrust_g > 50 and 0.4 < r.figure_of_merit <= 1.0 and r.efficiency_g_per_w > 1.0


def test_forward_flight_reports_prop_efficiency():
    p = prop_blade_params(get_prop_spec("longrange_7inch"))
    r = analyze(p, rpm=18000, v_forward=15.0)       # forward flight
    assert r.prop_efficiency is not None and 0.0 < r.prop_efficiency < 1.0
