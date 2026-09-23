# Drone radial open-air CFD (smoke + refine)

**Status:** recorded 2026-09-22 — smoke + refine + **GCI ladder** for **both** STLs  
**Solver:** `rhoSimpleFoam` · **Domain:** open_air · **Regime:** compressible-MRF  
**Image:** `opencfd/openfoam-default:2406` (canonical).

## Honesty

Steady compressible MRF in a truncated box is a **screening** record — tip Mach stamped, shocks not resolved, not datasheet-grade.

| Tier | Mesh | Iters | Drift gate |
|------|------|-------|------------|
| Smoke | `base_cell=0.005` | 400 | &lt; **25%** over last **25%** of force samples |
| Refine | ≤`0.004` (obj_1 used `0.003`) | 600–1000 | &lt; **10%** over last **10%** of force samples (late-window) |

Refine uses a **late-window** (`--tail-frac 0.10`) because FO force sampling is sparse (~40–100 points/run); a 25% window can still include settling. Future cases write denser FO history (`n_iters/100`).

## Geometry / RPM

| Case | STL | ~D | RPM @ Ma≈0.35 (smoke) | RPM refine |
|------|-----|----|----------------------|------------|
| obj_1 | `…/obj_1_ccw_impeller.stl` | ~60 mm | 38100 | 32657 (Ma≈0.30) |
| obj_2 | `…/obj_2_ccw.stl` | ~90 mm | 25257 | 25257 (Ma≈0.35) |

## Smoke results (gate 25% / tail 25%)

| Case | thrust_g | shaft_power_w | drift_% | fixture |
|------|----------|---------------|---------|---------|
| obj_1 | 74.2 | 236 | 23.4 | `obj_1_ccw_impeller_smoke.json` |
| obj_2 | 938 | 2034 | 4.7 | `obj_2_ccw_smoke.json` |

## Refine results

| Case | thrust_g | shaft_power_w | tip_mach | late drift_% | fixture |
|------|----------|---------------|----------|--------------|---------|
| obj_1 | 60.7 | 173 | 0.30 | 5.4 | `obj_1_ccw_impeller_refine.json` |
| obj_2 | 949 | 2058 | 0.35 | 3.8 | `obj_2_ccw_refine.json` |

obj_1 needed softer SIMPLE relaxation, `base_cell=0.003`, 1000 iters, Ma≈0.30, and late-window gate after coarser refine attempts stayed in a limit-cycle under a 25% sample window.

## Cockpit

Prop Optimize **CFD mesh** preset: Smoke (`0.005`/`400`) or Refine (`0.004`/`600`) on the existing CFD refine top-N card.

## Commands (refine freeze)

```bash
uv run python scripts/freeze_prop_cfd_fixture.py \
  --result runs/drone_radial_cfd/obj_1_refine4/result.json \
  --out validation/reference/drone_radial/cfd/obj_1_ccw_impeller_refine.json \
  --id obj_1_ccw_impeller_refine \
  --stl validation/reference/drone_radial/obj_1_ccw_impeller.stl \
  --base-cell 0.003 --iters 1000 --procs 8 \
  --drift-tol 10 --tail-frac 0.10 --require-gate
```

## Grid independence (GCI)

**Status:** recorded 2026-09-22  
**Ladder:** `base_cell` 0.005 / 0.0035 / 0.0025 · **iters** 800 · same RPM as smoke Ma≈0.35  
**Metric:** `thrust_g` (Roache GCI via `fansim.analyze.grid_convergence`)  
**Script:** `scripts/run_prop_grid_convergence.py`  
**Stamps:** `obj_1_ccw_impeller_gci.json`, `obj_2_ccw_gci.json` under `validation/reference/drone_radial/cfd/`.

| Case | RPM | thrust @0.005 | @0.0035 | @0.0025 | f_extrapolated (g) | p | GCI_fine % | asymptotic | converged |
|------|-----|---------------|---------|---------|-------------------|---|------------|------------|-----------|
| obj_1 | 38100 | 61.52 g | 59.06 g | 44.54 g | 42.01 g | 5.67 | 7.10 | 0.017 | no |
| obj_2 | 25257 | 923.9 g | 1037.9 g | 1108.5 g | 1248.8 g | 1.21 | 15.82 | 1.068 | yes |

**Interpretation:** obj_2 is in the asymptotic range (thrust rises monotonically coarse→fine; `converged=true`) but fine-level GCI is still ~16% — a screening band, not a datasheet claim. obj_1 is **not** asymptotic: thrust **drops** on the finest mesh (`asymptotic_ratio≈0.017`, `converged=false`), so the Roache extrapolation is not trustworthy; treat obj_1 thrust as unsettled discretization / force-tail behavior (see `force_tail_drift_pct` on the medium rung in the stamp JSON).

GCI here is **discretization uncertainty** for steady compressible-MRF open-air — not datasheet-grade. Forward-flight polars and bench calibration remain out of scope. The obj_2 AMI smoke is a separate section below.

## AMI smoke (obj_2)

**Status:** recorded 2026-09-23  
**Case:** `obj_2_ccw.stl` · RPM 25257 · `base_cell` 0.005 · 2 revolutions · `deltaT` 4e-5 s  
**Solver:** `rhoPimpleFoam` + cylindrical `cyclicAMI` (`regime` compressible-AMI)  
**Script:** `scripts/run_prop_ami_smoke.py`  
**Stamp:** `validation/reference/drone_radial/cfd/obj_2_ccw_ami_smoke.json`  
**Reference:** obj_2 MRF smoke thrust **938 g**. Band **703.5–1172.5 g**. Floor **10 g**.

| mean_thrust_g | samples | band_pass | band |
|---------------|---------|-----------|------|
| null | 0 | false | 703.5–1172.5 g |

**Interpretation:** Attempted. No finite mean. Reason: OpenFOAM command failed (134): createBaffles -overwrite. Not stamped as a pass.

AMI here is one short sliding-mesh smoke — not datasheet-grade. Forward-flight polars and bench calibration remain out of scope.
