# Drone radial open-air CFD (smoke)

**Status:** campaign recorded 2026-09-21 — obj_1 finished with finite metrics; **gate failed** (force-tail drift); obj_2 **not run**  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical). WSL-native OpenFOAM is optional later — not documented as a second path here.

## Honesty

Steady compressible MRF on a truncated box with smoke mesh (`base_cell=0.005 m`) is a
**screening** record. Tip Mach is stamped; shocks are not resolved. Not OEM / datasheet grade.
No success fixture was frozen for this campaign (gate failed).

## Geometry

| Case | STL | ~D |
|------|-----|----|
| obj_1 | `validation/reference/drone_radial/obj_1_ccw_impeller.stl` | ~60 mm |
| obj_2 | `validation/reference/drone_radial/obj_2_ccw.stl` | ~90 mm |

RPM from tip Mach ≈ 0.35: `rpm = Ma * 343 * 60 / (2π R)` (R from `.meta.json`).
(Campaign used Ma=0.35 after Ma≈0.38 blew up without T limiter; templates now include `limitTemperature` + milder relaxation.)

| Case | RPM (Ma≈0.35) |
|------|----------------|
| obj_1 | 38100 |
| obj_2 | 25257 (not run) |

## Gate (before obj_2)

1. Solver exit 0  
2. Finite thrust/torque/power  
3. `|thrust_g| ≥ 10`  
4. Force-z tail drift < 10% over last 25% of `force.dat`

### Campaign gate outcome (obj_1)

| Check | Result |
|-------|--------|
| Finite metrics | pass (`thrust_g≈74.2`, `shaft_power_w≈236`) |
| `|thrust_g| ≥ 10` | pass |
| Force-z tail drift < 10% | **fail** — drift ≈ **23.4%** |
| obj_2 | **skipped** |

An 800-iter retry made forces worse (thrust collapsed near zero); retained the 400-iter run above.

## Commands

Dry-run:

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.005 --iters 400 --procs 8 \
  --out runs/drone_radial_cfd/_dry_run/obj_1 --dry-run
```

Full obj_1 (requires Docker image):

```bash
uv run python scripts/evaluate_prop_cfd.py \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --rpm 38100 --base-cell 0.005 --iters 400 --procs 8 \
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

Obj_2 only if gate passes — same knobs (`--rpm 25257`, `--stl …/obj_2_ccw.stl`). **Not run this campaign.**

Freeze (when gate passes):

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
| obj_1 | ~74.2 | ~236 | 0.35 | ~23.4 (gate fail) | *not frozen* |
| obj_2 | — | — | — | — | skipped |

Local run dir (gitignored): `runs/drone_radial_cfd/obj_1_smoke/`.

## Template fixes landed during campaign

`PROP_FV_SCHEMES` / `PROP_FV_OPTIONS` needed: `wallDist.method meshWave`, `div(phi,Ekp)`, `div(phiMRF,p)`, `div(phid,p)`, `limitTemperature`, milder SIMPLE relaxation — otherwise `rhoSimpleFoam` aborted or blew up on this mesh/RPM.
