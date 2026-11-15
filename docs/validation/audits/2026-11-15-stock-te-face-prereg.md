# Trailing-edge wall on the hub-26 plate (2026-11-15)

Written before the run it judges. The z-edge attempt
(`2026-11-13-stock-z-edge-prereg.md`) is closed and is not repeated.
Stock YAML is still the wrapped v3 recipe. This run does not edit it.

The plate wall stays a full thickness out to the trailing edge, so the
section is 1.1–2.0 mm too long in Z. Switching the whole blade to NACA
makes the edge too short from r/R 0.60 out. This run only changes how
much of that wall is left at the trailing edge.

## What this run changes

Start from the hub-wall recipe: the outline candidate, `hub_radius` 26.0 mm,
`root_embed` 6.5 mm, root radius held at 19.5 mm, section family `plate`.
Every station field except `te_face` stays put. `te_face` is the fraction
of the wall left at the trailing-edge tip (1 = today's plate, 0 = the back
edge meets the chord). The leading edge is not moved.

At r/R 0.50, 0.60, 0.70, 0.80, 0.90, pick the `te_face` in [0, 1] that
makes the section's axial extent closest to the Noctua cylinder cut at
tip radius 54.5 mm. One search per station. If the error is still falling
at 0, use 0. The root station copies the r/R 0.50 value. The tip station
copies the r/R 0.90 value. No other radius is searched.

The extent is max Z minus min Z. Ours is the placed section wire. The
Noctua number is the same span on the scan's cylinder cut. No axial slide.

## Pass (both)

| | |
|---|---|
| F1 | axial extent error ≤ 0.40 mm at r/R 0.50, 0.60, 0.70, 0.80, 0.90 |
| F2 | leading-edge Z moves by ≤ 0.20 mm from the `te_face` = 1 wire at those radii |

If either line fails, record the faces and the residuals. No second search
under this file. The STL written from these faces is for measuring the
difference. It is not another attempt to pass.

## Results (filled after the run; do not edit anything above)
