# Fixing propeller CFD (release R2.2): diagnostic ladder, pre-registration

Written 2026-10-17, **before** any of these runs. Kimball chose to fix it, not hide it, on 2026-10-17. Background:
`2026-10-02-audit-08-prop-cfd.md`.
- At the UIUC static point, prop CFD reads C_T −44 % / C_P −40 % against UIUC APC SF 9×4.7.
- Mesh, geometry, boundaries and orientation were ruled out.
- The deficit is spread across mid-span: CFD/BEMT is 0.54–0.70 at r/R 0.36–0.89.
- The audit blamed fully turbulent k-ω SST at chord Re 6–8×10⁴ but **never tested that directly**.

The ladder tests the cheapest discriminating question first. Each rung decides whether the next one runs.

## Fixed setup (unless a rung changes it)

The case is `scripts/audit_prop_cfd.py`'s APC SF 9×4.7:
- UIUC geometry, generic 6 % section with camber 0.04;
- base cell 8 mm, surface level 4, 1000 iterations, freestream boundaries;
- tail-mean metrics.

Reference data: `validation/reference/uiuc_propdb/apcsf_9x4.7_*` (static kt1032; J-sweeps kt1033–1038).

Tolerances are unchanged from audit-08: **C_T ±15 %, C_P ±20 %**.

## Rung A: 2-D section (minutes per run; day CPU, never 4–9 PM)

The question is whether fully turbulent SST under-predicts this section's lift at Re 8×10⁴ by enough to explain the
3-D gap.

- **Case:** a 2-D OpenFOAM case of the exact generic section (6 % thickness, camber 0.04, as built by the prop
  builder), at Re = 8×10⁴. Use a C- or O-grid with y+ ≤ 1 and α = 0, 2, 4, 6, 8°.
- **Models:** `kOmegaSST` (today) and `kOmegaSSTLM` (Langtry–Menter transition, OpenFOAM v2406), each with the
  same grid.
- **Reference:** NeuralFoil (already a dependency) and XFOIL-class polars for the same section at the same Re. This
  is the same polar source family the BEMT uses, and BEMT is −13 % in 3-D.
- **Pass/decision rules:**
  - A1: if SST's C_l at α = 4° is ≥ 25 % below the reference *and* SST-LM is within 10 %, the turbulence model is
    confirmed and we go to rung C.
  - A2: if SST is within 10 % of the reference, the turbulence model is **refuted** as the main cause. Skip C and go
    to rung B and rung D.
  - Anything else is reported to Claude/Kimball before going on.

## Rung B: advance-ratio sweep in 3-D with today's setup (night, about 3 runs × 1 h)

The question is whether the deficit is static-only or everywhere.

- **Runs:** J = 0.3, 0.5, 0.7 at 6000 rpm (kt1035/1036 tables), freestream inflow U = J·n·D.
- **Rules:**
  - B1: if C_T is within ±15 % at J ≥ 0.5 but static is −44 %, the problem is **static-specific**. The suspects are
    then self-induced inflow, recirculation in the box and domain size, so go to rung D first.
  - B2: if C_T is about 30–45 % low at every J, the problem is **sectional**, consistent with A1.

## Rung C: 3-D transition model (night, heavy; runs only if A1)

- **Run:** `kOmegaSSTLM` on the blade with a y+ ≈ 1 layer stack (first cell ≈ 0.01 mm). Static point plus J = 0.5.
- **Pass:** C_T within ±15 % and C_P within ±20 % at both points.
- If C_T passes and C_P fails, report it. It is not a pass.

## Rung D: static domain and recirculation (night; runs if A2 or B1)

- Double the box in every direction, keeping the mesh at the blade, then run static. If C_T moves by more than 5 %,
  the domain was too small and the deficit is at least partly confinement.
- Report the box size against the prop diameter, the share of the outflow face with backflow, and the mass
  imbalance.

## What "fixed" means (R2.2 done)

Prop CFD passes C_T ±15 % and C_P ±20 % at static **and** at J = 0.5 on APC SF 9×4.7, with the setup that ships.
Then a **hold-out** check on APC E 9×6 (`apce_9x6_*`) passes at the same tolerances without retuning. Only after that
does the cockpit's prop "CFD refine" show numbers as a prediction.

If the ladder ends without a pass, prop CFD stays labelled "direction and bookkeeping only". The cockpit hides CFD refine
from Simple mode and labels it in Expert, and that is reported to Kimball.

Failures are recorded, not re-tuned.


## Results

### Rung B (2026-10-20 00:30–02:47, night queue; J points per amendment §5)

`runs/prop_cfd_jsweep/summary.json`, all three points converged. The process exited 0xC0000005 at teardown, after the
summary was written (the known OCCT/VTK teardown crash).

| J | CFD C_T | UIUC C_T | CFD error | CFD C_P error | BEMT C_T error (same geometry) | CFD / BEMT C_T |
|---|---|---|---|---|---|---|
| 0 (audit-08) | 0.0667 | 0.1192 | −44 % | −40 % | −13 % | 0.64 |
| 0.20 | 0.0557 | 0.0925 | −40 % | −38 % | −15 % | 0.71 |
| 0.30 | 0.0423 | 0.0763 | −45 % | −41 % | −20 % | 0.69 |
| 0.43 | 0.0211 | 0.0503 | −58 % | −49 % | −29 % | 0.59 |

**Verdict: B2 sectional** (C_T ≤ −30 % at every J). The shortfall is not static-specific, so rung D (domain) is not
indicated.

**A finding the ladder did not anticipate:** BEMT on the *same* geometry also falls further behind as J rises,
−13 % → −29 %. So there are two separate deficits:
1. **Shared (geometry input):** UIUC gives chord and β but not the airfoil, so both models use a generic 6 % section with
   4 % camber. A section with too little camber has too small a zero-lift angle. That costs a roughly constant ΔC_T,
   which is a growing relative error as C_T falls. Even a perfect CFD of this geometry would land near BEMT, and so
   would miss ±15 % beyond J ≈ 0.2.
2. **CFD-only:** CFD/BEMT ≈ 0.6–0.7 at every J on the same section. This is the deficit rung A tests (fully turbulent SST
   against transitional polars).

**Consequence for "fixed" (amended 2026-10-20, before rung A or C data):** APC SF cannot by itself show that CFD is
fixed, because its geometry is approximate.
- **CFD verification on APC SF:** after the fix (rung C or a model change), CFD C_T is within **±10 % of BEMT on the same
  geometry** at static, J 0.20 and J 0.30. This shows CFD gets the section aerodynamics right.
- **Validation:** a hold-out prop with **fully specified airfoil sections** plus measured C_T/C_P (grok to find; e.g.
  UIUC's own-design DA-series props) passes **C_T ±15 % and C_P ±20 %** at static and one J in mid range, with no
  retuning.
- The APC SF against UIUC numbers stay recorded as the starting point and are reported in the release notes as
  "approximate-geometry case".
