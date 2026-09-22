from __future__ import annotations

from pathlib import Path

import pytest

from fansim.prop_spec import get_prop_spec


def test_prop_cfd_mesh_knobs():
    from fansim.cockpit.prop_tab import prop_cfd_mesh_knobs

    assert prop_cfd_mesh_knobs("smoke") == (0.005, 400)
    assert prop_cfd_mesh_knobs("refine") == (0.004, 600)
    assert prop_cfd_mesh_knobs("unknown") == (0.005, 400)


def test_bemt_thrust_g_finite():
    from fansim.propeller.geometry import prop_blade_params
    from fansim.propeller.optimize import bemt_thrust_g

    spec = get_prop_spec("fpv_5inch")
    params = prop_blade_params(spec)
    g = bemt_thrust_g(params, spec)
    assert g > 0 and g == pytest.approx(g)  # finite


def test_blade_params_from_trial_params_roundtrip():
    from fansim.propeller.optimize import blade_params_from_trial_params

    spec = get_prop_spec("fpv_5inch")
    flat = {
        "n_blades": 3,
        "pitch_in": 4.3,
        "chord_root": 0.20,
        "chord_mid": 0.26,
        "chord_tip": 0.10,
        "camber": 0.04,
    }
    b = blade_params_from_trial_params(spec, flat)
    assert b.n_blades == 3
    assert b.stations[0].chord == pytest.approx(0.20 * (spec.diameter_mm / 2.0))


def test_evaluate_prop_cfd_skips_below_bemt_floor(tmp_path, monkeypatch):
    from fansim.propeller import cfd as prop_cfd

    # If Docker/OpenFOAM were called, fail the test.
    monkeypatch.setattr(
        prop_cfd, "run_mesh", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no mesh"))
    )
    monkeypatch.setattr(
        prop_cfd,
        "run_solve_prop",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no solve")),
    )

    spec = get_prop_spec("fpv_5inch")
    out = prop_cfd.evaluate_prop_cfd(spec, tmp_path, bemt_floor_g=1e9)  # impossible floor
    assert out["skipped"] is True
    assert out["bemt_thrust_g"] < 1e9
    assert "reason" in out


def test_cli_evaluate_prop_cfd_declares_bemt_floor():
    text = Path("scripts/evaluate_prop_cfd.py").read_text(encoding="utf-8")
    assert "--bemt-floor" in text


def test_cli_run_prop_optimization_declares_cfd_flags():
    text = Path("scripts/run_prop_optimization.py").read_text(encoding="utf-8")
    assert "--cfd-top" in text
    assert "--bemt-floor" in text
    assert "--cfd-out" in text


def test_refine_pareto_cfd_respects_floor(tmp_path, monkeypatch):
    from fansim.propeller import optimize as po

    calls = []

    def fake_eval(spec, workdir, **kw):
        calls.append(kw.get("bemt_floor_g"))
        return {"skipped": True, "bemt_thrust_g": 1.0, "reason": "floor"}

    monkeypatch.setattr("fansim.propeller.cfd.evaluate_prop_cfd", fake_eval)

    spec = get_prop_spec("fpv_5inch")
    pareto = [
        {
            "thrust_g": 100.0,
            "params": {
                "n_blades": 3,
                "pitch_in": 4.3,
                "chord_root": 0.2,
                "chord_mid": 0.26,
                "chord_tip": 0.1,
                "camber": 0.04,
            },
        }
    ]
    rows = po.refine_pareto_cfd(spec, pareto, tmp_path, n_top=1, bemt_floor_g=50.0)
    assert len(rows) == 1
    assert calls == [50.0]


def test_refine_pareto_cfd_forwards_mesh_knobs(tmp_path, monkeypatch):
    import fansim.propeller.optimize as po

    captured = {}

    def fake_eval(spec, workdir, **kw):
        captured.update(kw)
        return {"thrust_g": 100.0, "bemt_thrust_g": 80.0, "skipped": False}

    monkeypatch.setattr("fansim.propeller.cfd.evaluate_prop_cfd", fake_eval)
    spec = get_prop_spec("fpv_5inch")
    pareto = [
        {
            "thrust_g": 100.0,
            "params": {
                "n_blades": 3,
                "pitch_in": 4.3,
                "chord_root": 0.2,
                "chord_mid": 0.26,
                "chord_tip": 0.1,
                "camber": 0.04,
            },
        }
    ]
    rows = po.refine_pareto_cfd(
        spec, pareto, tmp_path, n_top=1, bemt_floor_g=0.0,
        base_cell=0.004, iters=600,
    )
    assert not rows[0]["skipped"]
    assert captured.get("base_cell") == pytest.approx(0.004)
    assert captured.get("iters") == 600
