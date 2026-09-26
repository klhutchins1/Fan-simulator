# Loaded-branch diagnostic ladder (roadmap §19.6): design

Date: 2026-09-26 · Status: approved ("just start")

## Problem

At CFD v3 in the designed rotation, the Stock A12x25 matches free air (58.7 vs 60.1 CFM) but collapses
under load:
- 5 Pa gives 21.6 CFM (unconverged, 11% oscillation);
- 10 Pa gives −6.2 CFM;
- the shut-off comes out at 9.5 Pa, against the published 22.9 Pa.

## Goal: validation truth for the Stock fan

Find which physics or domain lever restores the loaded branch. Expensive one-off runs are acceptable. A
cheap per-design version for the optimizer is a later, separate spec.

## Pass criteria

All of the following, from `docs/a12x25-reference.md` tolerances:
- the shut-off is within 22.9 ± 5 Pa;
- the loaded points converge (rule A, or its time-series equivalent for URANS);
- free air is within 60.1 ± 10%.

A rung that passes gets an extra 20 Pa point.

## Ladder

The rungs are cumulative, and the ladder stops at the first rung that passes. Probe points are 0, 5, 10
and 15 Pa. The Stock recipe runs at 2000 rpm with a 0.5 mm tip gap.

1. **plenum.** A cylindrical duct runs from the inlet past the rotor, ending half a duct diameter
   downstream of the impeller, and opens into a box with half-width 3 × duct radius. This is an
   outlet-chamber test: swirl dissipates in the box, and static pressure is read at the box outlet. The
   pressure definition is unchanged (outlet static − inlet total = back-pressure).
2. **frame.** Rung 1 plus the four-bar frame (existing `export_frame_stl`, from the fitted rig), inside
   the duct.
3. **urans.** Rung 2 solved transient: `pimpleFoam`, the same k-ω SST RAS model, frozen-rotor MRF,
   `adjustTimeStep` with maxCo 1.5, and 10 rotor revolutions (0.3 s at 2000 rpm). The metric is the mean
   over the last 25% of the history (the last 2.5 revs). Convergence uses rule A on that tail.

A sliding (AMI) rotor is out of scope. If rung 3 fails, it becomes its own spec.

## Components

- `fansim/cfd/casing.py`: `build_casing_solid(rig, stepped=False, plenum_z_mm=None)` ends the tube at
  `plenum_z_mm` when given; `export_casing_stl(..., plenum_z_mm=None)` passes it through.
- `fansim/cfd/openfoam_case.py`: `build_case(..., box_scale: float | None = None)` sets the hex
  half-width to `box_scale × duct_radius` when a casing is present. The default stays `BOX_SCALE`.
- `fansim/cfd/openfoam_case.py`: `apply_urans_transient(case_dir, *, end_time, delta_t=1e-5, max_co=1.5)`
  rewrites `controlDict` (the steady function objects with `pimpleFoam`, adjustable time step and
  sampling every step), `fvSchemes` (the transient `DES_FV_SCHEMES`) and `fvSolution`
  (`DES_FV_SOLUTION`). The turbulence model stays RAS k-ω SST. `run_solve_urans(runner, n_procs)` runs
  `pimpleFoam`.
- `scripts/run_loaded_ladder.py`:
  - `--rung plenum|frame|urans`, `--points 0,5,10,15`, `--procs`, `--iters`, `--out`;
  - writes `docs/validation/loaded_ladder/<rung>.json`, containing rows plus the verdict;
  - pure `ladder_verdict(rows, published_shutoff=22.9, published_free=60.1)` returns PASS / FAIL /
    INCONCLUSIVE with reasons, using `fansim.validation.pq_shutoff.shutoff_report_from_pq_rows`.
- Report: `docs/validation/a12x25_loaded_ladder.md`. `a12x25_pq_report.md` and roadmap §19.6 are updated
  with the answer.

## Testing

No-CFD unit tests cover:
- the plenum casing bounds;
- the `box_scale` blockMesh extents;
- the placement check with a plenum and a frame;
- the URANS files (application, adjustTimeStep, RAS model, function objects present);
- `ladder_verdict` cases.

The CFD runs themselves are controller execution.
