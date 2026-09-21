from __future__ import annotations

import math

import pytest


def test_bemt_static_ct_cp_finite():
    from fansim.propeller.bemt_catalog import bemt_static_ct_cp

    out = bemt_static_ct_cp(9.0, 4.7, rpm=6026.0, blade_count=2)
    assert out["geometry_match"] == "approximate"
    assert out["j"] == 0.0
    assert out["ct"] > 0.0 and out["cp"] > 0.0
    assert math.isfinite(out["ct"]) and math.isfinite(out["cp"])


def test_load_uiuc_fixture_apcsf_9x47():
    from fansim.propeller.bemt_catalog import load_uiuc_static_fixture

    fx = load_uiuc_static_fixture("apcsf_9x4.7_static")
    assert fx["diameter_in"] == pytest.approx(9.0)
    assert fx["pitch_in"] == pytest.approx(4.7)
    assert fx["rpm"] == pytest.approx(6026)
    assert fx["ct"] == pytest.approx(0.1192)
    assert fx["cp"] == pytest.approx(0.0484)
