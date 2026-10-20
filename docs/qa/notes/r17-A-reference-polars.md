# Round 17, Task A (R2.2a): reference polars for prop-CFD rung A

Prereg `prereg/round17` a212b29 (`qa_r17/PREREG_R17.md`), committed 2026-10-19 12:34 MDT before any data.
Master 46a3408, run clone `qa/run_r17`, box only. No CFD. Tools: NeuralFoil 0.3.3 (`xxxlarge`), XFOIL 6.99
(built from MIT source, gfortran, double precision). Data: `docs/qa/r17/r17-A-*.csv`; scripts and raw JSON:
`handoff/2026-10-19_from-qa-17/`.

## Plain-language answer
- At the rung-A decision point (Re 8×10⁴, α 4°) the reference is **CERTAIN** as registered:
  **C_l = 0.855 (band 0.847–0.863), C_d = 0.0201 (0.0199–0.0204)**. NeuralFoil and XFOIL at Ncrit 9 agree to 1.9 % on
  C_l and 2.5 % on C_d.
- The catch is that both tools read **about 8 % high on C_l** against the NASA wind-tunnel E387 at Re 1×10⁵ (α 4°).
  At Re 6×10⁴ every tool misses the measured E387 by 13–20 %, so **at 6×10⁴ the reference is UNUSABLE**.
- NeuralFoil is trained on XFOIL, so their agreement is not two independent checks. The measured E387 anchor is
  the only independent evidence, and it says "about 8 % high at 1×10⁵, unreliable at 6×10⁴".
- Ncrit 5 (a turbulent inflow) leaves C_l almost unchanged at α 4° but cuts C_d by about 25 %. The tools can't
  tell which Ncrit a spinning prop blade sees, so C_d is the weaker half of the reference.

## Section (exact builder coordinates)
`scripts/audit_prop_cfd.py` → `load_uiuc_geometry_blade` (thickness 0.06, camber 0.04, camber_pos 0.4 at every
station) → `build_impeller` → `_section_loop` → `section_loop_2d("naca")` → `airfoil.naca4(0.04, 0.4, 0.06,
n_chord=60)`. LE/TE thickness scales are 1.0, so nothing is changed. This is **NACA 4406 with the closed-TE
coefficient (−0.1036)**. `r17-A-section-naca4406-builder-n60.csv` holds the builder's 118 points (TE → upper → LE →
lower), from fansim's own function. The solvers used the same function at 160 points per surface. NeuralFoil at
60 vs 160 points differs by up to 0.04 in C_l and 4–7 % in C_d (report-only). In 3-D the section is wrapped on its
cylinder; the 2-D shape is unchanged.

## Sanity gate and anchor
- XFOIL gate: NACA 0012 at Re 1×10⁶, α 4°, Ncrit 9 gives C_l 0.428, inside the registered 0.40–0.48. **PASS**.
- Anchor: NASA TM-4062 (McGhee, Walker & Millard 1988, E387, Langley LTPT; US-Gov work, public use permitted).
  Table B1 runs 27–28 (Re 6×10⁴, M 0.05) and runs 15–16 (Re 1×10⁵, M 0.03) are transcribed in
  `r17-A-e387-tm4062-measured.csv`: two passes, at 130 and 260 dpi, with 0 disagreements. The E387 coordinates are
  Table I's design ordinates (`r17-A-e387-tm4062-coords.csv`); the two copies of that table agree exactly.
- Deviation: at Re 6×10⁴ the table has three repeats at exactly α 4.00° (C_l 0.643 / 0.697 / 0.721, the laminar
  bubble switching). I used their mean (0.687, C_d 0.0406), not interpolation.

| tool (E387, α 4°) | Re 6e4: C_l err / C_d err | verdict | Re 1e5: C_l err / C_d err | verdict |
|---|---|---|---|---|
| NeuralFoil Ncrit 9 | +13.3 % / −9.2 % | FAIL | +8.4 % / −9.8 % | PASS |
| NeuralFoil Ncrit 5 | +19.6 % / −44.2 % | FAIL | +7.0 % / −30.4 % | FAIL (C_d) |
| XFOIL Ncrit 9 | +14.2 % / −9.5 % | FAIL | +8.3 % / −9.4 % | PASS |
| XFOIL Ncrit 5 | +19.7 % / −44.2 % | FAIL | +7.0 % / −30.9 % | FAIL (C_d) |

So the credible tools are **Ncrit 9 only, and only for Re 8×10⁴ and 1.2×10⁵** (both use the 1×10⁵ anchor); none
is credible at 6×10⁴.

## NACA 4406 references (credible tools; full table in `r17-A-reference-spread.csv`)
| Re | α 4°: C_l median [band] | C_d median [band] | S_l / S_d | class |
|---|---|---|---|---|
| 6×10⁴ | n/a (all four: 0.734–0.842) | n/a (0.0190–0.0296) | all-tools 13.5 % / 44 % | **UNUSABLE** (no credible tool) |
| **8×10⁴** | **0.855 [0.847, 0.863]** | **0.0201 [0.0199, 0.0204]** | 1.9 % / 2.5 % | **CERTAIN** |
| 1.2×10⁵ | 0.885 [0.884, 0.886] | 0.0138 [0.0136, 0.0139] | 0.2 % / 1.9 % | CERTAIN |

- At 8×10⁴ the class is CERTAIN for α 1–8°, UNCERTAIN at α 0° (C_l 0.212 vs 0.248) and UNUSABLE at α 9–10°, where
  XFOIL Ncrit 9 does not converge. Including the Ncrit-5 tools, the α 4° C_d spread is 26 % (still ≤ 30 %).
- Report-only: C_l slope over α 2–6° is about 0.10 /°. There is a clear laminar-bubble signature: the XFOIL upper
  transition jumps from x/c 0.66 to 0.10 between α 5° and 6° at 8×10⁴, with the matching C_d kink.

## What I propose for rung A (Claude's call; the prop-CFD prereg is not edited)
- Use reference = median of NeuralFoil and XFOIL at Ncrit 9, with band = [min, max]. A1 needs SST ≥ 25 % below the
  band max (0.863 → SST C_l ≤ 0.647). A2 needs SST inside [0.9 × 0.847, 1.1 × 0.863] = [0.762, 0.949].
- Because both tools read about 8 % high on the measured E387 at 1×10⁵, an SST C_l 8–10 % below the reference
  could be correct physics, not a turbulence-model miss. I'd record any A2 or "anything else" result together
  with this anchor bias, and not move the 10 % band after the fact.
- Don't judge rung A at 6×10⁴, and don't judge it on C_d alone (the Ncrit sensitivity is about 25 %).
