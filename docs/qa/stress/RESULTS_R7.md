# Stress test round 7 (Task B): results — TRUNCATED at 65/801 by user decision

- Code: master `5980677` (clean clone `/workspace/fansim/repo-r7`). Scored only against `docs/qa/stress/PREREG.md` and prereg commits `43ce868` / `854fc85` (branch `prereg/round7`, `/workspace/fansim/qa/prereg_r6`).
- **Truncated by user decision:** stopped at 65 of 801 planned designs because the box was being suspended for hours at a time (ETA had grown to ~249 h). The prereg stop rule (K1 > 30 % of the first 200) was **not** triggered (K1 0/65). Rates below are from 65 designs and have wide uncertainty; per-stratum n is 4–9.
- Data: `handoff/2026-10-11_from-qa-7/stress/run_r7/{designs.jsonl.gz,summary.json}`; the one kept STL (K2 fail) `run_r7/S6_0019_P.stl`. Full tables from `make_tables.py`: `docs/qa/stress/tables_r7.md`.
- 0 job errors. All 65 P builds `OK`.

## Per-check counts (all 65 designs)

| check | PASS | FAIL | INCONCLUSIVE | N/A / skipped | r6 (120 designs) FAIL/tested |
|---|---|---|---|---|---|
| K1 build | 65 | 0 | – | – | 1/120 (QA-21) |
| K2 printable solid | 64 | **1** (S6_0019) | – | – | 0/119 |
| K3 below hub face | 65 | 0 | – | – | 0/119 |
| K4 tip radius | 65 | 0 | – | – | 0/119 |
| K5 direction (new rule) | 48 | **1** (S3_0014) | 16 | – | 7/119 (+24 INC, old rule) |
| K5_old (comparison) | 41 | 8 | 16 | – | – |
| K6 mirror | 49 | 0 | – | 16 N/A | 0/95 |
| K7 cup depth (C) | 14 | 0 | – | 2 N/A, 2 SKIPPED_MEM | 3/29 (QA-18) |
| K8 tier equivalence | 7 | 0 | – | – | 0/11 |
| K9 tier memory | 7 | 0 | – | – | 0/11 |
| K10 | 1 | 0 | – | – | 0/3 |
| K11 | 65 | 0 | – | – | 0/120 |
| K12 fuse memory model | 3 | **62** | – | 0 | (new in r7) |

K8: volume/vertex equal 7/7, sha256 identical 0/7 (QA-20 unchanged).

## Coverage by design group (P outcome, and fails)

| stratum | n | P OK | fails (K1–K11) | K5 INC | K12 FAIL |
|---|---|---|---|---|---|
| S1 | 7 | 7 | – | 2 | 7 |
| S2 | 8 | 8 | – | 3 | 8 |
| S3 | 8 | 8 | K5 S3_0014 | 2 | 8 |
| S4 | 9 | 9 | – | 2 | 9 |
| S5 | 7 | 7 | – | 1 | 4 (3 PASS: S5_0015/18/19) |
| S6 | 6 | 6 | K2 S6_0019 | 3 | 6 |
| S7 | 7 | 7 | – | 2 | 7 |
| S8 | 9 | 9 | – | 1 | 9 |
| CTL | 4 | 4 | – | 0 | 4 |
| **all** | 65 | 65 | 2 | 16 | 62 |

Planned per-stratum counts (r6 `counts.json`) were 60–180 per stratum; coverage is 4–12 % per stratum. Edge cases in S8 are partly covered (S8_0002/0008/0018–0024).

## K2 failure: S6_0019 — criterion artefact, not a printability bug

