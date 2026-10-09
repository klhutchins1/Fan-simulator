# Stationary outlet vanes (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** A one-body stator STL of thin staggered plates + hub barrel, snapped as a new stationary `stator` wall **instead of** the four-bar frame. Default **off**. `--stator` on the optimizer and `evaluate_candidate(stator=False)`. Not cambered NACA OGVs, not a searched vane count, not both frame and stator in the same 8 mm band.  
**Roadmap:** §2.2 stage 1. Swirl recovery is why this exists; stage 1 is geometry + case wiring so a later campaign can measure it.

## Plain language

The downstream “stator” today is four fat struts. They are blockage, not turning vanes. A real axial fan has a row of stationary vanes that take rotor swirl and make static pressure. Stage 1 builds that row as plates at a fixed stagger, just after the MRF, and puts it in OpenFOAM the same way `frame.stl` is wired. NSGA stays on the four-bar frame unless you pass `--stator`.

## Problem

```text
evaluate_candidate → export_frame_stl  → 4 bars, 2.4 mm thick, no stagger
build_case(..., frame_stl_mm=)         → stationary wall named frame
```

Those bars sit at `mrf_z_max + 0.5 mm`. A second row in the same slice would collide. Stacking stator *behind* the frame needs more axial room and a second mesh campaign. Stage 1 **replaces** the frame when the flag is on.

## Goal

1. **Solid** `fansim/cfd/stator.py` (mm, CadQuery), same z-band as today’s frame:

```text
z_start     = mrf_z_max/mm + 0.5
chord_mm    = 8.0          # axial depth of the row (same as STRUT_DEPTH_MM)
thick_mm    = 1.2
stagger_deg = 50           # from rotation plane; rotor is ~22–26, so more axial
n_vanes     = n_blades + 2 # detune BPF; not an NSGA variable
outer_r     = duct_radius/mm − 0.1
hub barrel  = same as frame (join so the fuse is one solid)
```

Each vane is a box `span × thick × chord`, rotated about its radial axis by `stagger_deg`, patterned around Z. Fuse vanes + hub barrel → **one** `cq.Solid`. Raise if `Solids()` ≠ 1.

2. **Export** `export_stator_stl(params, rig, path)` via the shared STL writer.

3. **`build_case(..., stator_stl_mm=None)`** — copy the casing/frame extra-wall pattern for name `stator`:

```text
triSurface/stator.stl
snappy geom / features / wall
0/ U noSlip, p zeroGradient, k/omega/nut wall functions
MRF nonRotatingPatches includes stator
```

Placeholders `@STATOR_*@` next to frame/casing. Empty when omitted.

4. **`evaluate_candidate(..., stator=False)`**

```text
stator False → export_frame_stl, frame_stl_mm set, stator_stl_mm None   (today)
stator True  → export_stator_stl, frame_stl_mm None, stator_stl_mm set
```

Stamp `raw["stator"]` = `"vanes"` | `"frame"`. Do not fail the eval if stator fuse fails — `_infeasible` like frame.

5. **CLI** — `scripts/run_optimization.py --stator` (store_true, default off) through `run_study` / `evaluate_candidate`. Cockpit and `run_grid_convergence` stay frame-only this cycle.

## Honesty

These are **flat staggered plates**, not cambered OGVs and not printed as part of the 25 mm Noctua frame. They exist so CFD can see a turning row. Do not claim AMCA static-efficiency recovery until a campaign compares `--stator` vs frame on one design.

## Tests (no Docker mesh)

- One solid; `zmin` after MRF; volume in the ballpark of `n_vanes * span * thick * chord` + barrel (≤15% fuse overlap).
- Mid-span at a vane angle is inside; halfway between vanes is outside (`n_blades=7` → 9 vanes, 40° pitch).
- `n_vanes == params.n_blades + 2`.
- `export_stator_stl` writes a file > 1 KB.
- SNAPPY / MRF / surfaceFeatures templates contain `@STATOR_` placeholders.
- `evaluate_candidate` is not required to run; a unit test that the flag picks stator vs frame can be a small helper `stationary_downstream(stator: bool) -> str` returning `"stator"` | `"frame"`.
- Argparse: `--stator` on the optimization parser (extract or read `run_optimization.py` / a tiny helper). No `★` in help.

## Non-goals

- Searching `n_vanes` / stagger / camber in NSGA
- Cambered NACA stator loft
- Frame **and** stator in one case
- BEM Euler credit for OGVs
- Cockpit switch
- Printing the stator with the impeller
- `--layers` on stator patches
