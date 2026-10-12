# Built blade vs its numbers: why the cut sections differ from the sliders (QA round 8, Task D; roadmap 27.4)

- **Code:** master `f86df9a`. Prereg `PREREG_R8.md` (`6b0aedf`). Script `handoff/2026-10-12_from-qa-8/scripts/run_d.py`.
  Data `data/d_results.json.gz`.
- **Designs:** Stock (`stock_a12x25_params()`), lt120 (`docs/qa/benchmarks/lt120/fansim_params.json`) and the
  first 5 non-stock rows of `cfd_designs.csv` (stock_thin, t9000, t9002, t9003, t9005). Each was built with
  `chord_basis` "measured" and "loft".
- **Build and measurement:** 2-blade `build_impeller` (disclosed; sections are per blade).
  `measure_sections` cylinder cuts at each station radius r = r0 + (tip − r0)·r_frac, with r0 = hub − root_embed,
  capped at 0.99·tip.
- **Estimator bias:** for each station I read an analytic NACA section with the station's own (m, p, t/c)
  through the same `_measure_loop`. That gives −0.0073…−0.0148 for m 0.04–0.10. At m 0.04 (lt120,
  t/c 0.06–0.18) it gives −0.008…−0.011, i.e. it reads 0.029–0.032. That is a larger bias than round 7's
  0.034–0.038, because the bias depends on t/c and camber position; I used the per-station value. "Net gap" = cut − param − bias.

## 1. Why `chord_basis="loft"` changed nothing on lt120 (with file:line evidence)
- **What the realisation measures, and where.** `chord_realisation.py:34-55` (`_station_measure_fracs`):
  - it measures **every** station radius r = r0 + span·r_frac, not only near the tip;
  - stations within 4.1 mm of the hub are skipped;
  - tip stations are capped at 0.99·tip.
  `measure_station_chords` (`:58-88`) builds **one blade, untrimmed, with no hub and no hub-face clip**
  (`build_blade_solid(..., _chord_realized=True, _trim_tip=False)`, `:71`). It then calls the **same**
  `section_compare.measure_sections` (`:72`). The fixed point is at `:136-172`: 2 iterations, loft × target/measured.
- **How that differs from my measurement.** The cut and the estimator are the same. The difference is the
  part being cut: the realisation cuts a lone, unclipped blade, while the shipped part is the fused impeller,
  where `clip_blade_below` (`blade.py:845-870`, applied at `:886` and `:985`; the QA-16 rule) cuts every
  blade at the hub's motor face.
- **lt120:**
  - The auto-sized hub (`_hub_axial_range`, `blade.py:724-750`) only covers the roots ±1.5 mm.
  - lt120's long, 36–40° staggered outer sections hang 5 mm lower: the blade's zmin is −12.63 mm, the
    impeller's −7.47 mm.
  - The clip removes the trailing part, so the cut chord is 3–16 % short.
  - Because the realisation never sees the clip, it barely stretches lt120's loft (+3 %). It is satisfied
    on the unclipped blade (its own reads: 23.51 / 26.27 / … / 41.63 vs targets 23.6 / 26.2 / … / 41.6).
- **Proof:**
  - lt120 rebuilt with `clip_below_hub=False`: the cut chord is within 0.5 % at every realised station
    (−3.2 % only at the 26.7 mm hub station, which is not realised). Camber net gap ≈ 0.
  - With the clip, the "measured" and "loft" bases both read −3…−17 %, hence "nothing changed".
- **lt120 camber is fine:** net gap ≤ 0.003 at every station. Round 7's "camber low" for lt120 was the
  estimator bias.
→ **QA-30.**

