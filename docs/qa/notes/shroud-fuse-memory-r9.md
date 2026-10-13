# Shrouded fuse memory (27.1), QA round 9 Task E

Code: master 2ce35b6, from a `git archive` export at /tmp/r9master (no worktree, nothing committed). The run
asserts it imported that tree. Hook: round-8 `hook_c` (unchanged copy in `docs/qa/shroud_memory/hook_c/`).
Runner `docs/qa/shroud_memory/run_e.py`, analysis `analyse_e.py` → `e_analysis.json`. Raw data:
`handoff/2026-10-12_from-qa-9/data/e_results*.jsonl.gz` (gitignored).

**Sample.** 12 shrouded S7 stress designs across ring height and size: 3 ring-height bins (0.30–0.55, 0.55–0.80,
0.80–1.0) × 4 blade counts (5/7/9/11 blades, 9.7k–22k faces at the call). Each also has an **unshrouded twin**
(same design, `shroud_thick_mm = 0`), which is an addition to the brief. There are also 4 unshrouded controls.
- 27/28 builds were OK.
- Control S5_0223 died with exit −9 (SIGKILL, "native crash") after 215 s while Task A and B.3 were also
  running. It is most likely the kernel OOM killer, but that is not proven. Not re-run.

## Result

**The guard under-covers shrouded designs with 9 or more blades.**
- The growth after the call (VmHWM − RSS at call) was within the guard's ask (1.15 × estimate) on 15/15 unshrouded
  builds, but only on **7/12 shrouded** ones.
- The 5 misses are all 9- and 11-blade rings: S7_0128 2.33 vs 2.22 GB, S7_0097 2.23 vs 2.10, S7_0172 2.79 vs 2.56,
  S7_0197 2.76 vs 2.61, S7_0188 2.99 vs 2.61.
- Against the round-8 unshrouded fit (1.02 GB + 92.5 KiB/face), the twins sit at −0.09 to −0.27 GB. The shrouded
  builds sit at +0.22 to +1.05 GB.

**The ring's extra cost:**
- **Per ring-face rate: can't be used.** The ring adds only **4 faces** to the face count passed to
  `check_fuse_memory` (identical on all 12 pairs). The rate comes out at ~318 MiB per face, which is meaningless, and
  it has the same LOO error as a constant.
- **Constant:** +1.24 GB over the estimate; leave-one-out RMSE 0.30 GB, worst 0.55 GB.
- **Ring height:** no signal. r(ΔHWM, height) = −0.18. LOO RMSE 0.33 GB, worst 0.65 GB, worse than the constant.
- **What fits (post hoc):** the extra peak scales with the *blade* face count, i.e. with how many blade–ring
  junctions the fuse has to make.
  - ΔHWM (shrouded − twin) = 66 KiB × blade faces − 0.25 GB. r² 0.84; LOO RMSE 0.14 GB, worst 0.36 GB.
  - Through zero: 50 KiB/face.
  - In practice that is roughly the per-face rate × 1.7 when a ring is present.

| pair | blades | ring h | faces | HWM shrouded / twin (GB) | ΔHWM | growth vs guard ask |
|---|---|---|---|---|---|---|
| S7_0023 | 5 | 0.38 | 9 747 | 2.12 / 1.75 | 0.37 | 1.10 / 1.39 ok |
| S7_0007 | 5 | 0.75 | 10 052 | 2.17 / 1.74 | 0.43 | 1.14 / 1.42 ok |
| S7_0010 | 5 | 0.87 | 10 052 | 2.12 / 1.75 | 0.37 | 1.09 / 1.42 ok |
| S7_0102 | 7 | 0.52 | 13 902 | 2.75 / 2.04 | 0.71 | 1.72 / 1.80 ok |
| S7_0094 | 7 | 0.57 | 13 909 | 2.64 / 2.16 | 0.48 | 1.62 / 1.80 ok |
| S7_0059 | 7 | 0.86 | 14 070 | 2.74 / 2.07 | 0.67 | 1.71 / 1.82 ok |
| S7_0128 | 9 | 0.51 | 18 097 | 3.37 / 2.40 | 0.97 | **2.33 / 2.22** |
| S7_0097 | 9 | 0.65 | 16 900 | 3.25 / 2.37 | 0.88 | **2.23 / 2.10** |
| S7_0121 | 9 | 0.99 | 18 088 | 2.94 / 2.38 | 0.56 | 1.91 / 2.21 ok |
| S7_0172 | 11 | 0.31 | 21 600 | 3.81 / 2.72 | 1.09 | **2.79 / 2.56** |
| S7_0197 | 11 | 0.60 | 22 117 | 3.79 / 2.70 | 1.09 | **2.76 / 2.61** |
| S7_0188 | 11 | 0.82 | 22 106 | 4.02 / 2.71 | 1.30 | **2.99 / 2.61** |

**Proposal only (no source edit):** when `shroud_thick_mm > 0`, estimate with the face rate raised by ~66 KiB/face,
or count the blade–ring junctions. Don't count the ring's own faces, and don't use a function of ring height. A flat
+1.0 GB for any ring would also cover all 12, at the cost of over-asking for 5-blade rings by ~0.6 GB.
