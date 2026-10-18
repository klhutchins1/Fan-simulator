# Round 14, Task C (board R1.3 / roadmap 27.7): optimizer space under wrap. Proposal only

Prereg 586bbe9 (C1–C4). Sample: 300 × `suggest_params`, optuna RandomSampler(seed 14003) (= NSGA-II's first
generation), the cockpit's settings: space "guided", hub range (20.725, 30), max tip 54.5 mm, no features/shroud.
Scripts `c_space.py`, `c3_build.py`, `c3_analyse.py`, `c3_tip_basis.py` → `data/c_space.json`, `c_sample.jsonl`,
`c3_build.jsonl`, `c3_analysis.json`, `c3_tip_basis.json`.

## C1 slider distributions vs Stock v3 (report)
- Guided bounds: stagger root 24–48°, mid 32–48°, tip 18–38°, camber 0–0.06.
- Stock v3: camber 0.0235–0.0478, stagger root 23.52° / mid 31.20° / tip 22.46°.
- **The guided space cannot reach Stock's root or mid stagger.** Its lower bounds (24 / 32°) sit above Stock
  (23.5 / 31.2°), so 0 % of designs are at or below Stock there. Medians: root 35.4°, mid 39.6°, tip 28.2°.
- Only **43.7 %** of cambers fall inside Stock's 0.024–0.048 range (uniform 0–0.06).

## C2 hang refusals (report)
- **10/300 = 3.3 %** refused by the 2 mm hang limit (Wilson 95 % 1.8–6.0 %), 0 other refusals.
- Drivers by Mann–Whitney AUC (refused vs allowed): sweep_tip 0.20 (low sweep → refused), chord_tip 0.78,
  chord_root 0.24. Stagger is not a top driver.
- Open space, same seed: 18/300 = 6.0 % (3.8–9.3 %).

## C3 built sections vs sliders (rule): FAIL 3/80 as registered, basis issue
- 40 allowed designs, 2-blade `build_impeller`, `measure_sections` at `_station_measure_fracs`. 40/40 built,
  80/80 stations readable. The hub station is not measured, because `_station_measure_fracs` puts it inside the hub cup.
- Max |error|: chord 2.1 %, net camber 0.0020, stagger **2.15°**.
- 3 tip stations exceed 1.5° (1.58 / 1.68 / 2.15°). The tip station reads **+0.96° on average** (sd 0.41); the mid
  station reads +0.07°.
- Report-only explanation: the code measures the tip at 0.99 R (r_frac 0.977–0.984), but the rule compares with
  the r_frac 1.0 slider. Against the design stagger linearly interpolated mid→tip at the measuring radius, the tip
  error is +0.55° mean, max 1.17°, **0 over 1.5°**.
- The remaining +0.5° tracks camber (r = 0.47), consistent with my estimator's stagger bias (B4c: +0.18° at camber
  0.04, uncorrected).
- No new QA item. Doc note: report tip stagger against the value at the measuring radius.

## C4 proposal: P0 passes at step 0
P0 = guided with camber [0.015, 0.06], stagger_root [19.5, 48], stagger_mid [27.2, 48], stagger_tip [18, 38]
(each lower bound = min(current, Stock − 4°)). On 300 fresh designs (seed 14004): refused **4.3 %** (Wilson
2.5–7.3 %) ≤ 5 %, so no ladder steps were needed. Top drivers are still sweep_tip / chord_root / chord_tip. The
Wilson upper bound is above 5 %. If Kimball wants the *upper* bound under 5 %, the lever is sweep_tip's lower
bound (the hang driver), not stagger. Not tested, proposal only.
