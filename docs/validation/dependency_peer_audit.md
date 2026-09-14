# Dependency and peer-repo audit (Task 4.1)

**Date:** 2026-09-14  
**Scope:** Critical runtime stacks for geometry, screening CFD, optimization, cockpit viz, and mesh I/O.  
**Sources:** `pyproject.toml`, `uv.lock`, `uv run` import checks, and in-repo smoke tests.

## Pin policy (this cycle)

| Decision | Rationale |
|----------|-----------|
| **No changes** to `pyproject.toml` / `uv.lock` | Lower bounds and viz caps already match how the tree is tested; resolved lock versions are consistent with smoke tests. |
| Python `>=3.12,<3.13` | Matches CadQuery/OCP wheels and project pytest/ruff target. |
| Viz caps `pyvista>=0.44,<0.49`, `trame>=3.6,<4`, `trame-vtk>=2.6,<3` | Avoids known PyVista 0.49+ / Trame 4 API churn before cockpit is re-validated. |

**Resolved versions (Windows, `uv.lock` + spot check 2026-09-14):**

| Package | `pyproject.toml` | Locked / env |
|---------|------------------|--------------|
| cadquery | `>=2.4` | 2.8.0 |
| cadquery-ocp (transitive) | — | 7.9.3.1.1 |
| scipy | `>=1.11` | 1.18.1 |
| trimesh | `>=4.0` | 5.1.0 |
| optuna (`[optim]`) | `>=3.6` | 5.0.0 |
| pyvista (`[viz]`) | `>=0.44,<0.49` | 0.48.4 |
| trame | `>=3.6,<4` | 3.13.2 |
| trame-vtk | `>=2.6,<3` | 2.8.13 |
| OpenFOAM Docker | (not in Python deps) | `opencfd/openfoam-default:2406` |

Version probe (optional):

```powershell
uv run --extra optim --extra viz python -c "import cadquery, scipy, trimesh, optuna, pyvista; print(cadquery.__version__, scipy.__version__, trimesh.__version__, optuna.__version__, pyvista.__version__)"
import importlib.metadata as m; print('cadquery-ocp', m.version('cadquery-ocp'))
```

On Windows, importing CadQuery can trigger a non-zero process exit **after** prints succeed (OCCT teardown); treat pytest’s summary line as authoritative (`docs/validation/suite_baseline_2026-09-14.md`).

---

## Per-package audit

### CadQuery / OCP

| | |
|--|--|
| **Role** | Parametric impeller loft, booleans, STL export (`fansim.geometry.build_impeller`). |
| **Smoke** | `tests/test_geometry.py::test_impeller_is_watertight_single_body` — fused solid, single body, watertight STL. |
| **Footgun** | Windows OpenCascade teardown (`0xC0000374` / `-1073741819`) after **green** pytest; not a geometry failure. Heavy builds in-process can also destabilize long test sessions — cockpit uses `build_stl_isolated` (`tests/test_isolated_build.py`). |

### OpenFOAM Docker (`opencfd/openfoam-default:2406`)

| | |
|--|--|
| **Role** | Steady incompressible fan cases: `simpleFoam`, snappyHexMesh, cylindrical MRF (`fansim/cfd/runner.py`, `templates.py`, `openfoam_case.py`). |
| **Image / tag** | `DEFAULT_IMAGE = "opencfd/openfoam-default:2406"`; container sources `openfoam2406` bashrc before each command. |
| **Smoke** | Fast: `tests/test_cfd.py::test_parse_fan_metrics`, `test_rig_dimensions_and_operating_point`. Docker-gated assembly (no mesh/solve): `tests/test_cfd.py::test_case_build_files` (`@pytest.mark.docker`). Manual: `docker images -q opencfd/openfoam-default:2406` via `fansim.cfd.runner.image_available()`. |
| **Footgun** | Docker not run in default CI/fast suite (`-m "not docker"`). Bind-mount paths must go through subprocess `docker` (runner already does) to avoid MSYS path mangling on Windows. MRF is a **frozen bulk rotation**, not AMI/sliding mesh — do not claim transient blade-resolved physics. Phase 3: free-air CFM still ~−32% vs published reference; speed or dependency tweaks do not close that honesty gap. |

### Optuna

| | |
|--|--|
| **Role** | Multi-objective blade search (`NSGAIISampler`, three maximize objectives + optional noise minimize) in `fansim/optimize/study.py`. |
| **Smoke** | `tests/test_optimize.py` (multi-direction study wiring), `tests/test_search_space.py`, `tests/test_optuna_storage.py`. Prune integrity: `tests/test_cror_optimize.py` (depth gate must **not** emit fake `(0, 0)` NSGA points). |
| **Footgun** | Global plan constraint: **no fake Optuna prune** — failed BEM/geometry gates must `PRUNED` or `FAIL`, not zero objectives. SQLite storage concurrency is custom-wrapped; don’t assume default Optuna examples for parallel workers. |

### PyVista / Trame / trame-vtk

