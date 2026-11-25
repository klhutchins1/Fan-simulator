# Pre-registration: physics snapshot tolerances (RV-1, 2026-11-24)

Written by Claude for Kimball, **before** the snapshot's first write (AGENTS.md rule 1). Plan:
`docs/review/2026-11-24-review-plan.md` (RV-1).

## What this is, and is not

The snapshot is a **regression pin**: it records what the code computes today and fails when that changes. It
judges no model against published data. RV-2 (the validation scoreboard) does that. This file is pre-registered
because its tolerance decides what counts as "the maths changed".

## Cases (fixed now; adding or removing one needs a dated amendment below)

All are cheap and need no geometry build, no CFD and no Docker. Inputs come only from `fansim/` and `config/`,
never `tests/`.

| id | what | outputs |
|---|---|---|
| `fan_bem.stock_v3` | `pq_curve(blade_from_flat(stock_blade_flat("a12x25")), rpm, tip_gap_mm=0.5)` at Stock's own rpm | every P–Q point (flow, static and total Δp, η, power); free CFM; shut-off; peak η and its CFM; status flags |
| `fan_bem.stock_v3_axial_force` | same, `pressure_model="axial_force"` | same |
| `fan_bem.stock_v3_stator` | same, `stator=True` | same |
| `fan_bem.stock_v3_rpm1500` | same at 1500 rpm | same |
| `fan_bem.lt120` | `pq_curve(lt120_params(), its rpm, tip_gap_mm=0.5)` | same |
| `fan_bem.default_params` | `pq_curve(BladeParams(), 2000, tip_gap_mm=0.5)` | same |
| `fan_bem.screen_cfm` | `system_curve.bem_screen_cfm(Stock v3, rpm, 10 Pa, 0.5 mm)` | free and op CFM |
| `mixed_bem.default` | `mixed_bem_screen_cfm(MixedFlowParams(), 3000, 10 Pa, 0.5 mm)` | free and op CFM |
| `prop_bemt.apc_sf_9x4.7` / `apc_e_9x6` | `analyze(approximate_prop_blade(...), rpm, v)` at static and J = 0.2, 0.4, 0.6 | T, Q, P, FM, FM raw, η, converged |
| `prop_bemt.polar` | `nondim` / `advance_ratio` on those points | J, C_T, C_P, η |
| `structural.stock_v3` | centrifugal root stress, tip deflection at 10 Pa, root bending stress, first bending Hz (PETG and PLA) | the report numbers |
| `structural.balance` | `static_unbalance`, `couple_unbalance`, `required_counterweight` on a fixed uneven 7-blade set | the numbers |
| `acoustics.*` | `dipole_pressure` and A-weighting at fixed inputs; `blade_pass_frequency`; tonal peak ratio for equal and fixed uneven spacing; `loading_noise_proxy`; `estimate_prop_noise` on the APC SF point | the numbers |
| `air` | every constant in `fansim/physics/air.py` | the values |

If an entry point named here does not exist or needs a geometry build, it is dropped. The first-write commit
lists what was dropped and why. No case may be added in that commit beyond this table.

## Tolerance (the pass/fail rule)

For every number in the snapshot:

- **Closed-form** cases (`structural.*`, `acoustics.*`, `air`, `prop_bemt.polar`): `|now − snap| ≤ 1e-9 · max(1, |snap|)`.
- **Iterative** cases (`fan_bem.*`, `mixed_bem.*`, `prop_bemt.apc_*`), which run fixed-iteration solvers and
  root-finding: `|now − snap| ≤ 1e-6 · scale`. For a series (the P–Q points), `scale` is the largest `|value|`
  of that quantity in the series, so a near-zero Δp at free delivery is not judged by relative error. For a
  scalar, `scale = max(1, |snap|)`.
- Booleans and strings (converged, free status) match exactly. The set of cases and keys matches exactly.

Any value outside its tolerance fails the test. There is no "close enough" or INCONCLUSIVE.

**Why these numbers.** Closed-form maths reproduces to the last bits on one platform, and 1e-9 leaves room for
cross-platform libm differences. The BEM and BEMT loops use fixed caps, but their stopping tests and polar
interpolation can move in the 7th–8th digit between numpy builds. 1e-6 is about 1000× tighter than the smallest
change anyone would call physics (the Stock P–Q code-lock in `tests/test_fan_bem.py` uses about 1e-3).

## Changing the snapshot

- Regenerate with `scripts/physics_snapshot.py --write --reason docs/validation/audits/<file>.md`.
- The snapshot stores `reason`, and the test checks that this file exists in the repo. A change without its audit
  file fails.
- If the tolerance is missed only on another platform (Windows CI vs Linux), record it here as an amendment.
  Do not widen the tolerance without a new pre-registration.

## First write

The first write takes `reason` = this file. It is a baseline, so it passes by construction. The test is judged on
every commit after it.

## Amendments

(none)
