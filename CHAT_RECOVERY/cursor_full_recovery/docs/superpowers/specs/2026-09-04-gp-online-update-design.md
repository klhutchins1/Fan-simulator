# Catalog GP online update (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** When `--surrogate-prescreen` is on, after each **feasible CFD** trial append `(feature_vector, cfm_*)` and **refit** the in-memory GP(s). Default on whenever the screen is on. Not XGBoost, not writing back to `catalog.db`, not changing the skip rule (still mean+1σ).  
**Roadmap:** §7.4 remainder (online update). XGBoost stays later.

## Plain language

The catalog GP is fitted once at study start. A long NSGA never teaches it what this run’s CFD already paid for. Stage 1 keeps the training matrices in `run_study` and, after every feasible trial with a finite free (and curve-scored load) CFM, appends the row and refits. Skipped / infeasible trials do not train. Do not rewrite the SQLite catalog mid-study.

## Goal

1. **`fansim/surrogate/catalog.py`**

```text
append_and_refit(model, X, y, x_new, y_new) -> (model, X, y)
```

- `x_new` shape `(n_features,)` or `(1, n)`; `y_new` scalar.
- Stack, `GaussianProcess().fit(...)`, return new model + matrices.
- If `model` is None or `X` is empty, still fit from the single new row when `len(y) >= 1` — but the **screen** still requires `MIN_TRAIN` before skips (unchanged `would_skip` path). Online rows only matter once the initial fit already passed `MIN_TRAIN`.

2. **`run_study`** — when free (and/or load) GP fitted:

```text
keep X_free, y_free (and X_load, y_load) from the initial training_xy
after evaluate_candidate, if result.feasible and finite cfm_free:
    append_and_refit free GP from feature_vector(params)
if load GP on and result.raw has k and finite cfm_load:
    append_and_refit load GP
pass updated model objects into the next trial (closure mutates outer refs)
```

3. **CLI** — no new flag this cycle. Online update is implied by `--surrogate-prescreen > 0`. Help text one clause: “refits after each feasible CFD trial.”

## Honesty

In-memory only. Does not improve historical catalog. Early trials still use the cold catalog fit. Do not claim the GP becomes a CFD replacement.

## Tests

- `append_and_refit` grows `X` by 1; predict on the new point is closer to `y_new` than before (or finite).
- Monkeypatch `run_study`: with floor > 0 and a tiny fake GP path — or unit-test the helper only + a study-level test that records how many times `GaussianProcess.fit` ran (≥2 after 2 feasible fakes). Prefer helper + one `run_study` monkeypatch counting refits.

## Non-goals

- XGBoost / sklearn
- Writing `catalog.db` during the study
- Online update when floor is 0
- Changing κ or the feature vector
