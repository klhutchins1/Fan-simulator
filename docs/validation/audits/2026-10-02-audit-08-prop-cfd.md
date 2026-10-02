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

3. **Open-air boundary conditions.** Ambient-total-pressure entrainment boundaries (`bc="entrain"`:
   upstream face and sides `totalPressure` / `pressureInletOutletVelocity`, downstream face at
   ambient static pressure), with the same box and level-4 mesh, give C_T 0.0670 / C_P 0.0291,
   against 0.0667 / 0.0290 with freestream boundaries. The boundaries do not matter here.
   Evidence: `prop_cfd_apcsf_9x4.7_entrain.json`.
4. **Geometry orientation.** A 0.5R slice of the CFD copy has the LE upstream (z −4.0 vs +4.0 mm,
   consistent with a 25 mm chord at ~17°) and the convex side upstream. Camber and pitch agree
   with the rotation.

**Remaining suspects (untested):**

5. **Low-Re sections on wall functions (leading).** At 0.75R the chord Re is about 8×10⁴, the run has no
   prism layers, and k-ω SST is fully turbulent. This usually costs some lift, not 44 %.

Note that BEMT on the same geometry lands within the static tolerances (C_T 0.1039, −13 %), while
CFD reads 0.067. The two disagree by ~36 % on the same blade, so the shortfall is in the CFD
modelling at this Reynolds number, not in the inputs. 

**Spanwise loading (2026-10-02).** CFD wall-pressure thrust per radial band (the total reproduces
the forces monitor, −2.171 N) against BEMT dT/dr on the same blade:

| r/R | 0.15–0.26 | 0.26–0.36 | 0.36–0.47 | 0.47–0.57 | 0.57–0.68 | 0.68–0.79 | 0.79–0.89 | 0.89–1.00 |
|---|---|---|---|---|---|---|---|---|
| CFD / BEMT | 1.59 | 0.89 | 0.65 | **0.54** | 0.62 | 0.56 | 0.70 | 0.73 |

The deficit is spread across mid-span (30–45 % low), and the tip holds up comparatively well. That
rules out tip-vortex and MRF-interface effects and points to **section aerodynamics in the CFD**:
fully turbulent k-ω SST on wall functions, with no prism layers, at chord Re ≈ 6–8×10⁴. Real
low-Re airfoils run with laminar flow and transition, which the BEMT polars come from. **Next
test:** prism layers (resolved near-wall, y+ ~1–5), then, if the gap remains, a transition model
(k-ω SST-LM).

## Ledger

New unit `propeller.cfd_setup` (prop metrics, sanity, direction wiring) is recorded PASS on its
checks. Its claim is limited to direction and bookkeeping. **Absolute accuracy is explicitly not
claimed.**
