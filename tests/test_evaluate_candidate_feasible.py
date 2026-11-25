"""Feasible ``evaluate_candidate`` path with numeric CFM (no Docker / no real CFD)."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
import trimesh

from fansim.cfd.metrics import FanMetrics
from fansim.geometry.blade import BladeParams
from fansim.geometry.features import Features
from fansim.optimize import objectives as obj_mod
from fansim.optimize.objectives import evaluate_candidate
from fansim.optimize.print_penalty import PRINT_K_CFM
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def _fake_export_stl(_shape, path):
    """Write a real (tiny) STL so orientation/rig-fitting can load real bounds from disk."""
    box = trimesh.creation.box(extents=(100.0, 100.0, 25.0))
    box.apply_translation((0.0, 0.0, 7.5))  # matches _Rep.bounds_mm z-range (-5..20)
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


def test_evaluate_candidate_feasible_asserts_numeric_cfm(tmp_path, monkeypatch):
    """Stub geometry/mesh/solve so the free→load→system-curve path returns real numbers."""
    params = _printable_params()
    # Generous tip clearance so the tip-gap gate cannot trip.
    params = replace(params, tip_radius=50.0)

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
        # First free (bp=0), then load.
        if calls["n"] == 1:
            return _metrics(cfm=80.0, dp_pa=2.0, shaft_w=0.5)
        return _metrics(cfm=55.0, dp_pa=8.0, shaft_w=0.5)

    monkeypatch.setattr(obj_mod, "parse_fan_metrics", fake_parse)

    res = evaluate_candidate(params, tmp_path / "eval", procs=1, iters=1, load_pa=5.0)
    assert res.feasible is True, res.reason
    # Default print penalty knocks reported free CFM (smooth-wall stamp stays in raw).
    # FSI may tighten print_k_cfm below the base PRINT_K_CFM when tip deflection is material.
    assert res.raw.get("cfm_free_cfd") == pytest.approx(80.0)
    assert "print_k_cfm" in res.raw and "print_k_eta" in res.raw
    assert res.cfm_free == pytest.approx(80.0 * float(res.raw["print_k_cfm"]))
    assert float(res.raw["print_k_cfm"]) <= PRINT_K_CFM + 1e-12
    assert res.cfm_load > 0.0
    assert res.cfm_load < res.cfm_free
    assert res.efficiency > 0.0
    assert abs(res.raw.get("derate", 1.0) - 1.0) < 1e-6
    assert calls["n"] == 2
    assert "k" in res.raw and res.raw["k"] > 0.0


def test_evaluate_candidate_print_penalty_off(tmp_path, monkeypatch):
    params = _printable_params()
    params = replace(params, tip_radius=50.0)

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
    res = evaluate_candidate(
        params, tmp_path / "eval_off", procs=1, iters=1, load_pa=5.0, print_penalty=False,
    )
    assert res.feasible is True, res.reason
    assert res.cfm_free == pytest.approx(80.0)
    assert "print_k_cfm" not in res.raw


def _stub_cfd(monkeypatch, *, run_sanity=None):
    """Same stubs as the feasible test: geometry, mesh and solve faked; free then load metrics."""

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
    if run_sanity is not None:
        monkeypatch.setattr(obj_mod, "run_sanity", run_sanity)


def test_a_crashed_bem_prescreen_is_stamped_not_silent(tmp_path, monkeypatch):
    """RV-3: the BEM pre-screen swallowed its exception, so the design went to CFD with no trace."""
    _stub_cfd(monkeypatch)

    def boom(*_a, **_k):
        raise RuntimeError("polar table missing")

    monkeypatch.setattr(obj_mod, "bem_screen_cfm", boom)
    params = replace(_printable_params(), tip_radius=50.0)
    res = evaluate_candidate(params, tmp_path / "eval", procs=1, iters=1, load_pa=5.0,
                             bem_prescreen_cfm=30.0)
    assert res.feasible is True
    assert res.raw["bem_prescreen_error"] == "RuntimeError: polar table missing"


def test_a_crashed_sanity_check_reads_error_not_skip(tmp_path, monkeypatch):
    """RV-3: a sanity crash became [] and the status read SKIP, like 'never ran' or 'clean'."""
    def boom(*_a, **_k):
        raise ValueError("bad postProcessing")

    _stub_cfd(monkeypatch, run_sanity=boom)
    params = replace(_printable_params(), tip_radius=50.0)
    res = evaluate_candidate(params, tmp_path / "eval", procs=1, iters=1, load_pa=5.0)
    assert res.feasible is True
    assert res.raw["sanity_status"] == "ERROR"
    assert res.raw["sanity_error"] == {"free": "ValueError: bad postProcessing",
                                       "load": "ValueError: bad postProcessing"}


def test_a_solve_failure_keeps_its_message(tmp_path, monkeypatch):
    """RV-3: 'solve failed: RuntimeError' dropped the message that says what broke."""
    _stub_cfd(monkeypatch)

    def boom(*_a, **_k):
        raise RuntimeError("simpleFoam exited 139")

    monkeypatch.setattr(obj_mod, "run_solve", boom)
    params = replace(_printable_params(), tip_radius=50.0)
    res = evaluate_candidate(params, tmp_path / "eval", procs=1, iters=1, load_pa=5.0)
    assert not res.feasible
    assert res.reason == "solve failed: RuntimeError: simpleFoam exited 139"
