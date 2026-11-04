"""Surrogate-guided search (roadmap §20.5). No Docker."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fansim.optimize.surrogate_search import (
    SurrogateCandidate,
    acquisition_ucb,
    fit_models,
    latin_hypercube,
    nsga_on_surrogate,
    predict_mu_sigma,
    run_surrogate_guided,
    seed_from_catalog,
    select_top_k,
    space_filling_doe,
    synthetic_label,
)
from fansim.surrogate.features import FEATURE_KEYS, feature_vector
from fansim.surrogate.gp import GaussianProcess


def test_latin_hypercube_shape_and_unit_cube():
    u = latin_hypercube(20, 5, seed=7)
    assert u.shape == (20, 5)
    assert np.all(u >= 0.0) and np.all(u <= 1.0)
    # One sample per stratum along each dim (LHS property on sorted bins).
    for j in range(5):
        ranks = np.argsort(np.argsort(u[:, j]))
        assert set(ranks.tolist()) == set(range(20))


def test_space_filling_doe_in_bounds():
    doe = space_filling_doe(12, space="guided", seed=1)
    assert len(doe) == 12
    from fansim.optimize.surrogate_search import search_bounds
    bounds = search_bounds("guided")
    for p in doe:
        assert "n_blades" in p and "chord_tip" in p
        for k, (lo, hi) in bounds.items():
            if k == "n_blades":
                assert lo <= p[k] <= hi
            else:
                assert lo - 1e-9 <= p[k] <= hi + 1e-9
        # feature_vector must accept DoE rows
        assert feature_vector(p).shape == (len(FEATURE_KEYS),)


def test_fit_and_predict_gp_on_synthetic():
    doe = space_filling_doe(30, space="guided", seed=3)
    X = np.vstack([feature_vector(p) for p in doe])
    y = {
        "cfm_free": np.array([synthetic_label(p)["cfm_free"] for p in doe]),
        "cfm_load": np.array([synthetic_label(p)["cfm_load"] for p in doe]),
        "efficiency": np.array([synthetic_label(p)["efficiency"] for p in doe]),
    }
    models = fit_models(X, y)
    assert isinstance(models["cfm_free"], GaussianProcess)
    mu, sigma = predict_mu_sigma(models, X[:5])
    assert mu["cfm_free"].shape == (5,)
    assert sigma["cfm_free"].shape == (5,)
    assert np.all(sigma["cfm_free"] >= 0.0)
    # Hold-out correlation should be strong on the synthetic law.
    hold = space_filling_doe(8, space="guided", seed=99)
    Xh = np.vstack([feature_vector(p) for p in hold])
    yh = np.array([synthetic_label(p)["cfm_free"] for p in hold])
    pred = models["cfm_free"].predict(Xh)
    assert np.corrcoef(pred, yh)[0, 1] > 0.7


class _MockSurrogate:
    """Deterministic μ/σ for ranking tests (no fit)."""

    def __init__(self, mu_fn, sigma_fn):
        self._mu = mu_fn
        self._sigma = sigma_fn

    def predict(self, X, return_std: bool = False):
        X = np.atleast_2d(np.asarray(X, float))
        mu = np.array([self._mu(row) for row in X], dtype=float)
        if not return_std:
            return mu
        sigma = np.array([self._sigma(row) for row in X], dtype=float)
        return mu, sigma


def test_nsga_on_surrogate_ranks_with_mock_predictions():
    # Prefer higher tip chord via FEATURE_KEYS index of chord_tip.
    tip_i = FEATURE_KEYS.index("chord_tip")

    def mu_free(row):
        return 2.0 * float(row[tip_i])

    def sigma_free(row):
        return 0.1 * float(row[tip_i])

    models = {
        "cfm_free": _MockSurrogate(mu_free, sigma_free),
        "cfm_load": _MockSurrogate(lambda r: 0.5 * mu_free(r), lambda r: 0.05),
        "efficiency": _MockSurrogate(lambda r: 10.0 + 0.01 * r[tip_i], lambda r: 0.01),
    }
    pool = nsga_on_surrogate(models, space="guided", n_trials=40, seed=11, population_size=8)
    assert len(pool) == 40
    assert all("chord_tip" in c.params for c in pool)
    # Pareto / high-μ designs should skew toward larger tip chords than the bound midpoint.
    tips = [c.params["chord_tip"] for c in pool]
    assert np.mean(tips) > 30.0  # guided tip chord mid is ~33; NSGA maximizes tip-linked μ


def test_select_top_k_uses_ensemble_spread_acquisition():
    cands = [
        SurrogateCandidate(
            params={"id": 1}, mu={"cfm_free": 40.0}, sigma={"cfm_free": 0.5},
        ),
        SurrogateCandidate(
            params={"id": 2}, mu={"cfm_free": 38.0}, sigma={"cfm_free": 5.0},
        ),
        SurrogateCandidate(
            params={"id": 3}, mu={"cfm_free": 50.0}, sigma={"cfm_free": 0.1},
        ),
    ]
    # κ=1: id2 has UCB 43, id1=40.5, id3=50.1 → top-2 are 3 then 2
    top = select_top_k(cands, 2, kappa=1.0)
    assert [c.params["id"] for c in top] == [3, 2]
    assert top[0].acquisition == pytest.approx(acquisition_ucb(50.0, 0.1, 1.0))
    assert top[1].acquisition == pytest.approx(acquisition_ucb(38.0, 5.0, 1.0))


def test_run_surrogate_guided_stub_loop(tmp_path):
    calls = {"n": 0}

    def verify(params, workdir):
        calls["n"] += 1
        Path(workdir).mkdir(parents=True, exist_ok=True)
        y = synthetic_label(params)
        return True, y, "mock"

    result = run_surrogate_guided(
        out_dir=tmp_path / "sg",
        n_doe=16,
        n_nsga=24,
        top_k=3,
        n_rounds=2,
        space="guided",
        seed=5,
        verify_fn=verify,
        catalog_db=None,
    )
    assert calls["n"] == 6  # 2 rounds × top_k 3
    assert len(result.verified) == 6
    assert all(c.feasible for c in result.verified)
    assert (tmp_path / "sg" / "surrogate_guided.json").exists()
    assert len(result.X) >= 16 + 6  # DoE + verified
    assert any("DoE" in n for n in result.notes)


def test_verify_cfd_does_not_label_doe_with_synthetic(tmp_path, monkeypatch):
    """QA-66: --verify-cfd must not train the DoE on synthetic_label."""
    from fansim.optimize import surrogate_search as ss

    calls = {"n": 0}
    real = ss.synthetic_label

    def counting(params):
        calls["n"] += 1
        return real(params)

    monkeypatch.setattr(ss, "synthetic_label", counting)

    def verify(params, workdir):
        Path(workdir).mkdir(parents=True, exist_ok=True)
        return True, real(params), "mock-cfd"

    with pytest.raises(RuntimeError, match="catalog with"):
        ss.run_surrogate_guided(
            out_dir=tmp_path / "sg",
            n_doe=8,
            n_nsga=8,
            top_k=1,
            n_rounds=1,
            space="guided",
            seed=3,
            verify_fn=verify,
            verify_cfd=True,
            catalog_db=None,
        )
    assert calls["n"] == 0


def test_verify_cfd_refuses_empty_catalog(tmp_path, monkeypatch):
    """Claude review 2026-11-03: refuse up front, do not return an empty result."""
    monkeypatch.setattr("fansim.cfd.runner.image_available", lambda: True)
    with pytest.raises(RuntimeError, match=r"catalog with ≥ 8 CFD rows"):
        run_surrogate_guided(
            out_dir=tmp_path / "sg",
            n_doe=4,
            n_nsga=4,
            top_k=1,
            n_rounds=1,
            verify_cfd=True,
            verify_fn=lambda p, w: (True, synthetic_label(p), "mock"),
            catalog_db=None,
        )


def test_verify_cfd_refuses_stub_when_docker_missing(tmp_path, monkeypatch):
    """QA-66: missing Docker under --verify-cfd is a refuse, not stub_verify."""
    monkeypatch.setattr("fansim.cfd.runner.image_available", lambda: False)
    with pytest.raises(RuntimeError, match="OpenFOAM Docker"):
        run_surrogate_guided(
            out_dir=tmp_path / "sg",
            n_doe=4,
            n_nsga=4,
            top_k=1,
            n_rounds=1,
            verify_cfd=True,
        )


def test_stub_labels_stamped_on_disk(tmp_path):
    """QA-66: --stub-labels writes 'synthetic labels, not CFD' into the JSON."""

    def verify(params, workdir):
        Path(workdir).mkdir(parents=True, exist_ok=True)
        return True, synthetic_label(params), "mock"

    run_surrogate_guided(
        out_dir=tmp_path / "sg",
        n_doe=8,
        n_nsga=8,
        top_k=1,
        n_rounds=1,
        space="guided",
        seed=2,
        verify_fn=verify,
        stub_labels=True,
    )
    data = json.loads((tmp_path / "sg" / "surrogate_guided.json").read_text(encoding="utf-8"))
    assert "synthetic labels, not CFD" in json.dumps(data)


def test_catalog_efficiency_prior_stamped_on_disk(tmp_path):
    """Claude review 2026-11-03: catalog efficiency (and load if filled) is a prior, not CFD."""
    from fansim.catalog import build_catalog

    runs = tmp_path / "runs"
    d = runs / "opt_s"
    d.mkdir(parents=True)
    rows = []
    for i in range(8):
        rows.append({
            "trial": i + 1,
            "cfm_free": float(40 + i),
            "cfm_load": 30.0,
            "params": {
                "n_blades": 7,
                "stagger_root": 40.0, "stagger_mid": 40.0, "stagger_tip": 40.0,
                "chord_root": 18.0, "chord_mid": 18.0, "chord_tip": 14.0 + i,
                "sweep_mid": 0.0, "sweep_tip": 0.0, "lean_mid": 0.0, "lean_tip": 0.0,
                "max_camber": 0.04,
                "hub_radius": 21.5, "tip_radius": 50.0,
            },
        })
    (d / "pareto.json").write_text(json.dumps(rows), encoding="utf-8")
    db = tmp_path / "cat.db"
    build_catalog(runs_dir=runs, store_dir=tmp_path / "none", db=db)
    _, _, note, priors = seed_from_catalog(db)
    assert priors["efficiency"] == "prior, not CFD"
    assert priors["cfm_load"] == "prior, not CFD"
    assert "prior, not CFD" in note
    result = run_surrogate_guided(
        out_dir=tmp_path / "sg",
        n_doe=8,
        n_nsga=8,
        top_k=1,
        n_rounds=1,
        stub_labels=True,
        catalog_db=db,
        verify_fn=lambda p, w: (True, synthetic_label(p), "mock"),
    )
    data = json.loads((tmp_path / "sg" / "surrogate_guided.json").read_text(encoding="utf-8"))
    assert data["priors"]["efficiency"] == "prior, not CFD"
    assert data["priors"]["cfm_load"] == "prior, not CFD"
