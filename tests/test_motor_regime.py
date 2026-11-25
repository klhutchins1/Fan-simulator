"""Tests for the motor envelope gate and physics-regime classifier."""


import pytest

from fansim.motor import A12X25_MOTOR, MotorEnvelope, check_envelope
from fansim.physics import classify_regime, fan_regime

# ---- motor envelope ----

def test_motor_derived_quantities():
    m = MotorEnvelope("test", rated_rpm=2000.0, max_input_power_w=1.68, motor_efficiency=0.4)
    assert m.rated_omega == pytest.approx(209.44, abs=0.1)
    assert m.max_shaft_power_w == pytest.approx(0.672)
    assert m.max_torque_nm == pytest.approx(0.672 / 209.44, rel=1e-3)


def test_feasible_low_power_design():
    chk = check_envelope(0.4, A12X25_MOTOR)
    assert chk.feasible and chk.power_margin > 1.0


def test_infeasible_high_power_design():
    # ~2 W shaft (a high-flow idealized design) exceeds the ~0.67 W stock motor
    chk = check_envelope(2.0, A12X25_MOTOR)
    assert not chk.feasible
    assert chk.power_margin < 1.0
    assert "shaft" in chk.reason


def test_torque_limit_flags():
    m = MotorEnvelope("t", rated_rpm=2000.0, max_input_power_w=10.0, motor_efficiency=1.0)
    # power OK (10 W cap) but torque above rated-speed torque should still flag
    over_torque = m.max_torque_nm * 2.0
    chk = check_envelope(0.5, m, torque_nm=over_torque)
    assert not chk.feasible and "mN.m" in chk.reason


# ---- physics regime ----

def test_axial_fan_regime_is_incompressible_turbulent():
    from fansim.physics.air import NU_AIR
    r = fan_regime(tip_speed_ms=11.6, diameter_m=0.11)
    assert r.reynolds == pytest.approx(11.6 * 0.11 / NU_AIR, rel=1e-6)  # ~84600
    assert r.mach < 0.05
    assert not r.compressible
    assert r.turbulence_model == "k-omega SST"
    assert "simpleFoam" in r.solver


def test_low_reynolds_is_laminar():
    r = classify_regime(length_m=0.001, velocity_ms=0.01)  # Re ~ 0.7
    assert r.turbulence_model == "laminar"


def test_high_mach_is_compressible():
    r = classify_regime(length_m=0.1, velocity_ms=200.0)   # Ma ~ 0.58
    assert r.compressible
    assert "rhoSimpleFoam" in r.solver


def test_acoustics_flag_selects_transient_tier():
    r = fan_regime(11.6, 0.11, need_acoustics=True)
    assert "FW-H" in r.transient_tier
