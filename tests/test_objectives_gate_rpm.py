"""RV-3 finding: the structural gates must judge the rpm the design will actually run at.

evaluate_candidate set ``params.rpm = target_rpm`` only after the centrifugal-stress and resonance
gates, so those gates used whatever ``params.rpm`` held (BladeParams default 2000). For the 3900 rpm
Delta AFC1212DE model that under-stated stress about 3.8x and blade-pass frequency 2x.
"""

from __future__ import annotations

from fansim.fan_spec import get_fan_spec
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def _stopped_after_gates(tmp_path, params, **kw):
    # An impossible tip-gap floor stops evaluate_candidate right after the structural gates,
    # before any geometry build or CFD; the early return still carries the gate numbers.
    return evaluate_candidate(params, tmp_path, tip_gap_mm=1000.0, **kw)


def test_gates_use_the_fan_models_rpm(tmp_path):
    spec = get_fan_spec("delta_afc1212de")
    params = blade_from_flat(stock_blade_flat("a12x25"))
    assert params.rpm == 2000.0
    res = _stopped_after_gates(tmp_path, params, spec=spec)
    assert not res.feasible and "tip gap" in res.reason
    assert res.raw["bpf_hz"] == params.n_blades * spec.rpm / 60.0


def test_gates_use_the_searched_rpm(tmp_path):
    params = blade_from_flat(stock_blade_flat("a12x25"))
    res = _stopped_after_gates(tmp_path, params, rpm=1200.0)
    assert res.raw["bpf_hz"] == params.n_blades * 1200.0 / 60.0


def test_callers_params_are_not_mutated(tmp_path):
    spec = get_fan_spec("delta_afc1212de")
    params = blade_from_flat(stock_blade_flat("a12x25"))
    _stopped_after_gates(tmp_path, params, spec=spec)
    assert params.rpm == 2000.0


def test_high_rpm_trips_centrifugal_stress_gate(tmp_path):
    """RV-3 O1: centrifugal_root_stress must see target_rpm, not stale 2000 rpm."""
    params = blade_from_flat(stock_blade_flat("a12x25"))
    assert params.rpm == 2000.0
    # At stale 2000 rpm Stock PETG has SF > 400 and passes stress (stopping later at tip gap);
    # at 30000 rpm centrifugal root stress exceeds allowable (SF < 3) and trips "overstressed".
    res = _stopped_after_gates(tmp_path, params, rpm=30000.0)
    assert not res.feasible
    assert res.reason.startswith("overstressed:"), res.reason
