# QA_REVIEW merge snippet for round 27

Base: master 9869116 `docs/QA_REVIEW.md` sha256 874289e4b02f006303bb2d509bbaddd42ebf30aa4326453c22b6b24c94b80f28.
Two inserts only, nothing removed or rewritten (the full merged file is `docs/QA_REVIEW.md` in this zip):
1. Insert these rows directly after the `| QA-70 |` tracker row:

| QA-71 | MED | Fan/Assess | Assess "rejected — stalls at this hose" text still says "CFD under-predicts static ~2×" (`fansim/optimize/objectives.py:154`, docstring :137), against G4's "about 10 %" | new (r27, 2026-11-09; behavioural via `_operating_point_reason`). Patch `docs/qa/patches/r27-QA71-QA72-g4-leftovers.patch`. Open. |
| QA-72 | LOW | Docs/CLI | Stale G4 numbers outside G4's list: `extract_design_rules.py:139` still writes "~3–5% discretization" (regenerating `design-rules.md` undoes G4); `run_optimization.py --help` says "BEM≈0.6× CFD"; docstrings `fan_bem.py:16`, `extract_design_rules.py:6` | new (r27, 2026-11-09). Same patch as QA-71. Open. |

2. Append this section at the end of the file:

## Round 27 (grok, 2026-11-09): current-master re-check on 9869116

Build `master` @ `9869116` (bundle sha256 `0f8e06e0…1d92` verified; fresh clone, no edits). No Docker/CFD/OpenFOAM; no Assess, Sweep,
Optimize, Export or Randomize click. Prereg `ef58906` (branch `prereg/r27`). Note: `docs/qa/notes/r27-recheck.md`. Evidence:
`handoff/2026-11-09_from-qa-27/`. No source diffs since 41e2dc9 in `volute_tab.py`, `fan_assess.py`, `fan_optimize.py`, `fan_flow_report.py`,
`fan_widgets.py`; the three earlier patches still apply (not landed).

- **A QA-57: still open (partly fixed).** Volute Assess copy (`volute_tab.py:159`, :163) and readout (:417) still lack "ranking only,
  unvalidated (CFD not yet converged)"; rendered Volute Design/Results show it only on the 2 Optimize lines. Patch `g3-QA57-volute-assess-label.patch` still applies.
- **B UI-39 / UI-40: still open.** Code unchanged; probe identical to ui-hunt-1 (steps ""/"1e9" → silent ValueError, "100" → 100 runs;
  Trials −5/100/1e9 → silent clamp). Rendered labels "steps" / "Trials", no range, no error state. The ui-hunt-1 patch only labels; the new
  **`docs/qa/patches/r27-UI39-UI40-refuse-run-counts.patch` supersedes it** and refuses out-of-range/non-integer values with a visible message
  before anything starts (23 new tests; red 1 failed).
- **C QA-70: still open.** Probe: hint-only run → no `noise` row. Patch still applies. G2 not re-tested.
- **D G4: verified for its listed files** (figures ~10 %, Assess "two CFD solves … 20–40 min" rendered in Simple, BEM ranking-only, GCI ≈ 21 %,
  blade claim gone, a12x25 close-ref + open list, README Known limits with R1.4's "about 5 % less airflow"). `test_r110_g4_stale_numbers.py`
  8/8; red check with 41e2dc9 files 8 failed. **QA-58: verified for G4's list. QA-69: verified** ("Noise estimate (min)" in doc and generator).
- **UI-41 / UI-42: still open** (static; code unchanged).
- **New: QA-71 (MED)** Assess stall-reject text still says "~2×"; **QA-72 (LOW)** generator caveat "~3–5%", CLI help "BEM≈0.6×", two docstrings.
  Patch `r27-QA71-QA72-g4-leftovers.patch` (3 tests; red 3 failed).
- Targeted tests on master: 64 passed. All four open patches together on scratch: 113 passed.
- **ID changes:** QA-69 → verified; QA-58 → verified (G4 list); new QA-71 (MED), QA-72 (LOW). UI-39/40/41/42, QA-70, QA-57 unchanged (open).
