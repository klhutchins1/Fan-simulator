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


# --- opt-in axial-force pressure model (QA-4) --------------------------------------------------
import copy  # noqa: E402

import pytest  # noqa: E402

from fansim.geometry.config import load_blade_params  # noqa: E402

AX = "axial_force"


def _stock7():
    return load_blade_params("config/problems/a12x25_reference.yaml")


def _restagger(p, deg):
    q = copy.deepcopy(p)
    for s in q.stations:
        s.stagger_deg = deg
    return q


def test_default_pressure_model_is_euler_and_unchanged():
    # A lock on the BEM code, so it keeps a fixed input: the v2 Stock (Stock itself moved to v3, 27.4).
    p = load_blade_params("config/problems/a12x25_reference_planar.yaml")
    a, b = pq_curve(p, 2000.0), pq_curve(p, 2000.0, pressure_model="euler")
    assert a == b
    assert a.free_delivery_cfm == pytest.approx(58.2, abs=0.05)
    assert a.shutoff_dp_pa == pytest.approx(38.87, abs=0.01)


def test_unknown_pressure_model_rejected():
    with pytest.raises(ValueError):
        operating_point(_stock7(), 2000.0, 0.02, pressure_model="bogus")


def test_axial_force_stock_calibration():
    """QA rule (a): Stock 7-station within 60.1 CFM ±10 % and 22.9 Pa ±25 % (datasheet; a fit)."""
    c = pq_curve(_stock7(), 2000.0, pressure_model=AX)
    assert c.free_status == "crossed"
    assert 54.1 <= c.free_delivery_cfm <= 66.1 and 17.2 <= c.shutoff_dp_pa <= 28.6


@pytest.mark.parametrize("stagger", [89.0, -45.0, -60.0])
def test_axial_force_paddle_and_reversed_are_not_fans(stagger):
    """QA rule (b): the Euler exploits (paddle 62.5 CFM at η 0.55; reversed blades +38 Pa) are gone."""
    stock = pq_curve(_stock7(), 2000.0, pressure_model=AX)
    c = pq_curve(_restagger(_stock7(), stagger), 2000.0, pressure_model=AX)
    assert c.free_status == "no_rise" or (
        c.free_delivery_cfm < 0.5 * stock.free_delivery_cfm
        and c.peak_efficiency < 0.5 * stock.peak_efficiency)


def test_axial_force_reversed_blade_gives_negative_pressure():
    pt = operating_point(_restagger(_stock7(), -45.0), 2000.0, 0.005, pressure_model=AX)
    assert pt.dp_static_pa < 0.0


def test_axial_force_zero_blades_and_efficiency_bounds():
    assert pq_curve(BladeParams(n_blades=0), 2000.0, pressure_model=AX).free_delivery_cfm == 0.0
    c = pq_curve(_stock7(), 2000.0, pressure_model=AX)
    assert all(0.0 <= p.efficiency < 1.0 for p in c.points)


def test_axial_force_efficiency_never_exceeds_one():
    """QA r4 E_rand1396 (11 blades, chords 48/58/50 mm): peak η 111 % before the energy bound."""
    from fansim.optimize.search_space import blade_from_flat

    from fansim.geometry.config import load_blade_params
    from fansim.optimize.search_space import blade_to_flat

    # E_rand1396 was defined on the v2 (planar) Stock flat; its other fields come from there.
    v2 = blade_to_flat(load_blade_params("config/problems/a12x25_reference_planar.yaml"))
    flat = {**v2, "n_blades": 11, "stagger_root": 51.145, "stagger_mid": 33.679,
            "stagger_tip": 24.794, "chord_root": 48.465, "chord_mid": 58.483, "chord_tip": 50.157,
            "max_camber": 0.0048, "thickness_root": 0.08, "thickness_mid": 0.06,
            "thickness_tip": 0.04, "camber_pos": 0.4, "hub_radius": 21.5, "tip_radius": 54.5,
            "sweep_mid": 0, "sweep_tip": 0, "lean_mid": 0, "lean_tip": 0}
    c = pq_curve(blade_from_flat(flat), 2000.0, pressure_model=AX)
    assert all(0.0 <= p.efficiency <= 1.0 + 1e-9 for p in c.points)
    assert c.peak_efficiency >= 0.99            # the bound is active on this design
