"""Boost mean + GP sigma ensemble for catalog pre-screen (§7.4)."""

from __future__ import annotations

import numpy as np

from fansim.surrogate.boost import BoostRegressor, available
from fansim.surrogate.gp import GaussianProcess


class BoostGpEnsemble:
    """``predict(..., return_std=True)`` → (μ_boost, σ_gp), same shape as the GP API."""

    def __init__(self):
        self.gp = GaussianProcess()
        self.boost = BoostRegressor() if available() else None
        self._fitted = False

    def fit(self, X, y) -> "BoostGpEnsemble":
        if not available():
            raise ImportError("sklearn required for BoostGpEnsemble")
        X = np.atleast_2d(np.asarray(X, float))
        y = np.asarray(y, float).ravel()
        self.gp = GaussianProcess().fit(X, y)
        self.boost = BoostRegressor().fit(X, y)
        self._fitted = True
        return self

    def predict(self, Xstar, return_std: bool = False):
        if not self._fitted or self.boost is None:
            raise RuntimeError("call fit() before predict()")
        Xstar = np.atleast_2d(np.asarray(Xstar, float))
        mu = self.boost.predict(Xstar)
        if not return_std:
            return mu
        _mu_gp, sigma = self.gp.predict(Xstar, return_std=True)
        return mu, sigma
