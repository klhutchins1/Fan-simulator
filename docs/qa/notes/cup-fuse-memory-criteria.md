# Pre-registration: motor-cup fuse memory strategies (roadmap 23.55, request 5), 2026-10-09 r4

Written and hashed **before** any strategy is run. The hash is recorded in `handoff/2026-10-09_from-qa-3/README.md`.

**Case:** Stock A12x25, the same as `tests/test_mount_gauge.py::test_gauge_accepts_carved_stock_export`:
- `flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat`;
- `params = blade_from_flat(flat)`;
- `export_print_ready(params, stl, mount=spec.motor_mount)` (tolerance 0.02, angular 0.1, also_step=True).

Master f238f54, Linux, the box's 8 cores. One fresh process per strategy, run one at a time.

**Baseline B:** the code as on master. For B and every strategy, record:
- peak RSS of the build process tree, sampled every 0.25 s;
- wall time;
- per-stage RSS high-water mark, using `/proc/self/clear_refs` resets. Stages: parts, hub carve, fuse, clean, export_stl, export_step, watertight_report.

**Strategies** (each a monkeypatch in a QA script; no repo edits):
- S1: sequential fuse (`hub.fuse(b1)`, then `.fuse(b2)` …, then one `.clean()`).
- S2: pairwise/tree fuse of blades, then fuse with the hub, then `.clean()`.
- S3: OCCT Boolean run serially (`SetRunParallel(False)`).
- S4: OCCT thread pool capped at 2 (`OSD_ThreadPool.DefaultPool_s(2)` before the first Boolean).
- S5: the same build in the isolated worker (`fansim.isolated_job.run_worker_module`). Here I measure the parent (test) process and the worker separately.
- S6: S1 + S3.
- S7: B with `MALLOC_ARENA_MAX=2` (control; allocator only).

**A strategy PASSES only if all of these hold:**
1. Peak RSS of the process doing the build is ≤ **4.0 GB** (B was 7.6–8.2 GB). For S5, the worker's own peak counts, not the parent's. Moving memory to another process does not pass rule 1 by itself.
2. The solid volume (OCC `Volume()` of the final solid) is within **0.1 %** of B.
3. The exported STL is watertight per trimesh (`is_watertight`), has 1 body (`len(split(only_watertight=False)) == 1`), and its Euler number equals B's.
4. The symmetric Hausdorff distance between B's and S's STL is ≤ **0.05 mm**: 200 k surface samples each way, trimesh `nearest.on_surface`.
5. The mount gauge is still OK: `write_print_fit_sidecars(...)` gives watertight, frame_ok and mount_ok all True.
6. Wall time is ≤ **1.5 ×** B's wall time.

**Outcome rules:**
- If any strategy passes, write a patch proposal to `docs/qa/patches/cup-fuse-memory.diff` for the best one (lowest peak; a tie goes to the simpler change).
- If none passes, write a note `docs/qa/notes/cup-fuse-memory.md` with the numbers and no patch.
- S5 is reported separately as a "test-process isolation" option, judged on rules 2–6 plus the parent's peak.
- These thresholds will not be changed after seeing results.
