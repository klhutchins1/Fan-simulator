# Honest optimizer CFD — tip gap + frame struts (stage 1)

**Date:** 2026-09-01  
**Status:** draft  
**Approach:** A — extra stationary `frame.stl` in snappyHexMesh; optimizer tip gap 0.5 mm  
**Roadmap:** §1.1. Not §1.2 (system curve), not the circular AMCA high-accuracy rig.

## Problem

The optimizer CFD is an idealized square duct with a 1 mm tip gap and **no
frame**. Tip leakage is the dominant real loss; four exhaust struts add
blockage and a wake. Screening therefore over-reads CFM and never rewards
leakage-managing geometry (the reason the tip ring exists). Validated
free-air on the real Noctua STL is +2%, but that STL already had a real tip
and sat in a different setup; parametric trials do not.

## Goal

Every optimizer trial (and cockpit Assess that uses `evaluate_candidate`)
meshes against:

1. A **0.5 mm** radial tip gap (roadmap; `--tip-gap` overrides).
2. **Four stationary struts** downstream of the rotor, hub to duct wall,
   outside the MRF zone.

The square screening duct, two operating points (free + `load_pa`), and
mesh-once-solve-twice stay.

## Non-goals (this spec)

- Quadratic system curve / rising impedance (§1.2)
- Circular AMCA 210 / ISO 5801 duct (high-accuracy plan)
- Designed shroud-to-frame gap study (§7.5)
- Noctua venturi inlet, motor cup, or honeycomb
- Changing BEM `DEFAULT_TIP_GAP_MM` (0.5 mm) — already the BEM default
- Changing `rig_for_impeller`'s default `tip_gap_mm=1.0` for validation /
  printed-part scripts that do not go through the optimizer
- New CFD campaign or Docker tests

## Tip gap

`evaluate_candidate` / `run_study` pass `tip_gap_mm=0.5` into
`rig_for_impeller`. CLI `--tip-gap` on `scripts/run_optimization.py`
overrides (default 0.5). Cockpit Assess uses the same 0.5 mm unless we add a
control later (not this spec).

`rig_for_impeller` already sizes the duct from `open_tip_rmax_mm +
shroud_thick_mm + tip_gap`. That path is unchanged; only the number the
optimizer passes in changes.

## Strut geometry

New helper `fansim/cfd/frame.py` (or `fansim/geometry/frame.py` if CAD-only):

```text
build_frame_stl(params, duct_radius_mm, impeller_z_max_mm, path) -> Path
```

Four rectangular bars, 90° apart:

| Dim | Value |
|---|---|
| Count | 4 |
| Thickness (tangential) | 2.4 mm |
| Axial depth | 8 mm |
| Inner radius | `params.hub_radius` |
| Outer radius | `duct_radius_mm − 0.1 mm` (inset so snappy does not coincide with the box walls) |
| Z start | `mrf_z_max_mm + 0.5 mm` — **after** the MRF band, not merely after the blade bbox |

`mrf_z_max` is already `impeller_z_max + 2 mm`. Placing struts at
`impeller_z_max + 1 mm` would put them **inside** the rotating zone. They
must sit downstream of MRF so they are stationary walls.

Fuse the four bars into one solid, export millimetre STL, scale to metres
with the impeller in `build_case`.

## OpenFOAM

`fansim/cfd/templates.py` `SNAPPY` and `SURFACE_FEATURES` gain a second
surface `frame.stl`:

- `geometry { frame.stl { type triSurfaceMesh; name frame; } }`
- `refinementSurfaces { frame { level (@SURFMIN@ @SURFMAX@); patchInfo { type wall; } } }`
- feature extract on `frame.eMesh` as well as `impeller.eMesh`

`topoSetDict` MRF cylinder is unchanged (impeller axial band × duct radius).
Struts are outside that band by construction.

`0/` wall BCs that currently apply to `impeller` must also apply to `frame`
(no-slip). Follow the existing patch grouping if there is one; otherwise
duplicate the impeller wall entries for `frame`.

`build_case(..., frame_stl_mm=None)`. `None` keeps today’s impeller-only
case (validation scripts). Optimizer / `evaluate_candidate` always pass a
frame STL.

## Optimizer / cockpit

`evaluate_candidate` builds the frame from the same `BladeParams` + rig used
for the impeller, writes `frame.stl` next to `impeller.stl`, and passes it
to `build_case`. Failures to build the frame are infeasible (`frame failed:`)
so a bad Boolean cannot silently drop struts.

No new Optuna search DOF.

## Tests (no Docker)

- Four bars; fused frame is a single watertight-enough solid (or four
  disjoint bars if fuse is skipped — pick **one fused solid** and assert
  `n_bodies == 1`)
- Frame `z_min` > `rig.mrf_z_max` (metres vs mm: be consistent in the test)
- Snappy dict contains `frame.stl` when a frame path is passed; impeller-only
  when `frame_stl_mm is None`
- `evaluate_candidate` / study path uses `tip_gap_mm=0.5` (unit-level: the
  call into `rig_for_impeller`, or a tiny helper `optimizer_tip_gap_mm()`
  returning 0.5)
- `--tip-gap` is a recognized flag on `scripts/run_optimization.py`

## Success

A new optimization trial meshes an impeller with a 0.5 mm gap and four
exhaust struts. Existing validation scripts that call `rig_for_impeller`
without a frame still get a 1 mm gap and no struts. Absolute CFM will drop
versus today’s idealized duct — that is the point.
