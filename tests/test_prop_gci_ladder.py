from __future__ import annotations

import math

import pytest

from fansim.propeller.gci_ladder import build_gci_summary, parse_cells


def test_parse_cells_three_values_coarse_to_fine():
    assert parse_cells("0.005,0.0035,0.0025") == [0.005, 0.0035, 0.0025]


def test_parse_cells_sorts_descending():
    assert parse_cells("0.0025,0.005,0.0035") == [0.005, 0.0035, 0.0025]


def test_parse_cells_rejects_bad():
    with pytest.raises(ValueError):
        parse_cells("0.005,0.0035")
    with pytest.raises(ValueError):
        parse_cells("0.005,0.005,0.0025")


def test_build_gci_summary_roache_on_thrust():
    # Synthetic f = 100 - C*h_mm^2 on base_cell in metres → p≈2
    levels = [
        {"base_cell": 0.004, "thrust_g": 100.0 - (4.0**2), "ok": True},
        {"base_cell": 0.002, "thrust_g": 100.0 - (2.0**2), "ok": True},
        {"base_cell": 0.001, "thrust_g": 100.0 - (1.0**2), "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1000.0, iters=800, levels=levels)
    assert s["gci"] is not None
    assert s["gci"]["p"] == pytest.approx(2.0, abs=1e-4)
    assert s["gci"]["f_extrapolated"] == pytest.approx(100.0, abs=1e-3)
    assert s["gci_reason"] is None


def test_build_gci_summary_null_when_rung_failed():
    levels = [
        {"base_cell": 0.005, "thrust_g": 10.0, "ok": True},
        {"base_cell": 0.0035, "thrust_g": None, "ok": False, "error": "solve failed"},
        {"base_cell": 0.0025, "thrust_g": 12.0, "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1.0, iters=800, levels=levels)
    assert s["gci"] is None
    assert "failed" in (s["gci_reason"] or "").lower() or "incomplete" in (s["gci_reason"] or "").lower()


def test_build_gci_summary_null_when_flat():
    levels = [
        {"base_cell": 0.005, "thrust_g": 50.0, "ok": True},
        {"base_cell": 0.0035, "thrust_g": 50.0, "ok": True},
        {"base_cell": 0.0025, "thrust_g": 50.0, "ok": True},
    ]
    s = build_gci_summary(stl="x.stl", rpm=1.0, iters=800, levels=levels)
    assert s["gci"] is None
    assert s["gci_reason"]


def test_cli_parser_defaults_and_cells():
    import importlib.util
    from pathlib import Path

    path = Path("scripts/run_prop_grid_convergence.py")
    spec = importlib.util.spec_from_file_location("run_prop_grid_convergence", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    ap = mod.build_parser()
    args = ap.parse_args([
        "--stl", "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
        "--rpm", "38100",
        "--out", "runs/drone_radial_cfd/gci/obj_1",
    ])
    assert args.rpm == pytest.approx(38100.0)
    assert args.iters == 800
    assert args.cells == "0.005,0.0035,0.0025"


def test_cli_main_rejects_bad_cells(monkeypatch, capsys):
    import importlib.util
    import sys
    from pathlib import Path

    path = Path("scripts/run_prop_grid_convergence.py")
    spec = importlib.util.spec_from_file_location("run_prop_grid_convergence_bad_cells", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_prop_grid_convergence.py",
            "--cells",
            "0.005,0.0035",
            "--stl",
            "validation/reference/drone_radial/obj_1_ccw_impeller.stl",
            "--rpm",
            "38100",
            "--out",
            "runs/drone_radial_cfd/gci/obj_1",
        ],
    )
    assert mod.main() == 2
    assert "ERROR" in capsys.readouterr().err
