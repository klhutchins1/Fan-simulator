# Task 4 Report: Metrics parse + evaluate_prop_cfd

## Status
- Implemented `parse_prop_metrics`, `run_solve_prop`, and `evaluate_prop_cfd` for prop open-air compressible MRF.
- Added unit test `test_parse_prop_metrics_from_forces` using synthetic OpenFOAM `forces` outputs.

## Changes
- `fansim/propeller/cfd.py`
  - Added `parse_prop_metrics(case_dir, omega_rad_s)` reading `postProcessing/forces/*/{force.dat,moment.dat}` via `fansim.cfd.metrics._pp_file/_last_data_row`.
  - Added `run_solve_prop(runner, n_procs)` mirroring `openfoam_case.run_solve` but running `rhoSimpleFoam` (with `potentialFoam` seeding).
  - Added `evaluate_prop_cfd(spec, workdir, ...)` that builds a prop STL, sizes an open-air domain from STL bounds, writes the case, runs mesh + `rhoSimpleFoam`, parses thrust/torque/power, and stamps `solver/domain/regime/tip_mach/rpm/spec`.
- `tests/test_prop_cfd.py`
  - Added `test_parse_prop_metrics_from_forces`.

## Test Evidence
- `uv run python -m pytest tests/test_prop_cfd.py -v`

## Notes / Concerns
- Metrics are taken directly from the `forces` FO totals (no `rho` scaling, as required); thrust uses `force[3]` and torque uses `abs(moment[3])`.
