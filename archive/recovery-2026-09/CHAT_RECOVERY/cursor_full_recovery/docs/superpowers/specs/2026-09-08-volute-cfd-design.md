# Volute / radial CFD domain (stage 1)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** First honest shippable radial-discharge OpenFOAM case: custom blockMesh (axial +Z inlet, +X outlet), snappy of impeller + volute casing, cylindrical MRF, `evaluate_volute` free+load path mirroring mixed-flow, CLI + cockpit Assess. Not NSGA, not tongue-refined mesh, not sealed exterior enclosure.  
**Roadmap:** §4.1 remaining after geometry scaffold.

## Plain language

Geometry already builds a radial impeller and scroll. Scoring still needs a domain that turns flow 90°. Stage 1 writes a tight hex box with inlet on the top face and outlet on the +X face, snaps the existing STLs, runs steady RANS MRF (or fails with clear reasons), and wires Assess.

## Goal

1. **`VoluteDomain`** + **`build_volute_case`** — OpenFOAM v2406 dictionaries; reuse mesh/solve helpers.
2. **`evaluate_volute`** — export STLs → build case → mesh → free+load solves → `ObjectiveResult` (system-curve like mixed-flow). Gates: watertight impeller, clearance floor. Stamp `topology=volute_radial`, honesty on tight-box exterior bypass risk.
3. **Archetype** `volute.evaluate` → `evaluate_volute` (no longer stub).
4. **CLI** `scripts/evaluate_volute.py`.
5. **Cockpit** Volute **Assess** via isolated subprocess (CadQuery-safe).
6. **Tests** (no Docker): domain extents, case files written, mocked evaluate feasible, archetype wired, CLI strings, cockpit Assess hook.

## Honesty

- Segmented scroll + rectangular stub are not CFD-grade tongue geometry.
- Tight hex may leave a small exterior leak path around the casing; stamped in `raw`.
- Default RPM is a free parameter (not A12x25 motor curve).
- Do not claim catalog-comparable CFM/Pa until a sealed enclosure / better tongue lands.

## Non-goals

- NSGA / BEM screen for volute
- Sealed fluid-only enclosure STL
- Replacing mixed-flow axial duct
- DES / FW-H

## Success

`evaluate_volute(VoluteParams(), workdir)` with CFD mocked returns feasible-shaped result; with Docker, CLI meshes/solves or returns a readable infeasible reason. Cockpit Assess calls the same path.
