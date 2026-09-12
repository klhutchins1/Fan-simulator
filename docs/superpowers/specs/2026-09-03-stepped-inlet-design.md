# Stepped inlet lip (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Optional concentric step on the **circular casing** inlet: a short larger bore, then a sudden contraction to `duct_radius`. Default **off**. `--stepped-inlet` on the optimizer. Not notched blade tips, not a Noctua-traced SID, not a new OpenFOAM patch.  
**Roadmap:** §2.6 stage 1. Noctua’s stepped inlet is a frame-lip tone trick; our screening “frame” is a tube, so the lip lives on `casing.stl`.

## Plain language

Noctua’s Stepped Inlet Design is a step on the **intake of the housing**, not a nick in the blade. Our circular screening duct is a straight cylinder. Stage 1 adds a 6 mm long, 1.2 mm deep enlargement at the inlet end (`domain_z_min`, flow +Z) so the flow hits a sudden contraction before the rotor. Default NSGA stays a plain tube. Do not claim quieter BPF until an LBM pass. Notched tips are a different trick and stay later.

## Problem

```text
build_casing_solid(rig) → constant inner_r = duct_radius  for the whole Z
```

There is no inlet lip. Square-tunnel (`circular_duct=False`) has no tube to step.

## Goal

1. **Constants** in `fansim/cfd/casing.py`:

```text
STEP_DEPTH_MM = 1.2    # radial enlargement of the inlet bore
STEP_LEN_MM   = 6.0    # axial length of the larger bore from zmin
```

2. **`build_casing_solid(rig, stepped=False)`** — default path **unchanged** (today’s tube). When `stepped=True`, one revolved solid:

```text
inner r(z):
  zmin → zmin+STEP_LEN :  duct_radius/mm + STEP_DEPTH
  then                  :  duct_radius/mm
outer r               :  inner(z) + CASING_WALL_MM   (or constant duct_r + wall + step, simpler)
Z span                :  domain_z_min … domain_z_max  (mm)
```

Prefer a **constant outer radius** `duct_r + CASING_WALL_MM + STEP_DEPTH` so the outside is still a cylinder. Raise if `Solids() != 1`.

3. **`export_casing_stl(rig, path, *, stepped=False)`** — pass through.

4. **`evaluate_candidate(..., stepped_inlet=False)`**

```text
circular_duct False → ignore stepped_inlet (no tube); raw["inlet"] = "none"
circular_duct True, stepped_inlet False → today’s tube; raw["inlet"] = "plain"
circular_duct True, stepped_inlet True  → export_casing_stl(..., stepped=True); raw["inlet"] = "stepped"
```

Same `casing.stl` / `casing` patch. No new snappy name.

5. **CLI** — `scripts/run_optimization.py --stepped-inlet` (store_true, default off) through `run_study`. No `★`. Cockpit stays a plain tube this cycle.

## Honesty

This is a **concentric inlet contraction** on the screening cylinder, not a copy of Noctua’s SID geometry (their step is on a 25 mm square frame with struts). Do not claim tone reduction. Square vs stepped CFM are not comparable; stamp `inlet` and leave old catalog rows without the key.

## Tests (no Docker mesh)

- Default `build_casing_solid(rig)` still matches today’s tube (bbox / mid-span inside-wall / bore empty). Existing `test_casing.py` stays green.
- Stepped: one solid; at `zmin+1` a point at `inner_r + 0.4` is **outside** the solid (in the enlarged bore); at mid-Z that same radius is **inside** the wall.
- At `zmin+1`, a point at `inner_r + STEP_DEPTH + 1` is inside the wall.
- `export_casing_stl(..., stepped=True)` writes > 1 KB.
- Monkeypatch: `stepped_inlet=True` calls casing export with `stepped=True` (extend `_stop_after_case_build` or a tiny wrapper). `raw["inlet"] == "stepped"`.
- `--stepped-inlet` in `run_optimization.py`; no `★`.

## Non-goals

- Notched / serrated blade tips
- Tracing a photographed Noctua inlet
- New OpenFOAM patch name
- Cockpit switch
- Square-tunnel step
- LBM tone campaign
- Changing `locationInMesh`
