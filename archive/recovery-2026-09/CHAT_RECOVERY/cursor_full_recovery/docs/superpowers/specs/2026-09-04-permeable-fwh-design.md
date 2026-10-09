# Permeable-surface FW-H (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Stop collapsing the LBM control-volume box into one force. Dump **per-face (or per-patch) permeable-surface loading** from FluidX3D, then reduce with the existing Farassat 1A panel kernel in `fansim/acoustics/fwh.py`. Opt-in: `evaluate_noise.py --permeable` (and a job-cfg / setup mode). Default finalist path stays Curle CV → optional `--fwh` compact. Not OpenFOAM DES, not blade-solid force (still NaN), not calibrated 22.6 dB(A), not NSGA.  
**Roadmap:** §1.4 remaining (permeable-surface dump). Compact loading stage 1 is already in.

## Plain language

A permeable FW-H surface is a **closed fluid surface around the fan**, not the spinning blade. We already integrate momentum flux on a fixed CV box for Curle — that box *is* permeable; we just sum every face into one `F(t)` and lose where the load sits. Stage 1 keeps the same box, logs **six face loads** (or a coarse patch grid on those faces), and runs the panel 1/r kernel so retarded time can differ by face. That is the smallest real step beyond compact FW-H without inventing a new mesh topology.

Print / Noctua bench (speed, CFM, mic) stays **parked** until another motor/frame is on hand. This slice is code + optional GPU recompile only.

## Problem

```text
FluidX3D setup.cpp     → one Fs(t) = sum of all CV faces
farfield / fwh compact → single source at the origin
fwh.loading_pressure_panels → ready, but no producer of multi-panel histories
```

Absolute broadband is still 1 mm-grid-limited. Blade `object_force` still NaNs on re-voxelized rotors.

## Goal

### 1. Dump format (Fan-simulator owns the contract)

New file next to the CV CSV, e.g. `build/noise_<label>_perm.npz` (or CSV if NPZ is awkward from C++ — prefer **one CSV** that Python packs):

**Option A (stage 1 default) — six faces:**

```text
t_s, F0x,F0y,F0z, F1x,..., F5x,F5y,F5z
```

Face order: `+x, -x, +y, -y, +z, -z`. Face centers and outward normals are **derived in Python** from the known CV box geometry written once in a sidecar or header:

```text
# companion JSON or cfg keys:
# cx_m, cy_m, cz_m, half_xy_m, half_z_m   (SI, fan-centered)
```

Or embed in `noise_job.cfg` after the LBM run from known lattice→SI units.

**Option B (if six faces prove too coarse in a later cycle):** subdivide each face into an `n×n` patch grid (`n=4` → 96 panels). Not this cycle unless six-face wiring is trivial.

### 2. FluidX3D (`FluidX3D/src/setup.cpp`)

- Keep today’s CV integrated CSV path as default (`mode=cv` or absent).
- When `noise_job.cfg` has `mode=permeable` (or `permeable=1`):
  - Same domain / spin / spinup / sample_every as today.
  - Each sample: compute the **six face integrals separately** (same flux formula as now, do not sum into one `Fs`).
  - Write `out` as the multi-column CSV above (or `out` with `_perm` suffix if we keep both).
- Recompile note in `docs/fluidx3d-setup.md` (one paragraph). Do not change `defines.hpp` extensions.

### 3. Python reduction (`fansim/acoustics/fwh.py`)

```text
face_panels_from_csv(path, box) -> list[panel]
  # each panel: r0 (face center, m), n_hat (outward), f[t,3] = face force on fluid

noise_from_permeable_panels(t, panels, **kw) -> dict
  # p = loading_pressure_panels(...)
  # same metric keys as noise_from_compact_force
  # "analogy": "fwh_permeable"
```

Thrust for the stamp: sum of mean face `F_z` (or keep CV total if both files exist). Reuse A-weighting / BPF helpers from `farfield`.

Collapse check: if all face forces are applied as **one** panel at the origin with `F = sum F_i`, metrics match compact within tolerance (sanity). Six distinct faces must **not** be required to match compact (different `r`).

### 4. CLI

`scripts/evaluate_noise.py`:

```text
--permeable     store_true; write mode=permeable into noise_job.cfg; reduce with permeable path
--fwh           unchanged (compact from integrated CV)
default         Curle 1/r² from integrated CV
--csv PATH      if set, skip LBM; with --permeable expect the multi-face CSV
```

Mutual honesty: do not pass `--fwh` and `--permeable` together (argparse error or permeable wins — pick **error**).

Stamp `analogy`: `curle` | `fwh_compact` | `fwh_permeable`. No `★`. No NSGA change.

### 5. Docs

- Spec accepted; roadmap §1.4 remaining text updated.
- `docs/fluidx3d-setup.md`: permeable mode + recompile.
- Bibliography FW-H line: permeable stage 1 → this dump + `noise_from_permeable_panels`.

## Honesty

- Still **relative** ranking under a fixed band-limit. Do not claim 22.6 dB(A).
- Six face centers are a **coarse** permeable surface; not a fine CAA mesh.
- Thickness (volume) and quadrupole terms stay out.
- Do not mix permeable rows with Curle / compact catalog stamps.
- No physical Noctua validation this cycle (motor/frame not available).

## Tests (no GPU required for unit tests)

- Synthetic six-face CSV → `face_panels_from_csv` → 6 panels; `noise_from_permeable_panels` finite `noise_dba_band`.
- Sum-to-origin collapse ≈ compact (rms or dB within 0.5 dB on synthetic tonal force).
- Two opposite faces with equal `F_z(t)`: on-axis `p` finite.
- `--permeable` in `evaluate_noise.py`; rejects `--fwh --permeable` together; no `★`.
- Existing `test_fwh.py` / `test_farfield.py` stay green.

Optional (GPU, manual): one A12x25 STL through `--permeable` after recompile; document runtime.

## Non-goals

- OpenFOAM DES + FW-H library
- Blade-surface / solid permeable dump
- Patch subdivision (`n×n`) this cycle
- NSGA third objective switch
- Prop FW-H
- Print / caliper / mic campaigns
- Claiming absolute dB(A) or shut-off via this path
