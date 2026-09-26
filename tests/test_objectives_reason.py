"""Graceful-degrade messaging for a failed system-curve intersection (no CFD/Docker)."""

from __future__ import annotations

from fansim.optimize.objectives import _operating_point_reason
from fansim.optimize.system_curve import SystemCurveError

_EXC = SystemCurveError("probe CFM must be positive")


def _reason(free_signed: float, probe_signed: float, converged: bool = True) -> str:
    return _operating_point_reason(
        _EXC,
        free_signed=free_signed,
        probe_signed=probe_signed,
        derate=1.0,
        p_free_pa=1.4,
        p_probe_pa=7.3,
        converged=converged,
        free_drift_pct=3.0,
        load_drift_pct=12.0,
    )


def test_stalled_probe_reports_free_air_not_raw_error():
    """Free delivery is fine but the hose probe reversed: report free-air + a lighter-hose hint,
    not the cryptic 'probe CFM must be positive'."""
    msg = _reason(free_signed=30.8, probe_signed=-22.0)
    assert "stalls at this hose" in msg
    assert "30.8 CFM" in msg  # free delivery surfaced
    assert "-22.0 CFM" in msg  # signed probe reversal surfaced
    assert "lighter hose" in msg
    assert "probe CFM must be positive" not in msg


def test_reversed_free_flow_keeps_duct_sign_hint():
    """Free delivery itself reversed -> the actionable spin/BC hint (not the stall message)."""
    msg = _reason(free_signed=-5.0, probe_signed=-9.0)
    assert "free outletFlow -5.0 CFM" in msg
    assert "rotor orientation" in msg and "fansim/cfd/orientation.py" in msg
    assert "stalls at this hose" not in msg


def test_unconverged_solve_is_flagged():
    msg = _reason(free_signed=30.8, probe_signed=-22.0, converged=False)
    assert "UNCONVERGED" in msg and "solver artifact" in msg


def test_converged_stall_has_no_unconverged_note():
    msg = _reason(free_signed=30.8, probe_signed=-22.0, converged=True)
    assert "UNCONVERGED" not in msg


def test_other_system_curve_failure_keeps_generic_message():
    """When both endpoints are positive, a different intersection failure keeps the plain form."""
    msg = _reason(free_signed=40.0, probe_signed=35.0)
    assert "system-curve:" in msg
    assert "1.4 Pa" in msg and "7.3 Pa" in msg
