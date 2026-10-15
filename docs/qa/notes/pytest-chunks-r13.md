# Chunked fast suite RSS on Linux (round 13 Task C, item 23.9)

Master `143d5a8`, run clone `/workspace/fansim/qa/run_r13`, prereg `02584e6` (branch prereg/round13).
Command (brief §C, plus `-p no:cacheprovider`): `scripts/pytest_chunks.py --chunks 3 --all -- -m "not docker and not slow" -q --tb=line`.
Sampler: process-tree RSS every 2 s, tagged by the `pytest chunk i/3` line (`data/c_rss.jsonl`, 1331 samples; only two gaps over 10 s, 11 s and 12 s).
Raw: `handoff/2026-10-14_from-qa-13/data/c_suite.log`, `c_rss.jsonl`, `c_meta.txt`; scripts `c_run.sh`, `c_sampler.py`.

| chunk | files | result | pytest time | peak tree RSS | peak single process |
|---|---|---|---|---|---|
| 1/3 | 76 | 630 passed, 14 skipped, 9 deselected | 16:02 | 5.08 GB | 5.06 GB |
| 2/3 | 76 | 581 passed, 1 skipped, 5 deselected | 8:03 | 2.92 GB | 2.90 GB |
| 3/3 | 75 | 566 passed, 4 skipped, 9 deselected, 1 xfailed | 21:02 | 6.89 GB | 6.18 GB |
| total | 227 | 1777 passed, 19 skipped, 23 deselected, 1 xfailed, 0 failed | 45:07 | 6.89 GB | 6.18 GB |

(GB = KiB/1024².) Suite wall time is 45 min 7 s of active time (box monotonic clock: 2713 s from start to the last sample). The
calendar span was 18:16 MDT Oct 14 to 07:42 MDT Oct 15 because the box was paused overnight, so that span is not a performance number.

## Verdict

- **M0 PASS.** 0 failed; exit code 0.
- **M1 PASS.** `/proc/vmstat oom_kill` was 3 at start and 3 at end. The newest dmesg OOM kill (python, ~6.2 GB anon) is at
  monotonic 39014 s, 620 s *before* this run started (39634 s), so it is outside the run window and not attributed to it.
- **M2 reported.** Peak per chunk 5.1 / 2.9 / 6.9 GB versus the 8.2 GB single process before 23.9. Chunk 3 is the ~7 GB one
  the brief allows; each chunk's memory is released when its process exits (the tree drops back to under 1 GB between chunks).

No single-process comparison run was done (the brief makes it optional; not worth the RAM/tokens).
