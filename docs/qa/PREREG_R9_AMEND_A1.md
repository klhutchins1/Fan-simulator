# Amendment A1 to PREREG_R9 (a0260c0), Task A, operational; written before any C (cup) build data

The C-build memory gate of 6.0 GB (round 7) can never be met on this box: idle MemAvailable is
3.3-4.8 GB of 16 GB (host-side usage), so all 30 W4 builds would be SKIPPED_MEM. New gate: wait up to
900 s (monotonic) for MemAvailable >= 3.5 GB, else SKIPPED_MEM. Justification: the largest C-build peak in
round 7 was 3.0 GB (14 builds, median 2.45 GB). Nothing else changes. The one design started under the
old gate (CTL_0002; P builds only, C still waiting) was discarded and is re-run from scratch.
