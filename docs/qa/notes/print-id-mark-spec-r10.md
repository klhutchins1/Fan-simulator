# Print-part ID mark-spec (roadmap §28), QA round 10 Task A — FINAL

Prereg: `qa_r10/PREREG_R10.md` @ `26aa359` (branch `prereg/round10`, `/workspace/fansim/qa/prereg_r6`).
Geometry: master a09905a (wrap merged ae3f1c4), `config/problems/a12x25_reference.yaml` (Stock v3, section_wrap
cylinder), print-ready via `build_impeller_with_mount` + A12x25 `MotorMount`, STL at tol 0.02 / ang 0.1. One B-rep solid,
watertight, 1 body. No hub growth was needed. Feature not implemented; the dummy pocket was cut in a QA script only.
Script: `handoff/2026-10-13_from-qa-10/scripts/a_mark.py`. Data: `handoff/.../data/a_out/a_geom.json`.

**Method change (disclosed):** the registered first-hit ray grid needed ~0.7 M rays with no embree on the box, which was too
slow. I used an equivalent rasterisation instead. A cell is flat if it is inside the projected flat triangles of the plane
(within 0.02 mm, normal along the face) and no material in front of the plane projects onto it. Same polar grid (0.05 mm ×
0.25°), PIL at 0.025 mm/px.

## Measurements (hub-down print: bed z = −8.186 mm, top z = +8.314 mm, hub r = 21.5 mm)
| face | flat region | notes |
|---|---|---|
| +Z (inlet, up) | **annulus r 10.0 → 21.45 mm, full 360°, width 11.45 mm** | Inside r = 10 is the 20 mm through bore. No blade material sits above the plane: the blades end at or below the hub top (model zmax = hub top) and join the hub's side wall at r = 21.5. The face is exactly planar (252 coplanar triangles). |
| −Z (bed) | annulus r 19.0 → 21.5 mm, **width 2.5 mm** | It sits outside the cup reach (cavity Ø37.25/2 + 0.35 clearance = 18.98 mm). Too narrow for a 3.2 mm glyph, so it fails M1 by itself. |
| cup floor | down-facing roof at z = 4.80 (12.985 mm above the motor face) | It is a ceiling inside the cup and sits on the motor, so it is **not usable** (as expected). |

Roof over the cup on +Z: 8.314 − 4.799 = **3.5 mm** thick between r 10 and 18.98.

## Rules
- **M1 PASS.** A 6 mm band (r 10.1–16.1) is flat over 360° (need ≥ 25°). 8 mm and 10 mm bands are also flat over 360°. The
  widest full-circle band is 11 mm.
- **M2 PASS.** The dummy recess is 8 (tangential) × 3.2 (radial) × 0.5 mm deep, centred r = 13.1 mm, θ = 90° (any θ works,
  since the ring is full-circle). After the cut: 1 solid, watertight, 1 body, ΔV = 12.800 mm³ (expected 12.8). Cup gauge K7
  is unchanged: floor 12.985 mm above the face, 20 grips, protrusion 0.696 mm. The cut took 17 s.
- **M3 PASS.** The footprint dilated by 1 mm is all flat face, so it is ≥ 1 mm from the bore edge, the hub rim and the blades.
  The recess floor (z 7.814) is 3.0 mm above the cup roof underside, which is ≥ 1 mm from cavity and grips. The pocket lies
  radially over the cavity (r 11.5–14.7 < 18.98), so the axial gap is the one that counts.
- **M4 (feasibility).**
  - 0.5 mm depth is about 4 layers at 0.12 mm (≥ 3 needed).
  - At 3.2 mm cap height, use a single-stroke or engraving font with **stroke ≥ 0.5 mm** (0.6 recommended, about 1.5 lines of
    a 0.4 nozzle). A 0.45 mm minimum is marginal.
  - 5 glyphs at 2.4 mm advance are about 12 mm of arc. At mid-radius 15.7 mm that spans about 44°, and the ring is 360°.
  - A 12×12 Data Matrix at 0.5 mm/module is 7 × 7 mm with its quiet zone. It fits in the 11.45 mm ring beside the text.
    But 0.5 mm modules are one nozzle width, so the matrix is **marginal on FDM** (optional; 0.6–0.8 mm modules would be
    safer and still fit: 8.4–11.2 mm squares).
  - The mark is on the last (top) surface of a hub-down print, so it needs no supports.
- Fallback (−Z) not needed. The bed annulus fails M1 by itself in any case (2.5 mm).

## Preferred pocket / mark (proposal)
- Face +Z hub top, z = 8.314, recess floor z = 7.814 (depth 0.5).
- Text band: r_inner 11.5, r_outer 14.7 mm (glyph cap 3.2 mm, radial), θ span ≈ 44° for 5 glyphs read tangentially. Keep
  ≥ 1 mm from r = 10 (bore) and r = 21.5 (rim).
- Optional matrix: a 7 mm square centred at r ≈ 15.7 mm, ≥ 1 mm away from the text along the arc.
- Engrave the glyph strokes only. A box pocket with raised glyphs is a fallback if strokes print poorly.
- Alphabet: **Crockford base-32** `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (no I L O U; on read, treat i/l → 1 and o → 0). 4 chars
  give 1.05 M codes and 5 chars give 33.5 M. A 5th char as a mod-37 Crockford check symbol is optional (`*~$=U` are only
  needed for the check digit).
- The README prints the same code (Sharpie fallback).

## Aero
- The full 8 × 3.2 pocket is 25.6 mm². That is **1.76 %** of the inlet hub disk (π·21.5² = 1452 mm²), or 2.25 % of the solid
  annulus excluding the bore.
- Engraved strokes only: about 13 mm² (≈ 0.9 %).
- **Both are above the 0.5 % no-CFD threshold**, so by the brief's rule this is not automatically exempt. A recess on the
  hub's front disk at r < 15 mm is in the low-velocity core. Whether to CFD it anyway is Cursor's call. Getting under 0.5 %
  would need ≤ 7.3 mm² of recess (e.g. 4 glyphs at 2.4 mm cap, stroke-engraved).

Sketch: `docs/qa/notes/print-id-mark-spec-r10_top.png`. No patch proposed. The pocket code is in a_mark.py (≈ 3 lines of
CadQuery: makeBox → rotate → `shape.cut`).
