# Blade sections wrapped onto cylinders (roadmap 27.4, option i)

Date: 2026-10-12 · Status: **draft for Kimball's review** · Roadmap §27.4 (QA-30, QA-31)

## Why

QA round 8 (Task D), confirmed here: on any leaned or skewed blade the built blade is not the blade the
sliders describe.
- Stock's sliders say camber 0.08–0.10, and the built blade's cylinder sections read 0.036–0.040. With lean,
  skew and sweep set to zero it reads 0.073–0.087, which is the slider minus the estimator's known bias.
- t9005's tip: the slider says 0.06, and the built blade reads 0.008.

The cause is placement. `_section_loop` (`fansim/geometry/blade.py`) lays each section **flat in the
tangent plane** at its radius, then rotates it to its lean angle. A flat section only touches its cylinder
along one line, so the cylinder at radius r cuts through a mix of neighbouring sections. Once those are
rotated by different lean angles, the cut is sheared and loses its camber.

BEM works on cylindrical strips using the slider numbers, while CFD runs on the built blade. So the two
are scoring different blades, and the sliders don't mean what they say.

Separately (QA-30): the chord realisation measures a lone, **unclipped** blade, so it never sees the
chord that the hub-face clip removes (lt120 loses 3–16 %).

## What changes

1. **Wrap each section onto its cylinder.**
   - In `_section_loop`, a point at tangential distance `t` (mm) from the stacking point goes to angle
     θ = lean + t / r on the cylinder of radius r, instead of staying on the tangent plane:
     `x = r·cos θ`, `y = r·sin θ`, and the axial z is unchanged.
   - Chord, stagger, camber and thickness are then exactly what a cylinder cut at r reads (on the unrolled
     cylinder, `t` is arc length).
   - `skew` (mm) becomes arc length on the cylinder, which is the same meaning it has in the
     measurement.
2. **A new `BladeParams.section_wrap` field**, either `"cylinder"` (the new default) or `"planar"` (legacy).
   - This follows the `chord_basis` pattern: when the key is absent you get the new default, and a migration
     script stamps every existing saved design `"planar"`. Old designs then rebuild exactly as they were
     scored, so no saved score becomes wrong. The editor, the flat dict, the stock cache key, CROR's
     params_io and the optimizer's trial attributes all carry the field.
   - In the cockpit, a planar design shows a one-line note: "Old blade shape: its camber sliders overstate
     the built blade. Re-create it to use the new shape."
   - The centrifugal builder keeps planar sections. Its blades are not axial strips, so that is out of
     scope.
3. **Measure the chord on the clipped blade (QA-30).** `chord_realisation.measure_station_chords` applies
   the same hub-face clip (`clip_blade_below` at the hub's motor face) before measuring. With wrapping, the
   loft chord only needs to stretch where the clip or the tip trim removes material.
4. **Refit Stock.** Stock's numbers were fitted to the real STL (MajorHardware's A12x25) through planar
   sections. Re-run `scripts/fit_recipe_to_stl.py` with wrapping, to a new
   `config/problems/a12x25_reference.yaml`, and keep the old one as `a12x25_reference_planar.yaml`. The
   real fan's shape doesn't change, only the numbers that describe it. I expect the camber sliders to drop
   to about 0.05.
5. **Not in this change:**
   - the optimizer's camber bounds, which were tuned when 0.06 built about 0.03 (that goes on the roadmap
     once we see the new Stock numbers);
   - the radial direction reader (27.2), which is re-tested after this change (V4);
   - external STLs.

## Checks (pre-registered here, before any wrapped build)

| # | check | pass |
|---|---|---|
| V1 | **Built = sliders.** On the refit Stock, t9005, t9003, lt120 and 4 stress designs with lean ≥ 30° (one featured), at every realised station: cylinder-cut chord vs slider, and cut camber vs slider minus the estimator bias for that section (QA's per-station analytic bias) | chord within 3 %; camber within 0.005; stagger within 1.5° |
| V2 | **Stock is still the real fan.** The refit Stock cut against the reference STL at r/R 0.50–0.99 | within the fit's own `TOL` (stagger 1.5°, chord 3 %, camber 0.005, thickness 10 %) at every measurable station |
| V3 | **It still builds.** 20 stress designs (all strata, including featured, shrouded, winglet and notched tips) | watertight, 1 body, within the tip radius, nothing below the hub face; full test suite green |
| V4 | **Direction proof.** The cylinder reader on wrapped rebuilds of 9605, 9606, 9620, 9630, S3_0002, S4_0005, S4_0012, S3_0014 and the 22 S3-cell parts from QA round 8 | 0 CONCLUSIVE-wrong (report: how many now read CONCLUSIVE) |
| V5 | **Same real fan, same airflow.** A full CFD run of the refit Stock vs the current Stock reference run | free-air CFM within ±3 % and loaded CFM within ±5 % |
| V6 (report only) | **BEM vs CFD.** On t9005, compare BEM against CFD for both the planar build and the wrapped build | no pass band: tells us whether BEM's over-rating of leaned blades shrinks |

If V2 or V5 fails, Stock keeps the planar recipe and wrapping stays opt-in until we understand why.

## Risks

- **Lofting curved (non-planar) section wires** may be less robust in OCCT than flat ones. The old comment
  says flat sections were chosen to keep the loft watertight. V3 is the gate. The fallback is to make
  the wire from more points per section.
- **Speed:** wrapping adds nothing per point. The loft and boolean costs should stay about the same.
- **Tracked reference STLs** may be rewritten by tests (known churn); restore them before committing.
- **Scores:** every *new* design's geometry differs from what the same sliders built yesterday, so old
  and new scores aren't comparable on equal sliders. They remain comparable as built blades.
