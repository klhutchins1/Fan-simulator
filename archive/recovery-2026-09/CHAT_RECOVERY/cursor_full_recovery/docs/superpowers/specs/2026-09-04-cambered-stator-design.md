# Cambered NACA stator OGVs (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Replace the flat staggered plates in `fansim/cfd/stator.py` with a **fixed** NACA 4-digit section (same axial band, stagger, vane count, hub barrel, `--stator` flag). Not searched camber/stagger/n_vanes, not frame+stator stack, not BEM Euler credit.  
**Roadmap:** §2.2 remaining (cambered NACA OGVs).

## Plain language

Flat plates at 50° only block and roughly turn. Real outlet guide vanes are cambered airfoils that recover swirl into static pressure. Stage 1 swaps the plate box for one fixed NACA profile extruded radially, still fused with the hub barrel as one solid. Optimizer wiring stays `--stator` on / off; NSGA still defaults to the four-bar frame.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Fixed NACA4, radial extrude of one midspan section | Matches “A”; small code; enough to measure swirl recovery later |
| **2** | CLI knobs for camber/stagger | Extra surface; not requested this cycle |
| **3** | Hub→tip lofted sections | Real, but heavy CadQuery + no data yet for spanwise schedule |

## Goal

### 1. Geometry (`fansim/cfd/stator.py`)

Keep unchanged:

```text
z_start     = mrf_z_max/mm + 0.5
chord_mm    = 8.0          # CHORD_MM / STRUT_DEPTH_MM
stagger_deg = 50.0
n_vanes     = n_blades + 2
outer_r / hub barrel / WALL_INSET / AFTER_MRF  # as today
```

Replace the `box(span, THICK_MM, CHORD_MM)` vane with:

```text
NACA m=0.04, p=0.4, t=0.12   # ~4% camber, 12% thick (~0.96 mm at 8 mm chord)
n_chord_pts = 40             # enough for fuse; not a fine CFD surface
```

Construction (mm, CadQuery):

1. `naca4(0.04, 0.4, 0.12, n_points=40)` → closed loop in chord-normalized coords.
2. Scale by `CHORD_MM`; place LE at `z_start`, chord along +Z before stagger (same axial band as today’s plate).
3. Extrude the profile along **span** (radial length `outer_r - bar_r0`), centered at mid-span `x_center` as today.
4. Rotate about the **radial** axis through the vane mid-chord by `STAGGER_DEG` (same sense as the plate).
5. Pattern about Z; fuse with hub barrel → one solid. Raise if `Solids() ≠ 1`.

Constants to export for tests: `STATOR_CAMBER`, `STATOR_CAMBER_POS`, `STATOR_THICKNESS` (fractions). Drop dependence on plate `THICK_MM` for the vane body (barrel unchanged). Keep `THICK_MM` only if tests still reference it — prefer updating tests to NACA thickness × chord ≈ 0.96 mm.

Camber sense: positive camber turns swirl toward axial (suction side faces into the rotor swirl). Document the LE→TE / rotation convention in a one-line comment matching the existing plate stagger sign.

### 2. Wiring

- `export_stator_stl` / `build_case(..., stator_stl_mm=)` / `evaluate_candidate(stator=)` / `--stator` / cockpit switch: **unchanged**.
- Stamp `raw["stator"]` already present; add `raw["stator_section"] = "naca4"` when stator is on (optional but useful). If `raw["stator"]` is only a bool today, keep it and add the section string only if cheap.

### 3. Docs

- Spec accepted; roadmap §2.2: cambered NACA stage 1 done; remaining = searched n_vanes/stagger, BEM Euler credit, frame+stator stack.
- Brief note in the original stator spec or roadmap only (no new bibliography paper required).

## Honesty

- Fixed section is a **starting** OGV, not an optimized cascade.
- Still replaces the frame (no stack).
- No claim of measured ΔP/η gain until a CFD campaign.
- CadQuery fuse can be fragile on thin TE — if fuse fails in practice, slightly blunt TE (already in `naca4` close) or reduce `n_points`; do not silently fall back to plates.

## Tests (no Docker mesh)

- `build_stator_solid` → one solid; vane count = `n_blades+2`; axial band still starts at `mrf_z_max + AFTER_MRF`.
- Solid intersects a probe near midspan midchord (reuse existing inside/intersect helper).
- NACA constants present; plate-box path gone (no `box(..., THICK_MM, CHORD_MM)` for vanes).
- Existing CLI `--stator` / `stationary_downstream` tests stay green.
- No `★`.

## Non-goals

- `--stator-camber` / searched stagger / n_vanes
- Frame + stator stack
- BEM swirl-recovery credit
- Spanwise camber schedule / twisted OGVs
- NSGA default switch to stator

## Success

`--stator` builds a single fused STL of cambered NACA vanes + hub; flat-plate vanes are gone; CFD case wiring unchanged.
