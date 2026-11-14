# Trailing edge onto the Noctua, leading edge held (2026-11-13)

Written before the build it judges. The hub-wall attempt
(`2026-11-13-stock-hub-wall-prereg.md`) passed its four lines and is closed.
Stock YAML is still the wrapped v3 recipe. This run does not edit it.

## What was measured first

On `outline_hub26` (the hub-wall STL) against `validation/reference/a12x25_impeller.stl`,
cylinder cuts at tip 54.5 mm:

| r/R | leading-edge z, built minus reference | axial extent, built minus reference |
|---|---|---|
| 0.50 | −0.09 mm | +2.02 mm |
| 0.60 | −0.01 mm | +1.22 mm |
| 0.70 | +0.03 mm | +1.36 mm |
| 0.80 | +0.06 mm | +1.27 mm |
| 0.90 | +0.01 mm | +1.05 mm |
| 0.95 | +0.12 mm | +1.38 mm |

The leading edge already lies on the Noctua (within 0.12 mm). The section is
1.0–2.0 mm too long in Z, so the trailing edge hangs below the Noctua. In the
same meshes the high edge (95th percentile of z) is 0.3–0.6 mm low from r = 27
mm out, and the low edge is 1.6–4.9 mm low. The hub-wall STL spans z −12.61 to
+7.78 mm. The Noctua spans −8.35 to +8.35 mm. A slicer that drops both files
onto their lowest point lifts this blade by about 4 mm and the edge then reads
high. The reference facets are coarse (median edge 2.6 mm). The extent error
above is smooth across radius, so it is not one bad triangle.

With no axial slide, that same hub-wall mesh has a mean distance of 0.361 mm
(best rotation 0.121 rad). The closed hub-wall pass of 0.233 mm used a 0.75 mm
slide. This run does not get that slide.

The r/R 1.00 cut is not a blade (the cylinder hits the tip) and is not a target.
The tip radius stays 54.5 mm. Chord, stagger, camber, thickness, skew and lean
are not free. The loft code is not changed.

## What this run changes

Start from the hub-wall recipe: the outline candidate in `scripts/outline_match.py`
(full leading-edge step) with `hub_radius` 26.0 mm and `root_embed` 6.5 mm.

`sweep` moves the whole section in Z. `le_sweep` moves the leading-edge region
only (weight 1 at the leading edge, 0 from mid-chord to the trailing edge).
For a measured error `d_le` = built minus reference leading-edge z and
`d_ext` = built minus reference axial extent:

- `le_sweep` decreases by `0.7 * d_ext`
- `sweep` increases by `0.7 * (d_ext - d_le)`

That holds the leading edge and lifts the trailing edge by 70 percent of the
gap. Damping 0.7 is the step the 2026-10-13 fit used. Sweep stays inside
[−10, 10] mm and `le_sweep` inside [−8, 8] mm.

Stations at r/R 0.50, 0.60, 0.70, 0.80 and 0.90 take the cut at that radius.
The tip station takes the r/R 0.95 cut. The root station, which is inside the
hub, takes the straight-line extrapolation in `r_frac` of the sweep and
`le_sweep` steps from the 0.50 and 0.60 stations.

Up to four builds. The search builds are the preview loft (one blade, copied
around the axis, full `n_span` / `n_chord`). After each measured build, apply
the step unless this is the fourth build. If the worst of `|d_le|` and
`|d_ext|` on the six radii is larger than on the previous kept build, throw
that build away and stop. If every radius already passes E1 and E2, stop.

The numbers below are from one full impeller of the kept recipe, not from the
preview.

## Pass (all four)

Cuts use tip 54.5 mm. No axial slide is applied to either mesh. Rotation about
Z is allowed for the distance only.

| id | rule |
|---|---|
| E1 | `|leading-edge z error|` ≤ 0.20 mm at r/R 0.50, 0.60, 0.70, 0.80, 0.90, 0.95 |
| E2 | `|axial extent error|` ≤ 0.40 mm at those same radii |
| E3 | `v2_check` true (stagger 1.5°, chord 3%, camber 0.005, thickness 10%) |
| E4 | mean distance ≤ 0.25 mm, axial shift fixed at 0, blade surface outside the hub |

Fail any one: do not replace Stock. Record the numbers below. Do not take a
second step under this file.

## Results (filled after the run; do not edit anything above)
