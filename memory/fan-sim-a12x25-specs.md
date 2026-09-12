<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

---
name: fan-sim-a12x25-specs
description: Published Noctua NF-A12x25 PWM specs — CFD validation ground truth
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9facc2be-ff12-44e2-9ede-0cced25b4756
  modified: 2026-08-28T20:34:02.877Z
---

Validation target for Fan-simulator (the numbers our CFD must reproduce before any absolute
claim). Source: noctua.at/en/nf-a12x25-pwm/specification + PCPartPicker. Full doc:
`E:\Projects\programming_2\Fan-simulator\docs\a12x25-reference.md`.

**⚠ HUB/FRAME DIMS CORRECTED 2026-08-31 — user PRINTED a fan + measured the REAL motor; the earlier
50 mm (Google) and ~52 mm (from the 'close, not original' remix STL) were BOTH WRONG (oversize hub =
bad print). REAL MEASURED, now in the a12x25 FanSpec/MotorMount:**
- **Motor hub the printed cup slips over = 37.25 mm inner dia** (NOT 50/52). cavity_dia_mm=37.25.
- **Max outer/tip diameter = 110 mm** to clear the frame (was 119). tip_dia_mm=(95,110). => MANY of our
  optimized designs (opt_extended2_t36 ~118 mm, etc.) now EXCEED the frame and need tip_radius shrunk.
- **Hub height >= 15 mm** (inside surface to back) to clear the frame spokes. MotorMount.min_hub_height_mm
  =15; cavity_depth_mm=13 (leaves ~2 mm cap). Export grows hub radius AND height to fit.
- Consequence: min mountable hub radius dropped 27.2 -> **19.8 mm** (cavity/2+min_wall) — far more designs
  are natively mountable now. rear bore 20 mm + 3 mm shaft unchanged (unverified against the real motor).
The 50 mm / 52 mm numbers BELOW are the SUPERSEDED wrong values — kept for history only.

- Max speed 2000 RPM (range 450-2000, PWM)
- **Max airflow (free delivery) = 60.1 CFM** (102.1 m³/h = 0.02836 m³/s)
- **Max static pressure (shut-off) = 2.34 mmH₂O = 22.9 Pa**
- **Max noise = 22.6 dB(A)** (min 18.8)
- Power ~1.68 W; tip clearance **0.5 mm** (NOT <0.1mm as earlier assumed); 7 blades; Sterrox LCP.

REALITY CHECK: our idealized sim gives ~81.5 CFM free-air for the 9-blade envelope baseline vs
the real 60.1 CFM → ~30-35% OVER-prediction from slip walls / no frame struts / unresolved
tip-leakage / coarse mesh. Self-consistent != validated. See [[fan-sim-adversarial-review]].

