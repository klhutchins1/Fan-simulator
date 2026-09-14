# North star §5.1 — staged until a commercial hub arrives

**Status:** software path ready for print-fit; still **blocked on hardware** (no commercial frame/hub on hand yet).  
**Recorder:** already built (cockpit Library → measurement fields → `validation/measurements/`).  
**Do not** mark roadmap §5.1 done until one real CFM/static/noise/weight point is saved.

## Why this doc exists

You can print an impeller now. You cannot honestly validate a **real-frame** design until you have a commercial hub (e.g. stripped A12x25). This runbook freezes the software path so arrival day is mechanical.

## Critical: which STL to print

| File | Use |
|------|-----|
| **Cockpit Export print STL** (Fan → Design) | **Yes — primary path** |
| Headless twin: `scripts/export_a12x25_print_ready.py` | Same carve/gauge; for CI / batch only |
| `validation/reference/a12x25_impeller.stl` | **No** — CFD close-reference only; not a carved motor cup |

Export carves the **measured MotorMount** (2026-08-31): cup **37.25 mm** × **13 mm** deep, rear bore **20 mm**, min hub wall **1.2 mm**, min hub height **15 mm**. Frame target: tip OD ≤ **109 mm** (110 mm ID − 0.5 mm radial gap), depth ≤ **25 mm**.

## Before the hub arrives (do this in the GUI)

1. Open the Fan cockpit → **Design**.
2. Leave **Fit hub to motor** and **Fit tip/depth to frame** **on** (defaults).
3. Click **Export print STL**.
4. Read the status line: motor cup carved + print-fit gauge mount/frame PASS.
5. In `exports/`, use the new `.stl` plus `*_mount_checklist.md` / `*_print_fit.json`.
6. Print that STL; keep the export files with the part.
7. Treat MotorMount as **semi-official** until you caliper the real motor; re-export if Δ > 0.2 mm.

## When the commercial hub arrives

1. Strip the stock impeller; keep the frame, motor, and wiring.
2. Caliper boss OD / cup depth / rear bore / shaft vs `fansim/fan_spec.py` `MotorMount`.
3. Dry-fit the printed impeller; re-export bore/cup if needed.
4. Mount; set RPM to match the sim (`actual_rpm` / datasheet).
5. Measure at least one of: **CFM**, **static Pa**, **dB(A)**; ideally also **weight** and **RPM**.
6. Cockpit → that design → measurement fields → Save → JSON under `validation/measurements/`.
7. Then §5.2: sim-vs-real / calibration from the store.

## Honesty

- Printable stand-in frames do **not** close §5.1.
- Synthetic store rows do **not** close §5.1.
- CFD reference STL silhouette pass does **not** mean print-mount ready.
- Multi-hour OpenFOAM validation campaigns stay as scripts (not day-to-day GUI buttons).
- One real measurement changes the design layer from hypothesis → result.
