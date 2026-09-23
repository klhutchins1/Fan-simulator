# §4.4 step 2: obj_2 wall-resolved MRF diagnostic

**Date:** 2026-09-23  
**Status:** approved (2026-09-23)  
**Approach:** A — one `rhoSimpleFoam` MRF solve, same case as the smoke, `MeshResolution.for_blade` with prism layers  
**Parent:** roadmap §4.4 (step 1 done; step 3 stays parked)  
**Related:** `validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json`, `fansim/cfd/openfoam_case.py` (`MeshResolution.for_blade`)

## Plain language

The obj_2 smoke reports about 938 g and 2034 W on a mesh that does not resolve the blade wall. This slice runs that same propeller, at the same RPM, with surface refinement picked from the measured wall and with prism layers on. It writes thrust, shaft power, and figure of merit next to the smoke fixture, and it says whether the STL is an axial rotor or a radial impeller. It does not have a pass band. The question is whether the ~2 kW is the geometry or the coarse wall.

## Goal

1. **One case:** `obj_2_ccw.stl` at **25257** RPM, spin **−1**, `base_cell` **0.005** m, **400** iterations, **8** procs, Docker `opencfd/openfoam-default:2406`, solver `rhoSimpleFoam`, regime `compressible-MRF`.
2. **Wall mesh:** measure the blade wall from the STL, then `MeshResolution.for_blade(0.005, min_wall_mm, add_layers=True)`. Prism count stays the class default **3**. Surface level stays inside the existing cap **`SURF_LEVEL_MAX` = 4**.
3. **Report:** thrust, shaft power, and figure of merit beside the smoke fixture. State the layout label. State whether level 4 actually put three cells through the measured wall.
4. **Honesty:** a finished finite result is stamped. A failed solve is recorded as a failure. Neither one rewrites the smoke, refine, or GCI fixtures.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | From each face centroid, cast a ray along the inward normal (opposite the outward normal). Ignore hits closer than **0.05 mm**. Wall thickness is `float(np.percentile(hits, 5))` on the rest. Fewer than **20** hits raises `RuntimeError`. The absolute minimum is recorded and is not what picks the mesh level |
| 2 | `for_blade` is called with that percentile, `add_layers=True`, and `base_cell=0.005`. `evaluate_prop_cfd` still builds `MeshResolution(base_cell=...)` when no mesh is passed |
| 3 | `wall_resolved` is true only when `base_cell / 2**surf_max` in mm is **≤** `min_wall_mm / 3` |
| 4 | Layout is **`axial`** when diameter / axial extent **≥ 2**, otherwise **`radial`**. Diameter is `2 * tip_radius_mm`. The report also gives the area-weighted mean `\|n_r\|` and `\|n_z\|` on faces whose centroid radius is **> 0.3** of tip radius. If mean `\|n_r\|` **>** mean `\|n_z\|`, the sentence says the outer surfaces face outward |
| 5 | Figure of merit is `T**1.5 / sqrt(2 * rho * A) / P` with `A = pi * R**2`, `R` from `measure_prop_stl`, and `rho = P_INF * 28.9 / (8314.462618 * T_INF)` using `P_INF` and `T_INF` from `fansim.propeller.cfd`. Smoke FM in the report uses the smoke fixture's thrust and power with this same density |
| 6 | CI tests cover the percentile, the resolved check, the layout rule, the figure of merit, and that the default mesh path is unchanged. No Docker in CI |
| 7 | One Docker solve writes `runs/drone_radial_cfd/wall/obj_2/`. A finite thrust and power stamp `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json` and mark roadmap §4.4 step 2 done. A failure leaves step 2 open and writes no stamp |
| 8 | `docs/validation/drone_radial_open_air_cfd.md` gains a wall-mesh section that quotes the JSON or records the failure, and notes that BEMT Prandtl–Glauert also raises stalled lift, so this CFD result is not a BEMT comparison |

## Non-goals

- A thrust or power pass band
- obj_1, a mesh ladder, or a new GCI
- AMI, a timestep change, or signed-thrust work (roadmap §4.4 step 3)
- Editing `_compressibility_cl_cd` or the BEMT loop
- y+ from a turbulence field. The resolved flag is the three-cell geometric check only
- Overwriting `obj_2_ccw_smoke.json`, `obj_2_ccw_refine.json`, or `obj_2_ccw_gci.json`
- Changing `evaluate_prop_cfd` results when the new mesh argument is omitted
- Mission presets (roadmap §14.7)

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | Optional `mesh` argument on `evaluate_prop_cfd`. A one-shot script measures the STL, builds `for_blade`, and calls that path | Same solver and domain as the smoke. Default callers stay on surf levels 1 and 2 with layers off |
| B | New solve loop that copies `evaluate_prop_cfd` | Two places to drift apart |
| C | Turn layers on for every prop smoke | Changes the screening mesh this diagnostic is comparing against |

## Ops (locked)

| Knob | Value |
|------|-------|
| STL | `validation/reference/drone_radial/obj_2_ccw.stl` |
| RPM | 25257 |
| spin | −1 |
| `base_cell` | 0.005 m |
| iters | 400 |
| procs | 8 |
| layers | on, `n_surface_layers` 3 |
| image | `opencfd/openfoam-default:2406` |
| workdir | `runs/drone_radial_cfd/wall/obj_2` (not committed) |
| smoke fixture | `validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json` (read only) |
| stamp | `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json` only after finite thrust and shaft power |

The prepared STL is the one that is measured, so tip radius, wall, and layout describe the mesh that was solved.

## Architecture

| Piece | Change |
|-------|--------|
| `fansim/propeller/wall_mesh.py` | `min_wall_mm(mesh) -> float`, `wall_sample(mesh) -> dict` with keys `min_wall_mm`, `abs_min_mm`, `n_hits`, `layout` (`axial` or `radial`), `mean_abs_nr`, `mean_abs_nz`, `faces_outward` (bool). `figure_of_merit(thrust_n, power_w, tip_radius_m) -> float`. `wall_resolved(base_cell_m, surf_max, min_wall_mm) -> bool`. `mesh_for_wall(base_cell_m, min_wall_mm) -> MeshResolution` |
| `fansim/propeller/cfd.py` | `evaluate_prop_cfd(..., mesh: MeshResolution \| None = None)`. `None` keeps `MeshResolution(base_cell=base_cell)` |
| `scripts/run_prop_obj2_wall.py` | Locked defaults, one solve, stamp or honest failure |
| `tests/test_prop_wall_mesh.py` | Unit tests, no Docker |
| `docs/validation/drone_radial_open_air_cfd.md` | Wall-mesh section |
| `docs/roadmap.md` | Step 2 marked done only after a finite stamp |

`mesh_for_wall` returns `MeshResolution.for_blade(base_cell, min_wall_mm, add_layers=True)`.

## Error handling

`main` catches only `RuntimeError` (missing STL, fewer than 20 wall hits, or a failed solve). It writes `result.json` with `thrust_g: null` and `shaft_power_w: null`, and exits **1**. Any other exception propagates. The stamp is written only when both thrust and shaft power are finite. When a mesh is passed into `evaluate_prop_cfd`, blockMesh and snappy use that mesh, including its `base_cell`.

## Testing

CI only for the unit tests. The Docker solve is one local run, recorded in the validation note. Do not commit `runs/`.