REAL STL ACQUIRED (user, 2026-08-26): `C:\Users\Kimball\Downloads\A12x25_Fan.STL` ("close, not
original"). Impeller only (no frame), watertight, 110.5mm dia x 16.7mm deep, ~9 heavily-swept
spiral blades, detailed hub with center bore. Prepped to `build/a12x25_real_z.stl` (axis Y->Z,
centered, tip r 55.3mm). `scripts/validate_stl.py` meshes an arbitrary impeller STL (builds
rig from its bounds) + runs free-delivery vs 60.1 CFM (flip --spin if flow reverses). Center
bore left open for first pass (minor). This is the real validation the parametric approx couldn't give.

**VALIDATION RESULT (2026-08-26): real STL free-air = 61.5 CFM vs published 60.1 = +2%, CONVERGED
(base_cell 0.004, spin=-1 correct). The earlier ~35% over-prediction was GEOMETRY (paddle approx),
NOT CFD. CFD is accurate ~2% on real geometry at free delivery — real validation, not just
self-consistency. NEXT: full P-Q + shut-off (22.9 Pa, near-stall harder), grid convergence.**

BORE CAPPED (2026-08-27): bore was r~9.93mm hole; added `manifold3d` dep + trimesh boolean union
with a plug cylinder -> `build/a12x25_real_capped.stl` (watertight, bore filled, min radius 0).
`scripts/validate_stl.py` works on any impeller STL. Running full P-Q on CAPPED STL: backs
0,4,8,12,16,20 Pa, 1500 iters, base_cell 0.004 -> curve vs published (60.1 CFM free, 22.9 Pa
shutoff). Near-shutoff points (16-20 Pa) likely UNCONVERGED (steady RANS near stall).**

**HUB / MOTOR-MOUNT MEASUREMENTS (user-supplied 2026-08-28, unblocks the motor-mount interface work
for the A12x25 — previously blocked on 'no fan to measure'):**
- **Motor/outer hub diameter = 50.0 mm** (radius 25 mm). NOTE our default hub_radius is 21.5 mm
  (43 mm dia) — the REAL Noctua hub is BIGGER (25 mm r). Steel core + brass reinforcement (motor internals).
- **Internal shaft diameter = 3.0 mm nominal** -> the motor-mount BORE. Use ~3.0 mm (+ slip-fit
  clearance, e.g. 3.0-3.2 mm) as the a12x25 bore default, REPLACING the 5.0 mm placeholder in
  print_export.py BoreSpec.
- Rear hub sticker (flat label) area ~40.0 mm dia.
- Blade-to-frame TIP CLEARANCE 0.5 mm (consistent w/ the 0.5 mm above); frame 120x120x25 mm,
  mounting holes 105 x 105 mm; Sterrox LCP; AAO.
- User note: the real STL (build/a12x25_real_capped.stl / A12x25_Fan.STL) also carries the hub
  geometry to measure directly. For OTHER fan models the user will source dims separately.
IMPLICATION: add these to the a12x25 FanSpec (hub_outer_dia_mm, shaft_bore_mm, tip_clearance_mm) so
print-export + the motor-mount interface can build a correctly-sized bore/cavity. See the HUB
UNDERSIDE / MOTOR-MOUNT backlog item in [[fan-sim-status]].

**MEASURED FROM THE REAL STL (build/a12x25_real_z.stl, 2026-08-28) — the motor-mount interface geometry
the user-supplied numbers didn't include. The real hub is a HOLLOW CUP that slips over the motor, NOT
our solid cylinder:**
- Impeller-only bounds: 110.5 mm dia x 16.7 mm deep (z -7.7..+9.0; no frame).
- MOTOR CAVITY: from z~-4.3 to +7.3 the innermost material is at r~25.9 mm => a ~52 mm-dia HOLLOW
  cavity, ~11.6 mm deep, sized to slip over the 50 mm motor hub (matches user's 50 mm motor-hub dia).
- REAR BORE: at the back face (z -7.7..-6.0) it necks to r~9.93 mm (~20 mm bore) — bearing/boss region
  (the earlier 'bore was r~9.93mm hole' we capped). The 3.0 mm shaft is on the MOTOR, not in this mesh.
- => real mount = ~52 mm cup cavity ~12 mm deep, closing to a ~20 mm rear bore. Our current build_hub
  makes a SOLID cylinder (r 21.5 mm) with NO cavity — cannot fit the motor. The motor-mount modeling
  needs: hub as a CUP (outer wall to hub_radius, inner cavity ~52 mm dia x ~12 mm deep from the rear
  face, rear bore ~20 mm), + retention. TENSION: optimizer likes SMALL hub (17-21 mm r, more flow) but
  a printable-on-Noctua-motor hub needs outer >= ~25 mm r to house the 50 mm motor -> a physical-build
  constraint distinct from the aero optimum. Analysis: quick per-z min-radius slice of the STL.

**GRID CONVERGENCE DONE (capped STL, free delivery, `scripts/grid_convergence_stl.py`):
6mm/100k->56.8, 4mm/258k->57.7, 3mm/550k->59.6 CFM (=-1% vs 60.1). Monotonic toward published =
strong validation. NOT fully flat (last step 3.2%); screening mesh 4-5mm has ~3-5% quantified
discretization error; ~2mm would land ~60-61 but 550k cells ~16min/point. RELATIVE rankings OK
at coarse (consistent). Free-air VALIDATED. Remaining frontier: TRANSIENT tier (URANS/LBM/GPU)
for shut-off pressure (22.9 Pa, steady RANS gives ~13) + noise. FluidX3D unbuilt.**
