# Fuse remaining-growth on Windows (roadmap 27.1, 2026-10-13)

The guard used to ask for the *whole* process peak × 1.15 in free RAM. By the time
`check_fuse_memory` runs, the worker already holds the lofts (0.5–1.9 GB working set here).
QA r8 Task C on Linux measured the rest: increment = VmHWM − VmRSS at the call = 0.28 GB +
72 KiB/face. QA r9 Task E showed a ring costs extra in proportion to *blade* faces (~66 KiB),
not the ring's four faces.

This note is the Windows refit. Hook: `docs/qa/fuse_growth/hook_win/sitecustomize.py` (needs
`GetProcessMemoryInfo` `argtypes` so 64-bit pointers are not truncated). Runner:
`scripts/measure_fuse_growth.py`, `FANSIM_MEMORY_TIER=8gb`, one isolated worker at a time.
Remaining = PeakWorkingSet at `os._exit` − WorkingSet at the fuse-guard call.

| design | faces | blade faces | shroud | WS at call | peak at exit | remaining |
|---|---|---|---|---|---|---|
| open_9b | 18 597 | 18 597 | no | 0.49 GB | 2.21 GB | **1.72 GB** |
| ring_9b | 18 601 | 18 597 | 1.6 mm | 0.49 GB | 2.67 GB | **2.18 GB** |
| ring_11b | 22 733 | 22 729 | 1.6 mm | 0.50 GB | 3.17 GB | **2.67 GB** |
| stock_v3 | 44 202 | 44 202 | no | 0.61 GB | 5.04 GB | **4.43 GB** |

Two open points want a negative intercept. Intercept is pinned at 0.10 GB; the slope **103 KiB/face**
is taken from Stock v3 so both open points sit under the line. The ring extra (ring_9b − open_9b)
is **26 KiB per blade face** — lower than Linux 66, so Windows does not copy that term.

With the 1.15 margin, the ask covers all four remaining values. `fuse_peak_estimate_gb` is still
the whole-peak diagnostic (0.37 GB + 86 kB/face); the guard uses `fuse_remaining_estimate_gb`.
