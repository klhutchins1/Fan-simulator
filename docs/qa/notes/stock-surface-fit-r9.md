# Stock surface fit (prototype), QA round 9 Task C

Prereg `PREREG_R9.md` §Task C (a0260c0). The shipped recipe is untouched.
- Files are in `docs/qa/stock_fit/`: `surf_lib.py` (the official metric and the V2 check), `fit_surface.py`,
  `fit_log.txt`, `fit_x.json`, `baseline_r9.json`, `proposal_eval.json`.
- **Proposal:** `docs/qa/stock_fit/a12x25_reference_surface_fit_proposal.yaml`.

**Method.**
- Start from v3 (wrapped). The variables are always-on per-station sweep, skew and stagger (stations 1–6) plus a
  camber delta (stations 2–6, ±0.004).
- The objective is a proxy: the distance from 2 500 fixed reference-surface points to 9 copies of one built blade,
  with the loft chords frozen. It was minimised with scipy `least_squares`, 12 iterations, 46 min.
- No extra stations were added.
- The judge is the unchanged `stock_surface_distance` method on a full `build_impeller` build, plus the
  `fit_recipe_to_stl` V2 measurement.

**Baselines re-measured on this box:** planar v2 mean 0.442 mm, outer (r/R 0.8–1.0) 0.210 mm; wrapped v3 0.562 /
0.367 mm. Claude's figures were 0.41 / 0.57; the planar mean is 0.03 higher here.

| target | rule | proposal | |
|---|---|---|---|
| T1 mean distance | ≤ 0.41 mm | **0.358** | PASS |
| T2 outer span | ≤ 0.26 mm | **0.205** | PASS |
| T3 V2 section tolerances | all stations | fails at r/R 0.60 (stagger −1.88°, camber −0.0144) and 0.70 (camber −0.0053) | **FAIL** |

**Verdict: FAIL (2/3).**
- The surface now sits closer to the STL than the planar recipe, both overall and outboard: by band, 0.32/0.20/0.19/
  0.19/0.21 mm from r/R 0.5 to 1.0.
- But the inner stations drifted outside V2. Surface distance and section numbers pull against each other at r/R
  0.6–0.7.
- Next step (proposal): run the same fit with V2 as hard constraints, or penalise V2 residuals in the objective,
  and add stations at r/R 0.55 and 0.65. Don't run CFD on this YAML as a Stock candidate until T3 passes. It is fine
  as a diagnostic, e.g. "does surface closeness move CFD toward planar?".
