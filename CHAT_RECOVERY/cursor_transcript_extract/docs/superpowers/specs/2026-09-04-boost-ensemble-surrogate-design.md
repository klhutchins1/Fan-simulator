<!-- EXTRACTED-FROM-CURSOR-TRANSCRIPT 2026-09-12 -->
# Catalog boosting ensemble surrogate (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Opt-in **ensemble** for `--surrogate-prescreen`: sklearn `HistGradientBoostingRegressor` supplies the CFM **mean**; the existing numpy **GP** still supplies **σ**. Skip rule stays `μ + σ < floor` (`would_skip`, κ=1). Same feature vector and online append/refit. Not a CFD replacement, not CNN/FNO, not writing `catalog.db` mid-study. This is the §7.4 “XGBoost” track without adding a separate `xgboost` package (HistGBR is already behind the `surrogate` optional extra).  
**Roadmap:** §7.4 remainder (XGBoost/boosting). Online GP update is already in.

## Plain language

The catalog screen guesses free/load CFM before CFD so hopeless designs can be skipped. The GP is cautious (it knows when it is unsure) but its mean can be weak as the catalog grows. A boosting model usually guesses CFM better on tabular geometry, but it does not know “how sure.” Stage 1 uses **both**: boost for the guess, GP for confidence. Default study behavior stays GP-only until you pass `--surrogate-boost`.

## Problem

```text
GaussianProcess.predict → (μ, σ)     # screen today
would_skip(μ, σ, floor)              # skip only when confident and low
HistGradientBoosting                 # optional dep already listed; unused
```

Roadmap asked for XGBoost next. Replacing the GP entirely would drop σ and risk skipping good designs. Quantile/bagged boost uncertainty is extra complexity for stage 1.

## Goal

### 1. `fansim/surrogate/boost.py`

```text
class BoostRegressor
  fit(X, y) -> self
  predict(X) -> μ          # shape (n,)

available() -> bool        # True if sklearn HistGradientBoostingRegressor imports

append_and_refit_boost(model, X, y, x_new, y_new) -> (model, X, y)
```

- Soft-import sklearn. Fixed, conservative hyperparameters (small `max_depth`, modest `max_iter`) so tiny catalogs do not explode. No hyperparam search this cycle.
- If sklearn is missing, `available()` is False; callers fall back to GP-only and print one clear reason.

### 2. `fansim/surrogate/ensemble.py` (or thin helpers in `catalog.py`)

```text
class BoostGpEnsemble
  # holds: gp: GaussianProcess, boost: BoostRegressor, X, y
  fit(X, y) -> self
  predict(Xstar, return_std=False) -> μ | (μ_boost, σ_gp)
  # when return_std: μ from boost, σ from gp.predict(..., return_std=True)
```

- Same public shape as `GaussianProcess.predict` so `evaluate_candidate` keeps calling `screen.predict(x, return_std=True)` + `would_skip`.
- `append_and_refit_ensemble(...)` stacks the row and refits **both** models from the shared `X, y` (same trigger as today’s GP online update: feasible CFD with finite CFM).

### 3. Wiring

- `prescreen_fit(..., boost=False)` — when `boost=True` and `available()` and `len(y) >= MIN_TRAIN`, return a fitted `BoostGpEnsemble` instead of a bare GP; else GP as today (or None if under-trained).
- `run_study(..., surrogate_boost=False)` — pass through; online refit uses the ensemble helper when the screen object is an ensemble.
- `scripts/run_optimization.py`: `--surrogate-boost` store_true. Ignored when `--surrogate-prescreen` is 0. Help: one clause that μ comes from HistGBR and σ from the GP.
- Cockpit `cli_argv`: optional bool → `--surrogate-boost` when the Optimize card already exposes GP floor (only if a switch already exists or is trivial; otherwise CLI-only this cycle is OK — prefer CLI-only if cockpit has no GP floor UI yet).

### 4. Docs

- Spec accepted; roadmap §7.4 “Remaining: XGBoost…” → boosting ensemble stage 1 done; CNN/FNO still later.
- Bibliography ML line: point at `BoostGpEnsemble` / `--surrogate-boost`.
- Honesty: still relative screening; do not claim the booster is calibrated CFM.

## Honesty

- Ensemble σ is still the **GP**’s uncertainty about the residual field, not a calibrated boost interval. That is intentional for stage 1.
- Soft-dep: without `pip install 'fansim[surrogate]'` (or sklearn), `--surrogate-boost` must not crash the study — warn and use GP-only.
- Do not mix “boost on” vs “boost off” skip decisions when comparing studies.
- In-memory online update only (same as GP online update).

## Tests (no Docker / no real catalog.db)

- `BoostRegressor` fits synthetic `y = f(X)` and predicts finite values (skip or xfail cleanly if sklearn missing — prefer pytest.importorskip).
- Ensemble `predict(..., return_std=True)`: μ differs from pure GP mean on a nonlinear toy (or at least boost path is exercised); σ matches GP σ within tight tolerance on the same training set.
- `would_skip` still driven by ensemble (μ_boost + σ_gp).
- CLI help mentions `--surrogate-boost`; rejects nothing required; no `★`.
- Existing GP / online-refit tests stay green with boost off.

## Non-goals

- Adding the `xgboost` package (HistGBR is the stage-1 stand-in)
- CNN / FNO / flow-field surrogates
- Changing `FEATURE_KEYS`, κ, or `MIN_TRAIN`
- Writing `catalog.db` during a study
- Hyperparameter Optuna for the booster
- Replacing BEM prescreen
- Claiming absolute CFM or dropping the GP

## Success

With sklearn installed and `--surrogate-prescreen FLOOR --surrogate-boost`, a study screens with boost means and GP σ; without the flag, behavior matches today; without sklearn, boost flag degrades to GP-only with a printed reason.
