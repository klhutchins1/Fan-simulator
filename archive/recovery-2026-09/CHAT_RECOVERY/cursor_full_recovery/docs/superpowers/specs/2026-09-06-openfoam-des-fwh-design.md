# OpenFOAM DES + permeable FW-H (stage A)

**Date:** 2026-09-06  
**Status:** accepted (user: scope A, approach 2, surface permeable box)  
**Approach:** Run a short **DES** transient on the existing OpenFOAM v2406 MRF fan case (`pimpleFoam` + `kOmegaSSTDES`), dump **six-face permeable-box loads** each sample interval, reduce with the existing Farassat 1A panel kernel in `fansim/acoustics/fwh.py`. CLI: `scripts/evaluate_des_fwh.py`. Stamp `analogy=openfoam_des_fwh`. Not libAcoustics, not solid-blade FW-H, not NSGA/catalog, not calibrated 22.6 dB(A).  
**Roadmap:** §1.4 remaining (OpenFOAM DES+FW-H).

## Plain language

Steady RANS + Curle/LBM FW-H still cannot claim absolute OF-path dB(A). Stage A adds the smallest honest OpenFOAM transient path: keep today’s snappy/MRF mesh and frame, switch turbulence/solver to DES/pimple, sample a **fixed permeable box** (same idea as LBM `--permeable`), and reuse Python FW-H. MRF is not a rotating blade — stamp that limitation; do not claim AMI acoustics.

Print / Noctua bench stays parked.

## Problem

```text
simpleFoam + kOmegaSST + MRF     → steady; no time history for FW-H
LBM permeable / patches          → GPU relative ranking only
fansim.acoustics.fwh             → ready for multi-panel histories
OpenFOAM DES + surface dump      → missing
```

Native `libAcousticAnalogy` / libAcoustics is version-fragile against OF2406; stage A avoids building a third-party `.so`.

## Goal

### 1. Transient DES case from the existing case builder

Extend (or thin-wrap) `fansim/cfd/openfoam_case.py` / templates so an opt-in path writes:

| Piece | Stage A choice |
|-------|----------------|
| Solver | `pimpleFoam` |
| Turbulence | `LES { LESModel kOmegaSSTDES; … }` (or IDDES if SST-DES wiring is awkward — prefer SST-DES) |
| Rotation | Keep **MRF** (honest stamp `rotation=MRF`) |
| Geometry | Same impeller + frame + circular duct as `evaluate_candidate` |
| Δt | Target ≤ 1/50 BPF (document actual); adjustable CLI |
| Window | Short: flush + ~5–10 revs max, wall-clock gated via CLI `--end-time` / `--max-revs` |
| Mesh | Reuse existing snappy settings; stage A does **not** require a finer DES mesh campaign |

Steady simpleFoam path unchanged (default).

### 2. Permeable box sampling (six faces)

Fixed axis-aligned box around the rotor (fan-centered), same contract as permeable LBM stage 1:

```text
t_s, F0x,F0y,F0z, F1x,..., F5x,F5y,F5z
```

Face order: `+x, -x, +y, -y, +z, -z`. Centers/normals from sidecar JSON:

```text
cx_m, cy_m, cz_m, half_xy_m, half_z_m
```

**Producer:** OpenFOAM function objects (or a small post-step) that integrate pressure (+ momentum flux if already cheap on face sets) on six `sampledSurface` / `faceZone` planes. Prefer **pressure force on the six box faces** first; document if viscous/momentum terms are deferred.

Write CSV under the case dir, e.g. `postProcessing/des_perm/face_loads.csv`.

### 3. Python reduction

Reuse `noise_from_permeable_panels` (or a one-line wrapper) → same keys as LBM permeable (`noise_dba_band`, tones, etc.) plus:

```text
"analogy": "openfoam_des_fwh"
"turbulence": "kOmegaSSTDES"
"rotation": "MRF"
"surface": "permeable_box"
```

Do **not** mix rows with catalog Curle / LBM `fwh_*` without an explicit analogy filter.

### 4. CLI

```text
uv run python scripts/evaluate_des_fwh.py \
  --stl build/a12x25_real_capped.stl   # or --base-json + --base-trial
  --out runs/campaign_des_fwh/
  [--procs 8] [--end-time …] [--delta-t …]
```

Default design: capped A12x25 STL if present, else documented fallback (trial 47 + frame). Emits `des_fwh.json` + face-load CSV copy.

### 5. Tests

- Unit: CSV (+ box JSON) → FW-H metrics dict includes `analogy=openfoam_des_fwh`.
- Unit: CLI declares expected flags; rejects nonsense combos if any.
- **No** full DES solve in CI (Docker/runtime).

## Non-goals

- libAcoustics / OF-native Farassat observers
- Impeller-wall (solid) FW-H / AMI / sliding mesh
- Thickness (volume) term; quadrupole
- NSGA / cockpit / catalog promotion
- Claiming 22.6 dB(A) or AMCA mic distance
- DES mesh GCI campaign
- Prop FW-H

## Done when

1. Spec + templates/runner exist.  
2. On a machine with OF2406 Docker, one design run writes stamped `des_fwh.json` from real (or smoke-short) DES samples.  
3. Roadmap §1.4 notes stage A DES+FW-H path (still lists libAcoustics / absolute cal as later).  
4. Unit tests for reduction + CLI wiring green.

## Implementation sketch (for the plan)

1. Templates: `controlDict` / `turbulenceProperties` / `fvSchemes` / `fvSolution` DES variants.  
2. Case builder flag `transient_des=True` (+ permeable box function objects).  
3. `fansim/cfd/des_fwh.py` — box geom, CSV IO, call existing FW-H.  
4. `scripts/evaluate_des_fwh.py` — mesh (or reuse) → solve → reduce.  
5. Tests + short docs note in `docs/fluidx3d-setup.md` or a new `docs/openfoam-des-fwh.md` pointer from roadmap.

## Honesty

MRF freezes blade geometry in the rotating frame — BPF tones and broadband from this path are **indicative**, not mic-ready. Stage A proves plumbing + analogy stamp; absolute calibration is out of scope.
