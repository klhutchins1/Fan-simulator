# Fuse memory measured at the fuse call (QA round 8, Task C; QA-27)

- **Code:** master `f86df9a`. Prereg `PREREG_R8.md` (QA-only clone `/workspace/fansim/qa/prereg_r6`, branch
  `prereg/round8`, commit `6b0aedf`, sha256 `b958dda3…ec67e9`), committed before any data.
- **Builds:** 22 P builds (full blade count, `build_stl_isolated`, preview off, no mount),
  `FANSIM_MEMORY_TIER=8gb` (serial fuse), one worker process at a time. Faces span 9.9k–71k. 6 are featured
  (S5_*) and 3 are shrouded (S7_*). Designs come from the round-7 stress population
  (`handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz`).
- **Hook:** `handoff/2026-10-12_from-qa-8/scripts/hook_c/sitecustomize.py`. At `check_fuse_memory(n_faces)`
  it records the worker's own VmRSS/VmHWM, MemAvailable and `time.monotonic()`. Before exit it records the
  worker's VmHWM. The build worker leaves through `os._exit(0)`, which skips `atexit`, so the hook also wraps
  `os._exit`. Each design calls the check once. Runner: `scripts/run_c.py` (all limits monotonic);
  scoring: `scripts/analyse_c.py`.
- **Deviations:**
  1. A round-8 Task B run (2-blade builds, about 1–1.5 GB) ran at the same time. This changes MemAvailable
     only, not the per-process VmRSS/VmHWM.
  2. S7_0013 was SKIPPED by the memory gate at first. I re-ran it once memory was free. By mistake, two
     runners built it at the same time. Its record is filtered to one worker pid; per-process numbers are
     unaffected (both workers gave VmHWM 3.66/3.67 GB).

## Results
- **Fits (least squares, 22 builds):**
  - `VmHWM` = **1.02 GB + 92.5 KiB/face** (R² 0.96, max residual 0.87 GB).
  - increment `VmHWM − VmRSS_at_call` = **0.28 GB + 72.0 KiB/face** (R² 0.93, max residual 1.0 GB).
  - `VmRSS_at_call` = 0.74 GB + 20.5 KiB/face. The process already holds 1.0–2.1 GB when the guard runs.
- **Intercept:** one process on Linux has the same ~1.0 GB intercept as round 7's summed build tree
  (≈ 1.0 GB). So the gap to the Windows 0.37 GB is **not** caused by summing processes. It is a platform or
  metric difference (Linux RSS vs Windows working set) or a setup difference. Slope: 92.5 KiB/face
  here. The shipped constant is 8.6e-5 GiB/face (≈ 90 KiB, "86 kB" in the code comment), and round 7's
  tree fit was 85.
- **Peak vs estimate:** VmHWM/est = 1.14–1.75, median 1.27. Every build except S5_0015 (1.14) is above the
  1.15 margin.
- **Shrouded designs are outliers:** S7_0013 and S7_0017 read 1.75 and 1.72, about +1 GB above the
  face-count fit at 15–20k faces. The ring fuse costs more than its faces suggest.

### Pre-registered comparison: "safe iff increment ≤ 1.15 × est − RSS_at_call"
**FAIL: 21/22 builds violate it.** Only S5_0015 (71k faces) passes. Algebraically the rule is VmHWM ≤ 1.15·est,
so it repeats round-7 K12 on clean single-process data.

### What the guard actually checks
The guard refuses when `1.15·est > MemAvailable`. MemAvailable does not include the RSS the worker already
holds. So the guard is protective iff `increment ≤ 1.15·est`:
- this held on **20/22**;
- it fails on **S7_0013** (increment 2.66 GB vs 2.41 GB);
- **S7_0017** is marginal (1.90 vs 1.95).
In this run MemAvailable at the call was always ≥ the increment (it was never tight: 2.75–9.25 GB).
The largest increment/estimate ratio was 1.27 (S7_0013). GB here means GiB (kB from /proc ÷ 1048576).

