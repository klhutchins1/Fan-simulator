# Section family: NACA vs rounded plate (bullnose)

**Date:** 2026-09-10  
**Status:** accepted — stage 1 shipped; polish remaining (hide LE/TE sliders in plate mode).  
**Approach:** `BladeParams.section_family` `"naca"` | `"plate"`. Plate = constant-thickness stadium (semicircle LE + TE, `R = t/2`). Camber and LE/TE thick scales ignored in plate mode.  
**Roadmap:** §2.8 — reproduce constant-thickness bullnose edges (user reference photo).

## Goal

1. `fansim/geometry/airfoil.py`: `rounded_plate(thickness, n_points=60) -> (N,2)` closed loop, same ordering as `naca4` (TE→upper→LE→lower→TE). Chord = 1. Flat faces at `y = ±t/2` between the semicircles.
2. `BladeParams.section_family: str = "naca"`.
3. `_section_loop` uses plate generator when family is `plate`; skip camber (use 0) and skip `apply_le_te_thickness`.
4. Cockpit: VSelect under Airfoil. Flat keys `section_family`.
5. Tests: plate LE/TE radius ≈ t/2; family round-trip; naca default unchanged.

## Non-goals

- Cambered plate, NSGA variable, removing LE/TE scales from NACA mode.