## 2. Measurements (all stations; "realised here" = the realisation measures this station)
| design | basis | r mm | chord/r | realised here | loft chord | chord param → cut (err) | stagger param → cut | camber param → cut (bias; net gap) | t/c param → cut |
|---|---|---|---|---|---|---|---|---|---|
| stock | measured | 19.5 | 0.91 | – | 17.75 | no blade loop (hub) | | | |
| stock | measured | 27.25 | 0.78 | y | 21.3 | 21.3 → 21.3 (-0.0 %) | 39.8 → 38.6 | 0.0412 → 0.0178 (-0.0084; **-0.0150**) | 0.111 → 0.120 |
| stock | measured | 32.7 | 0.71 | y | 23.3 | 23.2 → 23.2 (-0.1 %) | 34.6 → 36.1 | 0.0762 → 0.0321 (-0.0139; **-0.0302**) | 0.102 → 0.111 |
| stock | measured | 38.15 | 0.66 | y | 26.8 | 25.1 → 25.0 (-0.5 %) | 28.7 → 32.0 | 0.0834 → 0.0385 (-0.0139; **-0.0310**) | 0.097 → 0.100 |
| stock | measured | 43.6 | 0.63 | y | 32.3 | 27.6 → 27.5 (-0.5 %) | 21.9 → 26.9 | 0.0947 → 0.0394 (-0.0148; **-0.0405**) | 0.089 → 0.091 |
| stock | measured | 49.05 | 0.62 | y | 40.0 | 30.5 → 30.5 (-0.2 %) | 17.2 → 23.0 | 0.0985 → 0.0353 (-0.0147; **-0.0485**) | 0.081 → 0.083 |
| stock | measured | 53.95 | 0.62 | y | 49.6 | 33.5 → 33.5 (-0.2 %) | 16.3 → 21.8 | 0.0971 → 0.0367 (-0.0139; **-0.0464**) | 0.073 → 0.075 |
| stock | loft | 19.5 | 0.91 | – | 17.75 | no blade loop (hub) | | | |
| stock | loft | 27.25 | 0.78 | y | 21.3 | 21.3 → 21.3 (-0.0 %) | 39.8 → 38.6 | 0.0412 → 0.0178 (-0.0084; **-0.0150**) | 0.111 → 0.120 |
| stock | loft | 32.7 | 0.71 | y | 23.2 | 23.2 → 23.2 (-0.2 %) | 34.6 → 36.1 | 0.0762 → 0.0324 (-0.0139; **-0.0300**) | 0.102 → 0.111 |
| stock | loft | 38.15 | 0.66 | y | 25.1 | 25.1 → 24.0 (-4.6 %) | 28.7 → 32.1 | 0.0834 → 0.0438 (-0.0139; **-0.0257**) | 0.097 → 0.105 |
| stock | loft | 43.6 | 0.63 | y | 27.6 | 27.6 → 24.3 (-11.9 %) | 21.9 → 27.1 | 0.0947 → 0.0528 (-0.0148; **-0.0272**) | 0.089 → 0.103 |
| stock | loft | 49.05 | 0.62 | y | 30.5 | 30.5 → 24.1 (-21.2 %) | 17.2 → 23.7 | 0.0985 → 0.0647 (-0.0147; **-0.0191**) | 0.081 → 0.104 |
| stock | loft | 53.95 | 0.62 | y | 33.5 | 33.5 → 23.5 (-29.8 %) | 16.3 → 23.1 | 0.0971 → 0.0809 (-0.0139; **-0.0023**) | 0.073 → 0.103 |
| lt120 | measured | 23.0 | 0.81 | – | 18.6 | no blade loop (hub) | | | |
| lt120 | measured | 26.7 | 0.79 | n | 21.2 | 21.2 → 20.5 (-3.2 %) | 39.7 → 40.0 | 0.0400 → 0.0300 (-0.0106; **+0.0006**) | 0.180 → 0.187 |
| lt120 | measured | 30.4 | 0.78 | y | 24.5 | 23.6 → 23.5 (-0.5 %) | 39.5 → 39.8 | 0.0400 → 0.0294 (-0.0104; **-0.0001**) | 0.160 → 0.162 |
| lt120 | measured | 34.2 | 0.77 | y | 27.1 | 26.2 → 25.3 (-3.3 %) | 39.3 → 39.3 | 0.0400 → 0.0301 (-0.0093; **-0.0006**) | 0.140 → 0.146 |
| lt120 | measured | 37.9 | 0.76 | y | 29.9 | 28.9 → 27.0 (-6.4 %) | 38.9 → 38.7 | 0.0400 → 0.0300 (-0.0093; **-0.0008**) | 0.120 → 0.129 |
| lt120 | measured | 41.6 | 0.76 | y | 32.7 | 31.6 → 28.7 (-9.0 %) | 38.6 → 38.1 | 0.0400 → 0.0304 (-0.0085; **-0.0011**) | 0.100 → 0.111 |
| lt120 | measured | 45.3 | 0.75 | y | 35.3 | 34.2 → 30.3 (-11.3 %) | 38.2 → 37.6 | 0.0400 → 0.0309 (-0.0083; **-0.0008**) | 0.080 → 0.091 |
| lt120 | measured | 49.1 | 0.75 | y | 37.6 | 36.6 → 31.8 (-13.2 %) | 37.7 → 37.0 | 0.0400 → 0.0306 (-0.0079; **-0.0015**) | 0.060 → 0.072 |
| lt120 | measured | 52.8 | 0.74 | y | 40.4 | 39.1 → 33.3 (-14.8 %) | 37.0 → 36.2 | 0.0400 → 0.0303 (-0.0079; **-0.0018**) | 0.060 → 0.070 |
| lt120 | measured | 56.5 | 0.74 | y | 43.0 | 41.6 → 35.1 (-15.6 %) | 36.0 → 35.3 | 0.0400 → 0.0294 (-0.0079; **-0.0028**) | 0.060 → 0.071 |
| lt120 | loft | 23.0 | 0.81 | – | 18.6 | no blade loop (hub) | | | |
| lt120 | loft | 26.7 | 0.79 | n | 21.2 | 21.2 → 20.5 (-3.2 %) | 39.7 → 40.0 | 0.0400 → 0.0300 (-0.0106; **+0.0007**) | 0.180 → 0.186 |
| lt120 | loft | 30.4 | 0.78 | y | 23.6 | 23.6 → 22.9 (-2.8 %) | 39.5 → 39.8 | 0.0400 → 0.0303 (-0.0104; **+0.0008**) | 0.160 → 0.165 |
| lt120 | loft | 34.2 | 0.77 | y | 26.2 | 26.2 → 24.8 (-5.2 %) | 39.3 → 39.4 | 0.0400 → 0.0310 (-0.0093; **+0.0003**) | 0.140 → 0.148 |
| lt120 | loft | 37.9 | 0.76 | y | 28.9 | 28.9 → 26.5 (-8.4 %) | 38.9 → 38.8 | 0.0400 → 0.0310 (-0.0093; **+0.0003**) | 0.120 → 0.132 |
| lt120 | loft | 41.6 | 0.76 | y | 31.6 | 31.6 → 28.1 (-11.0 %) | 38.6 → 38.2 | 0.0400 → 0.0311 (-0.0085; **-0.0004**) | 0.100 → 0.113 |
| lt120 | loft | 45.3 | 0.75 | y | 34.2 | 34.2 → 29.7 (-13.1 %) | 38.2 → 37.6 | 0.0400 → 0.0318 (-0.0083; **+0.0001**) | 0.080 → 0.093 |
| lt120 | loft | 49.1 | 0.75 | y | 36.6 | 36.6 → 31.2 (-14.7 %) | 37.7 → 37.0 | 0.0400 → 0.0316 (-0.0079; **-0.0005**) | 0.060 → 0.073 |
| lt120 | loft | 52.8 | 0.74 | y | 39.1 | 39.1 → 32.7 (-16.4 %) | 37.0 → 36.3 | 0.0400 → 0.0311 (-0.0079; **-0.0010**) | 0.060 → 0.071 |
| lt120 | loft | 56.5 | 0.74 | y | 41.6 | 41.6 → 34.3 (-17.4 %) | 36.0 → 35.3 | 0.0400 → 0.0305 (-0.0079; **-0.0016**) | 0.060 → 0.072 |
| stock_thin | measured | 19.5 | 0.91 | – | 17.75 | no blade loop (hub) | | | |
| stock_thin | measured | 27.25 | 0.78 | y | 21.4 | 21.3 → 21.3 (-0.0 %) | 39.8 → 38.8 | 0.0412 → 0.0212 (-0.0073; **-0.0127**) | 0.077 → 0.083 |
| stock_thin | measured | 32.7 | 0.71 | y | 23.5 | 23.2 → 23.2 (-0.1 %) | 34.6 → 36.2 | 0.0762 → 0.0360 (-0.0121; **-0.0281**) | 0.071 → 0.075 |
| stock_thin | measured | 38.15 | 0.66 | y | 27.0 | 25.1 → 25.0 (-0.4 %) | 28.7 → 32.0 | 0.0834 → 0.0396 (-0.0126; **-0.0312**) | 0.068 → 0.070 |
| stock_thin | measured | 43.6 | 0.63 | y | 32.5 | 27.6 → 27.5 (-0.4 %) | 21.9 → 26.9 | 0.0947 → 0.0390 (-0.0133; **-0.0424**) | 0.062 → 0.064 |
| stock_thin | measured | 49.05 | 0.62 | y | 40.3 | 30.5 → 30.5 (-0.2 %) | 17.2 → 23.0 | 0.0985 → 0.0352 (-0.0132; **-0.0501**) | 0.057 → 0.058 |
| stock_thin | measured | 53.95 | 0.62 | y | 49.9 | 33.5 → 33.5 (-0.1 %) | 16.3 → 21.9 | 0.0971 → 0.0364 (-0.0125; **-0.0482**) | 0.051 → 0.052 |
| stock_thin | loft | 19.5 | 0.91 | – | 17.75 | no blade loop (hub) | | | |
| stock_thin | loft | 27.25 | 0.78 | y | 21.3 | 21.3 → 21.2 (-0.3 %) | 39.8 → 38.8 | 0.0412 → 0.0213 (-0.0073; **-0.0125**) | 0.077 → 0.083 |
| stock_thin | loft | 32.7 | 0.71 | y | 23.2 | 23.2 → 23.0 (-0.9 %) | 34.6 → 36.3 | 0.0762 → 0.0374 (-0.0121; **-0.0267**) | 0.071 → 0.076 |
| stock_thin | loft | 38.15 | 0.66 | y | 25.1 | 25.1 → 23.8 (-5.4 %) | 28.7 → 32.1 | 0.0834 → 0.0448 (-0.0126; **-0.0260**) | 0.068 → 0.074 |
| stock_thin | loft | 43.6 | 0.63 | y | 27.6 | 27.6 → 24.1 (-12.6 %) | 21.9 → 27.1 | 0.0947 → 0.0537 (-0.0133; **-0.0278**) | 0.062 → 0.073 |
| stock_thin | loft | 49.05 | 0.62 | y | 30.5 | 30.5 → 23.9 (-21.8 %) | 17.2 → 23.7 | 0.0985 → 0.0652 (-0.0132; **-0.0201**) | 0.057 → 0.073 |
| stock_thin | loft | 53.95 | 0.62 | y | 33.5 | 33.5 → 23.3 (-30.4 %) | 16.3 → 23.1 | 0.0971 → 0.0821 (-0.0125; **-0.0026**) | 0.051 → 0.072 |
| t9000 | measured | 19.5 | 1.74 | – | 34.0 | no blade loop (hub) | | | |
| t9000 | measured | 36.92 | 1.19 | y | 45.8 | 44.0 → 43.9 (-0.2 %) | 26.0 → 26.5 | 0.0600 → 0.0401 (-0.0104; **-0.0095**) | 0.050 → 0.050 |
| t9000 | measured | 53.81 | 0.71 | y | 35.7 | 38.0 → 38.2 (+0.4 %) | 22.0 → 23.3 | 0.0600 → 0.0409 (-0.0090; **-0.0101**) | 0.030 → 0.031 |
| t9000 | loft | 19.5 | 1.74 | – | 34.0 | no blade loop (hub) | | | |
| t9000 | loft | 36.92 | 1.19 | y | 44.0 | 44.0 → 42.7 (-3.0 %) | 26.0 → 26.5 | 0.0600 → 0.0415 (-0.0104; **-0.0081**) | 0.050 → 0.052 |
| t9000 | loft | 53.81 | 0.71 | y | 38.0 | 38.0 → 39.9 (+5.0 %) | 22.0 → 23.3 | 0.0600 → 0.0378 (-0.0090; **-0.0132**) | 0.030 → 0.029 |
| t9002 | measured | 19.5 | 0.95 | – | 18.5 | no blade loop (hub) | | | |
| t9002 | measured | 36.92 | 0.72 | y | 27.3 | 26.5 → 26.5 (-0.1 %) | 26.0 → 26.7 | 0.0600 → 0.0433 (-0.0104; **-0.0063**) | 0.050 → 0.049 |
| t9002 | measured | 53.81 | 0.71 | y | 41.2 | 38.0 → 37.9 (-0.2 %) | 22.0 → 24.0 | 0.0600 → 0.0327 (-0.0090; **-0.0183**) | 0.030 → 0.030 |
| t9002 | loft | 19.5 | 0.95 | – | 18.5 | no blade loop (hub) | | | |
| t9002 | loft | 36.92 | 0.72 | y | 26.5 | 26.5 → 25.8 (-2.6 %) | 26.0 → 26.7 | 0.0600 → 0.0450 (-0.0104; **-0.0047**) | 0.050 → 0.051 |
| t9002 | loft | 53.81 | 0.71 | y | 38.0 | 38.0 → 35.5 (-6.5 %) | 22.0 → 24.0 | 0.0600 → 0.0372 (-0.0090; **-0.0138**) | 0.030 → 0.032 |
| t9003 | measured | 19.5 | 0.92 | – | 18.0 | no blade loop (hub) | | | |
| t9003 | measured | 36.92 | 0.68 | y | 25.4 | 25.0 → 25.0 (-0.0 %) | 30.0 → 31.2 | 0.0600 → 0.0395 (-0.0104; **-0.0101**) | 0.050 → 0.050 |
| t9003 | measured | 53.81 | 0.71 | y | 42.7 | 38.0 → 37.8 (-0.4 %) | 22.0 → 24.7 | 0.0600 → 0.0274 (-0.0090; **-0.0235**) | 0.030 → 0.031 |
| t9003 | loft | 19.5 | 0.92 | – | 18.0 | no blade loop (hub) | | | |
| t9003 | loft | 36.92 | 0.68 | y | 25.0 | 25.0 → 24.6 (-1.6 %) | 30.0 → 31.2 | 0.0600 → 0.0403 (-0.0104; **-0.0093**) | 0.050 → 0.051 |
| t9003 | loft | 53.81 | 0.71 | y | 38.0 | 38.0 → 34.3 (-9.6 %) | 22.0 → 24.8 | 0.0600 → 0.0339 (-0.0090; **-0.0170**) | 0.030 → 0.033 |
| t9005 | measured | 19.5 | 0.92 | – | 18.0 | no blade loop (hub) | | | |
| t9005 | measured | 37.0 | 0.68 | y | 29.3 | 25.0 → 24.9 (-0.2 %) | 30.0 → 34.2 | 0.0600 → 0.0229 (-0.0109; **-0.0263**) | 0.058 → 0.063 |
| t9005 | measured | 53.95 | 0.70 | y | 58.2 | 38.0 → 38.0 (-0.1 %) | 22.0 → 30.2 | 0.0600 → 0.0075 (-0.0096; **-0.0430**) | 0.038 → 0.042 |
| t9005 | loft | 19.5 | 0.92 | – | 18.0 | no blade loop (hub) | | | |
| t9005 | loft | 37.0 | 0.68 | y | 25.0 | 25.0 → 21.7 (-13.3 %) | 30.0 → 34.5 | 0.0600 → 0.0325 (-0.0109; **-0.0166**) | 0.058 → 0.073 |
| t9005 | loft | 53.95 | 0.70 | y | 38.0 | 38.0 → 25.6 (-32.8 %) | 22.0 → 32.2 | 0.0600 → 0.0284 (-0.0096; **-0.0221**) | 0.038 → 0.061 |

