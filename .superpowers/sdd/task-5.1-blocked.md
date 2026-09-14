# Task 5.1 status — Print → measure → calibrate

**Status: BLOCKED (hardware)** — commercial A12x25 hub/frame not on hand yet.

**Software ready (2026-09-14):**
- Measured `MotorMount` in `fansim/fan_spec.py` (cup 37.25 × 13 mm, bore 20 mm; 2026-08-31)
- `scripts/export_a12x25_print_ready.py` — frame-fit Stock + carve cup + print sheet
- `fansim/manufacturability/mount_gauge.py` — STL vs mount/frame checklist
- Runbook: `docs/validation/north-star-staged.md`

Do **not** print `validation/reference/a12x25_impeller.stl` for mounting (CFD only).

When hardware is available, follow the north-star runbook and parent Task 5.1 in
`docs/superpowers/plans/2026-09-14-proper-state-program.md`. Until a real measurement is saved
under `validation/measurements/`, do not mark roadmap §5.1 done.
