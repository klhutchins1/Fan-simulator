# QA round 7 (from QA, 2026-10-11): master `5980677`, clean clone `/workspace/fansim/repo-r7`

## Status per task
- **Task A, settings changed during a run: done.**
  - Note: `docs/qa/notes/settings-during-run.md`.
  - Harness: `docs/qa/settings_during_run/harness.py`, with output in `harness_output.json`.
  - Prereg `43ce868` (QA-only clone `/workspace/fansim/qa/prereg_r6`, branch `prereg/round7`), sha256 `465f9fb3…1057ff`.
  - **New rows QA-22 to QA-26:**
    - QA-22 to QA-24 are MED: the score and lineage stamps are read from live state at save time, and selecting a design rewrites hose/refine.
    - QA-25 is LOW–MED: a Sweep picks up changes between steps.
    - QA-26 is LOW and display only.
  - Optimize, Export, the airflow pictures and the Fit actions pass. Geometry is always snapshotted correctly.
- **Task B, stress test on new master: TRUNCATED at 65/801 by user decision** (the box was being suspended for hours at a time; ETA had reached ~249 h). The prereg stop rule was not triggered.
  - PREREG amendments 5–12 were committed as `854fc85` (sha256 `170a889a…bcef2a0`) before any build. A copy is in `docs/qa/stress/PREREG.md`. Scored only against those rules.
  - Runner: `stress/` (K12 hook `stress/hook/sitecustomize.py`). Data: `stress/run_r7/{designs.jsonl.gz,summary.json}`, kept STL `stress/run_r7/S6_0019_P.stl`.
  - **Write-up: `docs/qa/stress/RESULTS_R7.md`** (tables: `docs/qa/stress/tables_r7.md`).
  - 0 errors, all 65 P builds OK. K1, K3, K4, K6–K11: 0 FAIL.
  - **K12 62/65 FAIL → QA-27 (MED):** real fuse RSS is median 29 % over `fuse_peak_estimate_gb` (IQR 25–36 %, max 80 %) vs the 15 % guard headroom.
  - **K2 1/65 (S6_0019):** one 9.75e-10 mm² sliver at the high-lean tip of a watertight, single-body mesh. Threshold artefact, not filed as a bug; suggest a relative degeneracy rule next prereg.
  - **K5 1/65 FAIL + 16 INCONCLUSIVE** (K5_old 8 FAIL): S3_0014, camber 0.024 / lean 42°, is the QA-19 misread just above the fix's 0.02 cut-off.
  - Box suspends: S2_0020 T16gb waited 44 082 s on a 600 s gate; S1_0020 P 9 377 s wall vs 35.8 s monotonic. The gates use `time.time()`; they should use `time.monotonic()` → QA-28 (LOW, runner only).
- **Task C (lt120), Task F (stacking cut), Task G (flow-report math) and Task D:** see below (second QA worker).

## QA-18/19/21 re-verification (tested commit `5980677`)
These were among the first designs of the Task B run, on the new code (`/workspace/fansim/qa/r7_stress/run/designs.jsonl`).

| finding | designs | round 6 | round 7 (`5980677`) |
|---|---|---|---|
| QA-21 tip trim | S5_0007 | K1 BUILD_FAIL (tip trim) | **fixed**: P OK; K1–K6 PASS |
| QA-18 cup through a short hub | S2_0000, S8_0002, S8_0008 | K7 FAIL (no cup floor) | **fixed**: hubs grown 12.7/12.6/10.9 → 15.0 mm; floor 12.985 mm above the (grown) hub face, 20 grips; K7 PASS ×3 |
| QA-19 direction false refusals | S3_0002, S4_0005, S4_0012, CTL_0001–0004 | K5 FAIL ×7 | **fixed** on 7/7 (CTL_0004 finished later and also passes): new-rule K5 PASS 7/7 (old rule still FAIL on all 7, as expected: CONCLUSIVE (−1,+1), chirality −1, design camber 0.0008–0.0164 < 0.02); mirrors refused by the new rule |
| QA-19 residual | S3_0014 (new in r7) | – | **new-rule K5 FAIL**: camber 0.0242, lean_tip 42°, CONCLUSIVE (−1,+1), mirror OK; same misread just above the 0.02 cut-off. QA-19 stays open for camber 0.02–0.04 × lean ≥ 30° |

## Tasks C, G, F and D (second QA worker)
Prereg: `PREREG_R7.md`, sha256 `c163f1d7eaa6b4763871b2542d1b18e3ca5d34f6562e7878db35686cf52d0e6e`. It was committed as `2073315` on branch `prereg/round7` in the QA-only clone `/workspace/fansim/research/repo_research`, before any data.
- **Task C, lt120 as BladeParams: done.**
  - Files: `docs/qa/benchmarks/lt120/{fansim_params.json,built_vs_table.json}` and `docs/qa/notes/lt120-conversion.md`.
  - C1 stagger PASS. C2 chord, C3 camber and C4 t/c FAIL. The cause is that the builder makes flat sections, while the paper's table is on cylinders. The estimator also under-reads camber.
- **Task G, flow-report math: done.**
  - File: `docs/qa/notes/flow-report-math-check.md`.
  - G1 PASS 16/16.
  - G2 FAIL: silent NaN in 3 edge cases (zero flow, zero weights, empty bands on a coarse mesh).
  - The ±15 % / 2.8 dB thresholds rest on one non-repeat pair. Proposal: 3–5 repeats per case and a 2σ threshold.
- **Task F, external-STL stacking cut: done; do not adopt.**
  - File: `docs/qa/notes/direction-stacking-cut.md`.
  - F1, F2, F3 and F6 FAIL (9630 is read wrong). F4 and F5 PASS.
  - A radial-plane variant (not pre-registered) had 0 wrong on 67 parts. Proposed for a pre-registered confirmation.
- **Task D, near-stall flag (optional): not done.** There was no time this round, and no prereg was written for it.
