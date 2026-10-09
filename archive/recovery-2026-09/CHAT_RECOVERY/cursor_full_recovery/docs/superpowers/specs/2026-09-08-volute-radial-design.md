# Volute / 90° radial blower (stage 1)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Geometry scaffold for a radial (90°) impeller plus a segmented Archimedean-scroll volute casing, export STLs, registry archetype with honest CFD stub, and a cockpit Preview/Export tab. Not a radial CFD domain, not NSGA, not squirrel-cage.  
**Roadmap:** §4.1 remaining (volute / 90° radial) after mixed-flow drop-in.

## Plain language

Mixed-flow still exits axially into the A12x25 duct. A true high-static blower turns the flow 90° and collects it in a volute. Stage 1 builds printable-ish solids so we can see and export the topology; Evaluate stays `NotImplementedError` because the axial MRF duct is the wrong domain.

## Goal

1. **`fansim/volute/`** — `VoluteParams`, `build_radial_impeller`, `build_volute_casing`, `export_volute_stls` (impeller + casing), optional fused preview STL.
2. **Defaults (mm):** hub 18, tip 50, blade height 20, 7 blades, volute clearance 3, wall 2, spiral expansion ~+25 mm over 360°, rectangular outlet stub.
3. **Archetype** `volute`: `build_geometry` → impeller STL; `evaluate` → `NotImplementedError` naming the missing radial/volute CFD domain.
4. **CLI** `scripts/export_volute.py` — write impeller + casing under `--out-dir`.
5. **Cockpit** top-level **Volute** tab: core knobs, isolated Preview (assembly), Export both STLs. No Assess/Optimize this cycle.
6. **Problem yaml** `config/problems/volute_radial.yaml` — documents archetype key + honesty note.

## Honesty

This is a **geometry + export scaffold**. Do not claim CFM/Pa. Do not wire axial `evaluate_candidate`. Spiral is a segmented approximation (n wedges), not a CFD-ready tongue mesh.

## Non-goals

- Radial / volute OpenFOAM domain or MRF
- NSGA / BEM screen
- Squirrel-cage / forward-curved blower
- Replacing mixed-flow (`centrifugal` key)

## Tests (no Docker)

Params validation; impeller one solid; casing ID > tip; export >1 KB each; archetype evaluate raises; cockpit tab strings; script parser; problem yaml archetype.
