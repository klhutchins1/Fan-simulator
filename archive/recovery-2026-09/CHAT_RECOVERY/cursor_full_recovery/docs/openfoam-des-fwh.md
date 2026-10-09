# OpenFOAM DES + permeable FW-H (stage A)

Operator note for `scripts/evaluate_des_fwh.py`. Spec:
`docs/superpowers/specs/2026-09-06-openfoam-des-fwh-design.md`.

## What this is

Short **pimpleFoam** + **kOmegaSSTDES** run on the existing snappy/MRF mesh,
six fixed permeable-box face samplers (`desFace0..5`), then Farassat 1A panel
reduction (`analogy=openfoam_des_fwh`).

## What this is not

- Not libAcoustics / OF-native observers
- Not AMI / sliding-mesh rotating blades (MRF is stamped `rotation=MRF`)
- Not calibrated 22.6 dB(A); do not mix with catalog Curle or LBM `fwh_*` rows
- Not an NSGA objective

## Commands

CSV-only (no Docker):

```bash
uv run python scripts/evaluate_des_fwh.py \
  --csv-only path/to/face_loads.csv --box-json path/to/des_perm_box.json \
  --out runs/campaign_des_fwh
```

Full smoke (Docker OF2406):

```bash
uv run python scripts/evaluate_des_fwh.py \
  --stl build/a12x25_real_capped.stl \
  --out runs/campaign_des_fwh \
  --procs 8 --end-time 0.002 --delta-t 2e-5
```

`--reuse-mesh` skips remesh when `case/constant/polyMesh` already exists.

A **plumbing smoke** (`end-time=0.002`) needs a near observer: reduction defaults to
**0.2 m** on +z so `r/c₀` (~0.6 ms) fits inside short windows. A 1 m mic (delay ~3 ms)
silences a 2 ms run. Face FO uses ``areaIntegrate(p)`` (``areaNormalIntegrate`` was
zero on cutting planes in OF2406).

## Contracts

- Face FO names: `desFace0` … `desFace5` (order +x,-x,+y,-y,+z,-z)
- CSV: `t_s, F0x,F0y,F0z, …, F5x,F5y,F5z`
- Box sidecar: `cx_m, cy_m, cz_m, half_xy_m, half_z_m` (+ optional `dia_mm`)
  OpenFOAM runs size the box from the **duct radius** (`box_from_duct`), not the
  LBM `cv_box_from_dia_mm` lattice (which can sit outside the snappy duct).
- Kinematic OF pressure → Newtons via `rho=1.2` in `fansim/cfd/des_fwh.py`
