# §4.3: Prop open-air AMI smoke (obj_2)

**Date:** 2026-09-23  
**Status:** attempted (2026-09-23) — createBaffles fixed; `rhoPimpleFoam` SIGFPE before forces sampled (mean still null)  
**Approach:** A — one `rhoPimpleFoam` sliding-mesh smoke on `obj_2`, new case overlay, existing open-air mesh  
**Parent:** `docs/superpowers/specs/2026-09-21-prop-drone-radial-cfd-design.md`  
**Related:** `docs/superpowers/specs/2026-09-07-prop-compressible-cfd-design.md` (MRF; AMI was a non-goal there), `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md`  
**Roadmap:** §4.3 — AMI smoke stamp on obj_2 (forward-flight polars and datasheet calibration still remaining)

## Plain language

Steady MRF already runs `obj_2` and reports about 938 g of thrust. This slice asks whether a short compressible sliding-mesh run on the same prop, at the same RPM, lands in the same ballpark. It is one smoke, not a campaign.

## Goal

1. **One case:** `obj_2_ccw` at **25257** RPM, `base_cell` **0.005**, Docker `opencfd/openfoam-default:2406`.
2. **Sliding mesh:** `rhoPimpleFoam` with a rotating inner cell zone and a cylindrical `cyclicAMI` interface. No MRF source term.
3. **Band:** time-mean thrust within **±25%** of the obj_2 MRF smoke figure **938 g**, and absolute mean at least **10 g**.
4. **Report:** validation note + roadmap line + a stamp JSON. A finished run that misses the band is recorded as a miss, not rewritten into a pass.

## Success criteria

| # | Criterion |
|---|-----------|
| 1 | Script builds the AMI case and runs `rhoPimpleFoam` (Docker `2406`) |
| 2 | Result JSON has finite `mean_thrust_g`, `regime=compressible-AMI`, and `band_pass` true or false |
| 3 | `band_pass` is true only when `703.5 ≤ mean_thrust_g ≤ 1172.5` and `abs(mean_thrust_g) ≥ 10` |
| 4 | `docs/validation/drone_radial_open_air_cfd.md` and roadmap §4.3 updated from that JSON |
| 5 | CI unit tests for the mean, the band, and the case overlay (no Docker) |
| 6 | MRF smoke, refine, and GCI fixtures untouched |

## Non-goals

- obj_1, a second STL, or an AMI mesh ladder
- DES, FW-H, cockpit button, datasheet calibration, forward-flight polars
- Replacing or retuning `evaluate_prop_cfd` / `rhoSimpleFoam` MRF
- Bolting AMI onto the parked fan `pimpleFoam` DES overlay (`docs/openfoam-des-fwh.md` stays “not AMI”)
- Claiming the ±25% band is grid-independent or time-converged
- WSL-native OpenFOAM as a second runner

## Approach choice

| Option | Summary | Trade-off |
|--------|---------|-----------|
| **A (chosen)** | New obj_2 smoke: reuse the open-air snappy mesh, add a cylinder baffle + `rotatingMotion`, solve `rhoPimpleFoam` | Real sliding interface; one Docker smoke |
| B | Stretch the parked fan DES `pimpleFoam` templates | That mesh has no AMI patches |
| C | Incompressible `pimpleFoam` AMI tutorial first | Drops the compressible regime this tier is about |

## Ops (locked)

| Knob | Value |
|------|-------|
| STL | `validation/reference/drone_radial/obj_2_ccw.stl` |
| RPM | 25257 |
| spin | −1 (same handedness as prop MRF; positive +z thrust after `normalize_metrics_sign`) |
| freestream | 1 m/s axial ε (static smoke, same as MRF) |
| `base_cell` | 0.005 m |
| procs | 8 |
| revolutions | 2 |
| `endTime` | `2 * 60 / 25257` s |
| `deltaT` | `4e-5` s |
| mean window | last revolution: samples with `t ≥ endTime − 60/25257` |
| reference | `MRF_REF_THRUST_G = 938.0` (obj_2 smoke row in the validation md; not read live from the fixture) |
| band | inclusive `[938 × 0.75, 938 × 1.25]` = **[703.5, 1172.5] g** |
| floor | `abs(mean_thrust_g) ≥ 10` |
| image | `opencfd/openfoam-default:2406` |

Forces are sampled every time step. The reported thrust is the arithmetic mean of `thrust_g` in the window, after the same sign normalization as MRF. `thrust_g` uses the existing conversion `F_z / 9.80665 * 1000`.

## Architecture

**Components**

| Piece | Role |
|-------|------|
| `fansim/propeller/ami_smoke.py` | AMI dictionary overlay, mean window, band check |
| `scripts/run_prop_ami_smoke.py` | One-shot CLI with the locked defaults |
| `build_prop_case` | Reused for STL scale, domain, blockMesh/snappy sizes, thermo, turbulence. Not modified in behavior |
| `run_mesh` | Not used as-is. AMI mesh adds `createBaffles` before the rotor `topoSet` |
| `evaluate_prop_cfd` / `run_solve_prop` | Unchanged. This slice does not call them |
| Validation md + roadmap | Human-facing smoke note |

**Mesh and motion**

Start from the existing open-air hex mesh (`blockMesh` + `snappyHexMesh` on the scaled impeller). Then:

