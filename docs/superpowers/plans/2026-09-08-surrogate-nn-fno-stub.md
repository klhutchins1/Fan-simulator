# Catalog NN+GP Ensemble + FNO Stub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opt-in neural mean + GP sigma for `--surrogate-prescreen`, plus an honest FNO stub that refuses to train without field data.

**Architecture:** Mirror `BoostGpEnsemble`: `NnRegressor` (soft-dep torch) for μ, existing `GaussianProcess` for σ, same `would_skip`. Wire `--surrogate-nn` (nn wins over boost if both set). Add `fansim/surrogate/fno.py` stub. Optional extra `fansim[surrogate-nn]`.

**Tech Stack:** Python 3.12 (uv), numpy GP, optional PyTorch, pytest (torch not required in default CI).

**Spec:** `docs/superpowers/specs/2026-09-08-surrogate-nn-fno-stub-design.md`

## Global Constraints

- Skip rule unchanged: `would_skip(μ, σ, floor)` with κ=1.
- Same `FEATURE_KEYS` / `feature_vector`.
- Defaults: `--surrogate-nn` off; requires `--surrogate-prescreen` floor > 0 (same gating as boost in argv helpers).
- If both `--surrogate-boost` and `--surrogate-nn`: **nn wins** (one clear log/reason string).
- FNO stub: `available() -> False`; train/predict raise `NotImplementedError` with field-snapshot message.
- Soft-dep torch via `[project.optional-dependencies] surrogate-nn = ["torch"]` (do not hard-require torch).
- Do not write `catalog.db` mid-study beyond existing append path.
- Skip staging `catalog/catalog.db`. Commit when user asks (plan steps may list commits).

## File map

| File | Role |
|------|------|
| `fansim/surrogate/nn.py` | `NnRegressor`, `available`, `unavailable_reason` |
| `fansim/surrogate/ensemble.py` | `NnGpEnsemble` |
| `fansim/surrogate/fno.py` | Stub |
| `fansim/surrogate/catalog.py` | `prescreen_fit(..., nn=False)`, `append_and_refit` for NnGp |
| `fansim/optimize/study.py` | `surrogate_nn` flag |
| `scripts/run_optimization.py` | `--surrogate-nn` |
| `fansim/optimize/cli_argv.py` | cockpit argv (if boost already wired) |
| `pyproject.toml` | `surrogate-nn` extra |
| `tests/test_surrogate_nn.py` | Unit tests |
| `docs/roadmap.md` / bibliography | §7.4 note |

---

### Task 1: `NnRegressor` + availability

**Files:**
- Create: `fansim/surrogate/nn.py`
- Modify: `pyproject.toml` (add `surrogate-nn = ["torch"]`)
- Test: `tests/test_surrogate_nn.py`

**Interfaces:**
```python
def available() -> bool: ...
def unavailable_reason() -> str: ...

class NnRegressor:
    def fit(self, X, y) -> NnRegressor: ...
    def predict(self, X) -> np.ndarray:  # shape (n,)
```

- Soft-import torch inside `available` / `fit`.
- Fixed architecture: input_dim = `len(FEATURE_KEYS)`, hidden `(64, 32)`, ReLU, 1 output; Adam ~200 epochs max or early stop on tiny data; `torch.manual_seed(0)`.
- If torch missing, `available()` False.

- [ ] **Step 1: Failing test**

```python
# tests/test_surrogate_nn.py
from __future__ import annotations
import numpy as np
import pytest

def test_nn_available_is_bool():
    from fansim.surrogate import nn as nnmod
    assert isinstance(nnmod.available(), bool)

@pytest.mark.skipif(
    __import__("importlib").util.find_spec("torch") is None,
    reason="torch not installed",
)
def test_nn_regressor_fit_predict_shape():
    from fansim.surrogate.nn import NnRegressor
    from fansim.surrogate.features import FEATURE_KEYS
    rng = np.random.default_rng(0)
    n, d = 30, len(FEATURE_KEYS)
    X = rng.normal(size=(n, d))
    y = X[:, 0] * 10 + 50
    mu = NnRegressor().fit(X, y).predict(X[:5])
    assert mu.shape == (5,)
    assert np.all(np.isfinite(mu))
```