## 3. Gap vs chord/r: the planar-section explanation is not supported
- **Chord.** With the "measured" basis, the chord is right (≤ 0.5 %) at every realised station of every
  design except lt120, whose chord loss is the hub clip. With the "loft" basis, Stock and stock_thin lose
  5–30 % from mid-span outward, at chord/r 0.62–0.66.
  - The loss grows **outward while chord/r falls** (0.78 → 0.62).
  - lt120, at higher chord/r (0.74–0.79), loses nothing once unclipped.
- **Camber**, measured basis, net of bias, at chord/r ≥ 0.4:
  - Stock: −0.015 … −0.049;
  - stock_thin: −0.013 … −0.050;
  - t9000: −0.010; t9002: −0.006 … −0.018; t9003: −0.010 … −0.024; t9005: −0.026 … **−0.043** (tip reads
    0.0075 for a slider 0.06);
  - lt120: ≤ 0.003.
  - Correlation of the net camber gap with chord/r over these stations is +0.55. That is the wrong sign for
    "the gap grows with chord/r".
- **What does track the gap: circumferential stacking (lean and skew).**
  - lt120 has none and shows no gap.
  - In the cfd rows, the gap grows with tip skew: t9000 skew 0 → −0.010, t9002 2 mm → −0.018, t9003 4.5 mm
    → −0.024, t9005 20 mm → −0.043. All four have the same lean (0/14/26°).
  - Diagnostic (post hoc, not registered): Stock with the loft basis and no clip. Each cell gives chord error
    / cut camber (param camber 0.041 … 0.097):

