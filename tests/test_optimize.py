"""Optimizer plumbing tests that do not require CFD: search space, gates, infeasible path."""

from __future__ import annotations

import optuna
import pytest

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.manufacturability import MATERIALS, check_printability
from fansim.optimize.objectives import INFEASIBLE, evaluate_candidate
from fansim.optimize.search_space import suggest_params
from fansim.structural import centrifugal_root_stress


def test_suggest_params_within_bounds():
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"])
    for _ in range(20):
        params = suggest_params(study.ask())
        assert 5 <= params.n_blades <= 11
        assert len(params.stations) == 3
        for st in params.stations:
            assert 14.0 <= st.chord <= 40.0
            assert 15.0 <= st.stagger_deg <= 70.0
            assert 0.0 <= st.lean_deg <= 45.0  # circumferential wrap DOF


def test_printability_rejects_thin_blade():
    thin = BladeParams(stations=[
        RadialStation(0.0, 10.0, 50.0, thickness=0.02),  # 0.2 mm section -> unprintable
        RadialStation(1.0, 10.0, 30.0, thickness=0.02),
    ])
    assert not check_printability(thin).printable


def test_printability_accepts_baseline():
    assert check_printability(BladeParams()).printable


def test_printability_allows_thin_tip_edge_but_gates_thin_body():
    # A blade with a solid body but a thin TIP edge (~one extrusion width) is printable — real blades
    # have thin tips. Radius-aware: 2 walls (0.8 mm) for the body, 1 wall (0.4 mm) for the tip edge.
    thin_tip = BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0, thickness=0.10),   # body ~3.4 mm
        RadialStation(0.5, 44.0, 26.0, thickness=0.08),
        RadialStation(0.95, 8.0, 22.0, thickness=0.06),   # tip edge ~0.48 mm (> 0.4 one-wall floor)
    ])
    assert check_printability(thin_tip).printable         # thin tip alone must NOT fail the gate

    tip_below_one_wall = BladeParams(stations=[
        RadialStation(0.0, 34.0, 26.0, thickness=0.10),
        RadialStation(0.95, 4.0, 22.0, thickness=0.06),   # ~0.24 mm < one extrusion width -> unprintable
    ])
    assert not check_printability(tip_below_one_wall).printable


def test_centrifugal_stress_negligible_at_2000rpm():
    r = centrifugal_root_stress(BladeParams(), material="PETG")
    assert r.ok and r.sigma_root_mpa < 1.0  # far below any filament yield


def test_all_blade_materials_have_positive_properties():
    for name, m in MATERIALS.items():
        assert m.yield_strength_mpa > 0 and m.density_kg_m3 > 0


def test_evaluate_candidate_gate_is_cheap_and_infeasible(tmp_path):
    """An unprintable design is rejected by the gate before any CFD runs."""
    thin = BladeParams(stations=[
        RadialStation(0.0, 10.0, 50.0, thickness=0.02),
        RadialStation(1.0, 10.0, 30.0, thickness=0.02),
    ])
    res = evaluate_candidate(thin, tmp_path / "c", procs=1)
    assert res.feasible is False
    assert "unprintable" in res.reason
    assert res.as_tuple() == (INFEASIBLE, INFEASIBLE, INFEASIBLE)


def test_evaluate_candidate_rejects_tpu_vibration_before_cfd(tmp_path):
    """§7.6 / UI Assess material gate: flutter resonance rejects without CFD."""
    from dataclasses import replace

    # 3000 rpm keeps centrifugal SF OK on TPU; flutter margin fails (audit #5 case).
    p = replace(BladeParams(), rpm=3000.0, n_blades=7)
    res = evaluate_candidate(p, tmp_path / "vib", procs=1, material="TPU")
    assert res.feasible is False
    assert "vibration" in res.reason.lower() or "blade-pass" in res.reason.lower()
