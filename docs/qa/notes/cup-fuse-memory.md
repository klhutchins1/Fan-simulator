# Cup-fuse memory strategies (QA r4 request 5): no strategy passes, so no patch

- **Pre-registration:** `docs/qa/notes/cup-fuse-memory-criteria.md`, sha256 `f8fcc8bbbacb72aa4abe5f48497952986289f92397f33b142031d5a3a3d5fee9`, hashed 15:32:58 MDT before any run. Copy: `/workspace/fansim/qa/prereg_r4/`.
- **Case:** Stock A12x25 → `fit_envelope` → `export_print_ready(mount=spec.motor_mount)` → `write_print_fit_sidecars`. This is `test_gauge_accepts_carved_stock_export`.
- **Setup:** master f238f54, Linux, 16 GB box. One run at a time, each a fresh process. The tree RSS was sampled every 0.25 s. Per-stage peak = VmHWM after `/proc/self/clear_refs`=5.
- **Scripts:** `handoff/2026-10-09_from-qa-3/cupfuse/` (`cupfuse_job.py`, `cupfuse_driver.py`, `run_all.sh`, `compare.py`). Results are in `stages_*.json`, `driver_*.json` and `verdicts.json`.

## Where the memory goes (baseline B)

| stage | s | peak after stage MB |
|---|---|---|
| imports + `build_impeller_parts` (hub, 9 lofted blades) | 11.8 | 1917 |
| carve cup into bare hub (fast path) | 0.2 | 1918 |
| **`fuse_impeller` = `hub.fuse(*9 blades).clean()`** | 33.5 | **7657** |
| export_stl (tol 0.02) | 2.9 | 7626 |
| export_step | 15.2 | 7629 |
| watertight_report + gauge | 0.5 | 7632 |

- The whole +5.7 GB is the single 10-argument OCCT Boolean (General Fuse with `SetRunParallel(True)`).
- RSS **stays** at ~7.6 GB after the fuse: the per-stage HWM *after a reset* is still 7.6 GB through export. So the memory is either still referenced (BOP history / intermediate data kept by the result) or freed but not returned to the OS. `MALLOC_ARENA_MAX=2` (S7) recovers only 1.3 GB of it.
- Tessellation, STEP and the gauge are negligible.

## Strategies (rule: peak ≤ 4000 MB, volume ±0.1 %, watertight/1 body/same Euler, Hausdorff ≤ 0.05 mm, gauge OK, wall ≤ 1.5×B = 110 s)

| id | strategy | peak MB | wall s | geometry vs B | verdict |
|---|---|---|---|---|---|
| B | baseline | 7657 | 73.4 | — (volume, Euler 0, 1 body, watertight) | — |
| S1 | sequential fuse (hub+b1, +b2, …) | 5219 | 169.5 | identical (Hausdorff 0.0000, Δvol 0) | FAIL (peak, time) |
| S2 | pairwise/tree fuse of blades, then hub | 8050 | 103.8 | identical | FAIL (peak) |
| S3 | `SetRunParallel(False)` (all booleans) | **4891** | 84.5 | identical | FAIL (peak, 891 MB over) |
| S4 | `OSD_ThreadPool.DefaultPool_s(2)` | 6522 | 75.5 | identical | FAIL (peak) |
| S5 | isolated worker (parent never imports OCP; the worker peak counts) | 7698 | 70.6 | identical | FAIL (peak). It isolates the cockpit but doesn't lower the peak. |
| S6 | S1 + S3 | 4460 | 200.0 | identical | FAIL (peak, time) |
| S7 | `MALLOC_ARENA_MAX=2` (control) | 6314 | 74.3 | identical | FAIL (peak) |
| X1 | S3 + `MALLOC_ARENA_MAX=2` (**exploratory, not pre-registered**) | 4925 | 89.1 | identical | would fail |

**Every strategy gives a byte-identical solid** (Hausdorff 0, volume and Euler equal, gauge OK). The trade-off is purely memory against time.

## Conclusion and suggestions (not patches)
1. **Best single lever:** run the fuse serially (S3). Peak 7.7 → 4.9 GB (−36 %) for +15 % time. That is a one-argument change if `fuse_impeller` calls `BRepAlgoAPI_Fuse` with `SetRunParallel(False)`, or a cadquery `Shape._bool_op(..., parallel=False)`. It misses the pre-registered 4.0 GB, so there's no patch. Claude may still want it on its own merits for the cockpit (16 GB boxes, the Preview-with-cup freeze in UI-4).
2. **The ~1.9 GB floor before the fuse** (imports plus 9 fine lofts) plus ~2.5–3 GB of serial fuse working set means the 4 GB target isn't reachable by fuse ordering or thread caps alone. Untested ideas, in order of expected gain:
   - (a) fuse a **coarser screen-density** loft for Preview with cup (Preview doesn't need print tolerance);
   - (b) build one blade, fuse it to a hub *sector*, then pattern/compound (needs a sewing/`glue` path);
   - (c) `fuse(..., glue=True)` (shared-face glue mode; it can be much cheaper when the blade roots only touch the hub, but it needs a geometry check);
   - (d) free the retained ~5 GB after the fuse (e.g. drop the BOP history with `op.SetToFillHistory(False)` before `Build`). That doesn't cut the peak, but it matters for multi-stage test processes (the slow suite inherits 7.3 GB between files).
3. For the tests: `test_mount_gauge`, `test_objectives_orientation`, `test_stock_handedness` and `test_blade_le_leads` each build this solid. A session-scoped fixture with the fused Stock impeller would cut 3 × ~60 s and keep the suite peak at one fuse.
