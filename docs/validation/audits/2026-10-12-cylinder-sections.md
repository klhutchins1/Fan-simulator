# Blade sections wrapped onto cylinders: checks V1–V6 (roadmap 27.4 option i, 2026-10-12)

Spec, with the checks fixed before any wrapped build:
`docs/superpowers/specs/2026-10-12-cylinder-sections-design.md`.
Scripts: `scripts/cylinder_sections_checks.py` (V1, V3, V4) and `scripts/cylinder_sections_cfd.py`
(V5, V6). Raw results: `data/2026-10-12-cylinder-sections-checks.json`.

## Plain-language summary

- **The wrap does what it should.** Where the hub-face cut doesn't touch the blade, the built blade
  measures back to its sliders on every design tested: camber within 0.001 and blade angle within
  0.1° (Stock, t9005, t9003, lt120 and four leaned stress designs). Before the change, Stock's camber
  read 0.036–0.040 for sliders of 0.08–0.10.
- **Stock still matches the real fan (V2 PASS).** The re-fitted recipe matches the A12x25 STL within the
  fit's tolerances. Its sliders now say camber ~0.045 instead of 0.08–0.10, and the blade-angle sliders
  moved by up to 6° at the tip. The old numbers were compensating for the planar sections.
- **V1 FAILS as registered, entirely because of the hub-face cut.** Every failing station is on a blade
  that hangs below the hub's motor face, where the build cuts it off (QA-16 rule). That cut is a real
  constraint of the printed part, not a wrap error. With the cut switched off, every station passes
  (diagnostic, post hoc).
- **Builds are sound (V3).** 20 of 20 designs build watertight in one piece, with volumes within 1.2 % of
  the planar build. The 3 "fails" are ringed fans whose ring reaches tip + ring thickness. The planar
  build does exactly the same, so my rule left out the ring; that is not a defect.
- **The direction check now reads leaned blades correctly (V4 PASS).** 0 wrong on 30 parts; 20
  CONCLUSIVE, all correct. **S3_0014, the round-7/8 false refusal (27.2), now reads correctly.** The 7
  older flat-leaned cases now read "can't tell" instead of "backwards", which is right for blades with
  camber below 0.02.

## Two builder bugs found and fixed during the checks

1. **Folded loft, lost hub (S4_0001).** The first version closed each wrapped loft with a *planar* end
   wire. On wide-root blades, that wire's ends stood out past the next wrapped wire (r 27.4 vs 25.2 mm),
   so the loft folded. OCCT then returned nothing for every boolean, and the "impeller" was a single
   blade: 1,190 mm³ vs 76,518 planar.
   - **Fix:** loft an open shell through the wrapped wires and close each end with a ruled face between
     the section's two halves (`_capped_loft`).
   - Regression test: `test_wrapped_impeller_keeps_its_hub_and_blades`. It fails on the old code with
     1,190 vs 76,518.
   - My V3 check passed S4_0001 in the first run, because "watertight, one body" also holds for a lone
     blade. **Declared addition:** V3 now also requires the volume to be within 5 % of the planar build.
2. **15× slower fuse (the 7-hour "hang", S6_0001).** A smooth loft made 18-pole B-spline faces. Where
   neighbouring blades overlap inside the hub, the fuse went from about 20 s to about 300–450 s.
   - **Fix:** a *ruled* loft, which gives bilinear patches like the planar loft's.
   - S4_0001 now builds in 26 s (planar 24 s) and S6_0001 in 46 s (planar 42 s).

