# Catalog GP surrogate (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Fit the existing numpy RBF GP on catalog `cfm_free`; optional `--surrogate-prescreen` skips CFD when the GP is confident the design is below a floor  
**Roadmap:** §7.4 stage 1. Not XGBoost, not online update, not `cfm_load`, not FNO/flow-field.

## Plain language

We already have a Gaussian process (`fansim/surrogate/gp.py`) and ~110 CFD
rows in the catalog. Neither talks to the other. `--bem-prescreen` is the
only cheap CFD skip, and it ranks CFD at ~0.62.

This cycle trains that GP on **free-delivery CFM** from catalog rows that
have a geometry vector, then offers the same kind of conservative floor
as BEM. Uncertain predictions do **not** skip CFD. `cfm_load` stays out:
wall-scored and curve-scored load numbers are not the same quantity, even
with provenance columns.

## Problem

`evaluate_candidate` spends ~5 min in Docker once it passes print / stress
/ gap / optional BEM. The catalog is an index of already-paid CFD. The GP
is unit-tested on synthetic data and never fitted on a real row. The
unused `scikit-learn` extra and `FidelityLadder` do not close that gap.

## Goal

1. **Fit once** at optimizer start from `catalog/catalog.db` (overrideable
   path). One GP, target `cfm_free`.
2. **`--surrogate-prescreen CFM_FLOOR`**, default **0 = off**, same shape
   as `--bem-prescreen`. Conservative: skip CFD only when
   `mean + 1·std < floor`. Far-from-data (large std) still goes to CFD.
3. **Never break the eval.** Missing DB, too few rows, missing keys, or
   a fit/predict exception → warning + behave as off.
4. **Cockpit Assess** does not pass a floor (user asked to score this
   design). Optimizer-only, like BEM.

## Non-goals (this spec)

- Training or screening on `cfm_load` / efficiency / noise
- Third CFD, system-curve BEM, circular AMCA
- XGBoost, sklearn, CNN, FNO, neural fields
- Updating the GP after each trial inside a study
- Using `FidelityLadder` as the optimizer loop
- Re-scoring or rewriting historical catalog rows
- Re-optimizing tip-round or bio-features

## Feature vector

Fixed 16 keys, same names as `blade_from_flat` / `suggest_params`. Missing
optional fields use these defaults so older catalog dicts still train:

```text
n_blades, hub_radius, tip_radius,
stagger_root, stagger_mid, stagger_tip,
chord_root,   chord_mid,   chord_tip,
sweep_mid,    sweep_tip,
lean_mid,     lean_tip,    max_camber,
shroud_thick_mm, shroud_height_frac
```

Defaults: `hub_radius` / `tip_radius` from `BladeParams()`; `sweep_*` /
`lean_*` / `max_camber` / `shroud_thick_mm` → 0; `shroud_height_frac` → 1.

`feature_vector(src)` accepts a catalog `params` dict **or** a
`BladeParams` (read stations 0/0.5/1). Required to **include** a row:
`n_blades` plus the three chords and three staggers. Rows missing those
are dropped, not imputed.

Leave winglet / spacing / features / tip-round out of the vector. They
are sparse and were tested null on flow.

## Training set

From `load_catalog(db)` keep a row when:

- `cfd_stale` is false
- `cfm_free` is a finite number
- `feature_vector` succeeds (required keys present)

Do not filter on `k` / `dp_op_pa` (those are load-line provenance).

`MIN_TRAIN = 20`. Below that, the screen is off.

Existing `design_matrix` + `GaussianProcess().fit(X, y)` stay as-is
(median length scale, optional LML grid). Persist nothing; in-memory for
the study process.

## Gate

After the BEM pre-screen, before `export_stl`:

```text
if floor > 0 and model is fitted:
    μ, σ = model.predict(x, return_std=True)
    if μ + σ < floor:
        infeasible("surrogate-prescreen: {μ:.0f}±{σ:.0f} CFM free < {floor:.0f} (skipped CFD)")
```

`σ` is the GP predictive std. Kappa is **1**. Stamp `raw` with
`surr_cfm_free`, `surr_std` when a prediction ran (including pass).

Both `--bem-prescreen` and `--surrogate-prescreen` may be set; either
rejection skips CFD.

## CLI

`--surrogate-prescreen` CFM_FLOOR, default 0. Help: catalog GP on
free-delivery CFM; skip CFD when mean+1σ is below the floor; 0 = off.
No `★`. No `--k`-style extra flags.

`--surrogate-db` path, default `catalog/catalog.db`. Only consulted when
the floor is > 0.

Fit in `run_study` (once), pass the fitted model + floor into
`evaluate_candidate`. Do not fit per trial.

If the floor is > 0 and the model does not fit, print one line to stdout
(`surrogate-prescreen: off (reason)`) and continue.

## Tests (no Docker, no real catalog.db)

`tests/test_surrogate_catalog.py` (plus a thin evaluate_candidate test
next to the existing BEM prescreen test):

- `feature_vector` on a flat dict and on `BladeParams` agree on the OPEN
  defaults
- Rows missing chords / missing `cfm_free` / `cfd_stale` are dropped
- `MIN_TRAIN - 1` rows → no fitted model
- Synthetic catalog (≥20 rows, `cfm_free = 2 * n_blades + chord_tip`):
  held-out correlation > 0.8
- Gate: μ+σ below floor → infeasible, no `impeller.stl`; μ+σ above floor
  proceeds past this gate
- Uncertain point (far from train X): large σ, does **not** reject at a
  floor the mean would fail
- `--surrogate-prescreen` / `--surrogate-db` help; no `★`

Use a tmp-path catalog built like `tests/test_catalog.py`, not
`catalog/catalog.db`.

## Files

| Path | Responsibility |
|---|---|
| `fansim/surrogate/features.py` | keys, defaults, `feature_vector` |
| `fansim/surrogate/catalog.py` | `fit_cfm_free(db) -> GaussianProcess \| None` |
| `fansim/surrogate/__init__.py` | export the new helpers |
| `fansim/optimize/objectives.py` | optional model + floor after BEM |
| `fansim/optimize/study.py` | fit once, pass through |
| `scripts/run_optimization.py` | flags + help |
| `tests/test_surrogate_catalog.py` | train + gate + CLI |
| `docs/roadmap.md` | §7.4 stage 1 after implementation |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
