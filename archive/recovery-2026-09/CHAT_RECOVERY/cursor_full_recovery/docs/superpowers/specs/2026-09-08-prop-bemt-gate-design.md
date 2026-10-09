# Prop BEMT-gate + CFD refine (stage 1)

**Date:** 2026-09-08  
**Status:** implemented  
**Approach:** Thin wrappers on existing BEMT + `evaluate_prop_cfd`: (1) optional **BEMT thrust floor** skips Docker CFD when hopeless; (2) optional **`--cfd-top N`** on the prop Optuna CLI CFD-refines the top N Pareto rows that pass the floor. Do not put CFD inside the Optuna loop.  
**Roadmap:** §4.3 remaining (BEMT-gate / Optuna refine).

## Plain language

Prop search is already instant BEMT. Compressible open-air CFD is minutes per design. Stage 1 adds the same honesty pattern as fan `--bem-prescreen`: refuse expensive CFD when BEMT says the blade is dead, and optionally CFD-check only the best Pareto finalists after a study.

## Goal

1. **`bemt_thrust_g(params, spec, *, rpm=None) -> float`** — thin helper around `analyze` (default `rpm=spec.rpm_max`).
2. **Floor on CFD** — `evaluate_prop_cfd(..., bemt_floor_g=0.0)`:
   - Build BladeParams from `prop_blade_params(spec)` when evaluating a stock spec, **or** accept optional `params: BladeParams | None`.
   - If `bemt_floor_g > 0` and BEMT thrust_g < floor → return dict with `skipped=True`, `reason=...`, `bemt_thrust_g`, stamps; **no** Docker.
   - Else run CFD as today; stamp `bemt_thrust_g` alongside CFD metrics when easy.
3. **CLI floor** — `scripts/evaluate_prop_cfd.py --bemt-floor G` (default 0 = off).
4. **Study refine** — `scripts/run_prop_optimization.py --cfd-top N` (default 0 = off) and `--bemt-floor G`:
   - After BEMT NSGA, take first N Pareto rows (existing thrust-sorted order).
   - Rebuild `BladeParams` from row `params` (same as `--export` path).
   - For each: if floor fails, record skip; else `evaluate_prop_cfd` into `--cfd-out` dir (default `runs/prop_cfd_refine/<spec>/`).
   - Write summary JSON listing BEMT vs CFD thrust_g / power for each row.
5. **Tests** — floor skip without Docker (monkeypatch or floor above BEMT); CLI flag strings; Pareto rebuild helper if extracted. No Docker in CI.

## Non-goals

- CFD inside Optuna objective  
- Cockpit / archetype NSGA for props  
- Forward-flight polar  
- Claiming CFD matches Gemfan datasheet  
- Changing fan `--bem-prescreen`

## Honesty

BEMT and compressible MRF disagree; the gate is a **cost filter**, not a calibrated surrogate. Stamp both numbers when CFD runs. Default floors/refine counts stay **off** (0).

## Defaults

| Knob | Default |
|------|---------|
| `bemt_floor_g` | 0 (off) |
| `--cfd-top` | 0 (off) |
| CFD RPM | same as `evaluate_prop_cfd` (0.7×rpm_max unless `--rpm`) |

Suggested manual smoke floor for `fpv_5inch`: on the order of hundreds of grams BEMT (tune after one dry compare); not mandated in code.

## Done when

- Unit tests green for floor skip + CLI flags  
- Manual optional: one `--cfd-top 1` refine when Docker is up  
- Roadmap §4.3 notes BEMT-gate stage 1 done; full Optuna-with-CFD and polar remain later  
