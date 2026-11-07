# Ruling 2026-11-06: prop CFD rung A0 C-grid (R2.2a′)

Claude, written before any follow-on run. Ladder: `2026-10-17-prop-cfd-fix-prereg.md`.
Rules: `2026-10-20-rulings-r18-r19-rungA.md` §1.
Data read: `runs/prop_section_a0_cgrid2/` (summary.json, `forceCoeffs1` histories, `0/` and `2000/` fields, polyMesh
boundary), and `scripts/prop_section_2d.py` at 96865fa.

## Verdict: INVALID as a judge of SST. This is not a FAIL of the turbulence model.

The wall is resolved (y+ mean 0.22–0.27, 100 % structured walls). Cursor's mesher fix did what the §1 ruling asked.
But the case still fails the basic checks a verification case has to pass before its numbers mean anything. So the
−14 % / −44 % lift says nothing yet about SST at Re 6×10⁶.

For context, fully turbulent SST on NACA 0012 at Re 6×10⁶ is a standard verification case. On a converged textbook
grid it lands within a few percent of Ladson's lift at 10°. A −44 % miss is a setup signature, not model physics.

## What is wrong with the case (from the run data)

1. **Not converged at 0° and 5°.**
   - At 0° the symmetric foil's C_l swings between −0.19 and +0.22 over the last 20 % of iterations (up to +0.29 earlier). The reported
     "0.086" is the mean of a limit cycle. A converged case gives |C_l| ≈ 0.
   - At 5° it still swings 0.442–0.470 in the tail (±3 %, which is more than half the ±5 % window).
   - So the C_d(0°) −2.4 % "pass" is also a mean of an oscillating solution. It does not count as a pass.
2. **The leading edge is under-resolved.**
   - `N_CGRID_TANGENT = 48` cells per surface with tangential grading 1 gives a uniform ≈ 2.1 mm cell (c = 100 mm).
   - The NACA 0012 leading-edge radius is 1.1·t²·c ≈ 1.6 mm, so the LE circle and the suction peak get about two
     cells.
   - That is consistent with the converged 10° solution: steady, with C_d 0.058 against Ladson's ≈ 0.012, which means
     a large premature separation.
3. **The trailing edge has a cell-size jump.** The foil cell at the TE is ≈ 2.1 mm. The first wake cell is ≈ 7.7 mm
   (32 cells over 16c, grading 20). A ≈ 3.7× jump at the TE smears the Kutta condition, which is a plausible source of
   both the lift deficit and the 0° unsteadiness.
4. **The grid is coarse in the normal direction and the domain is small.**
   - 60 normal cells from 0.36 μm to 8c give a growth ratio of ≈ 1.25 per cell. Practice is ≤ 1.15–1.2.
   - The far field is at 8c with a plain freestream boundary condition and no vortex correction. That alone costs a
     few percent of C_l. It is not the 44 %, but it eats the ±5 % window.

Checked and fine:
- The wake slit is merged (no wake patches left in `polyMesh/boundary`).
- The final far-field |U| is 0.998–1.002.
- The TE is a single closed point.
- α is applied once (grok r22 C).

## Rung A0c (pre-registered now): last A0 attempt for v0.1.0

Same script and solver settings. Only the C-grid parameters and the iteration count change. Section 0012, Re 6×10⁶,
`kOmegaSST`, Tu 0.1 %, α 0°, 5°, 10°. Reference: Ladson, unchanged.

**Grid-quality gate (must be met before the numbers are judged; report each item):**
- Tangential: ≥ 128 cells per surface, clustered so the LE cell is ≤ 0.1 % c and the TE cell is ≤ 0.1 % c.
- Every adjacent-cell size ratio is ≤ 1.2, including foil→wake across the TE.
- Normal: first-cell y+ ≤ 1 achieved (max, not only mean); growth ratio ≤ 1.15.
- Far field: R_OUTER ≥ 50c, with the wake extending ≥ 50c downstream.
- Convergence:
  - In the last 20 % of iterations, C_l peak-to-peak is ≤ 1 % of its mean at 5° and 10°, and ≤ 0.005 absolute at 0°.
  - |C_l(0°)| ≤ 0.01.
  - Raise `--iters` up to 10 000 as needed. Iteration count is not tuning.
- Grid independence (10° only): one run on a 2×-refined grid in both directions. C_l changes ≤ 2 %.

**Pass (unchanged windows):** C_l ±5 % at 5° and 10°, C_d ±20 % at 0°.

**Outcomes, fixed now:**
- **Gate met, PASS:** the 2-D setup is verified.
  - Re-run rung A **unchanged** on this mesher: NACA 4406, Re 8×10⁴, SST and SST-LM, α 0–8°.
  - Judge it by A1/A2 exactly as written in the ladder.
  - Any mesher change that also touches the 3-D prop mesher is a new pre-registration.
- **Gate met, FAIL:** a verified-quality grid still misses, so the fault is in the solver setup (schemes, BCs), not the
  grid.
  - The ladder **closes for v0.1.0**. Prop CFD stays "direction and bookkeeping only", which is already shipped
    (d262543).
  - Report to Kimball. Re-open in v0.1.1 or later only.
- **Gate not met** (e.g. it cannot converge at 0°): report the gate table and do not judge. Treat it as "Gate met,
  FAIL" for v0.1.0 purposes, which means the ladder closes. No further A0 rounds this release.

Rungs C and D stay blocked until A0c is resolved. B2 (sectional) and the 2026-10-20 "fixed" amendment stand.

## Cost

Day CPU. The current runs take ≈ 100 s each, and the A0c grid is about 10–20× larger, so expect minutes per run. Never
run it 4–9 PM.