| Stock variant | r 27 | r 33 | r 38 | r 44 | r 49 | r 54 |
|---|---|---|---|---|---|---|
| as is | −0 % / 0.021 | −0 % / 0.038 | −5 % / 0.044 | −12 % / 0.053 | −21 % / 0.065 | −30 % / 0.081 |
| lean = 0 | −1 % / 0.033 | +0 % / 0.053 | −2 % / 0.060 | −5 % / 0.068 | −9 % / 0.078 | −13 % / 0.089 |
| sweep = 0 | +0 % / 0.023 | −0 % / 0.037 | −5 % / 0.042 | −12 % / 0.048 | −21 % / 0.057 | −29 % / 0.070 |
| lean = skew = sweep = 0 | −1 % / 0.037 | +0 % / 0.066 | +0 % / 0.073 | −0 % / 0.084 | −1 % / 0.087 | −2 % / 0.086 |

  With no lean, skew or sweep, Stock's cut matches its numbers (chord ≤ 2 %; camber 0.086 vs 0.097 with
  bias −0.014, so net ≈ +0.003) at the same chord/r. So the gap comes from how the planar sections are stacked
  around the axis, not from chord/r.
- **The "measured" basis then makes camber worse.** It restores chord by stretching the loft chord (Stock
  tip 33.5 → 49.6 mm, t9005 tip 38 → 58 mm). The cylinder cut then keeps only the middle of a longer
  section, whose camber ratio is much lower. Stock tip: loft basis net −0.002, measured basis net −0.046.
