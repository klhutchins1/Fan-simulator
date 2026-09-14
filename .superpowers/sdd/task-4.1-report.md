# Task 4.1 Report — Dependency & peer-repo audit

**Status:** DONE  
**Date:** 2026-09-14

## Deliverables

| Item | Path | Notes |
|------|------|-------|
| Audit doc | `docs/validation/dependency_peer_audit.md` | Versions from `pyproject.toml` / `uv.lock`; smoke tests; footguns; peer match/differ tables |
| Pin changes | — | **None** — existing ranges and viz caps justified in doc |
| Commit | (this task) | Message: `Document dependency peer audit and justified pins.` |

## Verification

- Read `fansim/cfd/runner.py`: confirmed `opencfd/openfoam-default:2406` and `openfoam2406` bashrc sourcing.
- Spot-checked lock versions for cadquery 2.8.0, cadquery-ocp 7.9.3.1.1, scipy 1.18.1, trimesh 5.1.0, optuna 5.0.0, pyvista 0.48.4, trame 3.13.2, trame-vtk 2.8.13.
- `uv run --extra optim --extra viz python -c "..."` printed core versions; process exit non-zero on Windows after CadQuery/OCCT teardown (expected noise).

## Concerns / deferrals

- None blocking Task 4.1. Task 4.2 (perf baselines) intentionally not started.
- Docker-gated OpenFOAM smoke remains optional on developer machines without the image.

## Out of scope (honored)

- No push.
- `CHAT_RECOVERY/` untouched.
- Task 4.2 not implemented.
