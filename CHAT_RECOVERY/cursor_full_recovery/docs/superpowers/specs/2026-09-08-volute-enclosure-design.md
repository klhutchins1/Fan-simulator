# Volute sealed fluid enclosure + tongue cutwater (stage 2)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Replace thin shell casing in a leaky tight hex with a **filled exterior enclosure** matched to the CFD box, plus a discrete **tongue cutwater** at θ≈0. Same +Z/+X MRF case path as stage 1. Not NSGA, not CAD-class scroll, not catalog CFM claims.  
**Roadmap:** §4.1 fidelity after stage-1 radial MRF.

## Plain language

Stage 1 snapped a thin volute shell inside a hex; fluid could sneak around the outside (and under the floor). Stage 2 builds the casing as the solid that fills everything *except* the intended air path (eye + scroll channel + outlet stub), so snappy keeps only that path. A thin septum at the tongue stops wrap-around from dumping straight into the stub without a cutwater.

## Goal

1. **`volute_enclosure_extents_mm`** — shared mm box for casing fill and `domain_for_volute`.
2. **`build_volute_casing`** — filled box minus eye/channel/stub voids; fuse tongue tip; one solid.
3. **Honesty** stamp `stage2_sealed_enclosure_segmented_tongue` (case JSON + evaluate raw).
4. **Params** `tongue_angle_deg`, `tongue_tip_clearance_mm`; denser default `n_volute_seg=32`.
5. **Cockpit / problem YAML / roadmap** copy updated off tight-box bypass.
6. **Tests** (no Docker): extents match domain, honesty stamp, tongue validation, mocked evaluate.

## Honesty

- Scroll outer wall is still segmented (piecewise-constant radius per wedge).
- Tongue is a discrete angular septum, not a filleted OEM cutwater.
- Do not claim catalog-comparable absolute CFM/Pa yet.

## Non-goals

- NSGA / BEM for volute
- Replacing mixed-flow axial duct
- DES / FW-H / AMI

## Success

`evaluate_volute` with CFD mocked returns feasible-shaped result with sealed-enclosure honesty; domain extents equal enclosure box; casing builder remains one solid when CadQuery is healthy.
