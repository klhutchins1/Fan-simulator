# Task 1–3 Report — Surrogate NN+GP ensemble + FNO stub

## Scope
- Implemented Tasks 1–3 from the NN+GP + FNO stub plan:
  - **Task 1**: `NnRegressor` + availability gating + `pyproject.toml` optional extra.
  - **Task 2**: `NnGpEnsemble` + `catalog.prescreen_fit(..., nn=False)` and `append_and_refit` wiring.
  - **Task 3**: `fansim/surrogate/fno.py` honest stub + docstring note.

## Changes
- **New** `fansim/surrogate/nn.py`
  - `available()` / `unavailable_reason()` soft-import torch (no import at module import time).
  - `NnRegressor`: fixed small MLP \((64, 32)\), ReLU, deterministic `torch.manual_seed(0)`,
    conservative CPU training with early stopping.
- **Updated** `pyproject.toml`
  - Added optional dependency extra: `surrogate-nn = ["torch"]`.
- **Updated** `fansim/surrogate/ensemble.py`
  - Added `NnGpEnsemble`: mean from `NnRegressor`, sigma from `GaussianProcess`, matches
    `BoostGpEnsemble` API (`predict(..., return_std=True)`).
- **Updated** `fansim/surrogate/catalog.py`
  - `prescreen_fit(..., nn: bool = False)`:
    - If `nn` and torch is available → `NnGpEnsemble`.
    - If `nn` but torch missing → fall back to GP with reason string.
    - If `nn` and `boost` both True → **nn wins**, reason notes boost ignored.
  - `append_and_refit` now refits `NnGpEnsemble` when passed one.
- **New** `fansim/surrogate/fno.py`
  - `available() -> False`
  - `train_fno` / `predict_fno` raise `NotImplementedError` with “needs flow-field snapshots” guidance.
- **Updated** `fansim/surrogate/__init__.py`
  - Docstring mentions NN track and points to the FNO stub.
- **New tests** `tests/test_surrogate_nn.py`
  - Torch-gated tests for `NnRegressor`, `NnGpEnsemble`, and `prescreen_fit(nn=True)` behavior.
  - FNO stub test validates `available()` and `NotImplementedError` behavior.

## Tests run
- `uv run python -m pytest tests/test_surrogate_nn.py -q --tb=short`
- `uv run python -m pytest tests/test_boost_ensemble.py -q --tb=short`

## Notes / concerns
- NN training is intentionally minimal (small MLP + early stopping) to keep it predictable and fast
  for screening; it is not intended as a high-accuracy surrogate.
- No CLI flag wiring was done here (Task 4 in the plan); `nn=True` is currently reachable via code
  paths calling `prescreen_fit` directly.
