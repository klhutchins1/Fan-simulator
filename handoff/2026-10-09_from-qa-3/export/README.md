# Export / STL correctness (QA r4 request 6): Stock and 9504, with the mirror pair

**Pre-registration:** `docs/qa/notes/export-correctness-criteria.md`, sha256 `91171a08…7bcc7f`, hashed 15:32:58 MDT, before any run.

**Path (the cockpit's):**
- `prepare_export_flat(flat, spec, fit_frame=True, features=Features(), fit_hub=True)` → `python -m fansim.cockpit._export_worker` (`do_export`, `also_mirror=True`).
- Master f238f54, Linux.
- STLs in `/workspace/fansim/qa/r4_export/{stock,9504}/` (not copied: 4–10 MB each).
- Scripts: `export_run.py`, `export_check.py`, `cup_measure.py`. Results: `checks_*.json`, `cup_measure.jsonl`, `run_*.json`, `*_print_fit.json`.

**Inputs:**
- **Stock:** `stock_blade_flat('a12x25')`. No fit changes.
- **9504:** `ref_prev04_T06559_bem_9504.flat.json` from repo-r3 screen_r3. `fit_hub` set hub_height 0 → 15.0 mm, and tip_radius was rounded 54.4703 → 54.47.
- **Worker wall time:** Stock 205 s, 9504 88 s. Each builds 3 solids (main + as_designed + mirrored).

| check | rule | Stock | Stock mirrored | 9504 | 9504 mirrored | verdict |
|---|---|---|---|---|---|---|
| E1 watertight + winding | both | ✓ ✓ | ✓ ✓ | ✓ ✓ | ✓ ✓ | PASS |
| E2 single body | 1 | 1 | 1 | 1 | 1 | PASS |
| E3 Euler | 0 with the through-bore; mirror = original | 0 | 0 | 0 | 0 | PASS |
| E4 volume | > 0, is_volume | 27369.25 mm³ | 27369.25 | 25055.64 | 25055.64 | PASS |
| E5 tip Ø | 95–110, ≤ 110.1 | 109.00 | 109.00 | 108.94 | 108.94 | PASS (0.5 mm radial clearance to the 110 frame) |
| E6 axial depth | 10–25, ≤ 25.1 | 17.44 | 17.44 | 22.00 | 22.00 | PASS |
| E7 cup Ø | 37.25 ± 0.15 (as pre-registered) | 37.94 | 37.94 | 37.94 | 37.94 | **FAIL as written; the criterion was wrong.** The code cuts `cavity_dia + 2×grip_clearance` = 37.25 + 0.70 = 37.95 (`carve_motor_mount`, `cav_r`). The measured 37.94 matches it to 0.01. The grip-pad tips are at Ø 36.55 (0.35 mm radial crush on the 37.25 motor hub). This is as designed. |
| E8 cup depth | 13.0 ± 0.2 | 13.00 from the blade plane / **12.06 in the hub** | same | 13.00 / **10.58 in the hub** | same | **Finding:** the cup is cut 13 mm up from the impeller's lowest point (`z_bounds=bb.zmin`). The blades hang below the hub face by 0.94 mm (Stock) and 2.42 mm (9504), so the motor hub is held by only 12.06 / 10.58 mm of hub wall and grip pads. The gauge reports 13.0 and calls it OK. |
| E9 grips | 20, protrude 0.7 ± 0.15 | 20, 0.696 | 20, 0.696 | 20, 0.696 | 20, 0.696 | PASS |
| E10 blade count at 0.8 R | n_blades | 9 | 9 | 10 | 10 | PASS |
| E11 mirror | Hausdorff ≤ 0.05 mm after reflection; volume within 0.1 %; handedness sign flips | — | Hausdorff 9e-11 mm (y→−y), Δvol 0, sign −1 → +1 | — | Hausdorff 1e-10 mm, Δvol 0, sign −1 → +1 | PASS: an exact mirror image |
| E12 sidecars | .step .md mount_checklist print_fit handedness.json; mount_ok & frame_ok | all present, ✓ ✓ | | all present, ✓ ✓ | | PASS |

**Other observations:**
1. **The main STL is a duplicate.** With `also_mirror`, `do_export` writes `<stem>.stl` **and** `<stem>_as_designed.stl`, and they are identical (Hausdorff 5e-11). That is a third full build: Stock export 205 s instead of ~140 s, with three 7.6 GB fuses one after another in the worker.
2. **Gauge readings are inconsistent.** The gauge's `cavity_dia_mm` reads 38.06 (Stock) and 37.79 (9504) for a geometrically identical cup (37.94 by ray casting). It looks vertex-based, and it is reported to users in `*_print_fit.json`.
3. **Rounded caption.** `mount_msg` says "cup cavity 37 mm" (`:.0f` of 37.25; the cut is 37.94).
4. **The bore is through.** Ø 19.995 for all four, and Euler 0 is consistent with that.
