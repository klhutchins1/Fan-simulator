"""Mixed-flow Assess persist / scatter helpers (§8.6) — no Docker / CadQuery."""

from __future__ import annotations

import logging
from pathlib import Path

from fansim.centrifugal.persist import (
    load_all_mixed_designs,
    load_mixed_design,
    load_mixed_pareto,
    next_mixed_trial,
    save_mixed_design_json,
)
from fansim.cockpit.figures import mf_scatter_figure


def test_save_load_mixed_design_roundtrip(tmp_path: Path):
    work = tmp_path / "cockpit_mf_test"
    path = save_mixed_design_json(
        work,
        trial=9000,
        params={"n_blades": 9, "r_eye_mm": 16.0, "r_back_mm": 28.0, "r_tip_mm": 54.5,
                "z_span_mm": 18.0, "chord_mm": 22.0, "stagger_deg": 35.0},
        objectives={"cfm_free": 48.5, "cfm_load": 41.2, "efficiency": 28.0},
        extra={"source": "mixed_assess", "hose": "case"},
    )
    assert path.exists()
    row = load_mixed_design(work)
    assert row is not None
    assert row["trial"] == 9000
    assert row["objectives"]["cfm_free"] == 48.5
    assert row["params"]["n_blades"] == 9
    assert row["extra"]["hose"] == "case"


def test_load_all_mixed_designs_and_next_trial(tmp_path: Path):
    save_mixed_design_json(
        tmp_path / "cockpit_mf_a",
        trial=9000,
        params={"n_blades": 8},
        objectives={"cfm_free": 40.0, "cfm_load": 35.0, "efficiency": 25.0},
    )
    save_mixed_design_json(
        tmp_path / "cockpit_mf_b",
        trial=9000,  # collision → re-keyed on load
        params={"n_blades": 10},
        objectives={"cfm_free": 50.0, "cfm_load": 44.0, "efficiency": 30.0},
    )
    rows = load_all_mixed_designs(tmp_path)
    assert len(rows) == 2
    trials = {r["trial"] for r in rows}
    assert 9000 in trials
    assert len(trials) == 2
    nxt = next_mixed_trial(rows)
    assert nxt not in trials
    assert nxt >= 9000


def test_mf_scatter_figure_builds_trace():
    designs = [{
        "trial": 9000,
        "objectives": {"cfm_free": 48.0, "cfm_load": 40.0, "efficiency": 27.0},
        "params": {},
        "extra": {"source": "mixed_assess"},
    }]
    fig = mf_scatter_figure(designs)
    assert len(fig.data) == 1
    assert fig.data[0].x[0] == 48.0


def test_load_mixed_design_logs_corrupt(tmp_path, caplog):
    """§9.9 — corrupt mixed design.json is skipped with a warning."""
    work = tmp_path / "cockpit_mf_bad"
    work.mkdir()
    (work / "design.json").write_text("{not-json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="fansim.centrifugal.persist"):
        assert load_mixed_design(work) is None
    assert "skip corrupt mixed design.json" in caplog.text


def test_load_mixed_pareto_logs_corrupt(tmp_path, caplog):
    work = tmp_path / "opt_mf_bad"
    work.mkdir()
    (work / "pareto.json").write_text("{not-json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="fansim.centrifugal.persist"):
        assert load_mixed_pareto(work) == []
    assert "skip corrupt mixed pareto.json" in caplog.text
