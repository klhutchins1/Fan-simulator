# FSI tip deflection vs tip gap (stage 1)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Analytic cantilever tip deflection under hose `load_pa`; reject when δ ≥ leftover tip gap; optional extra CFM knockdown from gap-closure fraction when print penalty is on. Not FEA / OpenFOAM FSI.  
**Roadmap:** §7.6 stage 3 (FSI leftover after wall ks + thickness η).

## Plain language

Printed blades bend under pressure. If the tip moves toward the casing by as much as the leftover tip gap, the part can rub or leak badly. Stage 1 estimates tip deflection with the same cheap cantilever bar used for the flutter gate, compares it to the leftover gap, and (when print penalty is on) knocks reported CFM a little more as δ/gap grows. Default PETG A12-class blades stay clear; TPU / ultra-thin tips at high hose Pa can fail.

## Goal

1. `fansim/structural/deflection.py`: tip-station chord × thickness cantilever; uniform load `q = load_pa × chord`; `δ = q L⁴ / (8 E I)`.
2. Pre-CFD gate in `evaluate_candidate` after tip-gap leftover: infeasible when `δ ≥ remaining`.
3. Stamps: `tip_deflection_mm`, `deflection_gap_frac`, `deflection_load_pa`.
4. `apply_print_penalty(..., tip_deflection_mm=, tip_gap_mm=)`: `k_fsi = max(0.90, 1 − 0.5 × min(δ/gap, 1))` multiplies into CFM; stamp `print_k_fsi`.
5. Cockpit score caption shows tip δ when stamped.

## Non-goals

- Coupled OpenFOAM FSI / remesh
- Mixed-flow / CROR / prop paths this cycle
- Changing the fixed `PRINT_K_CFM = 0.95` base
- Fitting δ to one paper’s measured tip motion

## Tests (no Docker)

Default PETG clear; thin tip + high Pa or TPU can fail; CFM factor; caption clause.
