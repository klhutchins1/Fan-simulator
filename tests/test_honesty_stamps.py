"""Honesty contract: screening mesh stamps (§10.8 / §11.1). No Docker CFD."""

from __future__ import annotations

from pathlib import Path

from fansim.centrifugal.evaluate import evaluate_mixed_flow
from fansim.centrifugal.geometry import MixedFlowParams
from fansim.cror.evaluate import evaluate_cror
from fansim.cror.geometry import CrorParams
from fansim.geometry.blade import BladeParams
from fansim.optimize.objectives import SCREENING_GRID_STAMP, evaluate_candidate

STAMP_KEYS = ("grid_converged", "grid_note")


def test_screening_grid_stamp_is_not_converged():
    assert SCREENING_GRID_STAMP["grid_converged"] is False
    assert "GCI" in SCREENING_GRID_STAMP["grid_note"]


def _assert_screening_stamp_on_raw(raw: dict) -> None:
    for key in STAMP_KEYS:
        assert key in raw, f"missing {key!r} on raw"
    assert raw["grid_converged"] is False
    assert "GCI" in str(raw["grid_note"])


def test_axial_tip_gap_infeasible_carries_screening_stamp(tmp_path):
    """Cheap tip-gap gate before CFD must still stamp screening honesty."""
    params = BladeParams(tip_radius=54.9)
    res = evaluate_candidate(params, tmp_path / "w", tip_gap_mm=5.0, procs=1)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    _assert_screening_stamp_on_raw(res.raw)


def test_mixed_tip_gap_infeasible_carries_screening_stamp(tmp_path):
    params = MixedFlowParams(r_tip_mm=54.9)
    res = evaluate_mixed_flow(params, tmp_path / "w", tip_gap_mm=5.0)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    _assert_screening_stamp_on_raw(res.raw)


def test_cror_tip_gap_infeasible_carries_screening_stamp(tmp_path):
    params = CrorParams(front=BladeParams(tip_radius=54.9))
    res = evaluate_cror(params, tmp_path / "w", tip_gap_mm=5.0)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    _assert_screening_stamp_on_raw(res.raw)


def test_evaluate_modules_share_screening_grid_stamp():
    import fansim.centrifugal.evaluate as mixed_ev
    import fansim.cror.evaluate as cror_ev
    import fansim.volute.evaluate as volute_ev

    assert mixed_ev.SCREENING_GRID_STAMP is SCREENING_GRID_STAMP
    assert cror_ev.SCREENING_GRID_STAMP is SCREENING_GRID_STAMP
    assert volute_ev.SCREENING_GRID_STAMP is SCREENING_GRID_STAMP


def test_volute_evaluate_does_not_require_circular_inlet_area():
    """Sealed scroll path: no tube-in-hex inlet area gate."""
    src = Path("fansim/volute/evaluate.py").read_text(encoding="utf-8")
    assert "require_circular_inlet_area" not in src
