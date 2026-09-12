<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Physical validation rig (plan Phase 6 — deferred, hooks only)

The eventual credibility backbone for a "fan showdown": measure a printed part and feed the numbers
back through `validation/ingest.py` to calibrate the simulation. **Not built** — no calibrated
instruments on hand — but documented so it can be stood up later. Nothing in the pipeline depends on
it.

## What to measure (per operating point)
- **Airflow (CFM)** and **static pressure (Pa)** on a P–Q rig (ISO 5801 / AMCA 210 style): a plenum
  chamber with an auxiliary blower and a set of calibrated nozzles/orifice, so you sweep from free
  delivery to shut-off. This is the gold-standard comparison for `cfm_free`, `cfm_load`, shut-off.
- **Noise dB(A)** at 1 m: even an *uncalibrated* mic captures *relative* A/B deltas between designs
  under identical conditions — enough to check the LBM's relative ranking, which is all it claims.
- **RPM / tach** to fix the operating condition (match the sim's 2000 RPM), and shaft power if a
  torque/current measurement is available (for efficiency).

## Minimum viable version
Print two designs, run both on the same motor at the same RPM in the same duct, and record relative
CFM (anemometer), relative pressure (manometer), and relative noise (phone mic, same distance).
Absolute accuracy is secondary; **matched A/B deltas** validate the *relative* rankings the whole
project optimizes for (the honest north star).

## Ingest
`validation/ingest.py`:
- `load_measurements(csv)` → `list[MeasuredPoint]` (rpm, cfm, static_pressure_pa, noise_dba).
- `calibrate(measured, simulated)` → per-quantity sim→reality factors (CFM/pressure ratios, dB offset).

Fill the CSV, pair it with the matching simulated operating points, and the calibration factors tell
you how optimistic the idealized-geometry sim is — and let you correct future predictions.
