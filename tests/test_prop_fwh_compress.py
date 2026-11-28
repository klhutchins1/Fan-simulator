"""Prop synthetic FW-H + BEMT compressibility smoke."""

from __future__ import annotations

import math

import pytest

from fansim.prop_spec import get_prop_spec
from fansim.propeller.bemt import _compressibility_cl_cd, analyze
from fansim.propeller.geometry import prop_blade_params
from fansim.propeller.noise import prop_fwh_from_mean_thrust


def test_compressibility_raises_cl_and_drag():
    cl0, cd0 = 1.0, 0.02
    cl, _cd = _compressibility_cl_cd(cl0, cd0, 0.5)
    assert cl > cl0
    _cl2, cd2 = _compressibility_cl_cd(cl0, cd0, 0.85)
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


def test_analyze_records_local_mach(monkeypatch):
    from fansim.propeller import bemt as bemt_mod

    recorded = []
    real = bemt_mod._compressibility_cl_cd

    def _spy(cl, cd, mach, *, stalled=False, cl_cap=None):
        recorded.append(float(mach))
        return real(cl, cd, mach, stalled=stalled, cl_cap=cl_cap)

    monkeypatch.setattr(bemt_mod, "_compressibility_cl_cd", _spy)
    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    analyze(p, rpm=30000.0)
    assert recorded, "analyze never called _compressibility_cl_cd"
    lo, hi = min(recorded), max(recorded)
    assert hi >= 0.45
    assert hi >= 1.5 * lo


def test_compressibility_raises_high_rpm_thrust(monkeypatch):
    from fansim.propeller import bemt as bemt_mod

    p = prop_blade_params(get_prop_spec("fpv_5inch"))
    with_correction = analyze(p, rpm=30000.0)
    def _identity(cl, cd, mach, *, stalled=False, cl_cap=None):
        return (cl, cd)

    monkeypatch.setattr(bemt_mod, "_compressibility_cl_cd", _identity)
    without = analyze(p, rpm=30000.0)
    assert with_correction.thrust_n > without.thrust_n


def test_stalled_lift_is_unchanged_and_wave_drag_remains():
    cl, cd = _compressibility_cl_cd(1.0, 0.02, 0.5, stalled=True)
    assert cl == 1.0
    assert cd == 0.02
    cl_w, cd_w = _compressibility_cl_cd(1.0, 0.02, 0.85, stalled=True, cl_cap=0.1)
    assert cl_w == 1.0
    assert cd_w == pytest.approx(0.0272)


def test_attached_lift_respects_cap():
    cl, cd = _compressibility_cl_cd(1.0, 0.02, 0.5, stalled=False, cl_cap=1.05)
    assert cl == pytest.approx(1.05)
    assert cd == 0.02
    neg, _ = _compressibility_cl_cd(-0.5, 0.02, 0.5, cl_cap=0.4)
    assert neg == pytest.approx(-0.4)


def test_analytic_stall_is_not_scaled():
    from fansim.propeller.bemt import _section_aero

    cl, _cd, stalled, cap = _section_aero(math.radians(20.0), 0.0, re=None)
    assert stalled is True
    assert cap == pytest.approx(1.4)
    assert 0.5 < cl < cap
    assert _cd > 0.10
    out, cd_out = _compressibility_cl_cd(cl, _cd, 0.5, stalled=stalled, cl_cap=cap)
    assert out == pytest.approx(cl)
    assert cd_out == pytest.approx(_cd)


def test_analytic_clamp_before_stall_angle_is_stalled():
    from fansim.propeller.bemt import _section_aero

    cl, _cd, stalled, cap = _section_aero(math.radians(13.0), 0.0, re=None)
    assert stalled is True
    assert cl == pytest.approx(1.4)
    assert cap == pytest.approx(1.4)


def test_attached_table_lift_rises_inside_the_peak():
    from fansim.propeller.bemt import _section_aero

    cl, cd, stalled, cap = _section_aero(math.radians(4.0), 0.04, re=80000.0)
    assert stalled is False
    assert cl == pytest.approx(0.65703, abs=1e-5)
    out, _cd = _compressibility_cl_cd(cl, cd, 0.5, stalled=stalled, cl_cap=cap)
    assert out > cl
    assert out == pytest.approx(cl / math.sqrt(0.75))
    assert out <= cap


def test_low_re_section_uses_analytic_stall():
    from fansim.propeller.bemt import _section_aero

    cl, cd, stalled, cap = _section_aero(math.radians(20.0), 0.0, re=16000.0)
    assert stalled is True
    assert cap == pytest.approx(0.920926996097583)
    assert 0.3 < cl < cap
    assert cd > 0.15
