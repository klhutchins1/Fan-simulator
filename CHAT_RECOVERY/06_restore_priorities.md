# Suggested restore priorities for Claude

Work on `T:\Projects\Fan Simulator`. Prefer any recovered byte-identical files over regeneration.

## Phase 0 — inventory what already landed on T:

List tree; note which of these already exist from other restore attempts:
`pyproject.toml`, `fansim/`, `scripts/`, `tests/`, `docs/`, `catalog/`, `uv.lock`

## Phase 1 — skeleton that imports

1. Recreate package layout from `02_module_inventory.md`
2. Minimal `pyproject.toml` with deps cited in chats (numpy, scipy, cadquery, trimesh, optuna, trame, pyvista, …) + `dev`/`optim` extras
3. Stub modules with docstrings pointing at contracts in `04_physics_and_review_notes.md`
4. `scripts/cockpit.py` + `scripts/run_optimization.py` argparse surface from chat flags

## Phase 2 — geometry first (highest test value)

1. `airfoil.py` NACA4 + rounded_plate
2. `blade.py` BladeParams / build_impeller / cylindrical tip trim
3. `export.py` watertight STL
4. Restore/adapt tests: `test_geometry.py`, `test_rounded_plate.py`, `test_le_te_thick.py`, `test_span_interp.py`, `test_features.py`

## Phase 3 — optimize plumbing without Docker

1. `search_space.py`, `presets.py`, `system_curve.py`, `objectives.py` gates (mountable, vibration, build)
2. `fan_bem.py` + bem-prescreen (fix Euler power; ducted tip-loss honesty)
3. `study.py` Optuna NSGA wiring with mockable evaluate

## Phase 4 — CFD templates

1. `templates.py` / `openfoam_case.py` / `runner.py` / `metrics.py`
2. Docker image `opencfd/openfoam-default:2406`
3. Keep screening-fidelity honesty in README

## Phase 5 — cockpit

1. Thin `app.py` + fan tab modules (`fan_*`) or monolithic if faster
2. Tabs: Fan / Mixed / Volute / Prop / CROR
3. Lazy plotters; Assess → isolated eval worker

## Phase 6 — secondary archetypes

`propeller/`, `centrifugal/`, `volute/`, `cror/`, `acoustics/`, `wind_turbine/` scaffold

## Do not claim

- Exact Optuna trial STL geometry from CFM numbers alone
- Exact OpenFOAM dicts without a recovered copy
- That chat recovery equals the lost git history (`b360dde`, `a110f76` hashes are breadcrumbs only)

## Prompt seed for Claude

> Read `CHAT_RECOVERY/*.md` first. Rebuild `fansim` to match the module inventory and physics contracts. Prefer failing tests that encode the recovered names. Mark every regenerated file with a header comment `RECOVERED-FROM-CHAT` vs `RESTORED-BYTE-IDENTICAL` when you have a real copy.
