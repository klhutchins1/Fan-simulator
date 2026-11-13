# Volute convergence sweep (R2.5a), pre-registration

Claude, 2026-11-13, written before any of these runs. Parent rules: step 1 of
`2026-10-18-cror-centrifugal-validation-prereg.md`. Cursor, as lead, may amend this before the run.

## What is known (from data already in the repo)

The existing volute case is the default `VoluteParams` at 3000 rpm, free air, 1000 iterations, with SIMPLE relaxation
p 0.3 and U, k, ω 0.7 (`docs/validation/audits/direction_cfd_volute*.json`).

| mesh | cells | designed spin: oscillation | reversed spin: oscillation |
|---|---|---|---|
| coarse (base cell 6 mm) | 102 k | 3.4 % | 20.2 % |
| fine (base cell 4 mm) | 220 k | 17.8 % | 23.3 % |

The "17–23 %" in audit-07 is therefore mainly the fine mesh and the reversed rotor. Nobody has measured a loaded
point's oscillation. The comparison in R2.5c uses the designed rotor only.

## Runs (`scripts/volute_convergence_sweep.py`, night CPU)

The sweep covers 2 meshes × 3 variants × 2 points = 12 solves, each 3000 iterations at the designed spin. There is
one mesh per base cell, and the geometry and domain are unchanged.

| variant | p | U | k, ω |
|---|---|---|---|
| V0 | 0.3 | 0.7 | 0.7 |
| V1 | 0.2 | 0.5 | 0.5 |
| V2 | 0.15 | 0.3 | 0.3 |

V0 is today's settings, so it tests whether the case only needed more iterations.

The two points are free air (0 Pa back pressure) and 50 Pa (the production load point).

## Rule (fixed now)

**Per solve (step 1):**
- PASS needs peak-to-peak flow over the last 20 % of iterations ≤ 5 % of its mean (`oscillation_pct`), **and** a
  mass imbalance ≤ 1 % (sanity `mass_balance`).
- Anything else, including a failed solve, is INCONCLUSIVE.
- A pressure-driven case fixes ΔP at the boundary, so the quantity that swings is the flow. The step-1 "ΔP
  oscillation" is read as this flow oscillation at a fixed ΔP.

**Choice, per mesh:** the fix is the least-damped variant (V0, then V1, then V2) that passes **both** points on that
mesh. The fine-mesh choice is the one R2.5c uses. The coarse result is recorded but is not used for validation.

**If nothing passes on the fine mesh:**
- Relaxation alone does not fix it, so the next lever is transient averaging (pimpleFoam, frozen rotor).
- That gets its own pre-registration.
- No variant here is re-tuned, and no V3 is added after the data.

**Never** is any of this judged against the EPJ paper. Agreement is step 2, after R2.5b's geometry freeze.

## After the run

- Record the 12 rows and the choice under "Results" below.
- Set R2.5a on the board to `done` with the chosen variant, or to `needs a transient prereg`.
- The chosen relaxation becomes the volute default only through its own change with a test. This sweep only picks
  it.

## Results

(empty until the run)
