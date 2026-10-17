# Why the push row contradicts the score (roadmap 27.3e): investigation

2026-10-17. This is read-only analysis of the 15 cases that already exist: Stock from 27.3b, and 9604 and 9610
from 27.3d, five meshes each. No code was changed and nothing was re-solved.
- Probes: `scripts/push_row_probe.py` and `scripts/push_row_probe_blade_planes.py`.
- Data: `runs/push_row_probe*.json`.

## Symptom

9604 has 33 % *less* mean push than Stock on every mesh, yet it moves 13 % *more* air under load (27.3d). The card
shows ⚠ "pushes less" on the better fan.

## What the loaded field is

The saved field the card reads is the **fixed 8 Pa back-pressure probe**:
- the outlet is `fixedValue` at 6.667 m²/s² (kinematic), which is 8 Pa;
- the inlet is total pressure 0.

The score's loaded CFM is where the fan line through this solve meets the hose curve (`system_curve.py`). In this
field every fan works against the same outlet pressure, so the useful difference between fans is how much air
gets through.

## Finding 1 (the main defect): the measuring planes sit inside the blade rows

`flow_report.py` puts the planes at z_fan ± 0.18 r_tip, with a half-width of 0.04 r_tip. That is about
±9.8 ± 2.2 mm, whatever the blade's own position.

| design | blade z (r > hub + 1 mm) | inlet slab −12.0..−7.6 mm | exit slab +7.6..+12.0 mm |
|---|---|---|---|
| Stock | −7.9 … +8.2 mm | just upstream (grazes the LE) | **overlaps the TE** |
| 9604 | −16.4 … +4.2 mm | **inside the blade row** | 3–8 mm behind the TE |
| 9610 | −15.3 … +8.6 mm | **inside the blade row** | **overlaps the TE** |

So each design's "push" is taken at a different place in its own blade passage. Inside the passage, the static
pressure includes the blade-to-blade loading and the swirl's radial-equilibrium rise. At these planes the push
ranks with exit swirl (Stock 7.2 Pa, 9604 4.0, 9610 9.8 of swirl dynamic pressure) and *inversely* with airflow.
The spec's claim that swirl's tilt "cancels in the area mean" does not hold at these planes.

**With the planes moved just outside each design's own blades** (inlet at LE − 0.1 r_tip, exit at TE + 0.1 r_tip;
mean over five meshes):

| | loaded CFM | push, card planes | push, blade-relative planes | vs Stock (blade planes) |
|---|---|---|---|---|
| Stock | 43.3 | 12.8 Pa | 10.8 Pa (10.5–11.2) | – |
| 9604 | 48.9 | 8.6 Pa (**−33 %**) | 12.9 Pa (12.0–13.6) | **+19 %** |
| 9610 | 40.2 | 13.6 Pa (+7 %) | 11.0 Pa (10.6–12.0) | +2 % |

- The contradiction is gone. 9604 now pushes more and also moves more air.
- Outside the blades, the static rise is about 7–8.5 Pa for all three, close to the 8 Pa back pressure, and the
  swirl pressure there is 3–5 Pa.
- At LE − 0.3 r_tip the inlet slab has very few cells (0 on two meshes), because the mesh is coarse upstream. 0.1 r_tip
  is the usable gap.

## Finding 2: the other exit-plane rows are affected too

Backflow, swirl, dead air, tip ratio and the push bars all use the same exit slab. For Stock and 9610 the slab
overlaps the trailing edge, so those rows also mix in the blade wakes. Every 27.3 and 27.3b threshold was derived from
these planes (`FLOW_REPORT_VERSION` 3).

## Proposal (for Kimball; nothing applied)

1. Place the planes from each case's own blade extent (`impeller_cfd.stl`, r > hub + 1 mm): inlet at LE − 0.1 r_tip,
   exit at TE + 0.1 r_tip. Bump `FLOW_REPORT_VERSION` to 4 so every cached report recomputes.
   `fansim.cfd.spanwise` shares the plane, and the Expert spanwise plots move with it.
2. Re-derive the 27.3 / 27.3b / 27.3d numbers from the **existing** 25 fields with the new planes (no CFD). Use
   pre-registered rules carried over unchanged (2σ, never tighten, the same stop lines), and re-run the 27.3d
   Q1–Q3.
