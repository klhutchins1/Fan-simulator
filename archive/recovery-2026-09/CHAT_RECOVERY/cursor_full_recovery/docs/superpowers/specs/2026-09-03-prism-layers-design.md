# Opt-in prism layers (stage 3)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** A `MeshResolution.add_layers` flag, default **off**, that fills snappy `addLayers` + `impeller { nSurfaceLayers 3 }` through a testable mapping helper. Screening / NSGA stay layer-free. `--layers` on `scripts/run_grid_convergence.py` is the one-design on-ramp. Not y+≈1, not 8 cells in the tip gap, not a Docker mesh campaign.  
**Roadmap:** §1.5 stage 3 (adversarial-review “layers on ONE design first”). P–Q / shut-off stay later.

## Plain language

Snappy currently snaps then stops (`addLayers false`, `layers {}`). Fan losses live in the blade boundary layer, which the screening hex never sees. Turning layers on for every NSGA trial will explode meshes and wall-clock. Stage 3 is the dictionary + a flag the grid-convergence script can pass, so a later campaign can actually grow prisms on one impeller. Default remains off.

## Problem

```text
SNAPPY
  addLayers       false;
  addLayersControls { layers {} }
```

`build_case` has no switch. `evaluate_candidate` and the grid script cannot opt in.

## Goal

1. **`MeshResolution`** — new fields, defaults keep today’s mesh:

```text
add_layers: bool = False
n_surface_layers: int = 3
```

2. **Helper** (no Trame, no Docker, no STL):

```text
snappy_layers_mapping(mesh: MeshResolution) -> dict
  ADDLAYERS      "true" | "false"
  LAYER_PATCHES  impeller { nSurfaceLayers N; }  or empty
```

Only the **impeller** patch (blade + hub are one STL). Do not layer `frame`, `casing`, or hex `walls` this cycle.

3. **`SNAPPY` template** — placeholders, not a second copy of the dict:

```text
addLayers       @ADDLAYERS@;
...
    layers
    {
@LAYER_PATCHES@
    }
```

Keep the existing relativeSizes / expansionRatio 1.2 / finalLayerThickness 0.3 / minThickness 0.1. Those are wall-function layers, not low-Re y+≈1.

4. **`build_case`** passes the mapping into snappyHexMeshDict. Callers that omit `add_layers` write the same dict as today (`false`, empty layers).

5. **CLI** — `scripts/run_grid_convergence.py --layers` (store_true, default off) → `MeshResolution(..., add_layers=True)`. Do **not** add the flag to `evaluate_candidate`, cockpit, or NSGA.

## Honesty

Three relative layers on a ~3–5 mm surface mesh are **not** a resolved BL and **not** ≥8 cells across the printed tip gap. They are a first prism extrusion so a later y+/GCI campaign has something to grow. If snappy fails to extrude, that is a mesh-quality problem for the campaign, not a reason to turn layers on in screening.

## Tests (no Docker)

- Default `MeshResolution()` → `ADDLAYERS false`, `LAYER_PATCHES` empty / no `nSurfaceLayers`.
- `add_layers=True` → `true` and `impeller { nSurfaceLayers 3; }`.
- `n_surface_layers=5` shows up in the patch block.
- `SNAPPY` contains `@ADDLAYERS@` and `@LAYER_PATCHES@`.
- Argparse: `--layers` sets the flag (parse `run_grid_convergence`’s parser, or a tiny argv helper if argparse is buried in `main`). Do not `@pytest.mark.docker` a mesh.

## Non-goals

- Default-on for screening / NSGA / Assess
- Layers on casing, frame, or outer box
- Target y+ (1 or 30–50), `ks` roughness, extra tip-gap cells
- Full P–Q / shut-off
- Cockpit checkbox
- Running snappy as part of this slice
