# Task 3 + Task 4 Implementation Report (BEMT gate)

## Task 3 — `scripts/evaluate_prop_cfd.py --bemt-floor`

- Added CLI flag `--bemt-floor` (default `0.0`).
- Wired through to `fansim.propeller.cfd.evaluate_prop_cfd(..., bemt_floor_g=...)`.
- Adjusted “Docker image missing” behavior:
  - If the design is **skipped by BEMT floor**, still writes `result.json` and exits `0`.
  - If CFD would run but the image is missing, exits `2` (unchanged intent).

## Task 4 — Pareto CFD refine helper + CLI wiring

### `fansim/propeller/optimize.py`

- Added `refine_pareto_cfd(spec, pareto, out_dir, *, n_top, bemt_floor_g=0.0, **eval_kw) -> list[dict]`
  - Creates `rank_XX/` workdirs under `out_dir`
  - Calls `fansim.propeller.cfd.evaluate_prop_cfd` with the reconstructed `BladeParams`
  - Returns a summary list containing `rank`, `workdir`, `bemt_thrust_g`, `skipped` and `reason` (and `cfd_thrust_g` when run)
  - Imports `evaluate_prop_cfd` inside the function so tests can monkeypatch it without Docker

### `scripts/run_prop_optimization.py`

- Added CLI flags:
  - `--cfd-top N` (default `0`)
  - `--bemt-floor G` (default `0.0`)
  - `--cfd-out PATH` (default `runs/prop_cfd_refine/<spec>/`)
- After printing the Pareto front, when `--cfd-top > 0`:
  - Runs `refine_pareto_cfd(...)`
  - Writes `summary.json` under `--cfd-out`
  - If Docker image is missing and **any** of the top-N cases would actually run (not skipped), exits `2`

## Tests

- Updated `tests/test_prop_bemt_gate.py`:
  - Asserts `--bemt-floor` is declared in `scripts/evaluate_prop_cfd.py`
  - Asserts `--cfd-top`, `--bemt-floor`, `--cfd-out` are declared in `scripts/run_prop_optimization.py`
  - Unit-tests `refine_pareto_cfd` using a monkeypatched `evaluate_prop_cfd` (no Docker)

Run:

```bash
uv run python -m pytest tests/test_prop_bemt_gate.py -q --tb=short
```
