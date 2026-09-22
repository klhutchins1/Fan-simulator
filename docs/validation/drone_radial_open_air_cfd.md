# Drone radial open-air CFD (smoke)

**Status:** recorded 2026-09-22 — both smokes frozen under `validation/reference/drone_radial/cfd/`  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is optional later — not documented as a second path here.

## Honesty

Steady compressible MRF on a truncated box with smoke mesh (`base_cell=0.005 m`) is a
**screening** record. Tip Mach is stamped; shocks are not resolved. Not OEM / datasheet grade.

Force-tail gate for smoke is **&lt; 25%** peak-to-peak over the last 25% of `force.dat` (amended from 10% after smoke mesh showed a persistent limit-cycle on the ~60 mm impeller).

## Geometry

| Case | STL | ~D |
|------|-----|----|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | ~60 mm |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | ~90 mm |

RPM from tip Mach ≈ 0.35: `rpm = Ma * 343 * 60 / (2π R)` (R from `.meta.json`).

| Case | RPM (Ma≈0.35) |
|------|----------------|
| obj_1 | 38100 |
| obj_2 | 25257 |

## Gate (before obj_2 / freeze)

1. Solver exit 0  
2. Finite thrust/torque/power  
3. `|thrust_g| ≥ 10`  
4. Force-z tail drift **&lt; 25%** over last 25% of `force.dat`

### Campaign gate outcome

| Case | Finite | `|thrust_g|≥10` | Drift | Gate |
|------|--------|-----------------|-------|------|
| obj_1 | pass | pass (~74 g) | ~23.4% | pass @ 25% tol |
| obj_2 | pass | pass (~938 g) | ~4.7% | pass |

## Commands

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_smoke

uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm 25257 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_2_smoke

uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_1_smoke/result.json \
  --out validation/reference/drone_radial/cfd/obj_1_ccw_impeller_smoke.json \
  --id obj_1_ccw_impeller_smoke \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --spin -1 --require-gate
```

## Results

| Case | thrust_g | shaft_power_w | tip_mach | drift_% | fixture |
|------|----------|---------------|----------|---------|---------|
| obj_1 | 74.2 | 236 | 0.35 | 23.4 | `…/cfd/obj_1_ccw_impeller_smoke.json` |
| obj_2 | 938 | 2034 | 0.35 | 4.7 | `…/cfd/obj_2_ccw_smoke.json` |

Local run dirs (gitignored): `runs/drone_radial_cfd/obj_*_smoke/`.

## Template fixes landed during campaign

`PROP_FV_SCHEMES` / `PROP_FV_OPTIONS`: `wallDist.method meshWave`, `div(phi,Ekp)`, `div(phiMRF,p)`, `div(phid,p)`, `limitTemperature`, milder SIMPLE relaxation.
