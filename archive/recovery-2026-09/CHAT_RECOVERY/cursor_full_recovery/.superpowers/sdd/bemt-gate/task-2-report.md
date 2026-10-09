# Task 2 Report — Floor gate on `evaluate_prop_cfd`

## Summary
- Extended `fansim/propeller/cfd.py:evaluate_prop_cfd` with `params: BladeParams | None = None` and `bemt_floor_g: float = 0.0`.
- Added a BEMT pre-check at the CFD RPM and an early-return **skip** path when `bemt_thrust_g < bemt_floor_g`, ensuring no OpenFOAM/Docker steps run.
- When `params` is provided, STL generation now uses `build_impeller(params)` + `export_stl(...)` (instead of `build_prop(spec, ...)`) so custom chord/camber is respected.
- CFD results are stamped with `bemt_thrust_g` when the solve runs.

## Implementation details
- **Blade resolution**: `blade = params if params is not None else prop_blade_params(spec)`.
- **BEMT RPM**: uses the same RPM as CFD (`0.7*spec.rpm_max` when `rpm is None`, else the provided `rpm`).
- **Skip dict**: returns `{"skipped": True, "reason": "...", "bemt_thrust_g": ..., "rpm": ..., "tip_mach": ..., "spec": ...}`.
- **STL path**:
  - `params is None`: keeps legacy `build_prop(spec, stl)` behavior (incl. bore defaults).
  - `params is not None`: `export_stl(build_impeller(blade), stl, tolerance=0.02, angular_tolerance=0.1)` then `watertight_report(stl)` for bounds.

## Tests
- Added `tests/test_prop_bemt_gate.py::test_evaluate_prop_cfd_skips_below_bemt_floor`, which monkeypatches `run_mesh`/`run_solve_prop` to fail if called and asserts skip behavior under an impossible floor.
