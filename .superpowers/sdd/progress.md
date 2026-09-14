# SDD Progress — proper-state program
Plan: docs/superpowers/plans/2026-09-14-proper-state-program.md
Branch: master @ c356c4e

## Complete
- Phase 0–1: suite / roadmap / provenance / math / honesty (through 6fb9d55)
- Phase 2: A12x25 reference geometry acceptance + stock recipe
- Phase 3: validation runner + first P–Q (free-air 40.9 CFM, −32% vs published)
- Follow-on: free-air mesh ladder + tip-gap A/B → ~44.7 CFM (−26%) at 0.5 mm; mesh asymptotic (see a12x25_pq_report.md)
- Follow-on: frame / wall_ks free-air A/B → ~−1 CFM only; remaining gap is recipe vs OEM
- Follow-on: recipe fidelity — BEM sensitivity + flow_candidate CFD 45.2 CFM (+0.6 vs Stock); Stock wiring unchanged
- Phase 4: dependency audit (60b0924) + perf baselines/BEM speedups (ef75964)
- Task 6.1: keep/cut board (b4e84cb)

## Side fixes
- 23de116 Optimize gp_nn argv/CLI
- 9ff9809 CatalogEntry hub_models (cockpit Results)

## Blocked
- Task 5.1 print/measure/calibrate — needs hardware (see .superpowers/sdd/task-5.1-blocked.md)

## Program status
Software-side proper-state phases done except hardware north star (Phase 5).
BEM stagger retunes do not close RANS free-air gap; next honest path is trusted STL or Phase 5.
Local master ahead of origin (not pushed).
