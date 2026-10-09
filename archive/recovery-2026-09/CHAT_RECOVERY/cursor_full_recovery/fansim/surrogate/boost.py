"""Histogram gradient-boosting CFM mean (sklearn soft-dep; §7.4 boost track)."""

from __future__ import annotations

import numpy as np

_HGBR = None
_IMPORT_ERR: str | None = None
try:
    from sklearn.ensemble import HistGradientBoostingRegressor as _HGBR
except ImportError as exc:  # pragma: no cover - env without sklearn
    _IMPORT_ERR = str(exc)


def available() -> bool:
    return _HGBR is not None


def unavailable_reason() -> str:
    if available():
        return ""
    return _IMPORT_ERR or "scikit-learn not installed (pip install 'fansim[surrogate]')"


class BoostRegressor:
    """Conservative HistGradientBoostingRegressor wrapper for catalog CFM."""

    def __init__(self, *, max_depth: int = 3, max_iter: int = 100, learning_rate: float = 0.1):
        if not available():
            raise ImportError(unavailable_reason())
        self.max_depth = max_depth
        self.max_iter = max_iter
        self.learning_rate = learning_rate
        self._model = None

    def fit(self, X, y) -> "BoostRegressor":
        X = np.atleast_2d(np.asarray(X, float))
        y = np.asarray(y, float).ravel()
        self._model = _HGBR(
            max_depth=self.max_depth,
            max_iter=self.max_iter,
            learning_rate=self.learning_rate,
            random_state=0,
        )
        self._model.fit(X, y)
        return self

    def predict(self, X) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("call fit() before predict()")
        X = np.atleast_2d(np.asarray(X, float))
        return np.asarray(self._model.predict(X), dtype=float).ravel()


def append_and_refit_boost(model, X, y, x_new, y_new):
    """Append one row and return a freshly fitted BoostRegressor + matrices."""
    x_row = np.atleast_2d(np.asarray(x_new, float).reshape(1, -1))
    y_arr = np.asarray(y, float).ravel()
    if y_arr.size == 0:
        X2 = x_row
        y2 = np.asarray([float(y_new)], dtype=float)
    else:
        X2 = np.vstack([np.atleast_2d(np.asarray(X, float)), x_row])
        y2 = np.append(y_arr, float(y_new))
    return BoostRegressor().fit(X2, y2), X2, y2
