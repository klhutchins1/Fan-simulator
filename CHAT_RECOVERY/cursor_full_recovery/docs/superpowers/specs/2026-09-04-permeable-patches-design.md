# Permeable FW-H n×n patches (stage 1, n=2)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Subdivide each CV box face into a fixed **2×2** patch grid (24 panels). New FluidX3D job mode `mode=patches` dumps per-patch force histories; Python builds panel centers/normals and reduces with the existing Farassat 1A panel kernel. Six-face `mode=permeable` stays unchanged. Opt-in CLI: `evaluate_noise.py --patches`. Not n=4, not configurable N this cycle, not OpenFOAM DES, not calibrated 22.6 dB(A).  
**Roadmap:** §1.4 remaining after six-face permeable (n×n subdivision).

## Plain language

Six face centers are a coarse permeable surface. Splitting each face into four patches lets retarded time and direction differ across the face without a new mesh topology — still the same CV box, just finer integrals. Stage 1 locks **n=2** so the CSV stays manageable from C++ (~72 force columns + time).

## Problem

```text
mode=permeable → 6 panels (one per face)
loading_pressure_panels → already sums many panels
mode=patches → missing
```

## Goal

### 1. Dump contract (Fan-simulator owns it)

CSV:

```text
t_s, P0x,P0y,P0z, …, P23x,P23y,P23z
```

- **24 patches**, index order: for face `f` in `{+x,-x,+y,-y,+z,-z}`, then row-major `i,j ∈ {0,1}` on that face → global index `p = 4*f + 2*i + j`.
- Face local coords: for ±x faces, local axes are (y,z); ±y → (x,z); ±z → (x,y). Patch `(i,j)` center is at face center ± half extents × `(±0.5, ±0.5)` in the two local directions (`i,j` map to −0.5/+0.5).
- Outward normals match the six-face convention. Box SI geometry: same `cv_box_from_dia_mm` as six-face.
- Column prefix **`P`** (patch) so six-face `F*` CSVs are not confused.

### 2. FluidX3D (`setup.cpp`)

- `mode=cv` — unchanged summed Fs.
- `mode=permeable` — unchanged six faces.
- `mode=patches` (or `patches=1`): same spin/sample cadence; each sample integrate flux on **2×2 cells per face** (lattice loops split into two halves along each face axis); write the 24×3 CSV to `out`.
- Recompile note in `docs/fluidx3d-setup.md` (one paragraph add-on to permeable).

### 3. Python (`fansim/acoustics/fwh.py`)

```text
PATCH_N = 2   # stage 1 lock

patch_panels_from_csv(path, box, n=PATCH_N) -> list[panel]
  # 6*n*n panels; r0 from box + face index + (i,j)

analyze_patches_csv(...) -> noise_from_permeable_panels(...)
  # stamp "analogy": "fwh_patches"  (reuse panel metrics path)
```

Collapse sanity (tests): summing all patch forces on one face → that face’s six-face force (within float noise) when built from a synthetic split.

### 4. CLI (`scripts/evaluate_noise.py`)

```text
--patches      write mode=patches; reduce with patch path
--permeable    unchanged (six-face)
--fwh          unchanged (compact)
```

Mutual exclusion: any two of `--fwh` / `--permeable` / `--patches` → argparse error.  
`--csv` + `--patches` expects the `P*` multi-column CSV. Stamp `analogy`: `curle` | `fwh_compact` | `fwh_permeable` | `fwh_patches`.

### 5. Docs

- Spec accepted; roadmap §1.4 note n=2 patches done; n=4 / variable N later.
- Bibliography / fluidx3d-setup one-liner.

## Honesty

- Still **relative** / band-limited. Not 22.6 dB(A).
- 24 panels are still coarse vs CAA; not blade-solid force.
- Do not mix analogy stamps in catalog comparisons.
- No physical Noctua validation this cycle.

## Tests (no GPU)

- Synthetic 24-patch CSV → 24 panels; finite `noise_dba_band`; `analogy == fwh_patches`.
- Sum of 4 patches on one face equals a synthetic face force (vector RMS tol).
- CLI declares `--patches`; rejects `--patches --permeable` and `--patches --fwh`; no `★`.
- Existing six-face / compact / farfield tests stay green.

## Non-goals

- Configurable `n` / n=4 this cycle
- OpenFOAM DES + FW-H
- Thickness / quadrupole
- NSGA noise objective
- Claiming absolute dB(A)

## Success

With FluidX3D recompiled, `evaluate_noise.py <stl> --patches` writes a 24-panel CSV and returns finite band dBA with `analogy=fwh_patches`. Six-face and Curle paths unchanged when those flags are used.
