# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Unified design catalog (fansim/catalog.py)."""

from __future__ import annotations

import json

from fansim.catalog import build_catalog, catalog_stats, get_entry, load_catalog
from validation.ingest import MeasuredPoint
from validation.store import record_measurement


def _make_run(runs: "pathlib.Path", name: str, trials: list[dict]):
    d = runs / name
    d.mkdir(parents=True)
    (d / "pareto.json").write_text(json.dumps(trials))
    return d


def test_build_indexes_finalists_across_runs(tmp_path):
    runs = tmp_path / "runs"
    _make_run(runs, "opt_a", [{"trial": 1, "cfm_free": 80.0, "cfm_load": 74.0, "efficiency": 34.0,
                               "noise_swl": 50.0, "params": {"n_blades": 6}}])
    _make_run(runs, "opt_b", [{"trial": 2, "cfm_free": 70.0, "cfm_load": 63.0, "efficiency": 38.0,
                               "params": {"n_blades": 7}}])
    db = tmp_path / "cat.db"
    n = build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    assert n == 2
    ids = {e.design_id for e in load_catalog(db)}
    assert ids == {"opt_a_t1", "opt_b_t2"}   # stable ids, both runs — no islands
    a = get_entry("opt_a_t1", db)
    assert a.cfm_free == 80.0 and a.n_blades == 6 and a.is_pareto and a.source == "optimizer"


def test_measurements_join_by_design_id(tmp_path):
    runs = tmp_path / "runs"
    _make_run(runs, "opt_a", [{"trial": 1, "cfm_free": 80.0, "cfm_load": 74.0, "efficiency": 34.0,
                               "params": {"n_blades": 6}}])
    store = tmp_path / "meas"
    record_measurement("opt_a_t1", MeasuredPoint(rpm=2000, cfm=52.0, noise_dba=25.0),
                       sim={"cfm_free": 80.0}, store_dir=store)
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=store, db=db)
    e = get_entry("opt_a_t1", db)
    assert e.has_measurement and e.measured_cfm == 52.0 and e.measured_noise == 25.0
    assert e.cfm_error_pct is not None and e.cfm_error_pct > 0   # sim 80 over-reads vs measured 52


def test_measured_only_design_gets_an_entry(tmp_path):
    # a measured design that isn't any run's finalist still lands in the catalog (via the store's sim)
    store = tmp_path / "meas"
    record_measurement("hand_t0", MeasuredPoint(rpm=1800, cfm=44.0),
                       sim={"cfm_free": 70.0, "n_blades": 5}, store_dir=store)
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=tmp_path / "runs", store_dir=store, db=db)
    e = get_entry("hand_t0", db)
    assert e is not None and e.source == "measured" and e.has_measurement and e.n_blades == 5


def test_removed_ids_are_excluded(tmp_path):
    from fansim.catalog import save_removed
    runs = tmp_path / "runs"
    _make_run(runs, "opt_a", [{"trial": 1, "cfm_free": 80.0, "params": {"n_blades": 6}},
                              {"trial": 2, "cfm_free": 60.0, "params": {"n_blades": 8}}])
    db = tmp_path / "cat.db"
    save_removed(["opt_a_t2"], tmp_path / "removed.json")
    import fansim.catalog as cat
    orig = cat.REMOVED_LIST
    cat.REMOVED_LIST = tmp_path / "removed.json"   # point the exclusion list at the tmp one
    try:
        build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
        ids = {e.design_id for e in load_catalog(db)}
        assert ids == {"opt_a_t1"}          # opt_a_t2 hidden
    finally:
        cat.REMOVED_LIST = orig


def test_stats_and_empty(tmp_path):
    assert load_catalog(tmp_path / "missing.db") == []
    runs = tmp_path / "runs"
    _make_run(runs, "opt_a", [{"trial": 1, "cfm_free": 80.0, "params": {"n_blades": 6}},
                              {"trial": 2, "cfm_free": 60.0, "params": {"n_blades": 8}}])
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    s = catalog_stats(db)
    assert s["designs"] == 2 and s["pareto"] == 2 and s["measured"] == 0 and s["runs"] == 1
