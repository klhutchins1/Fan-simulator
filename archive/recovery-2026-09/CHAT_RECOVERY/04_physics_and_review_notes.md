# Physics & review notes (from “Fan simulator code review” + audit)

Use these as **contracts** when regenerating code — they were validated as intentional in review chats.

## CFD

- OpenFOAM **2406**, **simpleFoam**, **k-ω SST**, **MRF**
- Kinematic pressure × ρ; `rhoInf=1` on kinematic pTot
- Screening mesh: do **not** expect Langtry–Menter (needs y+≈1)
- Residual oscillation common; project judges convergence via **integrated flow drift**, not residualControl alone
- Continuity errors ~1e-3 local / cumulative ~0.05 typically OK mid-solve

## Objectives

- NSGA objectives: **cfm_free, cfm_load, efficiency** (+ optional noise)
- Static efficiency is the correct NSGA objective for PC fans (review affirmed)

## Fan BEM

- Shaft power should be **Euler work** (review flagged double-counting profile-drag / Cd if present)
- Prandtl tip-loss: open-rotor form is wrong for **ducted** fan with circular casing — prefer gap-leakage style (Storer & Cumpsty cited)
- `--bem-prescreen CFM_FLOOR` skips CFD when BEM system-curve op CFM below floor (conservative; ranks CFD ~0.62 historically)

## Propeller BEMT

- Review mentioned a′ / polar Re issues and missing GCI stamp on some mixed/CROR evaluates
- One note: 0.70 E knockdown should be test-pinned

## Acoustics

- Farassat 1A far-field loading: `p' = (r̂ · Ḟ) / (4π c r)`
- Review flagged an **extra 1/c** bug in `fansim/acoustics/fwh.py` at one point — verify if fixed before trusting
- IEC A-weighting present; absolute dB(A) calibration was still roadmap §1.4 style work
- Loading vs Proudman noise proxies available on `--noise`

## Structural / print gates

- PETG bend frequency vs blade-pass tone: need bend ≥ **1.2× BPF**
- Mountable: hub radius ≥ motor cavity/2 + wall
- Weight / envelope `check_build` against fan-model spec (A12x25)

## Honesty / docs debt

- `docs/adversarial-review.md` was **stale** (claimed noise missing, GPU idle, A12x25 unvalidated) while README contradicted — stamp historical or rewrite
- Layered GCI once failed (p≈0.28, GCI_fine≈21%) while §1.5 marked closed — do not over-claim screening CFM precision
- Stock A12x25 STL had ~+2% free-air validation mention; optimizer designs not hardware-validated

## Spec features implemented (vs parked)

Remembered as **in code**: rounded plate section, cylindrical tip trim, LE/TE scales, shroud/winglet/stator flags, features layer, surrogate prescreen hooks.

Parked / incomplete: full HAWT, absolute noise calibration, some UI polish, Problem/archetype registration for propeller.