→ **QA-31.**

## 4. Pre-registered rule
"Material if, at any station with chord/r ≥ 0.4, chord differs by > 3 % or camber by > 0.005 beyond the bias."
- **"measured" basis (the default):** chord fails on lt120 (up to −15.6 %); camber fails on Stock, stock_thin,
  t9000, t9002, t9003 and t9005.
- **"loft" basis:** chord fails on all 7, camber on 6.

**MATERIAL.** BEM computes on the slider numbers, so on leaned/skewed designs BEM scores a blade with
up to ~3.5× the camber the CFD mesh actually has at the outer stations (t9005 tip: slider 0.06, bias-corrected cut ≈ 0.017; Stock tip 0.097 vs ≈ 0.051).

## 5. Recommendation (no patch)
- **(iii) Give BEM the measured built sections. Do this first.**
  - It is cheap: one cylinder-cut pass per design, and the chord realisation already builds the blade.
  - It makes BEM and CFD score the same blade whatever the builder does, and it covers the hub-clip loss
    (QA-30) if the measurement uses the clipped part.
  - **Stock:** its geometry is unchanged (the recipe was fitted to the real STL through these same cuts).
    Its BEM input camber drops from ~0.08–0.10 to the cut ~0.05 (bias-corrected), so its BEM score moves.
    Any BEM↔CFD calibration done on Stock needs re-checking, and every catalogue score shifts.
- **(ii) Extend the realisation to all radii and to camber.**
  - "All radii" is already true (§1). The missing pieces are the **clip** (measure the clipped part, or
    clip before measuring) and **camber**.
  - A camber fixed point would raise the loft camber until the cut camber matches. That needs more builds,
    and with lean/skew it may not converge or may fight the chord stretch.
  - **Stock:** its station numbers are recipe values, not cut targets. Under (ii) they would have to be
    replaced by its measured cut values to keep the same blade, or Stock changes shape.
- **(i) Wrap the sections onto cylinders in the builder.**
  - This is the principled fix: a cylinder cut at a station radius then returns the designed section by
    construction, and neither the chord stretch nor the camber loss is needed.
  - It is the largest change: every existing design's geometry changes, and **Stock's recipe must be
    refitted** (its numbers were fitted to the real STL through planar sections). The hub clip still needs (ii)-style handling.
- **Suggested order:** (iii) now, for scoring consistency. Then decide (i) vs (ii) with a CFD A/B on one
  leaned design (for example t9005), as 27.4 intends.
