# Drone radial open-air CFD (smoke)

**Status:** campaign / pending measured fixtures  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is optional later — not documented as a second path here.

## Honesty

Steady compressible MRF on a truncated box with smoke mesh (`base_cell=0.005 m`) is a
**screening** record. Tip Mach is stamped; shocks are not resolved. Not OEM / datasheet grade.

## Geometry

| Case | STL | ~D |
|------|-----|----|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | ~60 mm |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | ~90 mm |

RPM from tip Mach ≈ 0.38: `rpm = Ma * 343 * 60 / (2π R)` (R from `.meta.json`).

| Case | RPM (Ma≈0.38) |
|------|----------------|
| obj_1 | 41366 |
| obj_2 | 27422 |

## Gate (before obj_2)

1. Solver exit 0  
2. Finite thrust/torque/power  
3. `|thrust_g| ≥ 10`  
4. Force-z tail drift < 10% over last 25% of `force.dat`

## Commands

Dry-run:

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 41366 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/_dry_run/obj_1 --dry-run
```

Full obj_1 (requires Docker image):

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 41366 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_1_smoke
```

Gate check after `result.json` exists:

```bash
uv run python -c "
import json
from pathlib import Path
from fansim.propeller.cfd_fixture import prop_cfd_smoke_gate
r = json.loads(Path('runs/drone_radial_cfd/obj_1_smoke/result.json').read_text())
ok, reasons = prop_cfd_smoke_gate(r, case_dir='runs/drone_radial_cfd/obj_1_smoke')
print('ok', ok); print('\n'.join(reasons))
"
```

Obj_2 only if gate passes — same knobs:

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_2_ccw.stl \
  --rpm 27422 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/obj_2_smoke
```

Freeze:

```bash
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
| obj_1 | pending | pending | pending | pending | `validation/reference/drone_radial/cfd/obj_1_ccw_impeller_smoke.json` |
| obj_2 | pending | pending | pending | pending | `validation/reference/drone_radial/cfd/obj_2_ccw_smoke.json` |
