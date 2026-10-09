# README / docs claims audit (QA r4 request 8), master f238f54, 2026-10-09

**Scope:**
- Every concrete claim in `README.md` (134 lines) and `docs/a12x25-reference.md` (53 lines), checked against the code on a clean clone (`/workspace/fansim/repo-r4`, `uv sync --extra dev`, Linux).
- CFD numbers were checked only for consistency with the cited validation docs. No CFD was re-run.

**Legend:** **FALSE** = contradicted by the code or by behaviour; **STALE** = was true once / points at superseded state; **GAP** = true, but a first-time reader will trip on it.

## Findings

| # | where | claim | verdict | evidence |
|---|---|---|---|---|
| D1 | README:12 | `Plan: ../../.claude/plans/i-want-a-plan-smooth-sifakis.md` | **FALSE** (on any machine but the author's) | The path is outside the repo, in a personal Claude plans dir. It doesn't exist on a clean clone. Remove it, or move the plan into `docs/`. |
| D2 | a12x25-reference:26 (+ `docs/validation/a12x25_geometry_acceptance.md:16`) | Geometry band "tip **55–57 mm**" (radius) | **FALSE / STALE** | Stock itself is `tip_radius 54.5` (`config/problems/a12x25_reference.yaml:14`, `tests/test_a12x25_reference_geometry.py:18`), which is *outside* the band. A radius ≥ 55 also contradicts the same doc's own 110 mm frame ID with 0.5 mm clearance (r ≤ 54.5) and `fan_spec` `tip_dia_mm (95,110)`. The band should be ≈ 54–54.5 mm (or Ø 108–109). |
| D3 | a12x25-reference:24 | "until **Task 3.1** mesh study tightens X/Y" | **STALE** | Roadmap 3.1 is "Application presets (case / heatsink / radiator), DONE 2026-09-01", not a mesh study. The validated CFD v5 and GCI work since then are not mentioned. |
| D4 | a12x25-reference:28–38 "Immediate reality check" | Slip duct walls; no frame/struts/venturi; no resolved tip leakage; coarse mesh, grid convergence pending | **STALE** | README:42 states CFD v5 = **sealed ring + four-bar frame + prism layers**, validated (59.8 vs 60.1 CFM; pq_report + audit-02). The section reads as the current state. It should be marked historical, or rewritten. |
| D5 | a12x25-reference:53 | "the (unbuilt) **FW-H** aeroacoustic tier" | **STALE** | README:28 describes a working GPU noise tier (FluidX3D LBM, Curle dipole → BPF tone + relative dB(A)). The FW-H wording no longer matches the noise path that exists. |
| D6 | README:93 quickstart | `uv run python scripts/cockpit.py --run runs/opt_mountable --reload` | **GAP** | `runs/` doesn't exist on a clean clone. It still starts: `build_server('runs/opt_mountable')` works and shows Stock. But it silently creates `./catalog/catalog.db` **relative to the CWD**, the same class of bug as UI-19. Say "the run dir may be empty/new", or point at an empty dir. |
| D7 | README:36, 110–112, 127–128 | `catalog.py build / list --pareto / show opt_mountable_t1` | **GAP** | The commands and flags exist (`build`, `stats`, `list --pareto --measured`, `show design_id`), and the id format `<run>_t<trial>` matches `validation/store.make_design_id`. But `catalog/catalog.db` is gitignored (`.gitignore:14`) and `validation/measurements/` doesn't exist until the first measurement, so on a clean clone `show` has nothing to show until a run + `build`. |
| D8 | README:129 (+ :130 `build/`) | `config/fan_models/` drop-in YAML specs; `build/` reference STLs | **GAP** | The directory doesn't exist on a clean clone. It's created on the first cockpit "save as user model" (`fan_spec.USER_MODELS_DIR = Path("config/fan_models")`, **CWD-relative**, like D6/UI-19). `build/` is likewise absent (it is the scripts' default `--out-dir`). The layout block reads as if these ship. |
| D9 | README:91–98 setup | `uv sync --extra dev` gives pytest/ruff; the surrogate extra gives sklearn; Python 3.12 | true | `pyproject`: `requires-python >=3.12,<3.13`, `dev = pytest, pytest-cov, ruff, mypy`, `surrogate = scikit-learn`. **GAP:** the `propulsion` extra (`setuav-pythrust`) isn't mentioned. Without it, 2 test modules skip at collection (`test_prop_power_propulsion.py`, `test_pythrust_export_propulsion.py`); they appear as "2 skipped" in every run. |
| D10 | README:92 | fast tests `-m "not docker and not slow"`, "same as CI" | true | `.github/workflows/ci.yml` runs the same markers (plus `--tb=line`, and `mypy` first). The README states **no test count**. For reference: 1573 passed (r3) on master e48a32d, 22 slow passed + 2 skipped (r4, this round). |
| D11 | README:23, 83 | OpenFOAM in Docker `opencfd/openfoam-default:2406`; 8-core parallel | true | `cfd/runner.py:14`, `propeller/cfd_fixture.py:12`; `--procs` default 8 (`run_optimization.py:51`, `openfoam_case.py:122`). |
| D12 | README:84 | FluidX3D at `../FluidX3D`; `FANSIM_FLUIDX3D`, `FANSIM_MSYS_BIN` | true | `fansim/external_tools.py`. |
| D13 | README:104–120 | `run_optimization --space guided --extended --mountable --noise --trials 30 --out`; `export_finalists --run --material`; `prune_runs [--apply]`; `validate_a12x25`; `score_feature_noise --run` | true (the flags exist) | argparse checked. `--space` choices are `open/guided/guided_lc`. `validate_a12x25` runs OpenFOAM (needs Docker), and the README's "(CFD; needs Docker)" note covers it. Not executed (no CFD). |
| D14 | README optimizer | Optuna NSGA-II | true | `optimize/study.py:50` `NSGAIISampler(population_size=16)`. |
| D15 | README materials | PLA, PLA+, PETG (default), ABS, TPU | true | `manufacturability/materials.py:27–38`. TPU is flagged as excluded for blades. |
| D16 | README features | tubercles / serrations / dimples | true | `geometry/features.py:8–10`. |
| D17 | README:77 | cockpit "Record measurement" panel | true | `fan_tab_ui.py:369` "Record measurement (physical)". |
| D18 | README:42–49 | CFD v5 numbers (59.8 vs 60.1 CFM, −0.5 %; 52.5/41.0 CFM at 5/10 Pa; FAN-01 +2.6/+3.1 %; Stock v2 56.5/49.8/40.2) | consistent with the cited docs | All numbers appear in `docs/validation/a12x25_pq_report.md` / audit-02 / `fan01_report.md`. Not re-run. |
| D19 | a12x25-reference table | 60.1 CFM = 0.02836 m³/s = 102.1 m³/h; 2.34 mmH₂O = 22.9 Pa; 2000 RPM = 209.4 rad/s; 9 blades; 0.5 mm clearance | true (the arithmetic) | 60.1 × 4.71947e-4 = 0.028364 m³/s = 102.11 m³/h. 2.34 × 9.80665 = 22.95 Pa. 2π·2000/60 = 209.44. 9 blades matches Stock `n_blades 9`. |
| D20 | (related, not in the two docs) `config/design_space.yaml:3–5` | `n_blades: 7`, `tip_radius: 56.5 # inside a 120 mm frame` | **STALE** | This is still the default `--params` for `scripts/run_baseline.py` and `run_fan_curve.py`. It contradicts 9 blades / 54.5 / 110 mm frame ID. `docs/validation/a12x25_geometry_acceptance.md:5` itself says "earlier docs incorrectly said 7". |
| D21 | a12x25-reference:26 link | `validation/a12x25_geometry_acceptance.md` | true | Resolves relative to `docs/`. |

**Not checkable here:** the external Noctua datasheet values (they match the repo's own tables, but no WebFetch was done), GPU noise, and anything needing Docker/CFD.

## Suggested tracker items
- **DOC-1 (LOW):** D1, the personal plan path.
- **DOC-2 (MED):** D2, the tip band excludes Stock and contradicts the frame clearance.
- **DOC-3 (LOW):** D3–D5, the a12x25-reference "reality check" / Task 3.1 / FW-H text is stale.
- **DOC-4 (LOW):** D6–D9, clean-clone gaps (empty runs/, catalog.db, config/fan_models, propulsion extra). Also: catalog/ and fan_models are CWD-relative (UI-19 class).
- **DOC-5 (LOW):** D20, `config/design_space.yaml` is still a 7-blade / 56.5 mm / 120 mm-frame default.
