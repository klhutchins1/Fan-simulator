# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Tests for the fidelity ladder and the GP surrogate (pure logic / math, no CFD)."""

import numpy as np
import pytest

from fansim.optimize.ladder import FidelityLadder, Tier, pareto_front, top_k
from fansim.surrogate import GaussianProcess, design_matrix


# ---- fidelity ladder ----

def test_ladder_funnels_expensive_evals():
    calls = {"cheap": 0, "fine": 0, "finalist": 0}

    def make(name, score_key):
        def _eval(c):
            calls[name] += 1
            return {score_key: c, "cfm": c}
        return _eval

    ladder = FidelityLadder([
        Tier("cheap", make("cheap", "s"), promote=top_k(3, "s")),
        Tier("fine", make("fine", "s"), promote=top_k(1, "s")),
        Tier("finalist", make("finalist", "s")),
    ])
    run = ladder.run([1, 2, 3, 4, 5])
    assert calls["cheap"] == 5      # every candidate screened cheaply
    assert calls["fine"] == 3       # only top 3 promoted
    assert calls["finalist"] == 1   # only the best reaches the expensive tier
    assert run.funnel == {"cheap": 5, "fine": 3, "finalist": 1}
    assert run.reached("finalist") == [5]


def test_pareto_front_selector():
    # 3 candidates; b is dominated by a (worse on both); a and c are non-dominated
    pairs = [("a", {"x": 2.0, "y": 2.0}), ("b", {"x": 1.0, "y": 1.0}),
             ("c", {"x": 3.0, "y": 0.5})]
    front = pareto_front(["x", "y"], ["maximize", "maximize"])(pairs)
    assert "a" in front and "c" in front and "b" not in front


# ---- GP surrogate ----

def test_gp_interpolates_training_points():
    rng = np.random.default_rng(0)
    X = np.linspace(0, 6, 12)[:, None]
    y = np.sin(X).ravel()
    gp = GaussianProcess(noise=1e-8).fit(X, y)
    pred = gp.predict(X)
    assert np.allclose(pred, y, atol=1e-3)   # near-exact at training points


def test_gp_uncertainty_grows_away_from_data():
    X = np.linspace(0, 3, 8)[:, None]
    y = np.sin(X).ravel()
    gp = GaussianProcess().fit(X, y)
    _, s_near = gp.predict([[1.5]], return_std=True)   # inside the data
    _, s_far = gp.predict([[20.0]], return_std=True)    # far outside
    assert s_far[0] > s_near[0]


def test_gp_multidim_and_design_matrix():
    rng = np.random.default_rng(1)
    keys = ["a", "b", "c"]
    params = [{"a": rng.random(), "b": rng.random(), "c": rng.random()} for _ in range(30)]
    X = design_matrix(params, keys)
    assert X.shape == (30, 3)
    y = X[:, 0] ** 2 + 2 * X[:, 1] - X[:, 2]   # smooth function
    gp = GaussianProcess().fit(X[:25], y[:25])
    pred = gp.predict(X[25:])
    # held-out prediction correlates strongly with truth
    assert np.corrcoef(pred, y[25:])[0, 1] > 0.9


def test_gp_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        GaussianProcess().predict([[0.0]])
