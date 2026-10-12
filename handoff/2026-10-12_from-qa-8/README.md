# QA round 8 (from QA, 2026-10-12): master `f86df9a`, clean clone `/workspace/fansim/repo-r8`

**Prereg (B, C, D in one commit, before any data):** `6b0aedf` on branch `prereg/round8` in the QA-only clone
`/workspace/fansim/qa/prereg_r6`. File `qa_r8/PREREG_R8.md`, sha256 `b958dda3a884a3ec7aac0899131e0b9f3efdabf6a951c3745dbcd5940fec67e9`.
Copy in `docs/qa/PREREG_R8.md`. Nothing was committed to repo-r8, the stress test was not resumed, and no fansim
source was edited (QA-side monkeypatches only, in QA processes).

## Status per task
- **A, settings changed during a run: PASS.**
  - A2–A5 and A7 are now class d. Assess-existing stamps `material`. P1/E1 are unchanged, as expected (27.5).
  - QA-22..25 verified fixed; QA-26 partly fixed (material stamp only).
  - **New QA-29 (LOW, display):** after Assess, the "Done ◆#n …" message is overwritten by a stale
    "Running Assess… m:ss" caption. It is a ticker vs viz-bake race and pre-existing.
  - Note: `docs/qa/notes/settings-during-run-r8.md`. Output: `docs/qa/settings_during_run/harness_output_r8.json`.
- **C, fuse memory at the call: rule FAIL (21/22).**
  - In one process on Linux, VmHWM = 1.02 GB + 92.5 KiB/face. So the 1.0 GB intercept is not a tree-sum
    artefact.
  - The increment after the call = 0.28 GB + 72 KiB/face.
  - The guard's real test (1.15·est vs MemAvailable) covered the remaining growth on 20/22. It fails on
    shrouded S7_0013 (2.66 vs 2.41 GB); shrouded designs run ~1 GB over the face fit.
  - Note: `docs/qa/notes/fuse-memory-at-call.md`.
- **B, radial-plane direction confirmation:** R1 PASS (0 wrong / 144 reads), R2 PASS (54/54), R3 PASS, R4 PASS,
  **R5 FAIL** (0 wrong but reads 43/54 = 79.6 %), **R6 FAIL** (flipped 0/5 refused: the rule as written
  can't catch a negative-camber design; 5 fully flat mirrors are unreadable). 0/23 S3-cell parts refused.
  - **Deviation:** the brief's `max_camber = −0.03` builds a *flat* blade (`airfoil.py:61,102`), so the
    flipped parts were rebuilt as true negative-camber sections by a QA-side wrapper (v2).
  - Proposal: a radial-led external rule (post hoc: 0 wrong, 53/54 read) and the builder rule against the
    intended spin.
  - Note: `docs/qa/notes/direction-radial-confirmation.md`.
- **D, built blade vs its numbers: MATERIAL.**
  - The realisation measures all station radii, but on an unclipped lone blade. On lt120 the hub-face clip
    removes 3–16 % of chord → **QA-30 (MED)**. That is why loft/measured made no difference.
  - Camber is 0.006–0.049 low (net of bias) on every leaned/skewed design, worst with the measured-chord
    stretch → **QA-31 (MED)**.
  - The gap tracks lean/skew, **not** chord/r: Stock with lean/skew/sweep zeroed matches.
  - Recommend (iii) now, then (i) vs (ii) by CFD A/B.
  - Note: `docs/qa/notes/built-vs-numbers.md`.
- **E (optional), near-stall flag: not done** (not cheap enough this round; no prereg written).

## Files
- `scripts/`:
  - A: see `docs/qa/settings_during_run/` (`harness.py` unchanged, `harness_bake_race.py`, `compare_outputs.py`).
  - B: `sample_b.py`, `run_b.py`, `run_b_flip_v2.py`, `analyse_b.py`, `stacking_cut.py` (round 7, unchanged).
  - C: `run_c.py`, `hook_c/sitecustomize.py`, `analyse_c.py`.
  - D: `run_d.py`, plus post-hoc diagnostics `d_diag.py` (realisation's own reads), `d_diag2.py` (blade vs
    impeller z-range), `d_diag3.py` (lt120 without clip) and `d_diag4.py` (Stock lean/skew/sweep zeroed).
- `data/` (gzipped; the `*.jsonl.gz` files are gitignored by `handoff/**/*.jsonl.gz`):
  - B: `b_sample`, `b_results` (v1), `b_flip_v2`, `b_results_v2merged` (scored), `b_analysis`, `b_analysis_v2`.
  - C: `c_results`, `c_results.calls`, `c_skipped_first_attempt`, `c_analysis`.
  - D: `d_results`.

## Run notes
- **B and C overlapped in time.** That affects C's MemAvailable only, not the per-process RSS/HWM.
- **S7_0013 (C):** skipped by the memory gate at first and re-run later. Two runners built it at once by
  operator error; the record is filtered to one pid.
- **Timing:** all limits use `time.monotonic()`. B: ~25 s/part. C: 13–71 s/build. D: ~6 min total. No
  suspends hit.
