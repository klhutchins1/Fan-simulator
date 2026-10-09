# Architecture (from chats)

## One-line product

Axial PC-fan design loop: **CadQuery geometry → isolated OpenFOAM (optional FluidX3D) → Optuna NSGA → SQLite catalog**, with a **Trame + Vuetify3 + Plotly + PyVista** cockpit as the interactive front door.

Scale remembered from audit chat:
- ~**126** Python modules under `fansim/`
- ~**90** test files / ~**720** tests (numbers varied slightly across snippets)
- ~**89** design-related artifacts mentioned in one summary

## Axial evaluate spine

```
suggest_params
  → blade_from_flat
  → evaluate_candidate (fansim/optimize/objectives.py)
  → two-point MRF CFD
  → ObjectiveResult.as_tuple  # cfm_free, cfm_load, efficiency[, noise]
  → run_study (Optuna study.db + trials/*/ + pareto.json)
  → catalog.build_catalog ← runs/*/ + validation/measurements/
  → cockpit browse / Assess
```

## Cockpit Assess path

```
on_assess
  → evaluate_candidate_isolated
  → _eval_worker   # crash-isolated CadQuery/CFD
  → cockpit_assess/design_*/design.json
```

Catalog is an **index only** — does not own OF cases; stable id shape remembered as `<run>_t<trial>`.

## Cockpit UI

- Entry: `scripts/cockpit.py` → `fansim.cockpit.app.build_server(run_dir, study_name)`
- Flags: `--run`, `--study-name`, `--port`, `--reload` (watches `fansim/` + `validation…`)
- Stack: Trame + Vuetify3 `SinglePageLayout`, Plotly scatters, PyVista plotters:
  `plotter`, `prop_plotter`, `mf_plotter`, `volute_plotter`
- Top tabs (`state.active_tab`): **Fan → Mixed → Volute → Prop → CROR**
- Fan subtabs (`state.fan_subtab`): **Design | Results | Library**
- Note from review: huge `except Exception` surface (~76) — UI stays up; failures become captions
- Archetype layer partially abandoned: `get_archetype("propeller")` still raises `NotImplementedError` while `fansim/propeller/` is a full stack

## Largest modules (line counts from audit)

| Lines | Path |
|------:|------|
| 4939 | `fansim/cockpit/app.py` (pre- or mid-extract; later fan tab split moved much of Fan UI) |
| 916 | `fansim/cfd/templates.py` |
| 745 | `fansim/geometry/blade.py` |
| 420 | `fansim/optimize/objectives.py` |
| 379 | `fansim/cfd/openfoam_case.py` |

Post-extract note from later work: `app.py` shrunk (~135 lines cited in one snippet) while `fan_tab.py` held ~3420 — then further split into `fan_*` modules.

## Tooling

- Package manager / runner: **`uv`**
- CFD Docker image: **`opencfd/openfoam-default:2406`**
- Solver stack remembered: **simpleFoam + k-ω SST + MRF**, kinematic pressure × ρ (`rhoInf=1` on kinematic pTot)
