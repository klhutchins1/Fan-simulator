# Fuse guard: refit Linux open-fan remaining growth (QA-35), 2026-10-15

## Pre-registration (written before fitting)

**Data:**
- **Fit and judge:** QA round 12 Task B open builds (12 open twins + 4 controls, OK rows only):
  `handoff/2026-10-14_from-qa-12/data/b_results.jsonl` with `b_results.calls.jsonl`. Remaining = VmHWM at exit −
  VmRSS at the `check_fuse_memory` call, as in `docs/qa/notes/fuse-remaining-r12.md`; faces = `n_faces` at the call.
- **Second judge, not refit:** QA round 8 Task C unshrouded builds (`handoff/2026-10-12_from-qa-8/data/c_results*.jsonl.gz`),
  where readable.

**Rule:**
1. Least-squares fit of remaining (GB) = a + b · faces on the r12 open builds.
2. Accept (a, b) if **every** r12 open build has remaining ≤ 1.0 × the estimate (so the 1.15 guard margin stays
   spare), and every readable r8 unshrouded build also has remaining ≤ 1.15 × the estimate.
3. Otherwise raise a (keep b) until the worst r12 open ratio is 0.95, then re-check the r8 points.
4. The shroud term (66 KiB per blade face) is **not** changed: shrouded builds sit at ≤ 0.80.
5. Windows constants are not touched (they were fitted separately on 2026-10-13).
6. The fit is accepted only if the new intercept and slope are physically plausible: a ≥ 0 and b within
   50–150 KiB/face. Otherwise stop and report.

## Result

(filled in after the fit)
