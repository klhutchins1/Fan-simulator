# Prop compressible open-air CFD (stage 1 — smoke evaluate)

**Date:** 2026-09-07  
**Status:** implemented (Docker smoke green on `fpv_5inch` @ 15k RPM, 2026-09-08)  
**Approach:** Add a **parallel** OpenFOAM path for drone props: large open far-field domain + single MRF zone + **`rhoSimpleFoam`** (perfect-gas air). Parse existing `forces` FO for thrust/torque/power. CLI smoke like CROR. Do **not** overload ducted fan `build_case`.  
**Roadmap:** §4.3.

## Plain language

Fan CFD is ducted incompressible `simpleFoam`. FPV props tip at Mach ~0.4–0.6 in open air — that path is the wrong physics. Stage 1 ships a smoke evaluate: build a prop STL from `PropSpec`, drop it in a big empty box, run compressible steady MRF, report thrust (grams) and shaft power. BEMT stays the screen; this CFD is for finalist / honesty checks only. No Optuna, no forward-flight polar, no AMI.

## Goal

1. **Open-air domain helper** — size from tip radius `R`: radial extent ~5`R`, upstream ~2`R`, downstream ~4`R` (tunable constants). No frame, no casing, no duct walls. Outer lateral patches = freestream / slip; inlet/outlet = freestream with static thrust default `U≈(0,0,ε)` (ε tiny axial, e.g. 0.1 m/s, so the solver has a clear freestream direction).
2. **`build_prop_case(...)`** (new, under `fansim/cfd/` or `fansim/propeller/cfd.py`) — writes compressible templates: `thermophysicalProperties` (perfect gas air), `0/T`, `0/p` (absolute Pa), `0/U`, k/ω/nut as needed, `MRFProperties` (one zone), `controlDict` application `rhoSimpleFoam`, forces FO on `impeller`. Mesh: blockMesh + snappy on impeller only (reuse snappy patterns where possible; skip casing/frame STLs).
3. **`evaluate_prop_cfd(spec, workdir, *, rpm=...)`** — export STL via `build_prop` / `prop_blade_params`, build case, mesh, solve, parse forces → result dict:
   - `thrust_n`, `thrust_g`, `torque_nm`, `shaft_power_w`, `tip_mach`, `rpm`
   - stamps: `solver=rhoSimpleFoam`, `domain=open_air`, `regime=compressible-MRF`
4. **CLI** `scripts/evaluate_prop_cfd.py` — `--spec fpv_5inch` (default), `--rpm`, `--iters`, `--procs`, `--base-cell`, `--out`, `--dry-run`.
5. **Tests** — dry/unit: domain extents, thermo + `rhoSimpleFoam` in case files, MRF omega from RPM, CLI declares flags. No Docker in CI. Manual Docker smoke when image available.

## Non-goals

- Prop Optuna / cockpit / archetype `evaluate` replacement of BEMT  
- Forward-flight polar (`V∞` sweep) — static thrust only in stage 1  
- AMI / sliding mesh / DES / FW-H for props  
- Changing ducted fan `simpleFoam` path  
- Claiming Gemfan/HQ datasheet accuracy

## Honesty

Steady compressible MRF in a truncated domain is a **screening** model. Tip compressibility is *acknowledged* (solver + tip Mach stamp), not fully resolved (no shock-capturing claim, coarse mesh OK for smoke). Compare order-of-magnitude to `PropSpec.ref_thrust_g` when present; do not fail the smoke if within ~2×.

## Defaults (smoke)

| Knob | Default |
|------|---------|
| Spec | `fpv_5inch` |
| RPM | mid-band e.g. `0.7 * rpm_max` (~21k) so tip Mach ≳ 0.3 without max-power torture |
| Iters | 300–800 (CLI) |
| Base cell | ~0.004–0.006 m (prop is smaller than 120 mm fan) |

**Smoke (2026-09-08):** `runs/prop_cfd_smoke/` — `fpv_5inch` @ 15k RPM, `rhoSimpleFoam`, finite thrust/torque (~212 g magnitude, sign later), tip Mach ≈ 0.29. T limiter + freestreamPressure/Velocity required for stability.
