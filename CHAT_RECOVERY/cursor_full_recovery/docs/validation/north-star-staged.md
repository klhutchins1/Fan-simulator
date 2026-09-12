# North star §5.1 — staged until a commercial hub arrives

**Status:** software path exercised 2026-09-11; still **blocked on hardware** (no commercial frame/hub on hand yet).  
**Recorder:** already built (cockpit Library → measurement fields → `validation/measurements/`).  
**Do not** mark roadmap §5.1 done until one real CFM/static/noise/weight point is saved.

## Why this doc exists

You can print an impeller now. You cannot honestly validate a **real-frame** design until you have a commercial hub (e.g. stripped A12x25). This runbook freezes the software path so arrival day is mechanical.

## Software path exercised (2026-09-11)

Print-ready stock A12x25 impeller (motor cup carved, watertight):

| Artifact | Path |
|----------|------|
| STL | `exports/north_star_a12x25_stock_20260911-163616.stl` |
| Print sheet | `exports/north_star_a12x25_stock_20260911-163616.md` |

Treat shaft/motor bore as confirmed against the real motor before the final print if your boss differs from the A12x25 `MotorMount` in `fansim.fan_spec`. Store the print with this filename (or a cockpit `design_id` once you Assess a preferred geometry).

**Next physical steps (you):** print that STL → wait for commercial hub → mount → measure → Save in cockpit.

## Before the hub arrives

1. Open the cockpit on any run (empty Optuna is OK).
2. Assess one design that **fits** the target hub (Fit envelope / `fits this hub`).
3. Export print-ready STL + print sheet (Design → Export) — *or use the stock export above*.
4. Treat shaft/motor bore as a **placeholder** until you measure the real motor (`print_export` notes this).
5. Print the impeller when ready; store the `design_id` (run + trial) with the part.

## When the commercial hub arrives

1. Strip the stock impeller; keep the frame, motor, and wiring.
2. Confirm hub cup / shaft against the print (re-export bore if needed).
3. Mount the printed impeller; set RPM to match the sim (`actual_rpm` / datasheet).
4. Measure at least one of: **CFM**, **static Pa**, **dB(A)**; ideally also **weight** and **RPM**.
5. In the cockpit, select that design → fill measurement fields → Save.
6. Confirm a JSON landed under `validation/measurements/` for that `design_id`.
7. Then do §5.2: sim-vs-real / calibration from the store.

## Minimum viable (from `validation/rig.md`)

Matched A/B deltas on the same motor/RPM/duct beat absolute AMCA accuracy for ranking. Absolute CFM can wait for a better rig.

## Honesty

- Printable stand-in frames do **not** close §5.1.
- Synthetic store rows do **not** close §5.1.
- One real measurement changes the design layer from hypothesis → result.
