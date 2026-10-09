# Task 1 Report: `bemt_thrust_g` + Pareto → BladeParams helper

## Status
**Complete** — TDD cycle finished; tests green; committed.

## Changes

### `fansim/propeller/optimize.py`
- Added `bemt_thrust_g(params, spec, *, rpm=None) -> float` — wraps `analyze()` and returns `perf.thrust_g`, defaulting RPM to `spec.rpm_max`.
- Added `blade_params_from_trial_params(spec, p: dict) -> BladeParams` — rebuilds blade geometry from Optuna trial dict keys (`n_blades`, `pitch_in`, `chord_root/mid/tip`, `camber`) via the same `dataclasses.replace` + `prop_blade_params` path as `suggest_prop`.

### `tests/test_prop_bemt_gate.py`
- `test_bemt_thrust_g_finite` — default fpv_5inch prop yields positive finite thrust.
- `test_blade_params_from_trial_params_roundtrip` — FixedTrial params round-trip through `suggest_prop` vs `blade_params_from_trial_params`.

## TDD Evidence
1. Wrote tests first → `ImportError: cannot import name 'bemt_thrust_g'` (expected).
2. Implemented minimal helpers per brief.
3. `uv run python -m pytest tests/test_prop_bemt_gate.py -q --tb=short` → **2 passed**.

## Commit
- `Add BEMT thrust helper and trial-to-BladeParams conversion.`
- Files: `fansim/propeller/optimize.py`, `tests/test_prop_bemt_gate.py`
- `catalog/catalog.db` not staged.

## Concerns
None — implementation matches brief exactly; roundtrip test confirms parity with `suggest_prop` export path.