| design | faces | RSS at call GB | VmHWM GB | increment GB | est GB | 1.15·est − RSS GB | rule | MemAvailable at call GB | 1.15·est GB | increment ≤ 1.15·est | HWM/est |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_0018 | 9938 | 1.00 | 1.65 | 0.65 | 1.22 | 0.41 | FAIL | 5.29 | 1.41 | yes | 1.35 |
| S7_0015 | 11089 | 1.00 | 2.24 | 1.24 | 1.32 | 0.52 | FAIL | 5.30 | 1.52 | yes | 1.70 |
| S2_0014 | 13884 | 1.00 | 2.19 | 1.19 | 1.56 | 0.80 | FAIL | 5.30 | 1.80 | yes | 1.40 |
| S7_0017 | 15391 | 1.00 | 2.91 | 1.90 | 1.69 | 0.94 | FAIL | 5.29 | 1.95 | yes | 1.72 |
| S8_0002 | 16075 | 1.01 | 2.21 | 1.21 | 1.75 | 1.01 | FAIL | 5.26 | 2.02 | yes | 1.26 |
| S2_0016 | 17832 | 1.00 | 2.39 | 1.39 | 1.90 | 1.19 | FAIL | 5.01 | 2.19 | yes | 1.26 |
| S6_0018 | 17853 | 1.30 | 2.64 | 1.34 | 1.91 | 0.89 | FAIL | 3.34 | 2.19 | yes | 1.38 |
| S1_0020 | 18084 | 1.00 | 2.55 | 1.55 | 1.93 | 1.21 | FAIL | 2.76 | 2.21 | yes | 1.33 |
| S3_0019 | 18084 | 1.00 | 2.51 | 1.51 | 1.93 | 1.21 | FAIL | 9.24 | 2.21 | yes | 1.30 |
| S7_0013 | 20097 | 1.01 | 3.66 | 2.66 | 2.10 | 1.41 | FAIL | 9.25 | 2.41 | **no** | 1.75 |
| S6_0015 | 20241 | 1.31 | 2.70 | 1.39 | 2.11 | 1.12 | FAIL | 2.75 | 2.43 | yes | 1.28 |
| CTL_0001 | 21783 | 0.99 | 2.69 | 1.70 | 2.24 | 1.59 | FAIL | 3.05 | 2.58 | yes | 1.20 |
| S6_0019 | 21794 | 1.32 | 2.99 | 1.67 | 2.24 | 1.26 | FAIL | 4.97 | 2.58 | yes | 1.33 |
| S1_0016 | 22102 | 1.01 | 2.69 | 1.68 | 2.27 | 1.61 | FAIL | 5.29 | 2.61 | yes | 1.18 |
| S5_0016 | 24804 | 1.34 | 3.18 | 1.84 | 2.50 | 1.54 | FAIL | 8.89 | 2.88 | yes | 1.27 |
| S5_0017 | 29522 | 1.48 | 3.65 | 2.17 | 2.91 | 1.86 | FAIL | 8.77 | 3.35 | yes | 1.25 |
| S6_0017 | 30828 | 1.33 | 3.71 | 2.38 | 3.02 | 2.14 | FAIL | 3.88 | 3.47 | yes | 1.23 |
| S6_0016 | 34253 | 1.31 | 3.89 | 2.58 | 3.32 | 2.50 | FAIL | 8.93 | 3.81 | yes | 1.17 |
| S5_0007 | 34433 | 1.32 | 3.94 | 2.61 | 3.33 | 2.51 | FAIL | 8.92 | 3.83 | yes | 1.18 |
| S5_0014 | 44121 | 1.63 | 4.86 | 3.23 | 4.16 | 3.16 | FAIL | 8.60 | 4.79 | yes | 1.17 |
| S5_0019 | 57387 | 1.95 | 6.10 | 4.15 | 5.31 | 4.15 | FAIL | 8.28 | 6.10 | yes | 1.15 |
| S5_0015 | 71261 | 2.08 | 7.42 | 5.33 | 6.50 | 5.39 | ok | 8.16 | 7.47 | yes | 1.14 |

## Recommendation for 27.1 (proposal only)
- Make the guard model the **remaining growth**, not the whole peak: `need = k × (a + b·faces) [+ shroud term]`,
  compared with MemAvailable, using a and b from the increment fit (0.28 GB, 72 KiB/face on Linux).
  - k must cover the residual. Measured increment / increment-fit is ≤ 1.03 on all 19 unshrouded builds,
    so `k = 1.15` covers them.
  - The 3 shrouded builds read 1.19, 1.42 and 1.60. They need about +1 GB, or a separate per-face rate for
    the ring's faces.
  - Alternatively, keep the whole-peak estimate but subtract the process's own VmRSS (which the brief
    suggests). On these data that is equivalent to `increment ≤ 1.15·est`, and 20/22 pass.
- Refit on Windows with the same hook, using the per-process peak working set at exit
  (`GetProcessMemoryInfo().PeakWorkingSetSize`). The Linux constants should not be shipped as-is.
