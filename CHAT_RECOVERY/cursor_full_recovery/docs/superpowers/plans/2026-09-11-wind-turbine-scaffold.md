# Wind-Turbine Archetype Scaffold Implementation Plan

> **For agentic workers:** Execute task-by-task. Spec: `docs/superpowers/specs/2026-09-11-wind-turbine-scaffold-design.md`

**Goal:** Register a real `WindTurbineArchetype` with BEM-lite `Cp`/`power_w` screen and shared loft geometry.

**Tech Stack:** Python 3.12, pytest, existing `BladeParams` / `export_stl`, Optuna optional for suggest.

## File map

| File | Responsibility |
|------|----------------|
| `fansim/wind_turbine/params.py` | `WindTurbineParams` |
| `fansim/wind_turbine/geometry.py` | params → `BladeParams` + STL |
| `fansim/wind_turbine/evaluate.py` | BEM-lite screen + honesty |
| `fansim/wind_turbine/archetype.py` | Archetype class |
| `fansim/wind_turbine/__init__.py` | exports |
| `fansim/problem/archetypes.py` | lazy register |
| `tests/test_wind_turbine.py` | unit tests |
| `tests/test_problem.py` | drop stub expectation |

## Tasks

### Task 1: Params + evaluate screen (no CadQuery)

- Write tests for `WindTurbineParams` defaults and `evaluate_wind_turbine` finite `Cp`/`power_w` + honesty stamp
- Implement `params.py` + `evaluate.py`

### Task 2: Geometry + archetype + registry

- Write tests for `blade_params_from_wind`, archetype suggest/objectives, registry type
- Implement geometry + archetype; wire lazy registry; update problem docs/roadmap

### Task 3: Optional STL build smoke

- One test that `build_geometry` writes STL (CadQuery; skip if too heavy — prefer smoke with export)

Commit when user asks.
