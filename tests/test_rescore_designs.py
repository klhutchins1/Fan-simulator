"""Enumeration / dedupe / reconstruction for scripts/rescore_designs.py (no CFD)."""

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

import optuna

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rescore_designs", ROOT / "scripts" / "rescore_designs.py")
rd = importlib.util.module_from_spec(_spec)
sys.modules["rescore_designs"] = rd
_spec.loader.exec_module(rd)

FLAT = {
    "n_blades": 7, "stagger_root": 26.0, "stagger_mid": 26.0, "stagger_tip": 22.0,
    "chord_root": 34.0, "chord_mid": 44.0, "chord_tip": 38.0, "sweep_mid": 3.0, "sweep_tip": 5.0,
    "hub_radius": 21.5, "tip_radius": 54.35, "tubercle_amp": 0.066, "tubercle_waves": 5,
}


def _make_catalog(path: Path, rows):
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE designs(design_id TEXT PRIMARY KEY, run TEXT, trial INTEGER,
        source TEXT, cfm_free REAL, cfm_load REAL, efficiency REAL, stl_path TEXT, params TEXT,
        cfd_stale INTEGER)""")
    for r in rows:
        con.execute("INSERT INTO designs VALUES(?,?,?,?,?,?,?,?,?,0)", r)
    con.commit()
    con.close()


def _make_study(d: Path):
    d.mkdir(parents=True)
    storage = f"sqlite:///{(d / 'study.db').as_posix()}"
    study = optuna.create_study(study_name="fansim", storage=storage,
                                directions=["maximize"] * 3)
    dist = {k: optuna.distributions.FloatDistribution(0, 100) for k in
            ("stagger_root", "stagger_mid", "stagger_tip", "chord_root", "chord_mid", "chord_tip",
             "sweep_mid", "sweep_tip")}
    dist["n_blades"] = optuna.distributions.IntDistribution(3, 12)
    p = {k: FLAT[k] for k in dist}
    for values, attrs in (([50.0, 40.0, 12.0], {"feasible": True, "cfd_version": 3}),
                          ([-1e6] * 3, {"feasible": False, "reason": "gate"})):
        t = optuna.trial.create_trial(params=p, distributions=dist, values=values, user_attrs=attrs)
        study.add_trial(t)
    return d


def test_result_record_timing_fields():
    """§19.12: rescore rows carry cells / wall_s / sec_per_iter."""
    from types import SimpleNamespace

    c = SimpleNamespace(
        design_id="t1", aliases=[], origin="test", params_hash="abc",
        old={}, settings={"iters": 100, "refine_op": False}, settings_source="defaults",
    )
    res = SimpleNamespace(
        feasible=True, cfm_free=50.0, cfm_load=40.0, efficiency=0.1, actual_rpm=2000.0,
        reason=None, raw={"sanity_status": "PASS", "converged": True},
    )
    rec = rd.result_record(c, res, wall_s=200.0, cells=500000)
    assert rec["cells"] == 500000
    assert rec["wall_s"] == 200.0
    # free + load = 2 solves × 100 iters
    assert rec["sec_per_iter"] == 1.0


def test_enumerate_dedupe_skip(tmp_path):
    stl_dir = tmp_path / "runs" / "r" / "cockpit_assess" / "design_1"
    stl_dir.mkdir(parents=True)
    (stl_dir / "design.json").write_text(json.dumps(
        {"extra": {"preset": "heatsink", "load_pa": 20.0, "refine_op": True, "material": "PLA+",
                   "cfd_version": 2}}))
    stl = str(stl_dir / "impeller.stl")
    db = tmp_path / "catalog.db"
    _make_catalog(db, [
        ("r_t1", "r", 1, "user", 10.0, 9.0, 5.0, stl, json.dumps(FLAT)),
        ("r_t2", "r", 2, "user", 11.0, 9.5, 5.5, "", json.dumps(FLAT)),          # same params
        ("r_t3", "r", 3, "user", 1.0, 1.0, 1.0, "", json.dumps({"n_blades": 5})),  # missing keys
        ("r_t4", "r", 4, "user", 1.0, 1.0, 1.0, "", "{}"),                       # empty params
        ("cockpit_prop_x_t1", "cockpit_prop_x", 1, "optimizer", 1.0, 1.0, 1.0, "", json.dumps(FLAT)),
    ])
    sd = _make_study(tmp_path / "studyrun")
    cands = rd.enumerate_all(db, [sd], root=tmp_path)
    by = {c.design_id: c for c in cands}

    assert "cockpit_prop_x_t1" not in by                      # prop runs excluded
    assert by["r_t1"].aliases == ["r_t2"] and "r_t2" not in by  # deduped
    assert by["r_t1"].settings["load_pa"] == 20.0 and by["r_t1"].settings["material"] == "PLA+"
    assert "design.json" in by["r_t1"].settings_source and by["r_t1"].old["cfd_version"] == 2
    assert not by["r_t3"].reconstructable and "not reconstructable" in by["r_t3"].skip_reason
    assert not by["r_t4"].reconstructable
    assert by["studyrun_study_t0"].reconstructable            # different params (no hub/tip/features)
    assert not by["studyrun_study_t1"].reconstructable       # rejection skipped by default


def test_study_feasible_kept_when_unique(tmp_path):
    sd = _make_study(tmp_path / "studyrun")
    cands = rd.enumerate_all(tmp_path / "missing.db", [sd], root=tmp_path)
    by = {c.design_id: c for c in cands}
    feas = by["studyrun_study_t0"]
    assert feas.reconstructable and feas.old["cfm_free"] == 50.0 and feas.old["cfd_version"] == 3
    assert not by["studyrun_study_t1"].reconstructable
    inc = rd.enumerate_all(tmp_path / "missing.db", [sd], include_infeasible=True, root=tmp_path)
    assert any(c.design_id == "studyrun_study_t1" or "studyrun_study_t1" in c.aliases for c in inc)


def test_update_catalog_adds_version_never_deletes(tmp_path):
    db = tmp_path / "c.db"
    _make_catalog(db, [("a", "r", 1, "user", 1.0, 1.0, 1.0, "", "{}"),
                       ("b", "r", 2, "user", 2.0, 2.0, 2.0, "", "{}")])
    n = rd.update_catalog(db, ["a"], {"cfm_free": 9.0, "cfm_load": 8.0, "efficiency": 7.0})
    con = sqlite3.connect(db)
    rows = {r[0]: r for r in con.execute("SELECT design_id, cfm_free, cfd_version FROM designs")}
    assert n == 1 and len(rows) == 2
    assert rows["a"][1:] == (9.0, rd.CFD_VERSION) and rows["b"][1:] == (2.0, None)
