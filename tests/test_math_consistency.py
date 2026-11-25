"""Math / unit consistency guards from §10 accuracy checklist (no Docker)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from fansim.analyze.fan_curve import shut_off_pa
from fansim.cfd.metrics import CFM_PER_M3S, RHO_AIR
from fansim.fan_bem import pq_curve
from fansim.geometry.blade import BladeParams


def test_cfm_factor_is_single_source():
    """§10.9 — CFM conversion must not drift across modules (#49)."""
    assert CFM_PER_M3S == pytest.approx(2118.882)
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


def test_ducted_bem_source_drops_prandtl_tip_loss():
    """§10.3 — ducted fan BEM must not apply Prandtl F; gap leakage only."""
    src = Path("fansim/fan_bem.py").read_text(encoding="utf-8")
    assert "do NOT apply Prandtl" in src or "do not apply Prandtl" in src.lower()
    assert "K_TIP_LEAK" in src


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
