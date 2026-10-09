# Linux fast suite, one process: master @ e48a32d (2026-10-09, round 3, §23.9)

**Command** (repo root; the cockpit was stopped first; nothing else heavy was run by this worker during the suite):
```
RSS_NODEID_FILE=/tmp/pytest_current_nodeid RSS_PERTEST_LOG=$PWD/handoff/2026-10-09_from-qa-2/memory/pertest_rss.tsv \
PYTHONPATH=$PWD/handoff/2026-10-09_from-qa-2/memory \
  .venv/bin/python -m pytest -q -m "not docker and not slow" -p no:cacheprovider -p rss_nodeid_plugin &
python3 handoff/2026-10-09_from-qa-2/memory/rss_sampler.py <pytest pid> rss_samples.tsv /tmp/pytest_current_nodeid
python3 handoff/2026-10-09_from-qa-2/memory/per_file_peaks.py rss_samples.tsv 10
```
- `rss_nodeid_plugin.py`: a tiny pytest plugin, no conftest change. It writes the running nodeid to a file and logs per-test RSS/HWM to `pertest_rss.tsv`.
- `rss_sampler.py`: samples /proc every 2 s, tagging each sample with the running nodeid → `rss_samples.tsv`. The END line gives the peaks.
- `per_file_peaks.py`: per-file peak RSS, the RSS just before the file started, and the nodeid at the peak.

## Result
- **1573 passed, 18 skipped, 23 deselected, 1 xfailed, 0 failed.** Wall time 20 min 44 s. No OOM kill (dmesg count unchanged).
- **Peak RSS 8192 MB** in `tests/test_mount_gauge.py::test_gauge_accepts_carved_stock_export`. The process runs single-process, with no child processes.

| file | peak MB | RSS before file | test at peak |
|---|---|---|---|
| tests/test_mount_gauge.py | 8192 | 752 | test_gauge_accepts_carved_stock_export |
| tests/audit/test_cror_mixed_setup_audit.py | 6454 | 589 | test_cror_blade_outside_zones_is_refused |
| tests/test_cror.py | 6402 | 728 | test_default_cror_fits_delta_not_a12x25 |
| tests/test_notched_tips.py | 4220 | 771 | test_notched_default_is_one_solid_in_120mm |
| tests/test_isolated_build.py | 3532 | 3072 | test_isolated_build_succeeds |

**Comparison:**
- Round 2 (961f953): 1555 passed, 21 min 40 s, peak 8.2 GB at ~60–65 % of the run.
- Round 1 runs were OOM-killed at 5.4–6.3 GB.
- Windows: 1565 passed, 2.47 GB.

**One file dominates: `test_mount_gauge.py`, and in it a single test.** It isn't accumulation: RSS was 0.75 GB when the file started, and the `malloc_trim` fixture brings it back down between files. Run alone, the same test peaks at **7.7 GB** (`single_test_default.log`).

**Why it's heavy (cheap check):**
- `py-spy` at 4.4 GB (`single_test_pyspy_at_4.4GB.txt`) is inside `export_print_ready → build_impeller_with_mount → fuse_impeller → hub.fuse(*9 blades)`. That is one OCCT Boolean (`BOPAlgo`, run in parallel on the `OSD_ThreadPool`, 22 process threads on 8 cores) fusing the motor-cup hub and 9 Stock blades in-process.
- RSS jumps from about 2.4 GB to 8.2 GB within about 12 s at that step.
- `MALLOC_ARENA_MAX=2` only lowers it to 6.4 GB (`single_test_arena2.log`), so it is mostly real OCCT working memory, not glibc arena fragmentation.
- Likely ways to make it cheaper (not tried):
  - run this test's export in the isolated worker the cockpit already uses;
  - mark it `slow`;
  - make the fuse non-parallel or fuse the blades incrementally;
  - cap the OCCT thread pool.
- I can't tell from here why Windows is 3× lower. It could be the OCCT build, the allocator, or the thread count on that machine.
- The CROR files (6.4 GB) are the same kind of thing: big Booleans run in-process.
