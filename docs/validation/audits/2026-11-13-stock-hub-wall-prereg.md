# Hub wall to the Noctua, blade stations held (2026-11-13)

Written before the build it judges. The outline attempt
(`2026-11-13-stock-outline-prereg.md`) failed O3 only: mean 0.332 mm, outer 0.228 mm,
hub band 1.102 mm, section tolerances held. That pre-registration is closed. This one
does not change its thresholds and does not edit Stock.

## What was measured first

On the candidate STL and `validation/reference/a12x25_impeller.stl`, cylinder cuts at
tip 54.5 mm find a blade on the candidate at r/R 0.42 and no blade on the Noctua until
r/R 0.48. From 0.48 out, the leading edge of the candidate tracks the Noctua (the angle
offset is constant to about 0.3°). Inboard of that, reference vertices at r 22–25.5 mm
sit on the hub faces only. The first full-circle ring at mid-height is r 25.75–26.0 mm.
Our hub radius is 21.5 mm, so the model draws an airfoil where the Noctua is hub.

The reference mesh also reaches r 55.25 mm. Our tip stays 54.5 mm (the frame clearance).
This run does not move the tip.

## What this run changes

Start from the outline candidate (the full leading-edge step in `scripts/outline_match.py`).
Keep every station. Keep the absolute root radius `hub_radius - root_embed` at 19.5 mm,
so the blade sections stay where they are.

1. `hub_radius` 26.0 mm, `root_embed` 6.5 mm. Build and judge.
2. If the outer distance exceeds 0.26 mm or `v2_check` fails, one retry:
   `hub_radius` 25.5 mm, `root_embed` 6.0 mm. No third try.

## Pass (all four, same lines as the outline attempt)

`official_distance` and `v2_check`, unchanged.

| id | rule |
|---|---|
| H1 | mean distance ≤ 0.41 mm |
| H2 | outer r/R 0.8–1.0 ≤ 0.26 mm |
| H3 | r/R 0.4–0.5 ≤ 0.70 mm |
| H4 | `v2_check` true at every measured station |

Fail any one: do not replace Stock. Record the numbers below.

## Results (filled after the run; do not edit anything above)
