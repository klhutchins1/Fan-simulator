# Circular screening duct (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep the square `blockMesh` hex. Snap a watertight cylindrical **casing** STL as the duct wall (same extra-surface pattern as `frame.stl`). Fluid lives inside radius `duct_radius`. Not an O-grid, not AMCA chambers, not grid-independence.  
**Roadmap:** §1.1 remaining (circular AMCA / ISO 5801 rig), stage 1. High-accuracy plan’s `testrig_cylinder.py` + layers + GCI stay later.

## Plain language

The optimizer still runs in a **square tunnel**. The rotor is circular, so the four corners are a bypass around the blade span. CFM is integrated on that square outlet, so flow is overstated and leakage-managing geometry (the ring) is under-rewarded. Stage 1 makes the **screening** duct a cylinder at the same radius we already call `duct_radius` (pinned frame ID when a spec is set). Absolute AMCA numbers, honeycomb, and y+ layers are not this slice.

## Problem

```text
blockMesh: square box, side = 2 * duct_radius
walls:     slip
frontal_area = (2R)²          # domain.py comment: “Phase-2 switches to circular”
locationInMesh = (0.9R, 0.9R, 0)   # in a square corner — outside a cylinder of radius R
```

`outletFlow` uses the remaining outlet patch, so reported CFM includes corner fluid. Frame struts already stop at `R − 0.1 mm` as if the wall were circular.

## Goal

1. **Casing solid** (mm), new `fansim/cfd/casing.py`:

```text
inner_r = rig.duct_radius / MM_TO_M          # fluid radius unchanged
wall    = 2.4 mm                             # same as frame barrel
outer_r = inner_r + wall
z       = [rig.domain_z_min, rig.domain_z_max] / MM_TO_M   # full duct
one solid tube (outer cylinder minus inner bore)
```

2. **Oversized hex** so the tube does not coincide with box faces:

```text
H_box = 1.12 * rig.duct_radius     # blockMesh ±X/±Y only; Z unchanged
```

`topoSet` MRF radius stays `duct_radius` (fluid). Frame geometry unchanged.

3. **`build_case(..., casing_stl_mm=)`** — same wiring as `frame.stl`:

   - copy → `constant/triSurface/casing.stl`
   - snappy geometry / features / `patchInfo { type wall; }`
   - `0/U,p,k,omega,nut`: `casing` is **noSlip** / wall functions (real duct wall)
   - `MRFProperties` `nonRotatingPatches` includes `casing`
   - leftover square `walls` patch stays slip (cells there should be deleted)

4. **`locationInMesh` when casing is on** — must sit in the **bore**, not a square corner:

```text
(0.35 R,  0,  domain_z_min + 0.25 * inlet_length)
```

Off-axis so it is not on the hub/axis; in the inlet so it is not inside a blade. No-casing cases keep today’s `(0.9 H, 0.9 H, 0)`.

5. **`TestRig.frontal_area`** = `π R²` always. Velocity-driven helpers (`inlet_flow_cfm`) were using the square area; optimizer CFM still comes from `outletFlow`, which will drop toward the circular value once the corners are gone.

6. **`evaluate_candidate` default on.** Export `casing.stl` next to `frame.stl`, pass both into `build_case`. Stamp `raw["duct"] = "circular"`. `circular_duct: bool = True`; `False` is the square-tunnel A/B escape (no CLI flag this cycle). Assess inherits on.

7. Do **not** rewrite `catalog/catalog.db`. Old rows have no `duct` key. New rows carry `duct=circular` via extra/`raw` (same idea as `frame_stl` / curve provenance — stamp, don’t backfill).

## Non-goals

- O-grid `testrig_cylinder.py`
- Prism layers / target y+
- GCI / three-mesh independence
- Full P–Q / shut-off campaign
- AMCA total-pressure planes / efficiency re-definition (adversarial §3.1)
- Noctua venturi, honeycomb, inlet bell
- Changing `--tip-gap`, frame bars, or system-curve algebra
- Docker mesh campaign as a required test

## Limitations (stage 1)

- Background hex is still coarse; the gap still has ~1 cell. This slice fixes **duct shape + area**, not resolved tip leakage.
- Snappy on a long tube can fail; a failed mesh stays infeasible (do **not** silently fall back to square — that would mix the ranking).
- Square vs circular CFM are not comparable. Historical catalog stays square-scored.

## Tests (no Docker)

- `frontal_area` is `π R²` for a default rig
- Casing solid is one body; inner radius matches `duct_radius`; bbox Z covers the domain; a point at `r = 0.5 R` is **outside** the solid (bore); a point at `r = inner + 1 mm` is **inside** the wall
- `build_case` without casing: no `casing.stl`, `locationInMesh` still in the corner
- `build_case` with casing: `casing.stl` in snappy + `0/U`, `locationInMesh` at `0.35 R` in the inlet, blockMesh `XMAX` ≈ `1.12 R`
- `evaluate_candidate(..., circular_duct=False)` skips casing export (monkeypatch path, same style as frame)

## Files

| Path | Responsibility |
|---|---|
| `fansim/cfd/casing.py` | tube solid + `export_casing_stl` |
| `fansim/cfd/domain.py` | `frontal_area = π R²` |
| `fansim/cfd/openfoam_case.py` | oversized box, casing surface, `locationInMesh` |
| `fansim/cfd/templates.py` | `CASING_*` placeholders (mirror `FRAME_*`) |
| `fansim/optimize/objectives.py` | export casing; stamp `duct` |
| `tests/test_casing.py` | solid / export |
| `tests/test_cfd.py` | area + `build_case` wiring |
| `docs/roadmap.md` | §1.1 stage 2 duct; remaining = layers / GCI / AMCA metrics |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
