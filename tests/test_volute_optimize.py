"""Volute geometry-proxy Optimize (§14.4b) — no Docker / CadQuery."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.volute.geometry import VoluteParams
from fansim.volute.optimize import (
    VOLUTE_PROXY_STAMP,
    run_volute_study,
    suggest_volute,
    volute_proxy_scores,
)
from fansim.volute.persist import (
    latest_volute_opt_dir,
    load_all_volute_pareto,
    load_volute_pareto,
    save_volute_pareto,
    volute_opt_out_path,
)


def test_suggest_volute_hub_lt_tip():
    class _T:
        def suggest_int(self, name, lo, hi):
            return lo

        def suggest_float(self, name, lo, hi):
            assert lo <= hi, f"{name}: {lo} > {hi}"
            return lo

    p = suggest_volute(_T())
    assert isinstance(p, VoluteParams)
    assert p.r_hub_mm < p.r_tip_mm
    assert p.n_blades >= 5


def test_suggest_volute_emits_design_keys():
    class _T:
        def __init__(self):
            self.params = {}

        def suggest_int(self, name, lo, hi):
            self.params[name] = lo
            return lo

        def suggest_float(self, name, lo, hi):
            self.params[name] = lo
            return lo

    t = _T()
    suggest_volute(t)
    for key in (
        "n_blades", "r_hub_mm", "r_tip_mm", "blade_height_mm", "spiral_growth_mm",
        "volute_clearance_mm", "tongue_angle_deg", "outlet_width_mm",
    ):
        assert key in t.params


def test_volute_proxy_scores_positive_and_ranked():
    lo = VoluteParams(n_blades=5, blade_height_mm=12.0, spiral_growth_mm=10.0,
                      volute_clearance_mm=8.0)
    hi = VoluteParams(n_blades=11, blade_height_mm=32.0, spiral_growth_mm=40.0,
                      volute_clearance_mm=1.0)
    c0, h0 = volute_proxy_scores(lo, rpm=3000.0)
    c1, h1 = volute_proxy_scores(hi, rpm=3000.0)
    assert c0 > 0 and h0 > 0
    assert c1 > c0
    assert h1 > h0


def test_run_volute_study_persists_and_resumes(tmp_path: Path):
    out = tmp_path / "cockpit_volute_opt_t"
    study1, pareto = run_volute_study(n_trials=40, seed=0, rpm=3000.0, out_dir=out)
    assert (out / "study.db").exists()
    assert (out / "pareto.json").exists()
    assert len(pareto) >= 1
    assert pareto[0]["extra"]["source"] == "volute_optimize"
    assert pareto[0]["extra"]["volute_proxy"] == VOLUTE_PROXY_STAMP
    assert "capacity_proxy" in pareto[0]["objectives"]
    assert "head_proxy" in pareto[0]["objectives"]
    n1 = len(study1.trials)
    study2, _ = run_volute_study(n_trials=15, seed=1, rpm=3000.0, out_dir=out)
    assert len(study2.trials) == n1 + 15
    loaded = load_volute_pareto(out)
    assert len(loaded) >= 1


def test_volute_persist_helpers(tmp_path: Path):
    runs = tmp_path / "runs"
    out = volute_opt_out_path(stamp="abc", runs_root=runs)
    assert out.name == "cockpit_volute_opt_abc"
    row = {
        "trial": 30001,
        "params": {"n_blades": 7},
        "objectives": {"capacity_proxy": 1.0, "head_proxy": 2.0},
        "extra": {"source": "volute_optimize"},
    }
    save_volute_pareto(out, [row], meta={"volute_proxy": VOLUTE_PROXY_STAMP})
    (out / "study.db").write_text("", encoding="utf-8")
    assert latest_volute_opt_dir(runs) == out
    all_rows = load_all_volute_pareto(runs)
    assert len(all_rows) == 1
    assert all_rows[0]["extra"]["source_run"] == out.name
