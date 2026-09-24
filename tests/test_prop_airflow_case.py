"""Prop CFD refine → airflow case selection helpers."""

from __future__ import annotations

from pathlib import Path

from fansim.propeller.airflow_case import first_prop_cfd_workdir, prop_cfd_workdir_from_study


def test_first_prop_cfd_workdir_skips_skipped_and_empty():
    rows = [
        {"skipped": True, "workdir": "/tmp/a"},
        {"skipped": False, "workdir": ""},
        {"skipped": False, "workdir": "/tmp/b"},
        {"skipped": False, "workdir": "/tmp/c"},
    ]
    assert first_prop_cfd_workdir(rows) == "/tmp/b"
    assert first_prop_cfd_workdir([]) is None
    assert first_prop_cfd_workdir(None) is None


def test_prop_cfd_workdir_from_study_prefers_solved_case(tmp_path: Path):
    study = tmp_path / "prop_study"
    refine = study / "cfd_refine"
    empty = refine / "cfd_00"
    empty.mkdir(parents=True)
    solved = refine / "cfd_01"
    (solved / "constant" / "polyMesh").mkdir(parents=True)
    assert prop_cfd_workdir_from_study(study) == str(solved)
    assert prop_cfd_workdir_from_study(None) is None
    assert prop_cfd_workdir_from_study(tmp_path / "missing") is None


def test_prop_cfd_workdir_from_study_falls_back_to_first_cfd(tmp_path: Path):
    study = tmp_path / "prop_study"
    only = study / "cfd_refine" / "cfd_00"
    only.mkdir(parents=True)
    assert prop_cfd_workdir_from_study(study) == str(only)
