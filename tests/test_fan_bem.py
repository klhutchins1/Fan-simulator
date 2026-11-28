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
import copy

import pytest

from fansim.geometry.config import load_blade_params

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
    # #117: builder radius mapping (hub - root_embed .. tip) moved Stock v2 free delivery 58.2 -> 57.85 CFM.
    assert a.free_delivery_cfm == pytest.approx(57.85, abs=0.05)
    # Unrounded Q→0 intercept; NU_AIR derive (#48) + no internal round (#50) + #117 mapping.
    assert a.shutoff_dp_pa == pytest.approx(38.80, abs=0.15)


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
    from fansim.geometry.config import load_blade_params
    from fansim.optimize.search_space import blade_from_flat, blade_to_flat

    # E_rand1396 was defined on the v2 (planar) Stock flat; its other fields come from there.
    v2 = blade_to_flat(load_blade_params("config/problems/a12x25_reference_planar.yaml"))
    flat = {**v2, "n_blades": 11, "stagger_root": 51.145, "stagger_mid": 33.679,
            "stagger_tip": 24.794, "chord_root": 48.465, "chord_mid": 58.483, "chord_tip": 50.157,
            "max_camber": 0.0048, "thickness_root": 0.08, "thickness_mid": 0.06,
            "thickness_tip": 0.04, "camber_pos": 0.4, "hub_radius": 21.5, "tip_radius": 54.5,
            "sweep_mid": 0, "sweep_tip": 0, "lean_mid": 0, "lean_tip": 0}
    c = pq_curve(blade_from_flat(flat), 2000.0, pressure_model=AX)
    assert all(0.0 <= p.efficiency <= 1.0 + 1e-9 for p in c.points)
# Energy bound near-cap; NU_AIR (#48) can nudge peak slightly (#50).
    assert c.peak_efficiency >= 0.95


# --- RV-3 review bug-fix regression tests --------------------------------------------------------

def test_viterna_no_pole_beyond_90_deg():
    """Viterna–Corrigan (1982) has a 1/sin(a) pole at ±180° if applied past ±90°."""
    import math

    from fansim.fan_bem import CD_90, _cl_cd_post_stall

    for deg in (-180.0, -179.9, -179.0, -175.0, -150.0, -120.0, -90.0, 90.0, 120.0, 150.0, 179.0, 180.0):
        cl, cd = _cl_cd_post_stall(math.radians(deg), 0.02, 40000.0)
        assert math.isfinite(cl) and math.isfinite(cd)
        assert abs(cl) <= 0.5 * CD_90 + 1e-6, f"alpha={deg}: cl={cl}"
        assert 0.0 < cd <= CD_90 + 1e-6, f"alpha={deg}: cd={cd}"
    cl_m180, _ = _cl_cd_post_stall(math.radians(-180.0), 0.02, 40000.0)
    cl_p180, _ = _cl_cd_post_stall(math.radians(180.0), 0.02, 40000.0)
    assert abs(cl_m180) < 1e-9 and abs(cl_p180) < 1e-9


def test_reynolds_scales_with_custom_rho():
    """At non-default density, nu = MU_AIR / rho so Re depends on rho (and alters low-Re polars)."""
    stock = _stock7()
    p_hi = operating_point(stock, 1200.0, 0.01, rho=1.2)
    p_lo = operating_point(stock, 1200.0, 0.01, rho=0.6)
    # If nu were hardcoded at NU_AIR, Re would be identical and dp_total / rho would be identical.
    assert abs(p_hi.dp_total_pa / 1.2 - p_lo.dp_total_pa / 0.6) > 1e-4


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rpm": -100.0},
        {"flow_m3s": -0.01},
        {"rho": 0.0},
        {"rho": -1.2},
        {"n_elem": 0},
        {"tip_gap_mm": -1.0},
        {"stator": True, "pressure_model": AX},
        {"pressure_model": "bogus"},
    ],
)
def test_operating_point_rejects_invalid_inputs(kwargs):
    args = {"rpm": 2000.0, "flow_m3s": 0.02, **kwargs}
    with pytest.raises(ValueError):
        operating_point(_stock7(), **args)


