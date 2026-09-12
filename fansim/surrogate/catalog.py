"""Fit the catalog GP on free-delivery CFM (roadmap §7.4 stage 1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from fansim.catalog import CatalogEntry, load_catalog
from fansim.surrogate.features import FEATURE_KEYS, feature_vector
from fansim.surrogate.gp import GaussianProcess

MIN_TRAIN = 20


def training_xy(
    entries: list[CatalogEntry],
    *,
    y_attr: str = "cfm_free",
    require_k: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Rows with a geometry vector and a finite target; stale / incomplete dropped.

    ``require_k=True`` keeps only curve-scored rows (system-curve ``k`` set) so wall-scored
    ``cfm_load`` does not mix into the load-line GP.
    """
    xs, ys = [], []
    for e in entries:
        if e.cfd_stale:
            continue
        if require_k and e.k is None:
            continue
        y_raw = getattr(e, y_attr, None)
        if y_raw is None:
            continue
        try:
            y = float(y_raw)
        except (TypeError, ValueError):
            continue
        if not np.isfinite(y):
            continue
        try:
            xs.append(feature_vector(e.params or {}))
        except (ValueError, TypeError, KeyError):
            continue
        ys.append(y)
    if not xs:
        return np.zeros((0, len(FEATURE_KEYS))), np.zeros(0)
    return np.vstack(xs), np.asarray(ys, dtype=float)


def append_and_refit(model, X, y, x_new, y_new):
    """Append one training row and return a freshly fitted screen model + matrices.

    Refits a ``BoostGpEnsemble`` when ``model`` is one; otherwise a bare GP.
    """
    from fansim.surrogate.ensemble import BoostGpEnsemble

    x_row = np.atleast_2d(np.asarray(x_new, float).reshape(1, -1))
    y_arr = np.asarray(y, float).ravel()
    if y_arr.size == 0:
        X2 = x_row
        y2 = np.asarray([float(y_new)], dtype=float)
    else:
        X2 = np.vstack([np.atleast_2d(np.asarray(X, float)), x_row])
        y2 = np.append(y_arr, float(y_new))
    if isinstance(model, BoostGpEnsemble):
        return BoostGpEnsemble().fit(X2, y2), X2, y2
    return GaussianProcess().fit(X2, y2), X2, y2


def prescreen_fit(
    db: str | Path,
    *,
    y_attr: str = "cfm_free",
    require_k: bool = False,
    boost: bool = False,
) -> tuple[object | None, np.ndarray | None, np.ndarray | None, str]:
    """Fitted GP (or boost+GP ensemble) + training matrices, or (None, None, None, reason)."""
    db = Path(db)
    if not db.exists():
        return None, None, None, f"no catalog at {db}"
    X, y = training_xy(load_catalog(db), y_attr=y_attr, require_k=require_k)
    kind = "curve-scored load" if require_k else "free"
    if len(y) < MIN_TRAIN:
        return None, None, None, f"{len(y)} {kind} rows with a geometry vector (need {MIN_TRAIN})"
    try:
        if boost:
            from fansim.surrogate.boost import available, unavailable_reason
            from fansim.surrogate.ensemble import BoostGpEnsemble
            if available():
                return BoostGpEnsemble().fit(X, y), X, y, ""
            gp = GaussianProcess().fit(X, y)
            return gp, X, y, f"boost unavailable ({unavailable_reason()}); using GP"
        return GaussianProcess().fit(X, y), X, y, ""
    except Exception as exc:  # noqa: BLE001 - screen must never break the study
        return None, None, None, str(exc)


def prescreen_model(
    db: str | Path,
    *,
    y_attr: str = "cfm_free",
    require_k: bool = False,
    boost: bool = False,
) -> tuple[object | None, str]:
    """Fitted screen model, or (None, reason) when the screen must stay off."""
    model, _X, _y, reason = prescreen_fit(
        db, y_attr=y_attr, require_k=require_k, boost=boost)
    return model, reason


def fit_cfm_free(db: str | Path) -> GaussianProcess | None:
    model, _reason = prescreen_model(db)
    return model


def fit_cfm_load(db: str | Path) -> GaussianProcess | None:
    model, _reason = prescreen_model(db, y_attr="cfm_load", require_k=True)
    return model
