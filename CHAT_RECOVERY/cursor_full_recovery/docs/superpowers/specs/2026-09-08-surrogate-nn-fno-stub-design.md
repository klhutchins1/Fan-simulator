# Catalog neural μ + GP σ ensemble + FNO stub (stage 1)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Opt-in **NN+GP ensemble** for `--surrogate-prescreen`: a tiny PyTorch MLP supplies CFM **mean**; the existing numpy **GP** still supplies **σ**. Skip rule stays `μ + σ < floor` (`would_skip`). Same feature vector and online append/refit pattern as `--surrogate-boost`. Ship a documented **FNO stub** (`fansim/surrogate/fno.py`) that does not train — no field snapshots yet. Not a CFD replacement, not writing `catalog.db` mid-study.  
**Roadmap:** §7.4 Remaining: CNN/FNO.

## Plain language

Boosting already improves the catalog CFM guess while the GP knows when it is unsure. A small neural net is the next mean-model experiment on the **same tabular geometry vector**. A Fourier Neural Operator needs flow-field tensors we do not store; stage 1 only reserves the module and refuses to pretend.

## Goal

1. **`fansim/surrogate/nn.py`**
   - `NnRegressor` with `fit(X, y)`, `predict(X) -> μ`, `available() -> bool` (torch import).
   - Small fixed MLP (e.g. 2–3 hidden layers, width ~32–64); fixed seed; no hyperparam search.
   - Soft-dep: optional extra `fansim[surrogate-nn]` = `torch` (keep `fansim[surrogate]` = sklearn for boost).

2. **`NnGpEnsemble`** in `ensemble.py` (parallel to `BoostGpEnsemble`)
   - `predict(..., return_std=True) -> (μ_nn, σ_gp)`.
   - Wire into `prescreen_fit` / study argv when `--surrogate-nn` is set (with `--surrogate-prescreen`).
   - If both `--surrogate-boost` and `--surrogate-nn`: **nn wins** (document); or reject both — prefer **nn wins** with one log line.

3. **Online update** — same `append_and_refit` hook path as boost when nn ensemble is active.

4. **`fansim/surrogate/fno.py` stub**
   - `available() -> False`
   - `train_fno(...)` / `predict_fno(...)` raise `NotImplementedError` with message: needs permeable/field snapshots; use NN/boost tabular surrogates until then.
   - Unit test asserts the raise; no torch FNO dependency.

5. **CLI / cockpit (minimal)** — `--surrogate-nn` on optimization argv (mirror boost gating: only with prescreen floor). Cockpit switch optional if trivial; else CLI-only stage 1.

6. **Tests** — nn predict shape; ensemble `would_skip`; missing torch falls back / clear reason; FNO stub raises; argv declares `--surrogate-nn`.

## Non-goals

- Training on invented CFD fields  
- GPU training pipeline / checkpoints as product  
- Replacing GP σ with NN dropout uncertainty  
- Deleting HistGBR boost path  
- Claiming CNN/FNO field fidelity

## Honesty

Tabular MLP ≠ FNO. Stamp / docs say `surrogate=nn+gp` when active. FNO remains **future** until we persist field data.

## Done when

- Unit tests green without requiring torch in default CI (skip or soft-fail when torch absent; at least one test path covers `available() is False`).
- With torch installed, nn ensemble fits tiny synthetic X,y and predicts.
- Roadmap §7.4 notes NN+GP stage 1 + FNO stub; real FNO still remaining.
