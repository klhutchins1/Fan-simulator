# North star §5.1 — staged until a commercial hub arrives

**Status:** software path ready for print-fit; still **blocked on hardware** (no commercial frame/hub on hand yet).  
**Recorder:** already built (cockpit Library → measurement fields → `validation/measurements/`).  
**Do not** mark roadmap §5.1 done until one real CFM/static/noise/weight point is saved.

## Why this doc exists

You can print an impeller now. You cannot honestly validate a **real-frame** design until you have a commercial hub (e.g. stripped A12x25). This runbook freezes the software path so arrival day is mechanical.

## Critical: which STL to print

| File | Use |
|------|-----|
| **Print-ready export** from `scripts/export_a12x25_print_ready.py` (or cockpit Design → Export) | **Yes — mount on the semi-official / commercial hub** |
| `validation/reference/a12x25_impeller.stl` | **No** — CFD close-reference only; not a carved motor cup |

The print export carves the **measured MotorMount** (2026-08-31): cup **37.25 mm** × **13 mm** deep, rear bore **20 mm**, min hub wall **1.2 mm**, min hub height **15 mm**. Frame target: tip OD ≤ **109 mm** (110 mm ID − 0.5 mm radial gap), depth ≤ **25 mm**.

## Before the hub arrives (do this now)

1. Export a frame-fitted Stock print:
   ```powershell
   uv run python scripts/export_a12x25_print_ready.py
   ```
   Writes under `exports/print_a12x25_stock_<stamp>/`:
   - `impeller_print.stl` — watertight, cup carved
   - `print_sheet.md` — material / orientation
   - `mount_checklist.md` — gauge vs MotorMount + frame
   - `print_fit.json` — machine-readable pass/fail
2. Confirm `mount_fits=True`, `gauge.mount_ok=True`, `gauge.frame_ok=True`.
3. Print that STL when ready; keep the export folder with the part.
4. Treat MotorMount as **semi-official** until you caliper the real motor; re-export if Δ > 0.2 mm.

Optional cockpit path: Assess a design that **fits this hub** → Design → Export (same `carve_motor_mount` path).

## When the commercial hub arrives

1. Strip the stock impeller; keep the frame, motor, and wiring.
2. Caliper boss OD / cup depth / rear bore / shaft vs `fansim/fan_spec.py` `MotorMount`.
3. Dry-fit the printed impeller; re-export bore/cup if needed.
4. Mount; set RPM to match the sim (`actual_rpm` / datasheet).
5. Measure at least one of: **CFM**, **static Pa**, **dB(A)**; ideally also **weight** and **RPM**.
6. Cockpit → that design → measurement fields → Save → JSON under `validation/measurements/`.
7. Then §5.2: sim-vs-real / calibration from the store.

## Minimum viable (from `validation/rig.md` when present)

Matched A/B deltas on the same motor/RPM/duct beat absolute AMCA accuracy for ranking. Absolute CFM can wait for a better rig.

## Honesty

- Printable stand-in frames do **not** close §5.1.
- Synthetic store rows do **not** close §5.1.
- CFD reference STL silhouette pass does **not** mean print-mount ready.
- One real measurement changes the design layer from hypothesis → result.
