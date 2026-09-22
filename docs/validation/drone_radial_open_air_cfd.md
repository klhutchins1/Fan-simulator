# Drone radial open-air CFD (smoke + refine)

**Status:** recorded 2026-09-22 — smoke fixtures for both STLs; refine fixture for **obj_2** only (obj_1 refine gate failed)  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is optional later — not documented as a second path here.

## Honesty

Steady compressible MRF on a truncated box is a **screening** record. Tip Mach is stamped; shocks are not resolved. Not OEM / datasheet grade.

| Tier | Mesh | Iters | Force-tail gate |
|------|------|-------|-----------------|
| Smoke | `base_cell=0.005` | 400 | **&lt; 25%** |
| Refine | `base_cell=0.004` | 600 | **&lt; 10%** |

## Geometry

| Case | STL | ~D |
|------|-----|----|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | ~60 mm |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | ~90 mm |

RPM from tip Mach ≈ 0.35: `rpm = Ma * 343 * 60 / (2π R)`.

| Case | RPM (Ma≈0.35) |
|------|----------------|
| obj_1 | 38100 |
| obj_2 | 25257 |

## Smoke campaign

### Gate outcome

| Case | Finite | `|thrust_g|≥10` | Drift | Gate @ 25% |
|------|--------|-----------------|-------|------------|
| obj_1 | pass | pass (~74 g) | ~23.4% | pass |
| obj_2 | pass | pass (~938 g) | ~4.7% | pass |

### Results

| Case | thrust_g | shaft_power_w | tip_mach | drift_% | fixture |
|------|----------|---------------|----------|---------|---------|
| obj_1 | 74.2 | 236 | 0.35 | 23.4 | `…/cfd/obj_1_ccw_impeller_smoke.json` |
| obj_2 | 938 | 2034 | 0.35 | 4.7 | `…/cfd/obj_2_ccw_smoke.json` |

## Refine campaign (2026-09-22 deepen)

### Gate outcome

| Case | Finite | `|thrust_g|≥10` | Drift | Gate @ 10% |
|------|--------|-----------------|-------|------------|
| obj_1 | pass (~65 g) | pass | ~31.2% | **fail** — no refine fixture |
| obj_2 | pass (~949 g) | pass | ~3.8% | **pass** |

### Results

| Case | thrust_g | shaft_power_w | tip_mach | drift_% | fixture |
|------|----------|---------------|----------|---------|---------|
| obj_1 | ~65 | ~257 | 0.35 | 31.2 (fail) | *not frozen* |
| obj_2 | 949 | 2058 | 0.35 | 3.8 | `…/cfd/obj_2_ccw_refine.json` |

### Commands

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.004 --iters 600 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_refine

uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm 25257 --base-cell 0.004 --iters 600 --procs 8 \
  --out runs/drone_radial_cfd/obj_2_refine

uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_2_refine/result.json \
  --out validation/reference/drone_radial/cfd/obj_2_ccw_refine.json \
  --id obj_2_ccw_refine \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --spin -1 --base-cell 0.004 --iters 600 --procs 8 \
  --drift-tol 10 --require-gate
```

Cockpit: Prop Optimize **CFD mesh** preset Smoke (`0.005`/`400`) or Refine (`0.004`/`600`) on the existing CFD refine top-N card.

Local run dirs (gitignored): `runs/drone_radial_cfd/obj_*_{smoke,refine}/`.

## Template fixes (smoke campaign)

`PROP_FV_SCHEMES` / `PROP_FV_OPTIONS`: `wallDist.method meshWave`, `div(phi,Ekp)`, `div(phiMRF,p)`, `div(phid,p)`, `limitTemperature`, milder SIMPLE relaxation.
