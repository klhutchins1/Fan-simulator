# Fuse peak RAM grows with face count, not with the tier strategy (roadmap 25.5, 2026-10-11)

QA round 6 saw featured (S5) builds peak at 7.6 GB on the 8gb tier, above that tier's 6.5 GB floor.
Re-measured here: Windows, one in-process `build_impeller` per run, peak working set from
`GetProcessMemoryInfo`, designs from the QA stress records (`handoff/2026-10-09_from-qa-5/stress/`).

| design | features | faces after fuse | tier | peak RAM | time |
|---|---|---|---|---|---|
| S1_0000 | none | 18 084 | 8gb (serial) | 2.0 GB | 23 s |
| S5_0011 | tubercles + serrations + dimples | 71 229 | 16gb (parallel) | 6.5 GB | 135 s |
| S5_0011 | same | 71 229 | 8gb (serial) | 6.6 GB | 134 s |
| S5_0011 | same | 71 229 | 6gb (one blade at a time) | 6.0 GB | 565 s |

**Stage split, S5_0011 at 8gb:** building the hub and 9 blades peaks at 2.3 GB (8 078 faces per blade).
The fuse takes it to 6.5 GB.

**Reading:**
- Surface features make each blade about 4× more faceted.
- The fuse's peak tracks the face count: about 0.37 GB + 86 kB per face (2.0 and 6.5 GB fitted within
  0.1 GB).
- The tier strategies barely change it for featured designs: one-blade-at-a-time saves 0.5 GB at 4×
  the time.

**Change:** before the fuse, `fansim.resources.check_fuse_memory` estimates the peak from the parts'
face count (×1.15 headroom). It raises `MemoryError` with a plain message when free RAM is short.
It doesn't block when free RAM can't be read or the tier is forced. The tier table's GB figures are
for Stock-like designs; the docstring now says so.

## Ledger

`geometry.stock_handedness` re-recorded on 2026-10-11 after the full suite (1704 passed, 0 failed), which includes its registered checks and its dependants'.

## Correction (same day): the guard only acts on cockpit builds

The full suite was run inside a release export while a second suite was running, and only 3.6–4.1 GB
of RAM was free. The guard then refused Stock (40 449 faces, estimate ×1.15 = 4.4 GB), so two
geometry tests failed.
- That is the guard working. But the same path runs inside the optimizer, Assess scoring and
  scripts, where a refusal would be **recorded as an infeasible design**. On a busy machine that
  would quietly corrupt results.
- **Now:** `check_fuse_memory` acts only when `FANSIM_FUSE_GUARD=1`. The cockpit's cup Preview
  (`build_stl_isolated(fuse_guard=True)`) and Export (`_export_worker`) set it, because a person reads
  the message there. Batch builds always go ahead, as before 25.5.
- Build errors now keep 400 characters of stderr, so the plain message isn't cut off.
