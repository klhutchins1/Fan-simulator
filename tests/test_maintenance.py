"""Disk-pruning safety (fansim/maintenance.py) — must delete ONLY regenerable case internals."""

from __future__ import annotations

from pathlib import Path

from fansim.maintenance import is_case_dir, prunable_targets, prune, scan_all, scan_run


def _fake_case(case: Path):
    """A minimal OpenFOAM-looking case with both prunable and must-keep contents."""
    (case / "system").mkdir(parents=True)
    (case / "system" / "controlDict").write_text("x")
    (case / "constant").mkdir()
    (case / "constant" / "transportProperties").write_text("x")         # dict — KEEP
    (case / "constant" / "polyMesh").mkdir()                             # mesh — PRUNE
    (case / "constant" / "polyMesh" / "points").write_text("m" * 5000)
    for i in range(2):
        (case / f"processor{i}").mkdir()                                 # decomposed — PRUNE
        (case / f"processor{i}" / "0").write_text("p" * 4000)
    (case / "logs").mkdir(); (case / "logs" / "solve.log").write_text("l" * 3000)  # PRUNE
    (case / "postProcessing").mkdir()                                    # raw FO — KEEP (tiny)
    (case / "postProcessing" / "forces.dat").write_text("f")
    (case / "impeller.stl").write_text("stl" * 1000)                     # geometry — KEEP
    (case / "result.json").write_text('{"cfm_free": 80}')               # numbers — KEEP


def test_is_case_dir(tmp_path):
    _fake_case(tmp_path / "c")
    assert is_case_dir(tmp_path / "c")
    assert not is_case_dir(tmp_path)   # no system/constant here


def test_prunable_targets_are_only_regenerable(tmp_path):
    c = tmp_path / "c"; _fake_case(c)
    names = {p.name for p in prunable_targets(c)}
    assert names == {"polyMesh", "processor0", "processor1", "logs"}
    # essentials must NOT be in the prune list
    assert "impeller.stl" not in names and "result.json" not in names
    assert "postProcessing" not in names and "transportProperties" not in names


def test_dry_run_deletes_nothing(tmp_path):
    c = tmp_path / "c"; _fake_case(c)
    freed = prune(prunable_targets(c), apply=False)
    assert freed > 0
    assert (c / "constant" / "polyMesh").exists() and (c / "processor0").exists()


def test_apply_removes_only_prunable(tmp_path):
    c = tmp_path / "c"; _fake_case(c)
    freed = prune(prunable_targets(c), apply=True)
    assert freed > 0
    # pruned:
    assert not (c / "constant" / "polyMesh").exists()
    assert not (c / "processor0").exists() and not (c / "processor1").exists()
    assert not (c / "logs").exists()
    # preserved:
    assert (c / "impeller.stl").exists() and (c / "result.json").exists()
    assert (c / "constant" / "transportProperties").exists()
    assert (c / "system" / "controlDict").exists()
    assert (c / "postProcessing" / "forces.dat").exists()


def test_scan_totals(tmp_path):
    runs = tmp_path / "runs"
    _fake_case(runs / "opt_a" / "trials" / "trial_0000")
    _fake_case(runs / "opt_a" / "trials" / "trial_0001")
    _fake_case(runs / "opt_b" / "cockpit_assess" / "design_9000")
    r = scan_run(runs / "opt_a")
    assert r["cases"] == 2 and r["bytes"] > 0
    allr = scan_all(runs)
    assert {x["run"] for x in allr} == {"opt_a", "opt_b"}
