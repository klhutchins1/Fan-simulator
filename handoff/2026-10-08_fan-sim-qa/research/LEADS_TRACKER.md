# Fan Simulator — Research Leads Tracker

Maintained by Fan Sim QA. Leads come mostly from the arxiv research bot's weekly "Fansim integration scout" (license-checked for an MIT release).
Status values: new, investigating, worth-it/proposed, adopted, not-worth-it, blocked. Never delete not-worth-it rows.
Notes live in `notes/<slug>.md`.

| Lead | Source | Date | Status | Verdict (plain language) | Notes |
|---|---|---|---|---|---|
| Rotor–strut tone + blade/strut-count rule (Huang; Tyler & Sofrin) | INTEGRATION_LEADS.md #1 | 2026-10-08 | new | Predicts which blade/strut counts let the loud strut whine through; math only, patents expired. Effort S–M. | |
| ECMA-418-1 tonality metrics + MoSQITo | INTEGRATION_LEADS.md #2 | 2026-10-08 | new | Industry-standard "how annoying is the whine" scores to replace the homemade one; Apache-2.0, pin version. Effort S. | |
| NASA BPM blade self-noise model (RP-1218) | INTEGRATION_LEADS.md #3 | 2026-10-08 | new | Fast broadband hiss estimate from the BEM numbers, for ranking designs. Public domain / Apache / MIT references. Effort M. | |
| Uneven-spacing classics + live-patent map | INTEGRATION_LEADS.md #4 | 2026-10-08 | new | Benchmark for the spacing tool; avoid Bosch US10480527B2 and Champ Tech US11635088B1 (live). Not legal advice. Effort S. | |
| Optuna 5 GPSampler | INTEGRATION_LEADS.md #5 | 2026-10-08 | new | Already installed; may need fewer CFD runs than NSGA-II. MIT. Needs benchmark. Effort S. | |
| Carter's rule deviation to replace SLIP = 0.71 | INTEGRATION_LEADS.md #6 | 2026-10-08 | blocked | Makes the loss depend on blade spacing. That reshuffles the ranking (19 of the top 30 change, 331 designs beat Stock) and lowers Stock free to 56.3 CFM, but it also flatters the paddle. It needs his CFD-scored designs (Audit #4) to prove it ranks better. Effort S–M. | [notes](notes/carter-deviation.md) |
| AcousticAnalogies.jl (NASA) moving-surface noise reference | INTEGRATION_LEADS.md #7 | 2026-10-08 | new | Full moving-blade noise reference; Apache-2.0. | |
| Koch 1981 stall pressure-rise limit | INTEGRATION_LEADS.md #8 | 2026-10-08 | worth-it/proposed | Caps the pressure the fan can make before it stalls. Stock shut-off goes from 38.9 to 22.9 Pa once tuned (13.7 Pa untuned); free CFM and design ranking don't change. Paper is paywalled, so the curve is approximate. Effort S. Patch: [koch-stall-cap.diff](patches/koch-stall-cap.diff) | [notes](notes/koch-stall-cap.md) |
| Balla & Vad 2021 cambered-plate lift/drag | INTEGRATION_LEADS.md #9 | 2026-10-08 | not-worth-it | Only fitted for 2–4× faster air and 0–10° angles, and only Stock uses plate blades. It moves Stock away from the real numbers (free 58.2 → 51.1 CFM, shut-off 38.9 → 40.1 Pa) and doesn't stop the paddle. Revisit with a low-Re plate polar. | [notes](notes/balla-vad-plate-polar.md) |
| DuctAPE.jl ducted-rotor solver | INTEGRATION_LEADS.md #10 | 2026-10-08 | new | MIT re-take on DFDC for rotors in a duct. | |
| CCBlade guaranteed-convergence BEM solve (Ning) | INTEGRATION_LEADS.md #11 | 2026-10-08 | not-worth-it | The current solver already converges: 0 of 6596 fan designs failed, 1 of 120 prop runs failed, and the new solver gives identical answers 3× slower. Revisit if prop sweeps start failing. | [notes](notes/ning-ccblade-solve.md) |
| Blade axial-force pressure accounting (QA-derived) | QA 2026-10-08 (from leads #8/#9 work) | 2026-10-08 | new | The real cause of the paddle/reversed-blade exploit: the BEM counts churned air as pressure. Computing pressure from the blades' axial push kills both exploits (paddle 62.5 → 8 CFM; reversed blade gives negative pressure) but needs re-tuning (Stock shut-off falls to 5 Pa). Effort M. | [notes](notes/axial-force-pressure-accounting.md) |
