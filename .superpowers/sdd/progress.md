# SDD Progress — proper-state program
Plan: docs/superpowers/plans/2026-09-14-proper-state-program.md
Branch: master @ 0ded165

## Complete
- Phase 0–1: suite / roadmap / provenance / math / honesty (through 6fb9d55)
- Phase 2: A12x25 reference geometry acceptance + stock recipe
- Phase 3: validation runner + first P–Q (free-air 40.9 CFM, −32% vs published)
- Follow-on: free-air mesh ladder + tip-gap A/B → ~44.7 CFM (−26%) at 0.5 mm; mesh asymptotic
- Follow-on: frame / wall_ks free-air A/B → ~−1 CFM only
- Follow-on: recipe fidelity — flow_candidate CFD 45.2 CFM (+0.6 vs Stock); Stock unchanged
- Follow-on: Stock P–Q @ tip 0.5 mm → free-air 44.6 CFM; shut-off proxy ~24 Pa (interim pass)
- Phase 4: dependency audit (60b0924) + perf baselines/BEM speedups (ef75964)
- Task 6.1: keep/cut board (b4e84cb)

## Side fixes
- 23de116 Optimize gp_nn argv/CLI
- 9ff9809 CatalogEntry hub_models (cockpit Results)

## Blocked
- Task 5.1 print/measure/calibrate — needs hardware (see .superpowers/sdd/task-5.1-blocked.md)
- Trusted OEM STL under validation/reference/ — needs licensed asset

## Program status
Software-side Phase 3 free-air gate still open (−26%). Shut-off interim proxy in band at tip 0.5 mm.
Baseline suite fails cleared (DES templates, eta_total, stub test); math consistency tests added (§10).
Next honest path: trusted STL or Phase 5 hardware.
Local master pushed to origin.