Also: lofts through wrapped wires can come out inside-out, so the loft is flipped when its volume is
negative (the QA-21 design's tip trim had been empty at every radius). And the last wrapped wire sits
0.5 mm outside the tip, so the trim crosses the blade rather than running along a wire.

## Results

### V1: built blade = sliders (FAIL as registered; the cause is the hub-face cut)

Chord within 3 % of the slider; camber within 0.005 and stagger within 1.5° of the same section read
analytically through the same estimator (built 2-blade).

| design | stations | worst chord | worst camber | worst stagger | verdict |
|---|---|---|---|---|---|
| Stock (refit) | 6 | 0.0 % | −0.0057 (r 27.2) | −0.47° | 1 FAIL |
| t9005 | 2 | −2.0 % | 0.0000 | +0.33° | PASS |
| t9003 | 2 | −1.7 % | +0.0003 | +0.37° | PASS |
| lt120 | 8 | −1.8 % | −0.0083 (r 56.5) | −1.54° | 5 FAIL (r ≥ 41.6) |
| CTL_0000 | 6 | 0.0 % | −0.0060 (r 27.2) | −0.58° | 1 FAIL |
| CTL_0002, CTL_0003, S5_0001 (featured) | 2 each | 0.1 % | 0.0002 | +0.80° | PASS |

**Diagnostic (post hoc, not a re-score):** with `clip_below_hub=False`, Stock passes at every station
(worst camber −0.0009, stagger −0.09°), and so does lt120 (worst camber −0.0006, stagger +0.06°).
- Stock's trailing corner hangs 0.94 mm below the hub face (QA-16), which touches the innermost station.
- lt120's outer sections hang 5 mm below.
- The QA-30 chord realisation (measure the *clipped* blade) keeps lt120's chord within 1.8 %. But the
  cut still removes the trailing part, so camber and stagger shift. No stretch can restore a section
  the cut removes.

**Consequence:** on blades that hang below the hub face, the sliders still overstate the built blade
near the cut. That is now the only remaining slider-vs-built gap. The flow-side fix belongs with the
hub-face rule, or with BEM using the built sections (option iii). It goes on the roadmap.

### V2: Stock still the real fan (PASS)

`scripts/fit_recipe_to_stl.py --wrap cylinder`, starting from the planar v2 recipe, converged in 3
iterations. Max |built − reference| at the measurable stations (r/R 0.50–0.99): stagger 0.44°, chord
0.2 %, camber 0.0049, t/c 0.6 %. Tolerances are 1.5°, 3 %, 0.005 and 10 %. Re-running the fit on the
fixed builder gave the same recipe. Log: `docs/validation/recipe_fidelity/fit_log_v3_cylinder.txt`.

| r/R | stagger v2 (planar) → v3 | camber v2 → v3 |
|---|---|---|
| 0.50 | 39.8 → 39.7 | 0.041 → 0.032 |
| 0.60 | 34.6 → 36.1 | 0.076 → 0.048 |
| 0.70 | 28.7 → 31.2 | 0.083 → 0.048 |
| 0.80 | 21.9 → 26.3 | 0.095 → 0.045 |
| 0.90 | 17.2 → 22.8 | 0.099 → 0.042 |
| 1.00 | 16.3 → 22.5 | 0.097 → 0.045 |

### V3: it still builds (all 20 sound; 3 ring "fails" are a rule error)

20 stress designs (2 per stratum S1–S8, plus a shroud, a featured design and two fillers), full blade
count:
- all watertight, one body, nothing below the hub face;
- volume within 1.2 % of the planar build (max +1.1 %, S3_0000);
- build times 41–203 s.

S7_0000, S7_0001 and S7_0002 have a 1.6 mm tip ring, and their rmax is 58.1 = tip 56.5 + 1.6. The planar
build reaches the same 58.1. The pre-registered "inside the tip radius" rule should have read "inside
tip + ring". **Correction to the rule, not a re-score.** Not covered: no notched-tip or winglet design
was in the sample (the stress inputs have none).

### V4: direction proof on wrapped rebuilds (PASS)

30 parts:
- 9605, 9606, 9620 and 9630;
- S3_0002, S4_0005, S4_0012 and S3_0014;
- the 22 S3-cell parts from QA round 8.

Result: 0 CONCLUSIVE-wrong. 20 CONCLUSIVE, all (ω +1, pump −1, χ −1). 10 INCONCLUSIVE: the 7 flat
(camber < 0.02) earlier false refusals, plus S4_0065, S8_0102 and S1_0304.

### V5: same real fan, same airflow (FAIL)

Full Assess CFD, same settings as the Stock reference run (a12x25, hose "case", 8 procs, base cell
6 mm, 500 iterations). Raw CFD values at 2000 rpm, before any motor derate.

| | free-air CFM | loaded CFM |
|---|---|---|
| Stock v2 planar (`runs/screen_rank_audit/stock_hubclip/full`) | 54.63 | 41.88 |
| Stock v3 wrapped (`runs/cyl_sections/stock_wrap/full`) | 59.32 | 45.02 |
| difference (pass band) | **+8.6 %** (±3 %) | **+7.5 %** (±5 %) |

**As the spec requires, Stock keeps the planar recipe and wrapping stays opt-in until this is
understood.** Both recipes match the same STL's cylinder sections within the fit tolerance (V2), yet they
differ by 8 % in CFD. So "matches the sections" doesn't pin down the shape well enough, or one of the two
lofts differs from the STL somewhere the six measured radii don't see. That could be between stations,
near the hub, at the LE/TE, or in the LE positions, which were off by up to 1.5 mm axially at r/R 0.50 in
both fits.

**Geometry diagnosis (post hoc, `scripts/stock_surface_distance.py`).** 6 000 points sampled on each
recipe's built blades, aligned to the real STL by rotation and axial shift, then measured as distance to the
STL surface:

| distance to the real STL | mean | 95th pct | r/R 0.4–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | 0.9–1.0 |
|---|---|---|---|---|---|---|---|---|
| planar v2 | 0.41 mm | 1.71 | 1.27 | 0.59 | 0.35 | 0.19 | 0.18 | 0.26 |
| wrapped v3 | 0.57 mm | 1.39 | 1.33 | 0.74 | 0.34 | 0.29 | 0.49 | 0.52 |

So matching five summary numbers per section at six radii does not pin the surface down. The wrapped
refit is about 0.3 mm further from the real blade on the outer 20 % of the span, where most of the work is
done. That fits its extra flow. **Next:** fit the wrapped recipe to the surface (or add LE/TE position to
the fit) rather than to the section summaries alone.

**Airflow diagnosis in progress (not a re-score):** the real STL, the planar recipe and the wrapped recipe, all at
free air in the validation rig with identical current settings (`runs/cyl_sections/v5_diag/`). The recipe
closer to the STL's CFD is the more faithful one.

### V6: BEM vs CFD on t9005 (report only)

BEM works on the sliders, so it gives the same answer for both builds: Euler free 62.4 / load 52.2 CFM,
axial-force free 66.2. CFD raw at 2000 rpm:

| t9005 | free | loaded | BEM Euler error, free / loaded |
|---|---|---|---|
| planar build (camber built ~0.008 at the tip for a 0.06 slider) | 74.02 | 59.47 | −16 % / −12 % |
| wrapped build (camber 0.06 as the slider says) | 66.77 | 54.56 | −7 % / −4 % |

- **BEM and CFD now agree much better** on this leaned design, because they finally describe the same
  blade.
- The wrapped t9005 moves **less** air than the planar one. The optimizer found t9005 as a *built*
  low-camber blade; under the new meaning its sliders describe a different, more cambered blade. The
  optimizer's designs need re-finding with the new builder, and its camber bounds re-thinking.
