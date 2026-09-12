"""Boosting + GP ensemble surrogate (roadmap §7.4). Synthetic only."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from fansim.surrogate.boost import available


def test_cli_help_mentions_surrogate_boost():
    text = Path("scripts/run_optimization.py").read_text(encoding="utf-8")
    assert "--surrogate-boost" in text
    assert "★" not in text


def test_available_matches_sklearn_import():
    try:
        import sklearn  # noqa: F401
        assert available() is True
    except ImportError:
        assert available() is False


@pytest.mark.skipif(not available(), reason="sklearn not installed")
def test_boost_regressor_fits_and_predicts_finite():
    from fansim.surrogate.boost import BoostRegressor
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 16))
    y = 2.0 * X[:, 0] + 0.5 * X[:, 1] ** 2
    m = BoostRegressor().fit(X, y)
    pred = m.predict(X[:5])
    assert pred.shape == (5,)
    assert np.all(np.isfinite(pred))


@pytest.mark.skipif(not available(), reason="sklearn not installed")
def test_append_and_refit_boost_grows_training():
    from fansim.surrogate.boost import BoostRegressor, append_and_refit_boost
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 16))
    y = X[:, 0] + 0.2 * X[:, 2]
    m = BoostRegressor().fit(X, y)
    x_new = X[0] + 0.01
    m2, X2, y2 = append_and_refit_boost(m, X, y, x_new, 10.0)
    assert X2.shape[0] == X.shape[0] + 1
    assert y2.shape[0] == y.shape[0] + 1
    assert np.isfinite(m2.predict(x_new.reshape(1, -1))[0])


@pytest.mark.skipif(not available(), reason="sklearn not installed")
def test_ensemble_mu_from_boost_sigma_from_gp():
    from fansim.surrogate.boost import BoostRegressor
    from fansim.surrogate.ensemble import BoostGpEnsemble
    from fansim.surrogate.gp import GaussianProcess
    rng = np.random.default_rng(2)
    X = rng.normal(size=(50, 16))
    y = 2.0 * X[:, 0] + 0.5 * X[:, 1] ** 2
    ens = BoostGpEnsemble().fit(X, y)
    gp = GaussianProcess().fit(X, y)
    x = X[:3]
    mu_e, sig_e = ens.predict(x, return_std=True)
    _mu_g, sig_g = gp.predict(x, return_std=True)
    mu_b = BoostRegressor().fit(X, y).predict(x)
    assert np.allclose(sig_e, sig_g, rtol=1e-5, atol=1e-5)
    assert np.allclose(mu_e, mu_b, rtol=1e-5, atol=1e-5)


@pytest.mark.skipif(not available(), reason="sklearn not installed")
def test_ensemble_would_skip_uses_boost_mu_plus_gp_sigma():
    from fansim.surrogate.ensemble import BoostGpEnsemble
    from fansim.surrogate.features import would_skip
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 16))
    y = X[:, 0] - 100.0
    ens = BoostGpEnsemble().fit(X, y)
    mu, sigma = ens.predict(X[:1], return_std=True)
    assert would_skip(float(mu[0]), float(sigma[0]), floor=500.0) is True


@pytest.mark.skipif(not available(), reason="sklearn not installed")
def test_prescreen_fit_boost_returns_ensemble(tmp_path):
    from fansim.surrogate.catalog import MIN_TRAIN, append_and_refit, prescreen_fit
    from fansim.surrogate.ensemble import BoostGpEnsemble
    from tests.test_surrogate_catalog import _synthetic_rows, _write_catalog
    db = _write_catalog(tmp_path, _synthetic_rows(MIN_TRAIN + 5))
    model, X, y, why = prescreen_fit(db, boost=True)
    assert why == ""
    assert isinstance(model, BoostGpEnsemble)
    assert X is not None and len(y) >= MIN_TRAIN
    x_new = X[0]
    model2, X2, y2 = append_and_refit(model, X, y, x_new, float(y[0]) + 1.0)
    assert isinstance(model2, BoostGpEnsemble)
    assert X2.shape[0] == X.shape[0] + 1
