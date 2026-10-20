# R1.8 two-stage hang check (QA-43 / QA-46)

Recorded 2026-10-20 after the code landed, against the pre-registered rules in
`2026-10-19-prereg-amendments-r17.md` §1. Not a re-tune.

## Stage 1 (search prefilter)

Refuse when `1.75 × designed hang > 2 mm` (`HANG_BUILT_FACTOR` in `fansim/geometry/blade.py`).
The 1.75 is the chord-refill series 1 + ½ + ¼ (grok r16 median 1.77, n = 140).

**False refusals:** grok r17 C, at the R1.7 export hub, 1/242 = 0.4 % of designs with built hang
≤ 2 mm. That is under the 3 % cap. **PASS.**

## Stage 2 (built solid)

`build_impeller_parts` measures hang on `build_blade_solid` with OCCT `BRepBndLib.AddOptimal`
(QA-49: not the n_span section-point shortcut) and refuses when hang > 2 mm, before CFD or
export. The message is "the printed blade would hang X mm below the hub (limit 2 mm)".

**Measurement:** feature-free grok r18 A ids (S2_0269, G_0502, S1_0461, S1_0534, S3_0173,
S4_0242) must match `docs/qa/r18/r18-A-built-hang-reference.csv` within 0.05 mm.

## Single-factor rule (recorded FAIL, not re-tuned)

1.75× designed on the auto hub misses S2_0269 (1.997 mm predicted, 2.25 mm built): 1/123.
That is why stage 2 exists. With R1.7's export hub, S2_0269 does not hang.
