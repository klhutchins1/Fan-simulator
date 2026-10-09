# Wind-turbine archetype scaffold (registry wiring)

**Date:** 2026-09-11  
**Status:** approved for implementation  
**Approach:** 1 — registry scaffold (not full HAWT stack)

## Goal

Replace the loud `wind_turbine` `_StubArchetype` with a real `WindTurbineArchetype` that
implements `suggest_design` / `build_geometry` / `evaluate` and registers under
`get_archetype("wind_turbine")`.

## Non-goals

- No cockpit tab, Optuna study CLI, or aeroelastic coupling
- No field-validated `Cp` claims
- No RANS / OpenFOAM domain for turbines in this stage
- Do not delete the registry key

## Package

`fansim/wind_turbine/`:

| Module | Role |
|--------|------|
| `params.py` | `WindTurbineParams` dataclass (diameter_m, hub_radius_m, n_blades, tip_speed_ratio, pitch_deg, freestream_ms) |
| `geometry.py` | Map params → `BladeParams` (turbine-ish twist) + `export_stl` |
| `evaluate.py` | BEM-lite / actuator-disk screen → `Cp`, `power_w` + honesty stamp |
| `archetype.py` | `WindTurbineArchetype` |

## Behavior

- **suggest:** defaults when `trial is None`; Optuna suggests n_blades, TSR, pitch when given a trial
- **build_geometry:** loft via shared impeller core; return STL path
- **evaluate:** screen only. `Cp = P / (0.5 ρ A V³)`, `A = π R²`. Always stamp  
  `raw["honesty"] = "scaffold: BEM-lite Cp screen; no aeroelastic / no RANS domain yet"`
- **objectives:** maximize `(Cp, power_w)`
- **regime:** `high-Re-BEM+RANS` (aspirational; evaluate stays BEM-lite)

## Registry

Lazy-register like propeller/volute. Remove `_StubArchetype` entry for `wind_turbine`.
`_StubArchetype` class may remain unused or stay for future stubs.

## Tests

- `get_archetype("wind_turbine")` is `WindTurbineArchetype`
- `suggest_design(None)` returns params
- `build_geometry` writes a non-empty STL (may be slow/CadQuery — mark if needed)
- `evaluate(..., bem_only=True)` or default screen returns finite `Cp`/`power_w` without Docker
- Update `test_stub_archetype_fails_loudly` — no stub left, or point at a different future key if any

## Docs

- Roadmap / `fansim.problem` docstring: wind_turbine no longer a stub
- Problem YAML optional (skip in stage 1)

## Honesty

This unblocks the registry; it does **not** make Fan-simulator a wind-turbine product.
Full HAWT (turbine-sign BEMT tables, freestream RANS, aeroelastic) is a later package.

## Status

- **2026-09-11:** Scaffold implemented (`fansim/wind_turbine/`, registry wired).
- **Parked for later:** full HAWT product path (BEMT tables, RANS domain, cockpit tab).
