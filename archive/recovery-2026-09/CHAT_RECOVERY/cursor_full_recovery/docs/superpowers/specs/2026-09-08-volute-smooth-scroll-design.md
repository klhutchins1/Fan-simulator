# Volute smooth Archimedean scroll + filleted tongue (stage 3)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Replace piecewise-constant wedge scroll with a **single extruded Archimedean polyline** (dense `n_volute_seg` samples) and a **filleted tongue tip** cylinder. Keep sealed enclosure fill + shared CFD extents. Honesty `stage3_smooth_scroll`.  
**Roadmap:** §4.1 after stage-2 sealed enclosure.

## Plain language

Stage 2 sealed the box but left a stair-step outer wall (constant radius per wedge) and a sharp angular cutwater. Stage 3 cuts one spiral-shaped channel void whose outer wall follows \(r(\theta)=r_0+(r_1-r_0)\,\theta/2\pi\), and rounds the tongue tip with a small cylinder so the cutwater is less knife-edged. Same +Z/+X MRF path.

## Goal

1. **`_archimedean_scroll_void`** — one extruded polygon (outer spiral + inner circle) instead of N annular sectors.
2. **Default `n_volute_seg=96`** — high-resolution polyline samples (still the sample count knob).
3. **`tongue_fillet_mm`** — cylindrical tip on the cutwater (default 1.5 mm).
4. **Honesty** `stage3_smooth_scroll` in case JSON + evaluate raw.
5. **`scroll_outer_radius_mm`** helper for tests / callers.
6. Cockpit / problem YAML / roadmap updated; tests for radius law, fillet bounds, honesty.

## Honesty

- Outer wall is a dense polyline, not a true CAD spline loft/revolve.
- Tongue is septum + tip cylinder, not a full OEM filleted cutwater solid.
- Do not claim catalog-comparable absolute CFM/Pa.

## Non-goals

- NSGA / BEM for volute
- True lofted/revolved CAD scroll or OEM tongue solid
- DES / FW-H / AMI
- Changing inlet/outlet axis convention

## Success

Geometry helpers prove monotonic Archimedean \(r(\theta)\); honesty stamps stage 3; mocked evaluate / domain extents unchanged; casing remains one solid when CadQuery is healthy. Remaining: spline loft / catalog-grade OEM tongue if needed later.
