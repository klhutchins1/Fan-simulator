# r22 C: A0b bookkeeping, `scripts/prop_section_2d.py` α / U / liftDir / dragDir (code reading only)

QA bot, 2026-10-29. Master **b3d5543**. Prereg **715891f** §C. No solve, no OpenFOAM, no case written. The table is
arithmetic on the formulas read from the code: `handoff/2026-10-29_from-qa-22/scripts/c_alpha_table.py` →
`data/r22-C-alpha-bookkeeping.csv`.

## Verdict: **consistent: no setup bug in the α bookkeeping → does not explain the A0 FAIL**

**Code path** (A0 run: `--section 0012 --re 6e6 --alphas 0 5 10`):
- **Mesh:** built once at α = 0 in `_mesh`, with the chord along +x. For each α the polyMesh is copied (`:929-980`), so
  the geometry is **never rotated**.
- **Inflow** (`write_case`, `:476-479`):
  - `u, nu = solve_u_nu(re, mesh=mesh)` gives the C-grid U = 1 m/s and ν = U·c/Re.
  - `a = math.radians(alpha_deg)`; `ux, uy = u·cos a, u·sin a`.
  - Written to `0/U` internalField, freestreamVelocity and the outlet inletOutlet value (`:632`, `:638-644`).
- **Force directions** (`:480-482`): `lift = (−sin a, cos a, 0)`, `drag = (cos a, sin a, 0)`. They are written into
  `forceCoeffs1` as `liftDir` / `dragDir` (`:595-596`).
- **Same variable `a`** feeds U, liftDir and dragDir, so α is applied **once**, through U only.
- **Report-only:** `patches (airfoil)`, `rho rhoInf`, `rhoInf` = RHO_ISA, `CofR (0.025 0 0)` (c/4),
  `pitchAxis (0 0 1)`, `magUInf` = u (= 1), `lRef 0.1`, `Aref` = 0.1 × 0.002 = 2e-4.
- **Coefficient read-back:** OpenFOAM v2406 `forceCoeffs` (with CofR) builds the frame e3 = liftDir and e1 = dragDir;
  `coefficient.dat` columns are Time, Cd, Cd(f), Cd(r), Cl, …. The parser's `parts[1]` = Cd and `parts[4]` = Cl are
  therefore right (checked against the api.openfoam.com 2406 source).

| α | U (m/s) | liftDir | dragDir | α used by U / lift / drag | geometry α | effective α | dragDir ∥ U | lift ⟂ drag, suction side |
|---|---|---|---|---|---|---|---|---|
| 0 | (1, 0, 0) | (0, 1, 0) | (1, 0, 0) | 0 / 0 / 0 | 0 | 0.000° | yes | yes |
| 5 | (0.996195, 0.087156, 0) | (−0.087156, 0.996195, 0) | (0.996195, 0.087156, 0) | 5 / 5 / 5 | 0 | 5.000° | yes | yes |
| 10 | (0.984808, 0.173648, 0) | (−0.173648, 0.984808, 0) | (0.984808, 0.173648, 0) | 10 / 10 / 10 | 0 | 10.000° | yes | yes |

**What a bookkeeping bug would have produced** (checked against Ladson; none of these is in the code):
- liftDir left at (0, 1, 0) while U rotates: C_l error is −0.24 % at 5° and −1.3 % at 10°. That is far too small for −14 %/−44 %.
- α applied twice (geometry and U both rotated): C_l would come out too **high**.
- α missing from U: C_l ≈ 0.
- **None matches** the A0 pattern (C_d(0°) −2.4 %, C_l(5°) −14 %, C_l(10°) −44 %, a deficit that grows with α).

**Code-visible alternatives (report-only; not tested, no CFD run):**
1. **Convergence:**
   - The C-grid uses `residualControl {}`, 2000 iterations and p relaxation 0.3.
   - C_l is averaged over the last 20 % of the `coefficient.dat` rows (writeInterval 20).
   - A still-rising C_l history would read low, more so at higher α. Look at the C_l history in the A0 case.
2. **Tangential resolution:** 48 cells per surface, spaced uniformly along the spline (96 airfoil faces, 9600 hexes).
   - The leading-edge suction peak is under-resolved, and this gets worse as α rises. That fits the trend.
3. **Far field** at only 8c (`R_OUTER`). This typically costs a few % of C_l; small, but in the same direction.
4. **Wake blocks:** the wake cut and the fine wake blocks are fixed along +x, while the real wake turns with α.

Of these, 1 and 2 could produce a deficit that grows with α. C does not rank them.

No new IDs: there is no bug in the bookkeeping. The alternatives are notes for R2.2a′, not QA findings.
