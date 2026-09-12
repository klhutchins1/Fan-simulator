# LBM geometry A/B polish (casing export + deltas)

**Date:** 2026-09-08  
**Status:** accepted  
**Approach:** Harden `scripts/run_lbm_geometry_ab.py` with a small library module: export plain + stepped casing STLs, compute shut-off Δ vs default when GPU metrics exist, and stamp honesty that stepped inlet is casing-only (not impeller-only FluidX3D shut-off).  
**Roadmap:** §2.3 / §2.6 / §2.6b remaining LBM A/B polish.

## Plain language

The campaign script already built default / sickle / notched impeller STLs. Stepped inlet was only a note. Polish exports the two casings, writes clearer summary JSON/MD, and compares shut-off Pa when a real LBM run fills in metrics. Do not pretend impeller-only shut-off measures stepped inlet.

## Goal

1. ``fansim/cfd/lbm_geometry_ab.py`` — load base JSON, variant BladeParams, stepped row, Δ helper, markdown.
2. Script exports ``casing_plain.stl`` / ``casing_stepped.stl`` (skip with ``--skip-casing``).
3. ``deltas`` in ``summary.json`` when shutoff metrics present.
4. Tests without GPU / without requiring CadQuery solid builds.
5. Roadmap: mark LBM A/B polish done; GPU campaign run still optional on user hardware.

## Honesty

- Impeller A/B shut-off uses tip clearance lattice, not ducted casing STL.
- Stepped vs plain needs ducted OpenFOAM (``--stepped-inlet``) or future ducted LBM.
- Do not claim quieter BPF from dry-run alone.

## Non-goals

- Recompile FluidX3D for casing ingest
- Photographed AAO LE match
- Catalog-grade volute scroll (cleared 2026-09-08 as stage3_smooth_scroll;
  optional spline loft / OEM tongue remains polish only) (cleared 2026-09-08 as stage3_smooth_scroll;
  optional spline loft / OEM tongue remains polish only)