3. Pre-registered checks of the fix:
   - 9604's push and loaded CFM move the same way against Stock on all five meshes;
   - no plane slab overlaps any blade (an assertion in `compute_metrics`).

Note: `flow_report.py` and `flow_verdicts.py` currently have someone else's uncommitted 27.3c work (`noise_hint_db`,
`fansim/acoustics/tip_loading.py`). Land or shelve that before the change.

## Pre-registration of the fix (Kimball approved 2026-10-17; written before the code)

**Change:** the flow report's inlet and exit slabs are centred at LE − 0.1 r_tip − h and TE + 0.1 r_tip + h. Here
h = max(0.04 r_tip, 2 mm) is the existing slab half-width. LE and TE are the min and max z of `impeller_cfd.stl`
vertices with r > hub + 1 mm, in metres. When there is no impeller STL, the old fixed planes are used and
`missing["planes"]` says so. The spanwise profile and the face picture use the same planes.
`FLOW_REPORT_VERSION` 3 → 4.

**Pass checks (all on the existing 25 cases, no CFD):**
- F1: on all five meshes, 9604's mean push against Stock has the same sign as its loaded CFM against Stock (+).
- F2: no slab touches the blade (the z ranges are disjoint) in all 25 cases. This is also a unit test.
- F3: re-derive Stock's 2σ tolerances (27.3b rule, `proposed_tolerances`, never tighten). Report only: a change to
  `BAND_TOL` / `BAR_TOL` / margins is proposed to Kimball, not baked.
- F4: re-run the 27.3d Q1–Q3 tables with v4 metrics and report every row whose verdict changes.

A failure is recorded, not re-tuned.

## Results of the fix (2026-10-17, branch `push-planes-27-3e`; `scripts/push_planes_checks.py`)

- **F1 PASS.** 9604 against Stock, per mesh m1–m5:
  - push +11.6 / +22.9 / +18.7 / +21.5 / +21.1 %;
  - loaded CFM +10.1 / +11.5 / +12.6 / +15.5 / +14.4 %.
  - Same sign on all five meshes (it was −29 to −36 % push at v3).
- **F2 PASS.** No slab touches a blade in any of the 20 cases (Stock 5 + 5, 9604 5, 9610 5).
- **F3 (report only).**
  - Stock on five meshes: mean push 10.46–11.20 Pa, 2σ = **5.7 %**. Proposed `BAND_TOL` (set by the bars) **0.12**.
  - Stock same-mesh repeats: 2σ 1.7 %, proposed 0.04.
  - The blade-relative planes have more mesh scatter than the old planes (2.9 % at v3), because the inlet slab now
    sits in coarser upstream cells.
  - Today's constants (mean 0.03, bars 0.08) are therefore below the v4 mesh scatter. Under the never-tighten rule
    the proposal is **mean 0.06, bars 0.12**, below the 0.15 stop line. It goes to Kimball (roadmap R0.2); nothing
    is baked here.
- **F4: verdict changes, v3 → v4** (same-mesh, today's constants):

| design | row | v3 | v4 |
|---|---|---|---|
| 9604 | push | ⚠ "pushes less" on 5/5 | ✓ "pushes harder" on 5/5 (+19 % ± 4.5) |
| 9604 | spin | ✓ better 5/5 | ✓ better 5/5 (swirl −10 pp; it was −26 pp inside the blade row) |
| 9604 | direction | flips | flips (ok / ok+; backflow −0.014 ± 0.019, on the margin) |
| 9610 | push | ✓+ 4/5 | **flips** ok / ok+ / ⚠ (+1.5 % ± 5.0: too close to call) |
| 9610 | spin | ⚠ 4/5 | ⚠ 4/5 |
| 9610 | dead | ⚠ 5/5 | ⚠ 5/5 (tip ratio −19 % ± 5; it was −75 % in the trailing-edge wake) |
| 9610 | direction | ⚠ 5/5 | ⚠ 4/5 |

**Verdict: the fix is accepted on F1 and F2.** The push row now agrees with the score. The rows that remain unstable
are the ones where the true difference sits inside the mesh scatter, which is roadmap R0.3 ("too close to call").

**Baked (Kimball 2026-10-17, R0.2): `BAND_TOL` 0.06, `BAR_TOL` 0.12** (`fansim/cfd/flow_verdicts.py`).
