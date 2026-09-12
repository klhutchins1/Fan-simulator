# Catalog load-line GP (stage 2)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Same numpy GP, second target: `cfm_load` on rows that have system-curve `k` (not wall-scored). Prefer that model for `--surrogate-prescreen` when it fits. Wall-scored `cfm_load` without `k` is dropped. No XGBoost, no online update.  
**Roadmap:** §7.4 remaining. Free-delivery GP stays as fallback.

## Plain language

Stage 1 skipped CFD on predicted **free** CFM. The hose objective is **load** CFM, and mixing 1 Pa wall numbers with curve-scored `cfm_load` is why load stayed out. Stage 2 trains only on rows with `k` set, and uses that GP for the skip when it has ≥20 rows.

## Goal

1. **`training_xy(..., y_attr="cfm_free", require_k=False)`** — existing default. `y_attr="cfm_load"` + `require_k=True` keeps finite `cfm_load` and non-None `k`.

2. **`fit_cfm_load(db)` / `prescreen_model(..., y_attr=, require_k=)`** — same MIN_TRAIN, same never-break.

3. **`--surrogate-prescreen`** — study fits free and load. `evaluate_candidate` skips on the **load** GP when it is not None, else the free GP. Same `mean+1·std < floor`. Message says `load` vs `free`.

## Tests (no Docker)

- Load training drops `k is None` even if `cfm_load` is set.
- 20 curve-scored rows (`k` set) → `fit_cfm_load` not None; 19 → None.
- Existing `training_xy` / `fit_cfm_free` tests still pass (default args).
- `evaluate_candidate(..., surrogate_load=model, surrogate_prescreen_cfm=500)` infeasible with `load` in the reason (reuse the existing geometry-skip test shape).

## Non-goals

- Per-hose GPs (one load GP for all k)
- Updating during a study
- Cockpit Assess
- Changing FEATURE_KEYS
