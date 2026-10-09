"""NN mean + GP sigma ensemble surrogate (roadmap §7.4). Synthetic only.

Torch is optional; NN tests skip when it's not installed.
"""

from __future__ import annotations

import importlib.util

import numpy as np
import pytest


def _has_torch() -> bool:
    return importlib.util.find_spec("torch") is not None


def test_nn_available_is_bool():
    from fansim.surrogate import nn as nnmod

    assert isinstance(nnmod.available(), bool)


@pytest.mark.skipif(not _has_torch(), reason="torch not installed")
def test_nn_regressor_fit_predict_shape():
    from fansim.surrogate.features import FEATURE_KEYS
    from fansim.surrogate.nn import NnRegressor

    rng = np.random.default_rng(0)
    n, d = 30, len(FEATURE_KEYS)
    X = rng.normal(size=(n, d))
    y = X[:, 0] * 10 + 50

    mu = NnRegressor().fit(X, y).predict(X[:5])
    assert mu.shape == (5,)
    assert np.all(np.isfinite(mu))


@pytest.mark.skipif(not _has_torch(), reason="torch not installed")
def test_nn_gp_ensemble_predict_std():
    from fansim.surrogate.ensemble import NnGpEnsemble
    from fansim.surrogate.features import FEATURE_KEYS, would_skip

    rng = np.random.default_rng(1)
    n, d = 25, len(FEATURE_KEYS)
    X = rng.normal(size=(n, d))
    y = 40 + X.sum(axis=1)

    m = NnGpEnsemble().fit(X, y)
    mu, sig = m.predict(X[:3], return_std=True)
    assert mu.shape == (3,) and sig.shape == (3,)
    assert isinstance(would_skip(float(mu[0]), float(sig[0]), 1e9), bool)


@pytest.mark.skipif(not _has_torch(), reason="torch not installed")
def test_prescreen_fit_nn_returns_ensemble(tmp_path):
    from fansim.surrogate.catalog import MIN_TRAIN, append_and_refit, prescreen_fit
    from fansim.surrogate.ensemble import NnGpEnsemble
    from tests.test_surrogate_catalog import _synthetic_rows, _write_catalog

    db = _write_catalog(tmp_path, _synthetic_rows(MIN_TRAIN + 5))
    model, X, y, why = prescreen_fit(db, nn=True)
    assert why == ""
    assert isinstance(model, NnGpEnsemble)
    assert X is not None and len(y) >= MIN_TRAIN
    x_new = X[0]
    model2, X2, y2 = append_and_refit(model, X, y, x_new, float(y[0]) + 1.0)
    assert isinstance(model2, NnGpEnsemble)
    assert X2.shape[0] == X.shape[0] + 1


def test_fno_stub_available_false_and_raises():
    import fansim.surrogate.fno as fno

    assert fno.available() is False
    with pytest.raises(NotImplementedError):
        fno.train_fno()
    with pytest.raises(NotImplementedError):
        fno.predict_fno()