1. `createBaffles` splits internal faces on a `searchableCylinder` into `AMI1` and `AMI2`, both `cyclicAMI` (each other’s neighbour) with `transform rotational`, axis `(0 0 1)`, centre `(0 0 0)`. Cylinder axis is +z through the origin. Radius is `1.05 * tip_radius` (same radial extent as today’s MRF cell zone). Axial extent matches `mrf_z_min`…`mrf_z_max`.
2. `topoSet` defines cell zone `rotor` as the cells inside that cylinder, after the baffles exist.
3. `dynamicMeshDict` uses `solidBody` + `rotatingMotion` on `rotor` with `omega` equal to `PropOpenAir.omega_signed`.
4. Do not write `constant/MRFProperties`. Impeller velocity BC is `movingWallVelocity`. AMI patches are `cyclicAMI` on every transported field.
5. A mean window with zero samples is non-finite (`mean_thrust_g: null`, exit 1).

**Solve**

`rhoPimpleFoam`, parallel when `procs > 1`, same `mpirun --allow-run-as-root --oversubscribe` pattern as `run_solve_prop`. Skip `potentialFoam`. `ddtSchemes` is `backward`. `fvSolution` is PIMPLE (`nOuterCorrectors 1`, `nCorrectors 2`, `nNonOrthogonalCorrectors 1`). Keep `hePsiThermo` / perfect gas and `kOmegaSST` from the prop MRF templates. Drop `steadyState`, `phiMRF`, and SIMPLE relaxation. Keep `limitTemperature`.

If `rhoPimpleFoam` exits because this image has no dynamic-mesh support, write `result.json` with `mean_thrust_g: null` and a reason, and stop. Do not rerun the case as MRF and stamp it AMI.

**Run layout**

```
runs/drone_radial_cfd/ami/obj_2/result.json
```

**Result JSON fields:** `mean_thrust_g`, `thrust_g_samples` (count in the window), `band_pass`, `band_lo_g`, `band_hi_g`, `mrf_ref_thrust_g`, `floor_g`, `regime` (`compressible-AMI`), `solver` (`rhoPimpleFoam`), `rpm`, `end_time`, `delta_t`, `stl`, `base_cell`. On failure before a finite mean: `mean_thrust_g: null` plus `reason`.

**Resume:** if `result.json` already has a finite `mean_thrust_g`, skip the solve unless `--force`.

**Stamp:** after a finished run (pass or honest band miss), copy the summary to `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json`. Do not copy a null-thrust crash.

**CLI sketch**

```bash
uv run python scripts/run_prop_ami_smoke.py
```

Defaults are the locked ops above. Optional overrides: `--stl`, `--rpm`, `--out`, `--procs`, `--base-cell`, `--force`. Overrides exist so the helper is testable; the documented smoke is the defaults.

**Exit codes**

| Code | When |
|------|------|
| 0 | Finite mean and `band_pass` true |
| 2 | Solve finished, mean finite, `band_pass` false (JSON still written) |
| 1 | Mesh/solve crash, or mean missing / non-finite |

CadQuery / antivirus teardown after a green JSON (Windows exit `3221226356` or `-1073741819`) is non-blocking, same as prior prop CFD.

## Failure modes

| Condition | Behavior |
|-----------|----------|
| STL missing | Exit 1 before Docker |
| `createBaffles` or mesh failure | Exit 1, no AMI stamp |
| Solver rejects dynamic mesh | `mean_thrust_g: null` + reason, exit 1, no stamp |
| Mean non-finite or `abs(mean) < 10` | `band_pass: false`, exit 2 if the mean is finite but under the floor; exit 1 if non-finite |
| Mean outside `[703.5, 1172.5]` | `band_pass: false`, exit 2, still stamp and document the miss |
| High unsteadiness inside the window | Record the mean anyway; no extra drift gate |

## Tests (CI — no Docker)

- Mean of a synthetic force history uses only the last-revolution window.
- Band edges are inclusive: 703.5 and 1172.5 pass; just outside fails; `abs(mean) < 10` fails.
- Overlay text contains `rhoPimpleFoam`, `cyclicAMI`, `movingWallVelocity`, `rotatingMotion`, and the written case has no `constant/MRFProperties`.
- CLI defaults: obj_2 STL, RPM 25257, `base_cell` 0.005.
- Existing MRF / GCI tests stay green. `build_prop_case` output for the MRF path stays `rhoSimpleFoam`.

## Documentation

- Add an AMI smoke section to `docs/validation/drone_radial_open_air_cfd.md`: knobs, mean thrust, band, pass/fail, “not datasheet, not time-converged.”
- Roadmap §4.3: AMI smoke note + link to this spec. Polars and datasheet stay listed as remaining.
- Spec status → implemented when the run JSON, stamp, and docs land. If the band fails, status is implemented with an honest miss, not left as approved-only.

## File map (expected)

| Path | Role |
|------|------|
| `fansim/propeller/ami_smoke.py` | mean, band, calls the overlay |
| `fansim/cfd/templates.py` | AMI dictionary strings (`controlDict`, `dynamicMeshDict`, `createBafflesDict`, PIMPLE schemes) |
| `scripts/run_prop_ami_smoke.py` | CLI |
| `tests/test_prop_ami_smoke.py` | unit coverage |
| `docs/validation/drone_radial_open_air_cfd.md` | report |
| `docs/roadmap.md` | §4.3 note |
| `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json` | stamp after a finished run |
| `runs/drone_radial_cfd/ami/` | local run, not committed |

## Honesty

This compares a **two-revolution** sliding-mesh mean on a **smoke mesh** to a **steady MRF** thrust. A pass says the sliding solve is in the MRF ballpark for this one prop and RPM. It does not prove AMI and MRF agree in general, and it does not retire the GCI caveat on obj_2 (~16% fine GCI).
