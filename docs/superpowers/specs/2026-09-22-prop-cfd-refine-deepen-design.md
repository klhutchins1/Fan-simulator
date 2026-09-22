# §4.3 deepen: refine mesh campaign + Prop CFD refine knobs

**Date:** 2026-09-22  
**Status:** implemented (2026-09-22) — both refine fixtures; refine gate uses late-window `--tail-frac 0.10`  
**Approach:** A — parallel `*_refine` fixtures (10% drift gate) + expose mesh/iters on existing Prop CFD refine top-N card  
**Parent:** `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md` (smoke campaign implemented)  
**Roadmap:** §4.3 deepen — finer screening CFD; does **not** claim datasheet or grid independence.

## Plain language

Smoke CFD on the drone radial STLs is a coarse first pass (25% force-tail gate). This deepen
re-runs both props with a finer mesh and more iterations, and only freezes new **refine**
fixtures if thrust wobble drops under **10%**. Smoke fixtures stay as the cheap baseline.
Then the Prop Optimize “CFD refine top-N” card gets smoke/refine presets so the same knobs
drive Pareto CFD without a second button.

## Goal

1. **Fidelity:** Refine open-air `rhoSimpleFoam` on `obj_1_ccw_impeller` and `obj_2_ccw`.
2. **Gate:** Freeze `*_refine.json` only when finite metrics, `|thrust_g| ≥ 10`, and force-tail drift **&lt; 10%**.
3. **Preserve smoke:** Do not overwrite `*_smoke.json`.
4. **Cockpit:** Wire `base_cell` / `iters` (smoke vs refine preset) into the existing CFD refine top-N card.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | Documented refine campaign commands + results in `docs/validation/drone_radial_open_air_cfd.md` |
| 2 | Each STL either has a committed `*_refine.json` (gate pass) or an honest “attempted, gate failed” note |
| 3 | Smoke fixtures unchanged |
| 4 | Prop CFD refine card can select smoke (`0.005`/`400`) or refine (`0.004`/`600`) knobs; values reach `evaluate_prop_cfd` |
| 5 | CI unit tests only (no Docker) |

## Non-goals

- Overwriting smoke fixtures  
- WSL-native OpenFOAM as a second canonical runner  
- New Prop button / Assess for arbitrary STL (STL remains CLI)  
- AMI / DES / FW-H / datasheet claims  
- Auto mesh-adaptation loop until 10% (one fixed refine knob set this slice)

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | Parallel refine fixtures + knobs on existing CFD card | Keeps smoke baseline; matches UI choice |
| B | Replace smoke fixtures | Loses cheap baseline |
| C | Fidelity harness only, no cockpit | Skips chosen UI deepen |

## Stage 1 — Refine campaign

**Runner:** Docker `opencfd/openfoam-default:2406` only.

**Knobs (starting):** `--base-cell 0.004`, `--iters 600`, `--procs 8`, Ma ≈ 0.35 RPM (same formula as smoke: obj_1 **38100**, obj_2 **25257**).

**Order:**

| Step | Action | Location |
|------|--------|----------|
| 0 | Optional dry-run both STLs | `runs/drone_radial_cfd/_dry_run_refine/` |
| 1 | Full solve obj_1 | `runs/drone_radial_cfd/obj_1_refine/` |
| 2 | Gate @ 10% drift | — |
| 3 | Full solve obj_2 (independent of obj_1 gate) | `runs/drone_radial_cfd/obj_2_refine/` |
| 4 | Gate @ 10% | — |
| 5 | Freeze only passers | `validation/reference/drone_radial/cfd/*_refine.json` |
| 6 | Update validation md + roadmap | docs |

**Gate:** Reuse `prop_cfd_smoke_gate(..., drift_tol_pct=10, tail_frac=0.10)` for refine
freezes (late-window). Default library `FORCE_TAIL_FRAC` stays **0.25** for smoke;
refine freezer passes `--tail-frac 0.10` explicitly. Amended after sparse FO sampling
made a 25% sample window include settling on obj_1.

**Freezer:** Add `--drift-tol` (default 25 for back-compat). Refine freeze uses `--drift-tol 10 --require-gate`.

**Fixture IDs:** `obj_1_ccw_impeller_refine`, `obj_2_ccw_refine`. Same schema as smoke; `notes` mention refine mesh + 10% gate. `mesh.base_cell_m` / `iters` record actual knobs.

**If gate fails:** Document in validation md; no fake refine fixture.

## Stage 2 — Cockpit CFD refine knobs

**Existing path:** Prop Optimize card → `refine_prop_cfd` → `refine_prop_pareto_cfd` → `evaluate_prop_cfd` (already accepts `**eval_kw`).

**UI:** On that card, add a preset (or two number fields):

| Preset | `base_cell` | `iters` |
|--------|-------------|---------|
| Smoke (default) | 0.005 | 400 |
| Refine | 0.004 | 600 |

Pass `base_cell` and `iters` into `refine_prop_pareto_cfd(..., base_cell=..., iters=...)`. Busy ticker / messages include which preset ran. No second button. No Optuna-in-loop CFD.

## Tests (CI — no Docker)

- Freezer CLI declares `--drift-tol`; gate fails when drift ≥ tol.
- `refine_pareto_cfd` (or cockpit helper) forwards `base_cell` / `iters` into mocked `evaluate_prop_cfd`.
- Committed `*_refine.json` load/stamp checks when present (skip if campaign gate-failed both).
- Existing smoke fixture tests remain green.

## Documentation

- Extend `docs/validation/drone_radial_open_air_cfd.md`: refine knobs, 10% gate, results table, smoke vs refine.
- Roadmap §4.3: refine stage note.
- Spec status → implemented when campaign + cockpit land (or “partial” if only one stage).

## File map (expected)

| Path | Role |
|------|------|
| `scripts/freeze_prop_cfd_fixture.py` | `--drift-tol` |
| `fansim/propeller/cfd_fixture.py` | unchanged defaults (25%); callers pass 10 for refine |
| `fansim/cockpit/prop_tab.py` | preset / knobs on CFD refine card |
| `fansim/propeller/optimize.py` | already forwards `**eval_kw` — verify only |
| `validation/reference/drone_radial/cfd/*_refine.json` | if gate passes |
| `docs/validation/drone_radial_open_air_cfd.md` | report |
| `tests/test_prop_cfd_fixture.py` / cockpit or optimize test | unit coverage |

## Honesty

Refine is still steady compressible MRF in a truncated box — a **finer screen**, not grid-independent or datasheet-grade. Tip Mach stamped; shocks not resolved. Smoke (25% gate) remains the cheap baseline; refine (10% gate) is the higher bar when attainable.
