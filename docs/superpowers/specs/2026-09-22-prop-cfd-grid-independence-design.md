# §4.3: Prop open-air grid independence (GCI)

**Date:** 2026-09-22  
**Status:** implemented (2026-09-22) — obj_1 ladder complete but **not** asymptotic (fine thrust drop); obj_2 asymptotic with ~16% fine GCI; screening only  
**Approach:** A — prop ladder CLI around `evaluate_prop_cfd` + existing Roache helper  
**Parent:** `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md`  
**Related:** `docs/superpowers/specs/2026-09-22-prop-cfd-refine-deepen-design.md` (screening refine; not a GCI ladder)  
**Roadmap:** §4.3 — drone_radial open-air GCI screening stamp recorded (AMI / polars / datasheet still remaining)

## Plain language

Smoke and refine fixtures show the props run and settle under force-tail gates. They do **not**
prove the thrust number is mesh-independent. This slice runs both STLs on three honest meshes
(coarse → fine), applies Roache GCI to thrust, and documents the uncertainty band — or honestly
reports when the order is undefined.

## Goal

1. **Ladder:** Both `obj_1_ccw_impeller` and `obj_2_ccw` at `base_cell` **0.005 / 0.0035 / 0.0025**.
2. **Fixed ops per STL:** Same RPM and iters on every rung (do not stitch smoke/refine fixtures).
3. **GCI:** Primary metric `thrust_g` via `fansim.analyze.grid_convergence.grid_convergence_index`.
4. **Report:** Validation md + roadmap note; optional committed summary JSON after a clean campaign.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | Script runs the honest three-level ladder via `evaluate_prop_cfd` (Docker `2406`) |
| 2 | Both STLs attempted; each has a summary with GCI fields or honest `gci: null` + reason |
| 3 | `docs/validation/drone_radial_open_air_cfd.md` and roadmap §4.3 updated |
| 4 | CI unit tests for summary / Roache wiring (no Docker) |
| 5 | Smoke and refine fixtures untouched |

## Non-goals

- Treating smoke/refine fixtures as GCI ladder rungs (different cells / RPM / iters)
- Extending fan `run_grid_convergence.py` / `grid_convergence_stl.py`
- AMI / DES / FW-H / datasheet claims
- Cockpit GCI button
- Force-tail drift as a pass/fail gate (diagnostic only this slice)
- WSL-native OpenFOAM as a second canonical runner

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | New `scripts/run_prop_grid_convergence.py` + reuse Roache helper | Clear prop path; ~6 Docker solves |
| B | Stretch fan STL GCI scripts into open-air props | Couples fan CFM path to prop thrust |
| C | Manual shell loop + hand md | Weak reproducibility |

## Ops (locked)

| Case | STL | RPM (Ma≈0.35) | iters | procs | cells |
|------|-----|---------------|-------|-------|-------|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | 38100 | 800 | 8 | 0.005, 0.0035, 0.0025 |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | 25257 | 800 | 8 | same |

**Metric for GCI:** `thrust_g`. Also record `shaft_power_w`, `tip_mach`, cell count (best effort), and force-tail drift % (informational).

## Architecture

**Components**

| Piece | Role |
|-------|------|
| `scripts/run_prop_grid_convergence.py` | CLI: STL × cells → `evaluate_prop_cfd` → ladder + Roache |
| `fansim.analyze.grid_convergence` | Unchanged Roache implementation |
| `evaluate_prop_cfd` | Unchanged Docker runner |
| `force_z_tail_drift_pct` | Per-rung diagnostic only |
| Validation md + roadmap | Human-facing GCI table |

**Run layout**

```
runs/drone_radial_cfd/gci/
  obj_1/{0.005,0.0035,0.0025}/result.json
  obj_2/{0.005,0.0035,0.0025}/result.json
  obj_1_gci_summary.json
  obj_2_gci_summary.json
```

**CLI sketch**

```bash
uv run python scripts/run_prop_grid_convergence.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --cells 0.005,0.0035,0.0025 --iters 800 --procs 8 \
  --out runs/drone_radial_cfd/gci/obj_1
```

Same for obj_2 at 25257. Script may also support `--both` with the baked RPM map above.

**Per rung:** mesh → solve → write `result.json`. **Resume:** skip rung if existing `result.json` has finite `thrust_g` unless `--force`.

**Summary JSON:** `levels[]` plus `gci` (`p`, `f_extrapolated`, `gci_fine_pct`, `gci_medium_pct`, `asymptotic_ratio`, `converged`) or `"gci": null` with a reason. Optionally copy summaries to `validation/reference/drone_radial/cfd/*_gci.json` after a clean campaign.

**Order:** obj_1 ladder, then obj_2 (independent).

## Failure modes

| Condition | Behavior |
|-----------|----------|
| Rung mesh/solve/non-finite thrust | Mark level failed; no GCI for that STL; continue other STL |
| Roache `ValueError` (flat / bad ordering) | `gci: null` + reason; still publish thrust table |
| High force-tail drift | Record only — do not abort ladder |
| CadQuery teardown AV after green JSON | Non-blocking (same as prior prop CFD) |

## Tests (CI — no Docker)

- Summary builder: three mocked finite levels → Roache fields via real `grid_convergence_index`.
- Incomplete / flat levels → `gci` null, no crash.
- Cell string parse / fine-medium-coarse ordering helpers if extracted.
- Existing `tests/test_grid_convergence.py` unchanged and green.

## Documentation

- Extend `docs/validation/drone_radial_open_air_cfd.md`: GCI knobs, per-level table, Roache row, asymptotic flag, “not datasheet.”
- Roadmap §4.3: GCI stage note + links to this spec and the plan.
- Spec status → implemented when both ladders + md land (or partial if one STL has undefined GCI).

## File map (expected)

| Path | Role |
|------|------|
| `scripts/run_prop_grid_convergence.py` | Ladder CLI |
| `fansim/analyze/grid_convergence.py` | reuse |
| `tests/test_prop_grid_convergence.py` | unit coverage |
| `docs/validation/drone_radial_open_air_cfd.md` | report |
| `docs/roadmap.md` | §4.3 note |
| optional `validation/reference/drone_radial/cfd/*_gci.json` | stamp after clean run |

## Honesty

GCI quantifies **discretization** uncertainty for this steady compressible-MRF open-air setup. It does not make the result datasheet-grade, resolve shocks, or replace AMI / freestream polars. Smoke (25% gate) and refine (10% late-window) remain screening baselines; this slice is the mesh-error stamp for §4.3.
