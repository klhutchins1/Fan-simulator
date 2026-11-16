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

Ran `scripts/outline_le_face.py`. `te_face` stayed 0. The leading-edge tip did not move.

| r/R | le_face | extent error | leading-edge tip shift |
|---|---|---|---|
| 0.50 | 0.00 | +0.376 mm | 0.000 mm |
| 0.60 | 0.44 | +0.005 mm | 0.000 mm |
| 0.70 | 0.38 | −0.005 mm | 0.000 mm |
| 0.80 | 0.61 | +0.003 mm | 0.000 mm |
| 0.90 | 0.86 | +0.001 mm | 0.000 mm |

| | |
|---|---|
| L1 | **PASS.** Largest extent error is +0.376 mm at r/R 0.50. |
| L2 | **PASS.** Leading-edge tip shift is 0 at every radius. |

**Verdict: PASS** on the section wire. The r/R 0.50 miss is the chord tips themselves: a sharp edge there is already 13.483 mm long and the Noctua span is 13.107 mm. No wall setting can remove that 0.38 mm. These faces are in `config/problems/a12x25_outline.yaml`. The print STL is the full impeller of that file.
