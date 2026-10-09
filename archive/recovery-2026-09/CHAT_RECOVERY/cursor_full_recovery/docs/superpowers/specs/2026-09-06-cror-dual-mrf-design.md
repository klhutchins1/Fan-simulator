# CROR dual-MRF evaluate (stage 1)

**Date:** 2026-09-06  
**Status:** implemented (Docker smoke green on `delta_afc1212de`)  
**Approach:** Wire `CrorArchetype.evaluate` to a steady OpenFOAM case with **two MRF cellZones** (front / rear, opposite Ω) on the existing fused CROR STL. Free + hose metrics via the same system-curve path as axial. No NSGA, no noise, no AMI.  
**Roadmap:** §4.2 dual-MRF CFD.

## Plain language

Geometry already exports one solid (front + rear + hub). CFD still raises `NotImplementedError`. Stage 1 adds a second cylinder cellZone and a second `MRFProperties` entry with flipped rotation so the rear recovers swirl in steady RANS. Same Docker OF2406 / `simpleFoam` stack as axial fans.

## Goal

1. **`fansim/cfd` dual-MRF support** — opt-in on `build_case` (or CROR-specific builder): `topoSet` creates `rotorFront` + `rotorRear`; `MRFProperties` has `MRF1` / `MRF2` with `±omega`. Zone axial bounds from CROR geometry helpers (front/rear half-depths + gap).
2. **`fansim/cror/evaluate.py`** — export STL, size `TestRig` from bounds, circular duct + optional frame, free+load solve, return `CandidateResult`-compatible metrics (or a thin CROR result dict matching archetype expectations).
3. **`CrorArchetype.evaluate`** — calls that path (no longer `NotImplementedError`).
4. **`scripts/evaluate_cror.py`** — smoke CLI (default `--spec delta_afc1212de`; stack depth ~33 mm).
5. **Tests** — unit: dual topo/MRF dict contains two zones and opposite omega; archetype evaluate is callable with mocked runner *or* template-only asserts. No Docker in CI.

## Non-goals

- NSGA / cockpit / searchable CROR campaign  
- Transient DES / FW-H for CROR  
- Separate front/rear STLs or AMI  
- Compressible / prop tier (§4.3)

## Honesty

Steady dual-MRF on a fused solid is a **screening** model. Do not claim unsteady interaction or CROR noise. Stamp `rotation=dual_MRF` in raw metrics when easy. Default geometry does not fit A12x25 depth — use a deeper envelope for smoke/evaluate.

## Done when

Default `CrorParams` evaluate runs under Docker (manual smoke) and unit tests for dual-MRF wiring pass; roadmap §4.2 notes stage-1 evaluate done, NSGA/noise still remaining.

**Smoke (2026-09-06):** `runs/cror_smoke/` — feasible, ~161 CFM free / ~123 @ 8 Pa, dual_MRF stamped (~10 min @ 300 iters / 8 procs).