- [ ] **Step 2: Implement `nn.py` + pyproject extra**

- [ ] **Step 3: Run tests**

Run: `uv run python -m pytest tests/test_surrogate_nn.py -q --tb=short`

---

### Task 2: `NnGpEnsemble` + catalog wiring

**Files:**
- Modify: `fansim/surrogate/ensemble.py`, `fansim/surrogate/catalog.py`
- Test: `tests/test_surrogate_nn.py`

**Interfaces:**
- `NnGpEnsemble` mirror `BoostGpEnsemble` (`fit`, `predict(..., return_std=True)`).
- `prescreen_fit(..., boost=False, nn=False)`:
  - if `nn` and nn available → `NnGpEnsemble`
  - elif `nn` and not available → GP + reason string
  - elif `boost` → existing boost path
  - else GP
  - if `nn and boost`: prefer nn (reason may note boost ignored).
- `append_and_refit`: if `isinstance(model, NnGpEnsemble)` refit `NnGpEnsemble`.

- [ ] **Step 1: Test ensemble + would_skip (torch-gated)**

```python
@pytest.mark.skipif(
    __import__("importlib").util.find_spec("torch") is None,
    reason="torch not installed",
)
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
```

- [ ] **Step 2: Implement ensemble + catalog**

- [ ] **Step 3: Test `prescreen_fit` with synthetic catalog optional** — or unit-level only if catalog fixtures heavy; at minimum test `append_and_refit` isinstance branch with monkeypatch.

---

### Task 3: FNO stub

**Files:**
- Create: `fansim/surrogate/fno.py`
- Modify: `fansim/surrogate/__init__.py` docstring
- Test: `tests/test_surrogate_nn.py`

```python
def available() -> bool:
    return False

def train_fno(*args, **kwargs):
    raise NotImplementedError(
        "FNO needs stored flow-field snapshots; use --surrogate-nn or --surrogate-boost "
        "tabular screens until field data exists (roadmap §7.4)."
    )

def predict_fno(*args, **kwargs):
    raise NotImplementedError(
        "FNO predict unavailable; no trained operator. See train_fno()."
    )
```

- [ ] **Step 1: Test raises + available False**

- [ ] **Step 2: Implement stub**

---

### Task 4: CLI / study / argv

**Files:**
- Modify: `scripts/run_optimization.py`, `fansim/optimize/study.py`, `fansim/optimize/cli_argv.py` (mirror boost), optionally cockpit switch
- Test: `tests/test_optimization_argv.py` + `tests/test_surrogate_nn.py`

- [ ] **Step 1: `--surrogate-nn` only appears when gp floor > 0 (same as boost)**

```python
def test_gp_nn_only_with_gp_floor():
    assert "--surrogate-nn" not in _argv(gp_floor=0, gp_nn=True)
    assert "--surrogate-nn" in _argv(gp_floor=40, gp_nn=True)
```

Extend `_argv` helper with `gp_nn=False`.

- [ ] **Step 2: `study.py` passes `nn=surrogate_nn` into `prescreen_fit`; log when nn wins over boost**

- [ ] **Step 3: Run argv + nn tests**

---

### Task 5: Docs

**Files:**
- `docs/roadmap.md` §7.4
- `docs/bibliography.md` §6
- Spec status → implemented
- `fansim/surrogate/__init__.py` note

- [ ] Update Remaining: real FNO when fields exist; NN+GP stage 1 done.

---

## Spec coverage

| Spec | Task |
|------|------|
| NnRegressor + soft torch | Task 1 |
| NnGpEnsemble + prescreen/append | Task 2 |
| FNO stub | Task 3 |
| `--surrogate-nn` | Task 4 |
| Roadmap / honesty | Task 5 |

## Self-review

- No invented field training.
- Torch optional; CI without torch still greens via skips + `available()` tests.
- Boost path preserved; nn wins if both flags set.
