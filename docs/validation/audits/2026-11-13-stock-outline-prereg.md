# Stock outline must follow the Noctua before the next print (2026-11-13)

Written before the build it judges. Kimball, 2026-11-13: do not print AVD9=. Overlaid on the
Noctua impeller, the blade hooks as it leaves the hub and the tips do not line up. He remembers
an earlier recipe sitting closer. That is already measured, and this run does not re-open it.

| build | mean distance | outer r/R 0.8–1.0 | r/R 0.4–0.5 |
|---|---|---|---|
| planar v2 (2026-10-12 / QA r9) | 0.41 mm (r9 box: 0.442) | 0.21 mm | 1.27 mm |
| wrapped v3, the current Stock and AVD9= | 0.57 mm (r9 box: 0.562) | 0.37–0.52 mm | 1.33 mm |

The r9 surface-fit proposal reached 0.358 / 0.205 mm and still left the hub band at 1.37 mm. It
failed the section tolerances at r/R 0.60 and 0.70, so it was not shipped. This run does not
loosen those tolerances and does not start from that proposal.

Wrapped v3 is closer in airflow (55.7 vs 54.5 CFM against the real STL at 58.3). That is why it
became Stock. It is further from the real surface, which is what the overlay shows. No CFD in
this run.

## What this run changes

Start from `config/problems/a12x25_reference.yaml` (wrapped v3). Do not edit that file.

Leading-edge residuals already recorded in
`docs/validation/recipe_fidelity/fit_log_v3_cylinder.txt`, iteration 3, built minus reference
(`dLEz`, `dLEs` mm) at r/R 0.50, 0.60, 0.70, 0.80, 0.90, 0.99:

`(+1.46, −0.13), (+0.94, −0.36), (+0.23, −0.28), (−0.24, −0.12), (−0.39, +0.35), (+0.19, +0.99)`

1. On the six measured stations, `sweep -= dLEz` and `skew -= dLEs`.
2. Set the root station's stagger, sweep and skew by linear extrapolation in `r_frac` from the
   first two measured stations **after** that move. Chord, thickness, camber and lean stay at
   the v3 values. `section_wrap` stays `cylinder`. The loft code is not touched.
3. Build. If `v2_check` fails, do step 1 at half those deltas, extrapolate the root again, and
   build once more. No third try.
4. Also export a planar v2 STL for the overlay. It is the earlier closer surface. It is not a
   candidate and it is not judged.

## Pass (all four)

Judged by `docs/qa/stock_fit/surf_lib.py`: `official_distance` (6000 points, seed 1, the same
alignment as `scripts/stock_surface_distance.py`) and `v2_check` (stagger 1.5°, chord 3%,
camber 0.005, thickness 10% at r/R 0.50, 0.60, 0.70, 0.80, 0.90, 0.99).

| id | rule |
|---|---|
| O1 | mean distance ≤ 0.41 mm |
| O2 | outer r/R 0.8–1.0 ≤ 0.26 mm |
| O3 | r/R 0.4–0.5 ≤ 0.70 mm |
| O4 | `v2_check` true at every measured station |

Fail any one: do not replace Stock. Record the numbers below. Do not run another candidate
under this pre-registration.

## Results (filled after the run; do not edit anything above)

Ran `scripts/outline_match.py` once, full leading-edge step. `v2_check` passed on that build, so the half step was not used. Stock YAML was not changed.

| id | rule | result |
|---|---|---|
| O1 | mean ≤ 0.41 mm | **0.332** PASS |
| O2 | outer ≤ 0.26 mm | **0.228** PASS |
| O3 | r/R 0.4–0.5 ≤ 0.70 mm | **1.102** FAIL |
| O4 | section tolerances | PASS (largest stagger −0.44°, camber 0.0050 at r/R 0.90) |

**Verdict: FAIL.** From r/R 0.5 to the tip the surface is 0.21–0.27 mm from the Noctua. The miss that remains is the hub band, down from 1.33 mm but still over the line. No second candidate under this pre-registration.

STLs: `runs/outline_match/candidate_full.stl` and `planar_v2.stl`. Copied for overlay to `T:\Projects\Fan Simulator\exports\outline_candidate_20261113.stl` and `outline_planar_v2_20261113.stl`.
