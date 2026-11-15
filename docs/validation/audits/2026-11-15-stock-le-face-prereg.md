# Leading-edge wall on the sharpened hub-26 plate (2026-11-15)

Written before the run it judges. The trailing-edge search
(`2026-11-15-stock-te-face-prereg.md`) failed and is closed. Its `te_face`
values stay at 0. This run does not search them again. Stock YAML is not edited.

With the back edge already sharp, the section was still 0.17–1.30 mm too long.
That leftover is the full wall at the leading edge.

## What this run changes

Start from `config/problems/a12x25_outline.yaml` (hub 26.0 mm, root embed 6.5 mm,
plate, `te_face` 0). Only `le_face` changes. `le_face` is the fraction of the
wall left at the leading-edge tip (1 = full wall, 0 = the front edge meets the
chord). Mid-chord stays the full wall.

At r/R 0.50, 0.60, 0.70, 0.80, 0.90, pick the `le_face` in [0, 1] that makes
the section's axial extent closest to the Noctua cylinder cut at tip radius
54.5 mm. One search per station. The root station copies r/R 0.50. The tip
station copies r/R 0.90. Extent is max Z minus min Z, with no axial slide.
Leading-edge Z is the chord tip, not the shoulder.

## Pass (both)

| | |
|---|---|
| L1 | axial extent error ≤ 0.40 mm at r/R 0.50, 0.60, 0.70, 0.80, 0.90 |
| L2 | leading-edge tip Z moves by ≤ 0.20 mm from the `le_face` = 1 wire at those radii |

If either line fails, record the faces and the residuals. No second search
under this file. The STL from these faces is the one to print and measure.

## Results (filled after the run; do not edit anything above)
