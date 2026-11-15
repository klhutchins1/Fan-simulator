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

Ran `scripts/outline_z.py`. The search stopped at preview build 2 (worst edge 0.391 mm, under the 0.40 mm extent bar). The full impeller of that recipe is the table below. Stock YAML was not changed.

| id | rule | result |
|---|---|---|
| E1 | leading-edge z ≤ 0.20 mm | **FAIL.** r/R 0.50 is −0.22 mm. The other five are inside 0.20 mm (largest +0.11 at 0.95). |
| E2 | axial extent ≤ 0.40 mm | **PASS.** 0.19, 0.35, 0.31, 0.23, 0.17, 0.39 mm from r/R 0.50 to 0.95. |
| E3 | section tolerances | **FAIL.** Stagger −4.12° to −2.31° (limit 1.5°). Camber +0.041 to +0.021 (limit 0.005). Chord −4.8% at r/R 0.50 (limit 3%). |
| E4 | mean distance ≤ 0.25 mm, no axial slide | **FAIL. 0.365 mm** at rotation 0.168 rad. The hub-wall mesh was 0.361 mm with no slide. |

Extent came down. The leading-edge bend that did it rotated the chord and bowed the camber, and the surface got no closer.

**Verdict: FAIL.** Closed. No second step under this file. STL `runs/outline_z/z_edge.stl` is the failed recipe, not a replacement for the hub-wall mesh.
