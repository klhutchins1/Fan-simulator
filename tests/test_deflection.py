"""Analytic tip deflection vs tip gap (roadmap §7.6 FSI stage 1)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fansim.geometry.blade import BladeParams
from fansim.manufacturability.materials import MATERIALS
from fansim.optimize.print_penalty import PRINT_K_CFM, apply_print_penalty
from fansim.structural.deflection import deflection_report, tip_deflection_mm


def test_default_petg_clear_of_half_mm_gap():
    r = deflection_report(BladeParams(), tip_gap_mm=0.5, load_pa=8.0)
    assert r.ok
    assert r.tip_deflection_mm < 0.5
    assert r.gap_frac < 1.0
    assert r.e_fdm_knockdown == pytest.approx(0.70)  # §10.11 FDM E knockdown


def test_resin_skips_fdm_e_knockdown():
    """§19.17: RESIN is in MATERIALS and keeps full E (knockdown 1.0)."""
    from fansim.structural.deflection import _fdm_e_factor

    assert "RESIN" in MATERIALS
    assert _fdm_e_factor("RESIN") == pytest.approx(1.0)
    assert _fdm_e_factor("PETG") == pytest.approx(0.70)
    d_resin = tip_deflection_mm(BladeParams(), material="RESIN", load_pa=20.0)
    d_petg = tip_deflection_mm(BladeParams(), material="PETG", load_pa=20.0)
    # Same load; PETG E_eff = 2.1*0.7, RESIN E = 2.5 → PETG deflects more
    assert d_petg > d_resin


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


def test_stock_blade_flags_beam_regime_warn():
    """§19.18: Stock tip aspect ≈ 1.0; gate still passes but stamps regime WARN."""
    from pathlib import Path

    from fansim.geometry.config import load_blade_params
    from fansim.structural.deflection import BEAM_ASPECT_MIN, beam_aspect_ratio
    from fansim.structural.flutter import flutter_report

    stock = load_blade_params(Path("config/problems/a12x25_reference.yaml"))
    assert beam_aspect_ratio(stock, station="tip") < BEAM_ASPECT_MIN
    r = deflection_report(stock, tip_gap_mm=0.5, load_pa=10.0)
    assert r.ok
    assert r.beam_regime_ok is False
    assert "WARN beam regime" in r.reason
    fr = flutter_report(stock)
    assert fr.ok  # margin still clears 1.2× BPF
    assert fr.beam_regime_ok is False
    assert "WARN beam regime" in fr.reason


def test_slender_beam_regime_ok():
    """Prismatic long span clears BEAM_ASPECT_MIN and leaves reason empty when gate passes."""
    from fansim.geometry.blade import RadialStation
    from fansim.structural.deflection import BEAM_ASPECT_MIN, beam_aspect_ratio

    sts = [RadialStation(r, 8.0, 30.0, thickness=0.10) for r in (0.0, 0.5, 1.0)]
    slender = replace(BladeParams(), stations=sts, hub_radius=20.0, tip_radius=60.0)
    assert beam_aspect_ratio(slender, station="tip") >= BEAM_ASPECT_MIN
    r = deflection_report(slender, tip_gap_mm=5.0, load_pa=1.0)
    assert r.ok and r.beam_regime_ok
    assert r.reason == ""
