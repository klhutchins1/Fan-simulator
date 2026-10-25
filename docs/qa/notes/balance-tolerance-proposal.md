# Real-world balance tolerance + four-run trim helper (lead #15, proposed 2026-10-21)

**Status:** Proposal only. Research prototype is in `research/proto/lead15/` (not in the repo). Awaiting a hand-off decision.
**Scope:** `structural/balance.py`, the print export balance sheet, and a small CLI helper. No physics, scoring or optimizer change.

## Problem

`balance_summary` checks only that the *design* is balanced (1e-6), and it reports a counterweight for the ideal shape. A printed rotor is never ideal:
- one blade 1 % heavy is about 2.4 g·mm on the Stock rotor;
- a 50 µm seat offset is about 1.7 g·mm.

ISO 21940-11 G 2.5 allows **0.41 g·mm** for the Stock (34 g at 2000 rpm), and G 6.3 allows 1.0 g·mm. Users aren't told that a trim is almost always needed, or how to do one without a
phase sensor.

## Approach

1. **`permissible_unbalance_gmm(mass_kg, rpm, grade=6.3)`** and **`e_per_um(rpm, grade)`** in `structural/balance.py`.
   - U_per = 9549.3·G·m/n. Written as our own code from the formula; no ISO tables.
   - Grade constants: `G_FAN_DEFAULT = 6.3` (ISO 14694 BV-3), `G_FAN_FINE = 2.5` (BV-4).
2. **Print sheet line** (`print_export.balance_summary`): "Tolerance at {rpm} rpm, G {grade}: {U} g·mm (≈ {blob} mg at the blade tip). A typical print is
   2–6× over this. Balance on the motor using the four-run trim below."
   - Mass = solid blades + hub at the sheet's infill, with the motor-cup volume removed. The `estimate_weight_g` default of 20 % infill on everything understates blade mass.
3. **Four-run calculator:** `four_run_correction(v0, v_trials, trial_mass_g, angles_deg=(0, 120, 240)) -> (mass_g, angle_deg, residual)`.
   - Least squares on V_i² = V0² + b² − 2·V0·b·cos(θ_i − ψ), for ≥3 trials at any angles.
   - Exposed as `fansim balance-trim` (CLI). Cockpit hook optional, later.
   - Text guidance:
     - tape the phone to the fan frame;
     - read the **1× (rotation-frequency) amplitude**;
     - use the same PWM or voltage for each run;
     - choose a trial weight that changes the reading by ≥30 %;
     - expect 1–2 rounds.
4. **Props:** show the G value as information only. ISO grades imply sub-mg blobs at 25k rpm, so no warning or gate.

## Non-goals

- Two-plane (dynamic) balancing. Fans are thin (axial length/diameter < 0.5).
- Any change to the uneven-spacing balance solver or to scoring.
- Live phone sensor ingest.

## Verification

- Unit tests:
  - the formula against hand values (Stock: 34 g, 2000 rpm, G2.5 → 0.406 g·mm);
  - exact four-run recovery from synthetic V_i at the 0/120/240 and 0/90/180 angle sets;
  - two published examples: Reliabilityweb ≈ 62 g at 40° (graphical 59 g at 42°), and Motionics 2.37 g at 252°, matched to ±1 %.
- Monte Carlo smoke test (in the proto): with 5 % reading noise, the median residual after one correction is ≤ 20 % of the initial unbalance.
- **Effort: S** (about 1 day including CLI and tests).
