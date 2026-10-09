# Mixed-flow impeller (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** A printable mixed-flow impeller that still fits the A12x25 cup + 110 mm frame + 25 mm depth. Conical hub, blades lofted on a diagonal meridional line (eye → tip), registered as the `centrifugal` archetype. Not a volute squirrel-cage, not NSGA, not a new CFD domain.  
**Roadmap:** §4.1 stage 1. High-pressure radial machines are why this exists; stage 1 is geometry + the archetype stub so a later campaign can mesh it in the existing axial duct.

## Plain language

An axial fan in a 25 mm frame cannot make much static pressure. A true centrifugal + volute would, but it does not drop into a Noctua through-flow square: inlet and exhaust are both axial. Mixed-flow is the honest topology in this envelope — air still goes in the front and out the back, but the hub is a cone and the blades run diagonally so the flow picks up a radial component.

The registry already has a `centrifugal` stub. Stage 1 fills it with that mixed-flow solid. Default NSGA stays axial. CFD stays `scripts/validate_stl.py` on the exported STL (same MRF duct). Do not claim it beats A12x25 at 20 Pa until that campaign exists.

## Problem

```text
get_archetype("centrifugal").build_geometry(...)  →  NotImplementedError
BladeParams + cylinder hub                    →  radial span, axial through-flow
```

A spinner cone on today’s axial hub is not mixed-flow. A 90° radial wheel needs a volute and a different outlet. Neither is this slice.

## Goal

1. **Params** `fansim/centrifugal/geometry.py` (mm):

```text
n_blades     = 9
r_eye_mm     = 16.0     # hub radius at the inlet (+Z nose)
r_back_mm    = 28.0     # hub radius at the motor end; must be >= mount_min_hub_radius (19.825)
r_tip_mm     = 54.5     # 110/2 − 0.5 mm leftover
z_span_mm    = 18.0     # hub + blade axial length; bbox depth must stay <= 25
chord_mm     = 22.0
stagger_deg  = 35       # from rotation plane, same convention as BladeParams
thickness    = 0.08     # fraction of chord
max_camber   = 0.04
```

`r_back_mm` is the motor-end hub. Raise if `r_back_mm < mount_min_hub_radius(A12X25)`. `r_eye_mm` must be `< r_back_mm` (cone grows in the flow / toward the motor).

2. **Solid** `build_mixed_flow(params) -> cq.Workplane`

```text
hub  = revolved truncated cone, r_eye at z_max, r_back at z_min, height z_span_mm
       (intake is +Z, motor / carve-cup face is −Z, same as carve_motor_mount)

blade = makeLoft of NACA4 sections along a diagonal:
        r_frac 0 → (r_eye,  z_max)     # root at the eye
        r_frac 1 → (r_tip,  z_min)     # tip at the back OD
        intermediate r,z linear in r_frac
        section construction = existing _section_points_3d (stagger, chord, naca4)
        n_span ~ 12

pattern n_blades around Z, fuse onto hub → one solid. Raise if Solids() ≠ 1.
```

Reuse `fansim.geometry.airfoil.naca4` and the axial section helper; do not copy-paste a second NACA. Do not go through `BladeParams` / `build_impeller` — that loft is cylinder-hub radial span.

3. **Export** `export_mixed_flow_stl(params, path, *, mount=A12X25.motor_mount)` via shared `export_stl`. After the fuse, `carve_motor_mount(..., r_back_mm)` so a print has the cup. If the cup cannot carve, still write the aero solid and return the `fits=False` message (same honesty as axial export).

4. **Archetype** replace the `centrifugal` stub:

```text
class MixedFlowArchetype(Archetype):
    name = "centrifugal"
    regime = "incompressible-RANS-MRF"
    suggest_design(trial) → MixedFlowParams with the defaults above
                            (n_blades 7–11, stagger 25–45 if a trial is passed; stage 1 may ignore trial)
    build_geometry(params, path) → export_mixed_flow_stl
    evaluate(...) → NotImplementedError pointing at validate_stl.py
    objective_names / directions → same as axial (cfm_free, cfm_load, efficiency)
```

`propeller` and `wind_turbine` stay stubs.

5. **Problem yaml** `config/problems/mixed_flow_a12x25.yaml` — `archetype: centrifugal`, same envelope constraints as axial (119 / 25 is the yaml number; geometry itself caps to 110 mm ID leftover). Notes: mixed-flow drop-in, not a volute.

6. **CLI** `scripts/export_mixed_flow.py` — write one STL (default params, A12x25 cup). No `★` in help. No `--stator`. Not on `run_optimization.py` this cycle (that script is axial NSGA).

## Honesty

This is a **diagonal mixed-flow rotor in a through-flow 25 mm frame**, registered under the existing `centrifugal` key. It is not a blower wheel, not a volute, and not proof that high-static PC fans should be mixed-flow. The axial MRF duct is the wrong domain for a radial machine and an acceptable first domain for mixed-flow that still exits axially. Do not change `evaluate_candidate` or cockpit.

## Tests (no Docker mesh)

- `r_back < mount_min` raises; `r_eye >= r_back` raises.
- One solid after fuse.
- Bounding box: `2*xmax <= 110.0 + 0.2`, `zmax - zmin <= 25.0 + 0.2`.
- Hub at rear: a point at `(r_back - 1, 0, zmin + 1)` is inside; a point at `(r_eye + 1, 0, zmax - 1)` is inside; a point on the axis at mid-z is inside the cone.
- Mid-span on blade 0 is inside; halfway between blades at mid-r is outside.
- `export_mixed_flow_stl` writes > 1 KB.
- `get_archetype("centrifugal")` is `MixedFlowArchetype`; `build_geometry` writes a file; `evaluate` raises `NotImplementedError`.
- `get_archetype("propeller")` still raises on `suggest_design`.
- `load_problem(mixed_flow_a12x25.yaml).archetype == "centrifugal"`.
- `scripts/export_mixed_flow.py` declares a parser; no `★`.

## Non-goals

- Volute / 90° radial discharge / squirrel-cage
- `evaluate_candidate` / NSGA / cockpit switch
- Mixed-flow BEM / Euler pump formula as a screen
- Searching cone angle in Optuna (defaults only; trial knobs optional no-ops)
- Changing the axial loft to “also do mixed-flow”
- Layers, stator, or circular-duct changes
