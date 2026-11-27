"""Math / unit consistency guards from §10 accuracy checklist (no Docker)."""

from __future__ import annotations

import math

import pytest

from fansim.analyze.fan_curve import shut_off_pa
from fansim.cfd.metrics import CFM_PER_M3S, RHO_AIR
from fansim.fan_bem import pq_curve
from fansim.geometry.blade import BladeParams


def test_cfm_factor_is_single_source():
    """§10.9 / #87 — CFM conversion is exact NIST SI (60 / 0.3048^3) and single-sourced (#49)."""
    assert CFM_PER_M3S == pytest.approx(60.0 / (0.3048**3), rel=1e-15)
    from fansim import fan_bem
    from fansim.optimize import meanline, multi_point

    assert fan_bem.CFM_PER_M3S == CFM_PER_M3S
    assert meanline.CFM_PER_M3S is CFM_PER_M3S
    assert multi_point.CFM_PER_M3S is CFM_PER_M3S


def test_cfd_rho_matches_amca_default():
    """§10.9 — screening CFD / AMCA proxies use ρ=1.2, not 1.225."""
    assert RHO_AIR == pytest.approx(1.2)


def test_bem_shutoff_is_q0_intercept_not_just_max_dp():
    """§10.7 — BEM shut-off follows Q→0 linear intercept like curve_report."""
    c = pq_curve(BladeParams(), rpm=2000, tip_gap_mm=0.5)
    pts = [{"cfm": p.flow_cfm, "static_pa": p.dp_static_pa} for p in c.points]
    expected = shut_off_pa(pts, q_near_zero=max(5.0, 0.15 * c.free_delivery_cfm))
    assert expected is not None
    # #50: BEM no longer rounds shut-off; must match the intercept exactly.
    assert c.shutoff_dp_pa == pytest.approx(expected, rel=1e-12, abs=0.0)


def test_ducted_bem_uses_gap_leakage_not_prandtl_tip_loss():
    """§10.3 — ducted fan BEM applies tip-gap leakage (K_TIP_LEAK), not Prandtl tip-loss roll-off."""
    from fansim.fan_bem import operating_point
    from fansim.geometry.blade import RadialStation

    # 1. Increasing tip gap monotonically lowers static rise via K_TIP_LEAK.
    p = BladeParams()
    p0 = operating_point(p, rpm=2000, flow_m3s=0.015, tip_gap_mm=0.0)
    p1 = operating_point(p, rpm=2000, flow_m3s=0.015, tip_gap_mm=0.5)
    p2 = operating_point(p, rpm=2000, flow_m3s=0.015, tip_gap_mm=2.0)
    assert p0.dp_static_pa > p1.dp_static_pa > p2.dp_static_pa

    # 2. A narrow outer-annulus blade (r_hub = 0.94 * r_tip, B = 2) at tip_gap_mm=0 still
    # carries full unattenuated Euler head (dp_total ≈ power / Q * SLIP). A Prandtl tip-loss
    # factor F -> 0 near r -> R would collapse outer-ring loading to a small fraction.
    outer = BladeParams(
        n_blades=2,
        hub_radius=51.7,
        tip_radius=55.0,
        stations=[
            RadialStation(r_frac=0.0, chord=20.0, stagger_deg=30.0, thickness=0.08, max_camber=0.03),
            RadialStation(r_frac=1.0, chord=20.0, stagger_deg=30.0, thickness=0.08, max_camber=0.03),
        ],
    )
    q = 0.0025
    pt = operating_point(outer, rpm=2000, flow_m3s=q, n_elem=4, tip_gap_mm=0.0)
    assert pt.dp_total_pa > 5.0
    assert pt.power_w > 0.0
    # Zero gap => zero tip-leakage loss; total pressure is pure SLIP * (shaft power / Q).
    from fansim.fan_bem import SLIP

    assert pt.dp_total_pa == pytest.approx(SLIP * pt.power_w / q, rel=1e-6)


def test_screening_grid_stamp_false():
    """§10.8 — every screening evaluate stamps grid_converged=False."""
    from fansim.optimize.objectives import SCREENING_GRID_STAMP

    assert SCREENING_GRID_STAMP["grid_converged"] is False
    assert "GCI" in SCREENING_GRID_STAMP["grid_note"]


def test_circular_inlet_helper_exists():
    """§10.10 — pure circular duct area check is available."""
    from fansim.cfd.duct_area import circular_inlet_area_ok

    r = 0.055
    assert circular_inlet_area_ok(math.pi * r * r, r)