def test_operating_point_rejects_negative_hub_and_empty_stations():
    bad_hub = copy.deepcopy(_stock7())
    bad_hub.hub_radius = -5.0
    with pytest.raises(ValueError):
        operating_point(bad_hub, 2000.0, 0.02)

    no_st = copy.deepcopy(_stock7())
    no_st.stations = []
    with pytest.raises(ValueError):
        operating_point(no_st, 2000.0, 0.02)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rpm": -100.0},
        {"rho": 0.0},
        {"n_elem": 0},
        {"n_points": 1},
        {"tip_gap_mm": -1.0},
        {"stator": True, "pressure_model": AX},
        {"pressure_model": "bogus"},
    ],
)
def test_pq_curve_rejects_invalid_inputs(kwargs):
    args = {"rpm": 2000.0, **kwargs}
    with pytest.raises(ValueError):
        pq_curve(_stock7(), **args)


def test_pq_curve_validates_pressure_model_even_for_zero_blades():
    with pytest.raises(ValueError):
        pq_curve(BladeParams(n_blades=0), 2000.0, pressure_model="bogus")


def test_degenerate_zero_rpm_and_inverted_radii():
    c0 = pq_curve(_stock7(), 0.0)
    assert (c0.free_status, c0.points, c0.converged) == ("no_rise", [], False)

    inv = copy.deepcopy(_stock7())
    inv.hub_radius, inv.tip_radius = 60.0, 50.0
    pt = operating_point(inv, 2000.0, 0.02)
    assert pt.converged is False and pt.dp_static_pa == 0.0


def test_fan_point_fields_are_native_python_floats():
    pt = operating_point(_stock7(), 2000.0, 0.02)
    for field in ("flow_cfm", "flow_m3s", "dp_static_pa", "dp_total_pa", "efficiency", "power_w"):
        assert type(getattr(pt, field)) is float, f"{field} was {type(getattr(pt, field))}"


def test_single_element_euler_identity_exact():
    """Direct analytic verification of the Euler + swirl-KE + friction equations on 1 element."""
    import math

    from fansim.fan_bem import K_FRICTION, RHO_AIR, SLIP

    bp = copy.deepcopy(_stock7())
    for s in bp.stations:
        s.chord = 35.0
        s.stagger_deg = 32.0
        s.max_camber = 0.02
    q = 0.02
    p_no_st = operating_point(bp, 2000.0, q, n_elem=1, tip_gap_mm=0.0, stator=False)
    p_st = operating_point(bp, 2000.0, q, n_elem=1, tip_gap_mm=0.0, stator=True)
    hub_r, tip_r = bp.hub_radius / 1000.0, bp.tip_radius / 1000.0
    r = 0.5 * (hub_r + tip_r)
    area = math.pi * (tip_r * tip_r - hub_r * hub_r)
    vx = q / area
    u = (2000.0 * 2.0 * math.pi / 60.0) * r
    vth = p_no_st.power_w / (RHO_AIR * q * u)
    vth_eff = SLIP * vth
    assert p_no_st.dp_total_pa == pytest.approx(RHO_AIR * u * vth_eff, rel=1e-12)
    swirl_ke = 0.5 * RHO_AIR * vth_eff * vth_eff
    assert p_st.dp_static_pa - p_no_st.dp_static_pa == pytest.approx(swirl_ke, rel=1e-12)
    assert p_no_st.dp_static_pa == pytest.approx(
        p_no_st.dp_total_pa - swirl_ke - K_FRICTION * 0.5 * RHO_AIR * vx * vx, rel=1e-12
    )


