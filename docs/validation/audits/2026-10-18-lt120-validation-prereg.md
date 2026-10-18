# Second published axial fan: lt120 (release R1.1, roadmap 25.7): pre-registration

Written 2026-10-17 (late), before any lt120 CFD. Data: `docs/qa/benchmarks/lt120/`.
- Lin & Tsai 2011 measurement, via Tutar & Cam 2025, CC BY 4.0.
- 7 blades, Ø120 mm, hub Ø50 mm, 2000 rpm.
- 5 static-pressure points digitised to ±0.05 Pa / ±0.05 CFM; the rig and its uncertainty are unknown.

## Geometry (freeze before any CFD)

- Build from `docs/qa/benchmarks/lt120/geometry.json` (Table 1: 10 stations of radius, chord, setting angle and NACA
  4-digit section), with **wrapped sections** (`section_wrap="cylinder"`, the shipping builder).
- The hub-hang **print** limit (`MAX_HANG_BELOW_HUB_MM`, R1.8) is a printability rule, not geometry. The reference
  build skips **only** that check, through an explicit `reference_build=True` path. Nothing else differs from a normal
  build.
- Stated assumptions (from `source.md`):
  - the setting angle is measured from the rotation plane;
  - tip gap 0.5 mm, so a round duct of ID 121 mm;
  - the table's radii 23.0–56.5 mm are used as given, with the hub at r = 25 mm as stated.
- Commit the STL + `validation/reference/lt120/geometry_freeze.json`. That commit is the freeze.
- Before CFD, check the built blade against the table with cylinder cuts (as in 27.4). Chord, stagger and camber must
  be within the shipping builder's own tolerance (`correct_clipped_sections` limits); anything outside is reported
  first.

## Rig and solve

- The validated Assess setup (ring + frame-less duct + layers, v5 conventions, tail-mean metrics), scaled to the 121 mm
  duct, with the same inlet and outlet lengths in diameters.
- Direction: designed orientation from the builder, which proves it CONCLUSIVE. INCONCLUSIVE stops the case.
- Each measured point is solved as a **fixed back-pressure** run at the measured ΔP, as Assess's load probe does, and
  CFD gives the flow Q at that pressure.
- Points: 13.71, 6.85, 14.69 and 17.14 Pa.
- The 34.01 Pa / 0.0038 m³/s point is **excluded in advance**: it is near shut-off, where steady RANS does not converge
  (A12x25: 15–20 Pa points did not converge; audit-02).
- **Mesh repeat:** every point on two meshes, base cell 5.8 mm and 6.2 mm (27.3b showed mesh scatter of ±1 % in CFM).
- Convergence gate: tail CFM peak-to-peak ≤ 2 % and mass imbalance ≤ 1 %. Otherwise the point is INCONCLUSIVE.

## Rules (fixed now)

The error at a point is the mean over the two meshes of Q_cfd / Q_meas − 1.

| verdict | rule |
|---|---|
| **PASS (validated)** | the two high-flow-branch points (6.85 Pa → 84.0 CFM and 13.71 Pa → 60.0 CFM) are each within **±10 %**, and both meshes agree within 3 % |
| **trends** | both within ±15 %, or the ±10 % rule fails on only one point |
| **FAIL** | anything worse, or either high-flow point INCONCLUSIVE |

- The 14.69 and 17.14 Pa points (the flat part of the curve) are **report-only**. A miss there is consistent with the
  known near-stall limit and does not change the verdict.
- Why ±10 %: the A12x25 reference passed at −0.5 % with a known rig. Here the rig and static tap convention are
  unknown, so the band is doubled from the ±5 % used for A12x25, and stated before running.
- Failures are recorded, not re-tuned. The geometry freeze cannot change after the first CFD run.

## Work split

1. Cursor: `reference_build=True` path (tested: refuses nothing else, skips only the hang check), the geometry freeze,
   the cut check, and `scripts/validate_lt120.py`.
   - The script writes `runs/lt120/summary.json` and resumes finished points.
   - Then add the night job.
2. Night: 4 points × 2 meshes = 8 runs, about 6 h. One night, from 00:30.
3. Claude: verdict, recorded here.
