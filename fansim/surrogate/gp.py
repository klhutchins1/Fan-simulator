# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Minimal Gaussian-process regressor (RBF kernel) — dependency-light surrogate for screening.

Exact GP regression: standardize inputs, RBF kernel, Cholesky solve. Length scale defaults to the
median pairwise distance (a robust, standard heuristic) or is chosen by maximizing the log marginal
likelihood over a small grid. Returns predictive mean and standard deviation, so the optimizer can
skip CFD on designs the surrogate is confident are poor, and spend evals where it's uncertain.
"""

from __future__ import annotations

import numpy as np
from scipy.linalg import cho_factor, cho_solve


def design_matrix(params_list: list[dict], keys: list[str]) -> np.ndarray:
    """Stack a list of param dicts into an (n_samples, n_keys) array in a fixed key order."""
    return np.array([[float(p[k]) for k in keys] for p in params_list], dtype=float)


def _rbf(a, b, ls, sig):
    # squared euclidean distances between rows of a and b
    d2 = np.sum(a**2, 1)[:, None] + np.sum(b**2, 1)[None, :] - 2.0 * a @ b.T
    return sig * np.exp(-np.maximum(d2, 0.0) / (2.0 * ls**2))


class GaussianProcess:
    """Exact GP regression with an RBF kernel and Gaussian noise."""

    def __init__(self, length_scale: float | None = None, signal_var: float | None = None,
                 noise: float = 1e-6, optimize: bool = True):
        self.length_scale = length_scale
        self.signal_var = signal_var
        self.noise = noise
        self.optimize = optimize
        self._fitted = False

    def _standardize(self, X):
        return (X - self._xm) / self._xs

    def log_marginal_likelihood(self, ls: float) -> float:
        K = _rbf(self._Xs, self._Xs, ls, self.signal_var) + self.noise * np.eye(len(self._Xs))
        try:
            c, low = cho_factor(K)
        except np.linalg.LinAlgError:
            return -np.inf
        alpha = cho_solve((c, low), self._yc)
        # -0.5 y^T alpha - sum(log diag L) - n/2 log(2pi)
        return float(-0.5 * self._yc @ alpha - np.sum(np.log(np.diag(c)))
                     - 0.5 * len(self._Xs) * np.log(2.0 * np.pi))

    def fit(self, X, y) -> "GaussianProcess":
        X = np.atleast_2d(np.asarray(X, float))
        y = np.asarray(y, float).ravel()
        self._xm, self._xs = X.mean(0), X.std(0)
        self._xs[self._xs == 0] = 1.0
        self._Xs = self._standardize(X)
        self._ym = y.mean()
        self._yc = y - self._ym
        if self.signal_var is None:
            self.signal_var = float(np.var(y)) or 1.0
        # length scale: median pairwise distance, optionally refined by marginal likelihood
        d2 = (np.sum(self._Xs**2, 1)[:, None] + np.sum(self._Xs**2, 1)[None, :]
              - 2.0 * self._Xs @ self._Xs.T)
        med = np.sqrt(np.median(d2[d2 > 0])) if np.any(d2 > 0) else 1.0
        if self.length_scale is None:
            self.length_scale = float(med)
            if self.optimize and len(X) >= 4:
                grid = med * np.array([0.25, 0.5, 1.0, 2.0, 4.0])
                self.length_scale = float(max(grid, key=self.log_marginal_likelihood))
        K = _rbf(self._Xs, self._Xs, self.length_scale, self.signal_var) + self.noise * np.eye(len(X))
        self._chol = cho_factor(K)
        self._alpha = cho_solve(self._chol, self._yc)
        self._fitted = True
        return self

    def predict(self, Xstar, return_std: bool = False):
        if not self._fitted:
            raise RuntimeError("call fit() before predict()")
        Xstar = np.atleast_2d(np.asarray(Xstar, float))
        Ks = _rbf(self._standardize(Xstar), self._Xs, self.length_scale, self.signal_var)
        mean = Ks @ self._alpha + self._ym
        if not return_std:
            return mean
        v = cho_solve(self._chol, Ks.T)
        var = self.signal_var - np.sum(Ks * v.T, axis=1)
        return mean, np.sqrt(np.maximum(var, 0.0))
