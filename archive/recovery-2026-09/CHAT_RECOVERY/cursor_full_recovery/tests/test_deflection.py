"""Analytic tip deflection vs tip gap (roadmap §7.6 FSI stage 1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fansim.geometry.blade import BladeParams
from fansim.optimize.print_penalty import PRINT_K_CFM, apply_print_penalty
from fansim.structural.deflection import deflection_report, tip_deflection_mm


def test_default_petg_clear_of_half_mm_gap():
    r = deflection_report(BladeParams(), tip_gap_mm=0.5, load_pa=8.0)
    assert r.ok
    assert r.tip_deflection_mm < 0.5
    assert r.gap_frac < 1.0


def test_tpu_can_fail_tip_gap_gate():
    r = deflection_report(
        BladeParams(), tip_gap_mm=0.5, material="TPU", load_pa=20.0)
    assert r.ok is False
    assert "FSI tip rub" in r.reason
    assert "TPU" in r.reason


def test_thinner_tip_deflects_more():
    base = BladeParams()
    thick_stations = tuple(
        replace(s, thickness=0.08) if s.r_frac >= 0.99 else s
        for s in base.stations
    )
    thin_stations = tuple(
        replace(s, thickness=0.02) if s.r_frac >= 0.99 else s
        for s in base.stations
    )
    thick = replace(base, stations=list(thick_stations))
    thin = replace(base, stations=list(thin_stations))
    d_thick = tip_deflection_mm(thick, load_pa=35.0)
    d_thin = tip_deflection_mm(thin, load_pa=35.0)
    # δ ∝ 1/t³ → (0.08/0.02)³ = 64×; allow slack for chord/station identity
    assert d_thin > d_thick * 30.0


def test_print_penalty_fsi_knocks_cfm():
    cfm_free, cfm_load, eta, stamps = apply_print_penalty(
        100.0, 80.0, 40.0,
        tip_deflection_mm=0.25,
        tip_gap_mm=0.5,
    )
    # k_fsi = 1 - 0.5 * 0.5 = 0.875 → floor 0.90; k_cfm = 0.95 * 0.90
    assert stamps["print_k_fsi"] == pytest.approx(0.90)
    assert stamps["print_k_cfm"] == pytest.approx(PRINT_K_CFM * 0.90)
    assert cfm_free == pytest.approx(100.0 * PRINT_K_CFM * 0.90)
    assert cfm_load == pytest.approx(80.0 * PRINT_K_CFM * 0.90)
    assert stamps["tip_deflection_mm"] == pytest.approx(0.25)
    assert stamps["deflection_gap_frac"] == pytest.approx(0.5)
    assert eta == pytest.approx(36.8)


def test_print_penalty_small_deflection_keeps_base_cfm():
    _, _, _, stamps = apply_print_penalty(
        100.0, 80.0, 40.0,
        tip_deflection_mm=0.0,
        tip_gap_mm=0.5,
    )
    assert stamps["print_k_fsi"] == pytest.approx(1.0)
    assert stamps["print_k_cfm"] == pytest.approx(PRINT_K_CFM)
