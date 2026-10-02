"""Tests for mixed-flow evaluate path. No Docker mesh."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from fansim.centrifugal.evaluate import evaluate_mixed_flow
from fansim.centrifugal.geometry import MixedFlowParams
from fansim.optimize.objectives import ObjectiveResult


def test_tip_gap_infeasible_without_cfd(tmp_path):
    # Force leftover below floor: tip almost fills the 55 mm half-frame
    p = MixedFlowParams(r_tip_mm=54.9)
    res = evaluate_mixed_flow(p, tmp_path / "w", tip_gap_mm=5.0)
    assert res.feasible is False
    assert "tip gap" in res.reason.lower()
    assert res.raw.get("grid_converged") is False


def test_evaluate_mixed_flow_mocked_cfd(tmp_path, monkeypatch):
    from fansim.centrifugal import evaluate as ev

    free_m = SimpleNamespace(
        cfm=70.0, efficiency=0.40, thrust_n=0.5, torque_nm=0.01,
        static_pressure_rise_pa=1.0,
        converged=True, flow_drift_pct=0.1,
        to_dict=lambda: {"cfm": 70.0},
    )
    load_m = SimpleNamespace(
        cfm=50.0, efficiency=0.32, thrust_n=0.4, torque_nm=0.012,
        static_pressure_rise_pa=8.0,
        converged=True, flow_drift_pct=0.1,
        to_dict=lambda: {"cfm": 50.0},
    )
    seq = iter([free_m, load_m])

    monkeypatch.setattr(ev, "export_mixed_flow_stl",
                        lambda params, path, **kw: Path(path).write_text("solid") or Path(path))
    monkeypatch.setattr(ev, "watertight_report",
                        lambda stl: SimpleNamespace(ok=True, n_bodies=1,
                                                    bounds_mm=((-50, -50, -9), (50, 50, 9))))
    # STL is faked, so skip the Audit #7 orientation (covered by tests/audit/test_cror_mixed_setup_audit.py)
    monkeypatch.setattr(ev, "prepare_axial_cfd", lambda stl, rig, wd, **k: (stl, rig))
    monkeypatch.setattr(ev, "export_frame_stl", lambda *a, **k: Path(tmp_path / "frame.stl"))
    monkeypatch.setattr(ev, "build_case", lambda *a, **k: None)
    monkeypatch.setattr(ev, "run_mesh", lambda *a, **k: None)
    monkeypatch.setattr(ev, "run_solve", lambda *a, **k: None)
    monkeypatch.setattr(ev, "parse_fan_metrics", lambda *a, **k: next(seq))
    monkeypatch.setattr(ev, "OpenFOAMRunner", lambda workdir: SimpleNamespace())

    res = evaluate_mixed_flow(MixedFlowParams(), tmp_path / "run", load_pa=8.0)
    assert res.feasible is True
    assert res.raw.get("topology") == "mixed_flow"
    assert res.raw.get("archetype") == "centrifugal"
    assert res.raw.get("grid_converged") is False
    assert "GCI" in str(res.raw.get("grid_note", ""))
    assert res.cfm_free > 0
    assert "print_k_cfm" in res.raw


def test_mixed_bem_prescreen_exception_is_infeasible(tmp_path, monkeypatch):
    """§9.6 — mixed BEM screen crash must not fall through to CFD."""
    from fansim.centrifugal import evaluate as ev

    def boom(*_a, **_k):
        raise RuntimeError("mixed bem boom")

    monkeypatch.setattr(ev, "mixed_bem_screen_cfm", boom)
    built = {"stl": False}

    def no_stl(*_a, **_k):
        built["stl"] = True
        raise AssertionError("geometry must not run after screen crash")

    monkeypatch.setattr(ev, "export_mixed_flow_stl", no_stl)
    res = evaluate_mixed_flow(
        MixedFlowParams(), tmp_path / "mf_crash", bem_prescreen_cfm=1.0)
    assert res.feasible is False
    assert "bem-prescreen failed" in res.reason
    assert "mixed bem boom" in res.reason
    assert res.raw.get("bem_prescreen_error", "").startswith("RuntimeError")
    assert built["stl"] is False


def test_mixed_solve_failure_keeps_exc_message(tmp_path, monkeypatch):
    """§9.9 — solve-failure reason must keep str(exc), not only the type name."""
    from fansim.centrifugal import evaluate as ev

    monkeypatch.setattr(
        ev, "export_mixed_flow_stl",
        lambda params, path, **kw: Path(path).write_text("solid") or Path(path))
    monkeypatch.setattr(
        ev, "watertight_report",
        lambda stl: SimpleNamespace(
            ok=True, n_bodies=1, bounds_mm=((-50, -50, -9), (50, 50, 9))))
    # STL is faked, so skip the Audit #7 orientation (covered by tests/audit/test_cror_mixed_setup_audit.py)
    monkeypatch.setattr(ev, "prepare_axial_cfd", lambda stl, rig, wd, **k: (stl, rig))
    monkeypatch.setattr(ev, "export_frame_stl", lambda *a, **k: Path(tmp_path / "frame.stl"))
    monkeypatch.setattr(ev, "build_case", lambda *a, **k: None)
    monkeypatch.setattr(ev, "run_mesh", lambda *a, **k: None)

    def boom(*_a, **_k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ev, "run_solve", boom)
    res = evaluate_mixed_flow(MixedFlowParams(r_tip_mm=50.0), tmp_path / "mf_solve")
    assert res.feasible is False
    assert res.reason == "solve failed: RuntimeError: disk full"


def test_archetype_evaluate_calls_mixed_flow(monkeypatch, tmp_path):
    from fansim.centrifugal.archetype import MixedFlowArchetype

    called = {}

    def fake_eval(params, workdir, **kwargs):
        called["ok"] = True
        return ObjectiveResult(True, cfm_free=1.0, cfm_load=1.0, efficiency=1.0)

    monkeypatch.setattr(
        "fansim.centrifugal.evaluate.evaluate_mixed_flow", fake_eval)
    out = MixedFlowArchetype().evaluate(MixedFlowParams(), tmp_path)
    assert called.get("ok")
    assert out.feasible is True


def test_cli_help_declares_evaluate_mixed_flow():
    text = Path("scripts/evaluate_mixed_flow.py").read_text(encoding="utf-8")
    assert "mixed-flow" in text.lower()
    assert "★" not in text