def test_pq_curve_high_flow_crossing_ignores_low_flow_stall_dip(monkeypatch):
    """#97: a low-flow stall dip below 0 Pa must not mask the true high-flow free-delivery crossing."""
    import fansim.fan_bem as fb
    from fansim.cfd.metrics import CFM_PER_M3S

    profile = [
        (10.0, 8.0),
        (20.0, -2.0),   # stall dip below 0 Pa (would cross at 18 CFM)
        (30.0, 6.0),    # recovers on main branch
        (40.0, 3.0),
        (50.0, -3.0),   # true high-flow free-delivery crossing at 45 CFM
    ]
    it = iter(profile)

    def _fake_op(*_a, **_k):
        cfm, dp = next(it)
        return fb.FanPoint(
            flow_cfm=cfm, flow_m3s=cfm / CFM_PER_M3S,
            dp_static_pa=dp, dp_total_pa=max(dp, 0.0) + 1.0,
            efficiency=0.2 if dp > 0 else 0.0, power_w=1.0, converged=True,
        )

    monkeypatch.setattr(fb, "operating_point", _fake_op)
    c = pq_curve(_stock7(), 2000.0, n_points=len(profile))
    assert c.free_status == "crossed"
    assert c.free_delivery_cfm == pytest.approx(45.0, abs=1e-9)


def test_pq_curve_beyond_sweep_when_tail_recovers_positive(monkeypatch):
    """#97: if static rise dips below 0 Pa early but ends positive, free delivery is beyond_sweep."""
    import fansim.fan_bem as fb
    from fansim.cfd.metrics import CFM_PER_M3S

    profile = [(10.0, 5.0), (20.0, -1.0), (30.0, 4.0), (40.0, 6.0)]
    it = iter(profile)

    def _fake_op(*_a, **_k):
        cfm, dp = next(it)
        return fb.FanPoint(
            flow_cfm=cfm, flow_m3s=cfm / CFM_PER_M3S,
            dp_static_pa=dp, dp_total_pa=max(dp, 0.0) + 1.0,
            efficiency=0.2 if dp > 0 else 0.0, power_w=1.0, converged=True,
        )

    monkeypatch.setattr(fb, "operating_point", _fake_op)
    c = pq_curve(_stock7(), 2000.0, n_points=len(profile))
    assert c.free_status == "beyond_sweep"
    assert c.free_delivery_cfm == pytest.approx(40.0, abs=1e-9)


def test_pq_curve_shutoff_extrapolated_flag(monkeypatch):
    """#97: FanCurve explicitly reports whether shutoff_dp_pa was extrapolated or fell back to max."""
    import fansim.fan_bem as fb
    from fansim.cfd.metrics import CFM_PER_M3S

    c_stock = pq_curve(_stock7(), 2000.0)
    assert c_stock.shutoff_extrapolated is True

    c_zero = pq_curve(_stock7(), 0.0)
    assert c_zero.shutoff_extrapolated is False

    # Lowest sweep point (20 CFM) exceeds q_near_zero = max(5, 0.15 * 45) = 6.75 CFM -> fallback
    profile = [(20.0, 12.0), (30.0, 8.0), (40.0, 3.0), (50.0, -3.0)]
    it = iter(profile)

    def _fake_op(*_a, **_k):
        cfm, dp = next(it)
        return fb.FanPoint(
            flow_cfm=cfm, flow_m3s=cfm / CFM_PER_M3S,
            dp_static_pa=dp, dp_total_pa=max(dp, 0.0) + 1.0,
            efficiency=0.2 if dp > 0 else 0.0, power_w=1.0, converged=True,
        )

    monkeypatch.setattr(fb, "operating_point", _fake_op)
    c_fb = pq_curve(_stock7(), 2000.0, n_points=len(profile))
    assert c_fb.shutoff_extrapolated is False
    assert c_fb.shutoff_dp_pa == pytest.approx(12.0, abs=1e-9)