- 7 blades, lean_tip 58.4°, sweep_tip 10.6°, max_camber 0.0113, 77 032 faces. **Watertight, 1 body, volume 31 856 mm³ > 0**; K3/K4 PASS.
- It fails only the "0 faces with area < 1e-9 mm²" clause: exactly **1** sliver triangle, area **9.75e-10 mm²**, at r ≈ 53.7 mm (near the tip, tip R 56.5), vertices ~0.01 mm apart, nearly collinear.
- The same mesh has 6 545 faces under 1e-6 mm² (median face 0.107 mm²): high-lean tips tessellate into many slivers, and this one just crossed the fixed threshold. A slicer ignores it.
- Verdict: a K2 FAIL by the pre-registered rule (counted as such), but **not filed as a builder bug**. Recommendation for the next prereg: define "degenerate" relative to edge length (e.g. zero-area after merging at 1e-6 mm) or report sliver count as an observation.

## K5: one new-rule failure, S3_0014 (residual QA-19)

- All 7 round-6 false refusals (S3_0002, S4_0005, S4_0012, CTL_0001–0004) now pass the new rule (old rule still FAILs all 7, as expected). CTL_0004, pending at the interim note, finished and passes.
- **S3_0014** (9 blades, max_camber **0.0242**, lean_tip **42.0°**): proof CONCLUSIVE omega −1 / pump +1 / chirality −1 on 18 sections (27 flat skipped); the mirror reads +1 and K6 passes. The design camber is just above the 0.02 cut-off of the QA-19 fix, so the new rule refuses it. This is the same lean-as-camber misread as QA-19, one camber bin higher (cell 0.02–0.04 × lean ≥ 30°: 1 FAIL, 3 INC of 8).
- K5_old FAIL 8 vs K5 FAIL 1: the fix removed 7 of 8 by-construction refusals.
- 16 INCONCLUSIVE: 11 `no_cambered_sections`, 5 `sections_disagree`. They concentrate at low camber / high lean (see K5 map in `tables_r7.md`).

## K12: fuse memory estimate is too optimistic (new finding)

- Estimate `fuse_peak_estimate_gb(n) = 0.37 GB + 86 kB × n`; the guard allows 15 % headroom (FAIL if peak > 1.15 × estimate).
- 62/65 FAIL. Peak/estimate ratio: **median 1.29, IQR 1.25–1.36** (actual RSS 25–36 % over the estimate), 10th–90th percentile 1.17–1.51, min 1.04, max 1.80. Max excess 1.57 GB. Faces 9 938–44 121 on failing builds.
- The 3 passes are S5 (1.04, 1.10, 1.13).
- Impact: with the tier forced (as in the runner) the guard is bypassed; un-forced, it would admit builds that then need ~30 % more RAM than it planned for → OOM risk on 6–8 GB machines. Suggested fix: refit (intercept and slope) on these 65 points, or raise the headroom to ≥ 1.5×.

## Runner robustness (box suspends)

- Two builds have wall ≫ monotonic: S1_0020 P 9 377.6 s wall vs 35.8 s monotonic; S8_0020 C 9 982.1 s vs 31.5 s. Times above exclude them.
- Memory gates: S2_0020 T16gb waited **44 082 s** on a 600 s gate; CTL_0004 T16gb 5 386 s, S1_0020 C 3 766 s, S8_0023 C 2 419 s (all SKIPPED_MEM). Cause: `wait_mem()` and `build()` in `design_job.py` use `time.time()` for the gate limit, so a suspended box blows through the limit. They should use `time.monotonic()` (filed LOW, see QA_REVIEW).
- Total build time 6.09 h wall vs 0.73 h monotonic.

## Timing and memory (suspend-flagged excluded)

| kind | n | median s | max peak RSS MB |
|---|---|---|---|
| P | 65 | 22.1 | 8 594 |
| C | 14 | 21.1 | 3 017 |
| T16gb | 5 | 16.9 | 3 944 |
| T6gb | 7 | 71.6 | 2 582 |
| R | 1 | 26.7 | 3 742 |

## Comparison to round 6 (120 designs, master `31228d0`)
- QA-21 (K1 tip trim) and QA-18 (K7 cup through short hub) do not recur: K1 0/65, K7 0/14.
- K5 false refusals 7/119 → 1/65 under the new rule; INCONCLUSIVE 24/119 (20 %) → 16/65 (25 %), similar.
- K2 goes from 0/119 to 1/65 (threshold artefact above).
- K12 is new; no r6 baseline.