| | |
|--|--|
| **Role** | Cockpit 3D plotters (`pyvista.trame.ui.plotter_ui`) on Fan / Prop / Mixed / Volute tabs. |
| **Smoke** | Unit-level mesh checks: `tests/test_glyphs.py`, `tests/test_midplane.py`, `tests/test_acoustics.py` (`pytest.importorskip("pyvista")`). Cockpit shell wiring: `tests/test_cockpit_view.py` (figures/data; no full server start in fast suite). |
| **Footgun** | **Protocol-before-start:** `VtkRemoteLocalView.update_geometry` runs during widget build, but `server.protocol` exists only after `server.start`. Current trame-vtk raises `ValueError: Protocol does not exist yet` without deferral — patched in `fansim/cockpit/trame_vtk_compat.py` (`patch_trame_vtk_protocol_defer()` from `fansim/cockpit/app.py`). Keep viz pins until Trame 4 / PyVista 0.49 migration is tested. |

### trimesh

| | |
|--|--|
| **Role** | STL watertight metrics, preview-vs-fused bounds, rough wall / export helpers. |
| **Smoke** | `tests/test_geometry.py::test_impeller_is_watertight_single_body` (`watertight_report`), `tests/test_isolated_build.py::test_preview_mesh_matches_fused_bounds`, `tests/test_wall_ks.py` (tiny STL export). |
| **Footgun** | STL coordinates are **millimeters** in geometry export but **meters** in OpenFOAM case placement (`fansim/cfd/domain.py` scale). Mixing units breaks rig sizing and reported CFM. |

### SciPy

| | |
|--|--|
| **Role** | Shape-preserving span interpolation (`PchipInterpolator` when `BladeParams.span_interp == "pchip"`), stats in loading studies, general numerics alongside NumPy. |
| **Smoke** | `tests/test_span_interp.py` (linear default + PCHIP mid-skew smoothing), `tests/test_loading.py` (`scipy.stats.spearmanr`). |
| **Footgun** | PCHIP is for **spanwise design curves**, not for replacing BEM/CFD discontinuities. Default remains `linear` for backward-compatible loft behavior. |

---

## Peer references: we match / we differ

Skimmed public patterns (documentation and reference implementations), not line-by-line parity.

### OpenFOAM MRF fan CFD

| Reference | What they do | We match | We differ |
|-----------|--------------|----------|-----------|
| [OpenFOAM User Guide — MRF](https://doc.openfoam.com/2312/tools/pre-processing/mesh/advanced/mrf/) | `MRFProperties` on a `cellZone`, `omega` in rad/s, patches listed as `nonRotatingPatches`, steady incompressible RANS | Same solver class (`simpleFoam`), MRF zone around rotor, ω from RPM, wall/inlet/outlet non-rotating | Custom snappyHexMesh + duct/frame/casing/stator STLs; not a textbook “fan inside box” tutorial mesh. Single-zone MRF (plus dual-zone CROR), not AMI/sliding interfaces. |
| ESI / OpenCFD Docker `opencfd/openfoam-default:2406` | v2406 tool chain and `bashrc` layout | Image tag and `openfoam2406` env sourcing in `OpenFOAMRunner.run` | Case templates maintained in-repo (`fansim/cfd/templates.py`), not shipped with upstream tutorials |

### BEMT / propeller performance (CCBlade / QProp class)

| Reference | What they do | We match | We differ |
|-----------|--------------|----------|-----------|
| [NREL CCBlade](https://github.com/NREL/CCBlade.jl) / blade-element momentum docs | Radial strips, Cl/Cd, thrust/torque integration | Prop path in `fansim/propeller/bemt.py` is QProp/JavaProp-class strip integration; tests in `tests/test_bemt.py` (RPM scaling, registry sanity) | No CCBlade airfoil tables; analytic/UIUC polars in-tree. Ducted **fan** BEM (`fansim/fan_bem.py`) adds gap leakage and omits Prandtl — see `docs/validation/math_audit_2026-09-14.md` §10.3–10.4 |
| QProp / ETC propeller BEM sign conventions (`Vt = Ωr(1−a′)`) | Tangential induction in swirl iteration | After math audit **10.4**, prop BEMT couples axial + tangential induction (`V_t = Ωr − V̄_θ`) | Axial fan screening uses separate BEM closure, not QProp’s prop-centric input decks |

### Optuna multi-objective

| Reference | What they do | We match | We differ |
|-----------|--------------|----------|-----------|
| [Optuna multi-objective tutorial](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/002_multi_objective.html) | `directions=[...]`, Pareto-aware sampler | `NSGAIISampler` + three maximize fan objectives (+ optional noise minimize); `tests/test_mountable.py`, `tests/test_shroud.py` | Custom `fansim/optimize/ladder.py` Pareto export, BEM/geometry **prune gates**, isolated CFD eval workers — not a minimal tutorial loop |

---

## Related validation docs

- Fast suite baseline: `docs/validation/suite_baseline_2026-09-14.md`
- Math / BEM sign fixes: `docs/validation/math_audit_2026-09-14.md`
- Phase 3 CFD honesty (free-air gap): `docs/validation/a12x25_pq_report.md`

## Commands (regression spot-check)

```powershell
cd "T:\Projects\Fan Simulator"
uv run --extra optim --extra viz --extra dev python -m pytest `
  tests/test_geometry.py tests/test_cfd.py tests/test_span_interp.py `
  tests/test_isolated_build.py tests/test_cror_optimize.py -q --tb=no -m "not docker"
# Optional with local Docker image:
uv run python -m pytest tests/test_cfd.py::test_case_build_files -q
```
