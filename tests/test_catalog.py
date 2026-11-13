"""Unified design catalog (fansim/catalog.py)."""

from __future__ import annotations

import json
from pathlib import Path

from fansim.catalog import build_catalog, catalog_stats, get_entry, load_catalog
from validation.ingest import MeasuredPoint
from validation.store import record_measurement


def _make_run(runs: Path, name: str, trials: list[dict]):
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


def test_classify_puts_small_blade_on_a12x25(tmp_path):
    from fansim.catalog import results_for_hub
    runs = tmp_path / "runs"
    params = {
        # Stock's hub (21.5 mm). Since a6b77c9 the A12x25 grip pads need r >= 21.075 mm, so 21.0 no longer fits.
        "n_blades": 5, "hub_radius": 21.5, "tip_radius": 49.8,
        "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
        "chord_root": 34, "chord_mid": 30, "chord_tip": 28,
        "sweep_mid": 0, "sweep_tip": 2, "max_camber": 0.02,
    }
    _make_run(runs, "opt_realframe", [{"trial": 22, "cfm_free": 53.9, "cfm_load": 50.0,
                                       "efficiency": 30.0, "params": params}])
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    e = get_entry("opt_realframe_t22", db)
    assert "a12x25" in e.hub_models
    assert e.fit_status == "fits"
    hits = results_for_hub(load_catalog(db), "a12x25")
    assert any(x.design_id == "opt_realframe_t22" for x in hits)


def test_oversized_tip_not_in_a12x25_results(tmp_path):
    from fansim.catalog import results_for_hub
    runs = tmp_path / "runs"
    params = {"n_blades": 9, "hub_radius": 16.5, "tip_radius": 59.0,
              "stagger_root": 26, "stagger_mid": 26, "stagger_tip": 22,
              "chord_root": 34, "chord_mid": 44, "chord_tip": 38,
              "sweep_mid": 3, "sweep_tip": 5, "max_camber": 0.05}
    _make_run(runs, "opt_run1", [{"trial": 9038, "cfm_free": 92.4, "cfm_load": 87.0,
                                  "efficiency": 35.0, "params": params}])
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    e = get_entry("opt_run1_t9038", db)
    assert "a12x25" not in (e.hub_models or [])
    hits = results_for_hub(load_catalog(db), "a12x25")
    assert all(x.design_id != "opt_run1_t9038" for x in hits)


def test_placed_on_includes_in_results_even_if_geometry_borderline():
    from fansim.catalog import CatalogEntry, results_for_hub
    e = CatalogEntry(design_id="placed_t1", hub_models=[], placed_on="a12x25",
                     cfd_stale=True, fit_status="fits")
    hits = results_for_hub([e], "a12x25")
    assert hits[0].design_id == "placed_t1"
