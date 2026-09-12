# Module inventory (recovered names)

Treat missing files as **targets to recreate**, not confirmed present on T:.

## `fansim/geometry/`

- `blade.py` — `BladeParams`, `RadialStation`, `build_impeller`
- `airfoil.py` — NACA4 + `rounded_plate`; `BladeParams.section_family`
- `features.py` — tubercles / serrations / dimples
- `export.py` — STL + watertight checks
- `_build_worker.py` — crash-isolated build
- Cylindrical tip: `cylindrical_tip` + `_trim_blade_to_tip_cylinder` (boolean OCCT)

## `fansim/cfd/`

- `domain.py` — `TestRig`, tip gap (`OPTIMIZER_TIP_GAP_MM` remembered ~0.5 mm default)
- `openfoam_case.py` — `build_case`, mesh/solve orchestration
- `templates.py` — ~916 lines of OpenFOAM dicts; `residualControl` ~1e-4
- `runner.py` — `OpenFOAMRunner`, `image_available()`
- `metrics.py` — `FanMetrics`; convergence via outlet-flow drift (~2% over last 25% iters)
- `frame.py`, `stator.py`, `casing.py`, midplane helpers
- LBM-related: `lbm_geometry_ab.py`, `lbm_shutoff.py` (shut-off residual CFM)

## `fansim/optimize/`

- `objectives.py` — `evaluate_candidate`, mountable/build/weight gates
- `study.py` — `run_study`, Pareto summary
- `search_space.py` — Optuna DOFs; hub/tip ranges remembered ~ hub 17–28 mm, tip 48–58 mm
- `system_curve.py`, `isolated_eval.py`, `cli_argv.py`
- `presets.py` — `case`≈8 Pa, `heatsink`≈20, `radiator`≈35 @ 50 CFM
- `design.py` — `Design` dataclass (moved here late; cockpit `data.py` re-exports)
- surrogates hooks, print/motor penalties, `_eval_worker.py`

## `fansim/cockpit/` (supporting slices named in review)

- `data.py` — `load_designs`, `Design` (re-export)
- `placement.py` — `fit_envelope`, `scale_to_hub`, `measure_flat`, `placed_child_record`
- `library_view.py`, `busy.py`, `score_caption.py`
- Later extract (this thread): `fan_session`, `fan_copy`, `fan_widgets`, `fan_models`,
  `fan_assess`, `fan_optimize`, `fan_viz`, `fan_ui`, `fan_tab`
- Public API: `setup_fan_tab` / `render_fan_tab`
- Lazy PyVista: only Fan plotter at startup; Mixed/Volute/Prop on first visit (`plotters.ensure_plotter`)

## `fansim/propeller/`

Open-rotor path: `bemt.py`, `geometry.py`, `optimize.py`, `cfd.py`, `polar.py`, `polars.py`,
`noise.py`, `persist.py`, `calibrate.py`

## `fansim/centrifugal/` (mixed-flow)

`geometry.py` (`MixedFlowParams`), `bem.py`, `evaluate.py`, `optimize.py`, `persist.py`,
`archetype.py`, workers

## `fansim/volute/`

Radial blower + scroll: `geometry.py`, `case.py`, `evaluate.py`, `domain.py`, `archetype.py`

## `fansim/cror/`

Counter-rotating: `geometry.py` (`CrorParams`), `optimize.py`, `evaluate.py`, `noise.py`, `persist.py`

## `fansim/acoustics/`

`fwh.py` (Farassat / permeable / patches), `farfield.py`, `proxies.py`, `tonal.py`,
`loading.py`, `case.py`

## `fansim/structural/`

Gates: stress / vibration / tip deflection (PETG BPF vs bend frequency gates seen in opt logs)

## `fansim/manufacturability/`

`fdm_rules.py`, `printability_score.py`, `print_export.py`, `materials.py` (`DEFAULT_MATERIAL`, PETG)

## `fansim/surrogate/`

Catalog GP (`gp.py`, `catalog.py`), boost / optional NN hooks

## Other top-level package pieces

- `fansim/fan_bem.py` (or `fansim/fan…` — chat truncated; BEM + `--bem-prescreen`)
- `fansim/isolated_job.py` — shared `run_worker_module`, `load_objective_result` (this thread)
- `fansim/wind_turbine/` — scaffold only (BEM-lite); full HAWT parked
- Geometry/centrifugal/volute thin `isolated.py` wrappers

## Scripts (remembered)

- `scripts/cockpit.py`
- `scripts/run_optimization.py`
- `scripts/run_baseline.py`
- `scripts/run_fan_curve.py`
- `scripts/catalog.py`

## Docs (remembered)

- `docs/roadmap.md` (large; §1–§12 style; mojibake scrubbed late)
- `docs/design-rules.md`
- `docs/adversarial-review.md` (stale vs README in places — review said stamp historical)
- `docs/validation/north-star-staged.md`
- `docs/fluidx3d-setup.md`, `docs/high-accuracy-plan.md`
- Specs under `docs/superpowers/specs/`:
  - `2026-09-11-fan-tab-extract-design.md`
  - `2026-09-11-wind-turbine-scaffold-design.md`
  - `2026-09-04-boost-ensemble-surrogate-design.md`
  - `2026-09-04-cockpit-opt-live-resume-design.md`
