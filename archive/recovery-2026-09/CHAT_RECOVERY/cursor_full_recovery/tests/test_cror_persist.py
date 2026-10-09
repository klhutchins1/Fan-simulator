"""CROR cockpit persist helpers (no Docker / CadQuery)."""

from __future__ import annotations

from pathlib import Path

from fansim.cror.persist import (
    cror_opt_out_path,
    latest_cror_opt_dir,
    load_all_cror_pareto,
    load_cror_pareto,
    save_cror_pareto,
)


def test_cror_pareto_roundtrip(tmp_path: Path):
    out = cror_opt_out_path(stamp="t1", runs_root=tmp_path)
    rows = [
        {
            "thrust_g": 100.0,
            "eff_g_per_w": 1.2,
            "rel_dba": 55.0,
            "depth_mm": 24.0,
            "params": {"n_front": 7, "n_rear": 9, "axial_gap_mm": 4.0,
                       "stagger_deg": 40.0, "chord_mm": 14.0},
        }
    ]
    save_cror_pareto(out, rows, meta={"n_trials": 10})
    assert load_cror_pareto(out)[0]["thrust_g"] == 100.0
    assert latest_cror_opt_dir(tmp_path) == out
    all_rows = load_all_cror_pareto(tmp_path)
    assert len(all_rows) == 1
    assert all_rows[0]["source_run"] == out.name
