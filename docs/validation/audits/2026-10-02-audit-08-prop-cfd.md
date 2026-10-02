# Audit #8: prop CFD (open-air compressible MRF) (2026-10-01 … 10-02)

Question: does the prop CFD path (`evaluate_prop_cfd`, rhoSimpleFoam, single MRF zone in an
open-air box) turn the prop the right way, account its forces honestly, and match a measured prop?

## Plain-language verdict

**Direction and bookkeeping are proven. Absolute thrust and power are not: CFD reads ~40 % low
against UIUC measurements of the APC Slow Flyer 9×4.7.** Do not use prop CFD numbers as
performance claims until the gap is closed. BEMT, which is partly validated (Audit #3), stays the
prop screening tool.

## What was checked and fixed

1. **Sign handling.** `normalize_metrics_sign` already reports a wrong thrust sign and never flips
   spin (fixed after Audit #1). Confirmed. The forces function object integrates the local density
   (`rho rho`), which is correct for the compressible solver.
2. **Final-sample metrics → tail mean.** `parse_prop_metrics` read the last iteration. It now
   reports the converged-tail mean, plus thrust and torque convergence by the fan's rule (tail-half
   means within 2 %) and the oscillation.
3. **No prop sanity checks → `run_prop_sanity`.** It checks:
   - thrust direction;
   - that the rotor does work (M_z·ω < 0);
   - the momentum-theory bound FM = T^1.5/(√(2ρA)·P) ≤ 1, WARN below 0.2;
   - tip Mach;
   - convergence.
   These are wired into `evaluate_prop_cfd`. The momentum check also flags the 2026-09-22 drone
   radial records (FM ≈ 0.03 and 0.11), which ran with a manual direction because their geometry
   proof is INCONCLUSIVE. Treat those records as suspect.
4. **Long runs.** `evaluate_prop_cfd(postprocess_only=True)` plus `audit_prop_cfd.py --resume` read
   a finished case whose Python wrapper died while the solver kept running.

## CFD both ways + validation (`scripts/audit_prop_cfd.py`)

The prop is built from the UIUC measured geometry (r/R, c/R, β) with a generic 6 % section and
camber 0.04, the same approximation the BEMT audit uses. It is solved at the UIUC static point,
6026 rpm (tip Mach 0.21), on a 2.0 M cell mesh (base 8 mm, surface level 4 = 0.5 mm at the blade),
for 1000 iterations. Rules were fixed before the run.

| solve | thrust | power | converged | sanity |
|---|---|---|---|---|
| designed (builder direction, flipped, spin −1) | **+220.5 g** (2.16 N) | 21.6 W | yes (shift 0.02 %, osc 0.1 %) | all PASS, FM ≈ 0.48 |
| reversed (same STL, spin +1) | **−122.5 g** (pushes air backwards) | 21.7 W | yes | thrust_direction FAIL (expected) |

- **Direction: PASS.** The designed direction gives 0.100 N/W against 0.055 N/W reversed (1.8×).
- **Validation: FAIL.** C_T is 0.0667 against 0.1192 measured (**−44 %**, tolerance ±15 %). C_P is
  0.0290 against 0.0484 (**−40 %**, tolerance ±20 %).

Evidence: `docs/validation/audits/prop_cfd_apcsf_9x4.7.json`.

## Why the validation misses

**Ruled out:**

1. **Mesh.** At surface level 5 (2.46 M cells, `prop_cfd_apcsf_9x4.7_L5.json`) the result is 221.8 g
   / 21.1 W, against 220.5 g / 21.6 W at level 4 (thrust +0.6 %, power −2.4 %). The loading is
   mesh-converged.
2. **3-D geometry.** The built STL's sections match the UIUC table: chord within 0.3 mm and β within
   0.4° at r/R 0.3–0.9. Measured camber is 0.032 and thickness about 6 %.

**Remaining suspects (untested):**

3. **Open-air domain and boundary conditions (leading).** The upstream face is a fixed, uniform
   1 m/s axial inflow (`freestreamVelocity`) only 2R ahead of the prop. A static prop draws its
   inflow from rest in every direction, so forcing uniform inflow close upstream distorts the
   induced field and can let the slipstream recirculate in the box. That would lower thrust and
   power together, as observed. (The side boundaries fall back to zero-gradient, so they are not
   the main constraint.) **Test:** a larger box with ambient-total-pressure entrainment
   boundaries.
4. **Low-Re sections on wall functions.** At 0.75R the chord Re is about 8×10⁴, the run has no
   prism layers, and k-ω SST is fully turbulent. This usually costs some lift, not 44 %.

Note that BEMT on the same geometry and section assumptions lands within the static tolerances.
So the CFD setup, not the geometry, is the outlier.

## Ledger

New unit `propeller.cfd_setup` (prop metrics, sanity, direction wiring) is recorded PASS on its
checks. Its claim is limited to direction and bookkeeping. **Absolute accuracy is explicitly not
claimed.**
