"""Prop Optimize out-path / resume helpers — no CadQuery / Docker."""

from __future__ import annotations

from pathlib import Path

from fansim.prop_spec import get_prop_spec
from fansim.propeller.optimize import run_prop_study
from fansim.propeller.persist import latest_prop_study_dir, prop_out_path


def test_prop_out_path_new_vs_resume(tmp_path: Path):
    last = tmp_path / "cockpit_prop_old"
    last.mkdir()
    (last / "study.db").write_text("", encoding="utf-8")
    new = prop_out_path(resume=False, last_dir=last, stamp="20260101_120000", runs_root=tmp_path)
    assert new == tmp_path / "cockpit_prop_20260101_120000"
    resumed = prop_out_path(resume=True, last_dir=last, stamp="ignored", runs_root=tmp_path)
    assert resumed == last
    # Resume without study.db falls back to a new folder
    empty = tmp_path / "cockpit_prop_empty"
    empty.mkdir()
    fallback = prop_out_path(resume=True, last_dir=empty, stamp="20260101_130000", runs_root=tmp_path)
    assert fallback == tmp_path / "cockpit_prop_20260101_130000"


def test_latest_prop_study_dir(tmp_path: Path):
    a = tmp_path / "cockpit_prop_a"
    b = tmp_path / "cockpit_prop_b"
    a.mkdir()
    b.mkdir()
    (a / "study.db").write_text("x", encoding="utf-8")
    (b / "study.db").write_text("y", encoding="utf-8")
    # bump b mtime
    import time
    time.sleep(0.05)
    (b / "study.db").write_text("y2", encoding="utf-8")
    assert latest_prop_study_dir(tmp_path) == b


def test_run_prop_study_resume_appends_trials(tmp_path: Path):
    spec = get_prop_spec("fpv_5inch")
    out = tmp_path / "cockpit_prop_resume"
    study1, _ = run_prop_study(spec, n_trials=30, seed=0, out_dir=out, prop_model="fpv_5inch")
    n1 = len(study1.trials)
    study2, _ = run_prop_study(spec, n_trials=20, seed=1, out_dir=out, prop_model="fpv_5inch")
    assert len(study2.trials) == n1 + 20
    assert (out / "pareto.json").exists()
