"""Audit #8 rules (scripts/audit_prop_cfd.py): C_T/C_P normalisation and verdicts, no CFD."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "apc", Path(__file__).resolve().parents[2] / "scripts" / "audit_prop_cfd.py")
apc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apc)


def _uiuc_result(fx, scale_t=1.0, scale_p=1.0):
    """CFD-shaped result that reproduces the UIUC static point at this density."""
    rho = apc.P_INF / (apc.R_AIR * apc.T_INF)
    n, d = fx["rpm"] / 60.0, fx["diameter_in"] * 0.0254
    return {"thrust_n": scale_t * fx["ct"] * rho * n * n * d ** 4,
            "shaft_power_w": scale_p * fx["cp"] * rho * n ** 3 * d ** 5,
            "thrust_sign_ok": True, "converged": True}


def test_uiuc_static_point_is_about_4n_and_37w():
    fx, _, _ = apc.apc_setup()
    r = _uiuc_result(fx)
    assert r["thrust_n"] == pytest.approx(3.9, rel=0.03)
    assert r["shaft_power_w"] == pytest.approx(36.0, rel=0.05)


def test_coeffs_round_trip_and_validation_band():
    fx, _, _ = apc.apc_setup()
    c = apc.coeffs(_uiuc_result(fx), fx)
    assert c["e_ct"] == pytest.approx(0.0, abs=1e-9) and c["e_cp"] == pytest.approx(0.0, abs=1e-9)
    assert apc.validation_verdict(c, True)["verdict"] == "PASS"
    hi = apc.coeffs(_uiuc_result(fx, scale_t=1.2), fx)        # +20 % C_T > 15 % tol
    assert apc.validation_verdict(hi, True)["verdict"] == "FAIL"
    assert apc.validation_verdict(c, False)["verdict"] == "INCONCLUSIVE"


def test_direction_verdict():
    good = {"thrust_n": 3.9, "shaft_power_w": 36.0, "thrust_sign_ok": True, "converged": True}
    rev = {"thrust_n": -1.0, "shaft_power_w": 30.0, "thrust_sign_ok": False, "converged": True}
    assert apc.direction_verdict(good, rev)["verdict"] == "PASS"
    assert apc.direction_verdict({**good, "thrust_sign_ok": False}, rev)["verdict"] == "FAIL"
    assert apc.direction_verdict(good, {**rev, "converged": False})["verdict"] == "INCONCLUSIVE"
    better_rev = {**rev, "thrust_n": -5.0, "shaft_power_w": 30.0}
    assert apc.direction_verdict(good, better_rev)["verdict"] == "FAIL"
    assert apc.direction_verdict(good, None)["verdict"] == "INCONCLUSIVE"
