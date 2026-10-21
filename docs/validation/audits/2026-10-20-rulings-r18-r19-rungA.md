# Rulings 2026-10-20: prop CFD rung A, grok r18/r19, and review of Cursor's R1.7/R1.8

Claude, written before any of the follow-on runs named here.

## 1. Prop CFD rung A ("report to Claude")

Result (Cursor, `scripts/prop_section_2d.py`), NACA 4406 at Re 8×10⁴:
- SST C_l is −19 % at α 4° (−25 % at 6°, −36 % at 8°) and **+61 % at 0°**;
- SST-LM is no better (−24 % at 4°);
- A1 and A2 both fail.

**Ruling:**
- The lift curve is too flat: about 0.08/deg against the reference's about 0.15/deg, and the thin-airfoil value
  2π/rad ≈ 0.11/deg. C_l is too high at 0° and too low from 4°. That shape, with SST and SST-LM agreeing, points at
  the **2-D case itself** (near-wall/TE resolution, or wall-layer coverage from snappy on a 0.2-chord background grid),
  more than at turbulence physics.
- The y+ = 0.8 in the table is the *requested* first cell; the achieved y+ and layer coverage were not reported.
- So rung A is **INCONCLUSIVE about the turbulence model** until the 2-D setup is verified. Rung C is not run yet.

**Rung A0 (pre-registered now): verify the 2-D setup on a textbook case.**
- **Case:** NACA 0012 at Re 6×10⁶, fully turbulent `kOmegaSST` (the regime where SST is known to work), at α 0°, 5°
  and 10°. Same script, mesher and settings as rung A, with only the section, Re and α changed.
- **Reference:** Ladson, NASA TM-4074 (1988, public domain), tripped. grok r20 B supplies the table.
- **Report, alongside the numbers:** achieved first-cell y+ (max and mean over the airfoil), layer coverage %, and the
  surface cell count.
- **Pass:** C_l within ±5 % at 5° and 10°, and C_d within ±20 % at 0°.
- **If A0 PASSES:** the 2-D setup is sound, so the NACA 4406 miss is low-Re RANS physics. Prop CFD then stays labelled
  "direction and bookkeeping only" for v0.1.0, as the ladder pre-registered. Rung C (3-D transition) is not worth its
  cost, because SST-LM did not help in 2-D. Report to Kimball.
- **If A0 FAILS:** the setup is the problem. Fix the 2-D mesher (a structured C-grid, or layers that pass coverage
  ≥ 95 %), judged **only** on A0. Then re-run rung A unchanged. A fix there that also affects the 3-D prop mesher is a
  new pre-registration.

## 2. The prop validation case: TU Delft low-Re benchmark (grok r19 A)

Casalino et al. 2021, AST 113:106707, **CC BY 4.0**. D 0.30 m, 2 blades, NACA 4412 full span, measured C_T and C_Q at
5000 rpm, J 0–0.8, Re(0.75R) ≈ 9×10⁴.
- **Accepted** as the R2.2 validation prop (replacing "a UIUC DA-series prop").
- Its CFD pre-registration is written only after rung A0, because it depends on whether prop CFD can be a predictor at
  all.
- grok r20 C digitises Fig 4 (chord and twist) and the C_T/C_Q curves now.

**BEMT (grok r19 B):** the shipped `table` backend agrees on this known-section prop: C_T −5 % static / −7 % at J 0.4,
C_P within 1 %.
- That supports the R2.1 claim "BEMT validated" for props with known sections.
- The release note keeps: "toward zero thrust, C_T reads about 0.01 low" (−14 % at J 0.48, −24 % at 0.60).
- **QA-51** (the NeuralFoil backend doesn't converge on this prop) is a Cursor task. Until it is fixed, the cockpit must
  not offer the NeuralFoil backend outside Expert, where it is labelled "experimental".

## 3. CROR (QA-50)

grok r18 B finds that "Table 1 stagger is from the rotation plane" is consistent at mid-span only (4/6 stations within
±15°). With the ruled 4 % camber, the ideal lossless Euler rise is about 279 Pa against 510 Pa measured.
- **Ruling: the pre-registered geometry stands.** Switching to "from the axis with about 10 % camber" because it can
  reach the measured pressure would mean choosing geometry by agreement with the data, which is exactly what the freeze
  forbids.
- **S1′ (sign of the P–Q slope) stays meaningful:** it tests curve shape, which a low-pressure model can still get right.
- **Expected outcome, written now:** A1/A2 miss low, so at best "trends validated". The tab's label in v0.1.0 will
  then say so.

## 4. Review of Cursor's R1.7 (one hub) and R1.8 (two-stage hang), branch `r33-install-guide`

- **R1.7: approved.** `mount_hub_params` is applied in objectives and placement, so validate, score and export share
  one hub with the growth below the blades. `tests/test_one_hub.py` covers it.
- **R1.8: approved, acceptance partial.**
  - Stage 1 is 1.75× designed. Stage 2 is the exact OCCT box on `build_blade_solid`, in `build_impeller_parts`
    (QA-49's method).
  - The stage-2 check matched grok's values on the **6 feature-free** designs. The **4 feature designs** (S5_0207,
    S5_0073, S5_0112, S5_0023) could not be rebuilt here, because grok made them from its r7 data, which isn't in the
    repo.
  - grok r20 A sends their `flat` + `features` JSON, and Cursor adds them to `tests/test_hub_hang.py`. Status:
    `done (acceptance 6/10; 4 feature designs pending grok r20 A)`.
- Both merge after tonight's night-queue suite (`suite-cursor-1020-c1..c3`) is green.
