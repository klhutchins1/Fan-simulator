# Round 29 for grok (Cursor, refreshed 2026-11-12)

This replaces the 2026-11-11 bundle. That bundle was master `98e3f2c`. It was never returned. Do not use it.

**Build:** `fansim_master.bundle` in this folder is master including the commit that adds this brief. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Write `docs/qa/rounds/r29.md` only (do not edit `docs/QA_REVIEW.md` or the board). Re-check a fix only when it was HIGH. Do not invent a new tolerance. The hub and glyph pass rules are already written.

If `docs/qa/rounds/r29.md` already records a letter below, take the next letter that is not written up. Do not restart a finished letter.

## Tasks

| # | task | board |
|---|---|---|
| A | **QA-73 HIGH re-check.** Export Stock with a known print-id. From outside +Z the recessed code must read left-to-right, un-mirrored, matching the README / `*_print_fit.json`. Cap is **5.0 mm**, stroke **0.9 mm**, band r **11.5–16.5** (P6 after H7MQ8 T3 FAIL). Red: the same tests fail on pre-fix `eeb0e2d`. Green: `tests/test_print_id.py` + `tests/test_print_id_glyphs.py`. | QA-73, QA-80 |
| B | **QA-79 hub face, not bbox.** On a t9002-class design (blades above the hub): the mark is on the hub +Z face. A section at `z_hub − 0.25 mm` shows the code; a section at blade `zmax − 0.25 mm` does not. | QA-79 |
| C | **Hub opening, re-derive.** `grip_protrude_mm` is **0.35**, equal to clearance, so A12x25 pad tips sit on `cavity_dia_mm` **37.25**. The old 0.7 mm protrude put tips at **36.55**. Confirm `tests/test_mountable.py` (`test_a12x25_pad_tips_match_the_opening_that_fits` and `test_a12x25_default_pads_stay_on_the_motor_hub_diameter`) and the layout in `fansim/fan_spec.py`. Do not change `cavity_dia_mm`. Do not retune. Prereg: `docs/validation/audits/2026-11-11-hub-opening-prereg.md`. | P4a |
| D | **QA-51 label only.** Simple mode does not offer NeuralFoil. Expert title contains "experimental". Test: `tests/test_qa51_neuralfoil_expert.py`. Do not try to make the TUD prop converge. | QA-51 |
| E | **R2.6 reachability.** No centrifugal-only flow and no wind-turbine flow is reachable from the cockpit or the README Quickstart. Mixed and Volute stay. The `fansim/wind_turbine` package may stay in the repo. Test: `tests/test_r26_hide_scaffolds.py`. | R2.6 |
| F | **A0c code read only.** C-grid flags exist and today's defaults stay 48 / 60 / 32, far field 8 chord, wake 16 chord. The gate flags (128 tangential, far field and wake 50 chord, LE/TE cell ≤ 0.1% chord, adjacent ratio ≤ 1.2, normal growth ≤ 1.15) match `docs/validation/audits/2026-11-06-ruling-rung-a0-cgrid.md`. Test: `tests/test_prop_section_2d.py`. Do not start the OpenFOAM solve. The night job `r22a-a0c-gate` owns that run. | R2.2a″ |
| G | Do not CFD the pocket. Do not re-prove G2/G3. Do not open research leads 23+. QA-74/75/76 travel with A. | — |

## Print session (record only)

Kimball printed H7MQ8 (Stock v3, PLA+, 0.6 mm, 27.41 g) and E0MWW (t9002 extra). Both files have pad tips at 36.55 mm and do not seat. A 6 mm ring at 37.25 mm fits the motor better. A full Stock export with that same circle is `AVD9=` (2026-11-12). That print is not a T1 pass until it is on the frame. T3 glyphs on H7MQ8 failed; the enlarged letters are in the code. Do not treat the ring or the coupon as article B.
