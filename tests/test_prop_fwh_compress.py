"""Prop synthetic FW-H + BEMT compressibility smoke."""

from __future__ import annotations

from fansim.prop_spec import get_prop_spec
from fansim.propeller.bemt import _compressibility_cl_cd, analyze
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.noise import prop_fwh_from_mean_thrust


def test_compressibility_raises_cl_and_drag():
    cl0, cd0 = 1.0, 0.02
    cl, cd = _compressibility_cl_cd(cl0, cd0, 0.5)
    assert cl > cl0
    cl2, cd2 = _compressibility_cl_cd(cl0, cd0, 0.85)
    assert cd2 > cd0


def test_bemt_still_positive_thrust():
    p = analyze(prop_blade_params(get_prop_spec("fpv_5inch")), rpm=21000.0)
    assert p.thrust_g > 0
    assert p.figure_of_merit > 0


def test_prop_fwh_synthetic():
    out = prop_fwh_from_mean_thrust(2.0, rpm=21000.0, n_blades=3)
    assert out["analogy"] == "fwh_prop_synthetic"
    assert "noise_dba_band" in out
    assert out["samples"] > 10
