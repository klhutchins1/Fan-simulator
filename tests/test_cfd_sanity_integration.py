"""evaluate_candidate stamps sanity_status but a sanity FAIL never makes a design infeasible.

Mocks the whole CFD pipeline (geometry/mesh/solve), following
tests/test_evaluate_candidate_feasible.py, so this runs without CFD/Docker.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import trimesh

from fansim.cfd.metrics import FanMetrics
from fansim.cfd.sanity import FAIL, PASS, SanityCheck
from fansim.geometry.blade import BladeParams
from fansim.geometry.features import Features
from fansim.optimize import objectives as obj_mod
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def _fake_export_stl(_shape, path):
    box = trimesh.creation.box(extents=(100.0, 100.0, 25.0))
    box.apply_translation((0.0, 0.0, 7.5))
    box.export(str(path))
    return path


def _metrics(*, cfm: float, dp_pa: float, shaft_w: float = 5.0) -> FanMetrics:
    return FanMetrics(
        flow_m3s=cfm / 2118.882,
        cfm=cfm,
        static_pressure_rise_pa=dp_pa,
        thrust_n=1.0,
        torque_nm=0.02,
        shaft_power_w=shaft_w,
        air_power_w=1.0,
        efficiency=0.25,
        p_inlet_kin=0.0,
        p_outlet_kin=dp_pa,
        converged=True,
        flow_drift_pct=0.5,
    )


def _printable_params() -> BladeParams:
    flat = stock_blade_flat("a12x25")
    return blade_from_flat(flat, Features())


def _wire_common_mocks(monkeypatch):
    class _Rep:
        ok = True
        n_bodies = 1
        bounds_mm = ((-50.0, -50.0, -5.0), (50.0, 50.0, 20.0))

    monkeypatch.setattr(obj_mod, "build_impeller", lambda _p: object())
    monkeypatch.setattr(obj_mod, "export_stl", _fake_export_stl)
    monkeypatch.setattr(obj_mod, "watertight_report", lambda _stl: _Rep())
    monkeypatch.setattr(obj_mod, "export_frame_stl", lambda *_a, **_k: None)
    monkeypatch.setattr(obj_mod, "build_case", lambda *_a, **_k: None)
    monkeypatch.setattr(obj_mod, "run_mesh", lambda *_a, **_k: None)
    monkeypatch.setattr(obj_mod, "run_solve", lambda *_a, **_k: None)
    monkeypatch.setattr(obj_mod, "OpenFOAMRunner", lambda *_a, **_k: SimpleNamespace())

    calls = {"n": 0}

    def fake_parse(_workdir, omega_rad_s=0.0):
        calls["n"] += 1
        if calls["n"] == 1:
            return _metrics(cfm=80.0, dp_pa=2.0, shaft_w=0.5)
        return _metrics(cfm=55.0, dp_pa=8.0, shaft_w=0.5)

    monkeypatch.setattr(obj_mod, "parse_fan_metrics", fake_parse)
    return calls


def _params():
    params = _printable_params()
    return replace(params, tip_radius=50.0)


def test_evaluate_candidate_stamps_sanity_status(tmp_path, monkeypatch):
    """A clean (all-PASS) sanity run stamps sanity_status without touching feasibility."""
    _wire_common_mocks(monkeypatch)
    monkeypatch.setattr(
        obj_mod, "run_sanity",
        lambda *_a, **_k: [SanityCheck("mass_balance", PASS, 0.1, "<=1%", "ok")],
    )

    res = evaluate_candidate(_params(), tmp_path / "eval", procs=1, iters=1, load_pa=5.0)
    assert res.feasible is True, res.reason
    assert res.raw.get("sanity_status") == PASS
    assert isinstance(res.raw.get("sanity"), list) and len(res.raw["sanity"]) == 2
    assert all("phase" in c for c in res.raw["sanity"])


def test_evaluate_candidate_sanity_fail_flags_but_stays_feasible(tmp_path, monkeypatch):
    """A synthetic sanity FAIL is surfaced in raw/reason, but never rejects the design."""
    _wire_common_mocks(monkeypatch)
    monkeypatch.setattr(
        obj_mod, "run_sanity",
        lambda *_a, **_k: [SanityCheck("power_sign", FAIL, 1.0, "<0", "Mz*omega >= 0")],
    )

    res = evaluate_candidate(_params(), tmp_path / "eval_fail", procs=1, iters=1, load_pa=5.0)
    assert res.feasible is True, res.reason
    assert res.raw.get("sanity_status") == FAIL
    assert "sanity FAIL" in res.reason
    assert "power_sign" in res.reason
