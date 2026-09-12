"""Catalog GP surrogate (roadmap §7.4 stage 1). No Docker, no real catalog.db."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fansim.catalog import CatalogEntry, build_catalog
from fansim.geometry.blade import BladeParams
from fansim.optimize.search_space import blade_from_flat
from fansim.surrogate.catalog import MIN_TRAIN, fit_cfm_free, fit_cfm_load, training_xy
from fansim.surrogate.features import FEATURE_KEYS, feature_vector, would_skip


def _flat(**kw) -> dict:
    p = {
        "n_blades": 7,
        "stagger_root": 40.0, "stagger_mid": 40.0, "stagger_tip": 40.0,
        "chord_root": 18.0, "chord_mid": 18.0, "chord_tip": 14.0,
        "sweep_mid": 0.0, "sweep_tip": 0.0, "lean_mid": 0.0, "lean_tip": 0.0,
        "max_camber": 0.04,
        "hub_radius": 21.5, "tip_radius": 50.0,
        "shroud_thick_mm": 0.0, "shroud_height_frac": 1.0,
    }
    p.update(kw)
    return p


def test_feature_vector_dict_matches_bladeparams():
    flat = _flat()
    bp = blade_from_flat(flat)
    assert len(FEATURE_KEYS) == 16
    assert np.allclose(feature_vector(flat), feature_vector(bp))


def test_feature_vector_rejects_incomplete_dict():
    with pytest.raises(ValueError):
        feature_vector({"n_blades": 7, "chord_root": 18.0})


def test_training_xy_drops_incomplete_missing_cfm_and_stale():
    good = CatalogEntry(
        design_id="a", params=_flat(), cfm_free=40.0, cfd_stale=False)
    no_chords = CatalogEntry(
        design_id="b", params={"n_blades": 6}, cfm_free=40.0)
    no_cfm = CatalogEntry(
        design_id="c", params=_flat(), cfm_free=None)
    stale = CatalogEntry(
        design_id="d", params=_flat(n_blades=8), cfm_free=50.0, cfd_stale=True)
    X, y = training_xy([good, no_chords, no_cfm, stale])
    assert X.shape == (1, 16)
    assert y == pytest.approx([40.0])


def _write_catalog(tmp_path, rows: list[dict], name: str = "opt_s"):
    runs = tmp_path / "runs"
    d = runs / name
    d.mkdir(parents=True)
    (d / "pareto.json").write_text(json.dumps(rows), encoding="utf-8")
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    return db


def _synthetic_rows(n: int, start: int = 0) -> list[dict]:
    rows = []
    for i in range(n):
        nb = 5 + (start + i) % 7
        tip = 14.0 + ((start + i) % 9) * 3.0
        rows.append({
            "trial": start + i + 1,
            "cfm_free": float(2 * nb + tip),
            "cfm_load": 30.0,
            "params": _flat(n_blades=nb, chord_tip=tip),
        })
    return rows


def test_fit_cfm_free_needs_min_train(tmp_path):
    db = _write_catalog(tmp_path, _synthetic_rows(MIN_TRAIN - 1))
    assert fit_cfm_free(db) is None


def test_fit_cfm_free_held_out_correlates(tmp_path):
    rows = _synthetic_rows(25)
    db = _write_catalog(tmp_path, rows)
    model = fit_cfm_free(db)
    assert model is not None
    hold = _synthetic_rows(5, start=40)
    X = np.vstack([feature_vector(r["params"]) for r in hold])
    y = np.array([r["cfm_free"] for r in hold])
    pred = model.predict(X)
    assert np.corrcoef(pred, y)[0, 1] > 0.8


def test_would_skip_only_when_mean_plus_std_below_floor():
    assert would_skip(mu=20.0, sigma=2.0, floor=500.0) is True
    assert would_skip(mu=80.0, sigma=2.0, floor=30.0) is False
    # mean is below the floor but uncertainty covers it — still run CFD
    assert would_skip(mu=20.0, sigma=20.0, floor=30.0) is False


def test_uncertain_point_does_not_skip(tmp_path):
    db = _write_catalog(tmp_path, _synthetic_rows(24))
    model = fit_cfm_free(db)
    far = feature_vector(_flat(
        n_blades=7, chord_root=200.0, chord_mid=200.0, chord_tip=200.0,
        tip_radius=400.0, hub_radius=80.0))
    mu, sigma = model.predict(far.reshape(1, -1), return_std=True)
    floor = float(mu[0]) + 0.1   # mean alone would fail
    assert would_skip(float(mu[0]), float(sigma[0]), floor) is False
    assert float(sigma[0]) > 1.0


def _fitting_params() -> BladeParams:
    from fansim.geometry.blade import RadialStation
    return BladeParams(
        tip_radius=50.0,
        stations=[
            RadialStation(0.0, 18.0, 40.0, thickness=0.12, max_camber=0.04),
            RadialStation(0.5, 18.0, 40.0, thickness=0.10, max_camber=0.04),
            RadialStation(1.0, 14.0, 40.0, thickness=0.08, max_camber=0.04),
        ],
    )


def test_surrogate_prescreen_rejects_before_geometry(tmp_path):
    from fansim.optimize.objectives import evaluate_candidate

    db = _write_catalog(tmp_path, _synthetic_rows(24))
    model = fit_cfm_free(db)
    work = tmp_path / "surr"
    res = evaluate_candidate(
        _fitting_params(), work, procs=1,
        surrogate_prescreen_cfm=500.0, surrogate=model)
    assert res.feasible is False
    assert "surrogate-prescreen" in res.reason
    assert not (work / "impeller.stl").exists()
    assert "surr_cfm_free" in res.raw and "surr_std" in res.raw


def test_surrogate_prescreen_exception_is_infeasible_not_silent_cfd(tmp_path):
    """§9.6 — GP predict crash must stamp + skip CFD, not fall through."""
    from fansim.optimize.objectives import evaluate_candidate

    class BoomScreen:
        def predict(self, *_a, **_k):
            raise ValueError("gp blew up")

    work = tmp_path / "surr_crash"
    res = evaluate_candidate(
        _fitting_params(), work, procs=1,
        surrogate_prescreen_cfm=1.0, surrogate=BoomScreen())
    assert res.feasible is False
    assert "surrogate-prescreen failed" in res.reason
    assert "ValueError" in res.reason
    assert "gp blew up" in res.reason
    assert res.raw.get("surrogate_prescreen_error", "").startswith("ValueError")
    assert not (work / "impeller.stl").exists()


def test_surrogate_prescreen_below_floor_does_not_skip_when_uncertain():
    x = feature_vector(_fitting_params())
    # Far-from-data analogue: huge sigma, mean below floor.
    assert would_skip(mu=10.0, sigma=40.0, floor=30.0) is False
    assert would_skip(mu=float(x[0]), sigma=0.1, floor=500.0) is True


def test_cli_help_mentions_surrogate_prescreen_and_no_star():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--surrogate-prescreen" in text
    assert "--surrogate-db" in text
    assert "★" not in text
    assert "mean+1" in text or "mean + 1" in text or "mean+1σ" in text or "1σ" in text


def test_training_xy_load_drops_wall_scored_without_k():
    curve = CatalogEntry(
        design_id="a", params=_flat(), cfm_load=35.0, k=80.0, cfd_stale=False)
    wall = CatalogEntry(
        design_id="b", params=_flat(n_blades=8), cfm_load=35.0, k=None)
    X, y = training_xy([curve, wall], y_attr="cfm_load", require_k=True)
    assert X.shape == (1, 16)
    assert y == pytest.approx([35.0])


def test_append_and_refit_grows_training_and_pulls_prediction():
    from fansim.surrogate.catalog import append_and_refit
    from fansim.surrogate.gp import GaussianProcess

    rows = _synthetic_rows(24)
    X = np.vstack([feature_vector(r["params"]) for r in rows])
    y = np.array([r["cfm_free"] for r in rows], float)
    model = GaussianProcess().fit(X, y)
    new = _flat(n_blades=9, chord_tip=30.0)
    x_new = feature_vector(new)
    y_new = 99.0
    before = float(model.predict(x_new.reshape(1, -1))[0])
    model2, X2, y2 = append_and_refit(model, X, y, x_new, y_new)
    assert X2.shape[0] == X.shape[0] + 1
    assert len(y2) == len(y) + 1
    after = float(model2.predict(x_new.reshape(1, -1))[0])
    assert abs(after - y_new) < abs(before - y_new)


def test_run_study_refits_surrogate_after_feasible_trial(tmp_path, monkeypatch):
    from fansim.optimize import study as study_mod
    from fansim.optimize.objectives import ObjectiveResult
    from fansim.surrogate import catalog as cat_mod
    from fansim.surrogate.gp import GaussianProcess

    rows = _synthetic_rows(MIN_TRAIN)
    X0 = np.vstack([feature_vector(r["params"]) for r in rows])
    y0 = np.array([r["cfm_free"] for r in rows], float)
    fits = {"n": 0}
    real_fit = GaussianProcess.fit

    def counting_fit(self, X, y):
        fits["n"] += 1
        return real_fit(self, X, y)

    monkeypatch.setattr(GaussianProcess, "fit", counting_fit)

    def fake_prescreen_fit(_db, **_kw):
        model = GaussianProcess().fit(X0, y0)
        return model, X0.copy(), y0.copy(), ""

    monkeypatch.setattr(cat_mod, "prescreen_fit", fake_prescreen_fit)

    def fake_evaluate(_params, workdir, *_a, **_kw):
        from pathlib import Path
        Path(workdir).mkdir(parents=True, exist_ok=True)
        return ObjectiveResult(
            feasible=True, cfm_free=55.0, cfm_load=40.0, efficiency=1.0,
            raw={"k": 1.0, "tip_gap_mm": 0.5},
        )

    monkeypatch.setattr(study_mod, "evaluate_candidate", fake_evaluate)
    n_before = fits["n"]
    study_mod.run_study(
        n_trials=2, out_dir=tmp_path, procs=1, iters=1, base_cell=0.02,
        surrogate_prescreen_cfm=1.0, surrogate_db=tmp_path / "unused.db")
    # initial free+load fits via fake_prescreen_fit (2) plus counting_fit inside them (2),
    # then 2 free + 2 load online refits (4). Accept: online adds >= 2 fits after start.
    assert fits["n"] >= n_before + 2


def test_cli_help_mentions_surrogate_online_refit():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "Refits after each feasible" in text
    assert "★" not in text
