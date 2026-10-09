# Partial-height tip ring (stage 2)

**Date:** 2026-09-02  
**Status:** draft for review  
**Approach:** A — `shroud_height_frac` in [0, 1], default 1.0; hoop grown from the trailing edge  
**Roadmap:** §7.5 geometry slice. Not ring-to-frame CFD gap, not winglet×shroud policy.  
**Amends:** `docs/superpowers/specs/2026-09-01-tip-shroud-design.md` (full-span ring stays the default)

## Plain language

Stage 1 fused a hoop across the whole tip chord. Literature’s efficiency peak is a
shorter band (~30% of axial chord), not a full cover. This cycle adds a height
knob so you can draw that band in the cockpit. The optimizer and BEM keep treating
only a **full** ring as un-tipped. Existing recipes stay full-span.

## Problem

`--shroud` and the thickness slider always span the tip-section Z min/max. You
cannot build the 30% TE band the papers score, and a partial hoop would still
get the un-tipped BEM if we reused today’s `thick > 0` rule.

## Goal

When the ring is on (`shroud_thick_mm > 0`):

1. A second param, `shroud_height_frac`, sets how much of the **tip axial chord**
   the hoop covers. Default **1.0** is today’s full-span cylinder.
2. A value below 1.0 grows the cylinder from the **trailing edge** toward the
   leading edge.
3. Fit / frame / catalog OD is unchanged (still `+ 2 × shroud_thick_mm`).
4. BEM drops tip-loss **only** at `shroud_height_frac == 1.0`.
5. `--shroud` still stamps 1.6 mm at height 1.0. No new CLI flag. No search DOF.

## Non-goals (this spec)

- Designed ring-to-frame gap in optimizer CFD (§7.5 remainder / §1.1)
- Winglet auto-zero or a winglet×shroud search policy
- Searching `shroud_height_frac` or adding `--shroud-partial`
- Catalog backfill
- Changing the Propeller tab
- Replacing stage 1’s full ring as the default
- Third CFD solve / system-curve changes

## Param

New field on `BladeParams`:

```text
shroud_height_frac: float = 1.0   # 1 = full tip Z-span (stage 1); ignored if thick == 0
```

`shroud_thick_mm = 0` remains the only off switch. Height is ignored.

`blade_from_flat` reads `shroud_height_frac` (default 1.0) so old flats without
the key stay full-span. Do **not** scale this field in `scale_to_hub` (it is
already a fraction of the built tip).

## Geometry

Reuse `_shroud_solid`. Radii unchanged:

| Dim | Value |
|---|---|
| Outer radius | `open_tip_rmax_mm + shroud_thick_mm` |
| Inner radius | `tip_section_rmin_mm − 0.8 mm` |

Axial span today is `_tip_z_span` → `(z0, z1)`, height `h = z1 − z0`.

Tip-section airfoil `x` is 0 at LE and 1 at TE (`_section_points_3d`). Let
`z_te` be the axial coordinate of the TE (`x = 1`) vertices and `z_le` of the
LE (`x = 0`) vertices. Grow from `z_te` toward `z_le`.

When `shroud_thick_mm > 0`:

```text
span = z1 - z0                         # tip-section axial chord
h_req = shroud_height_frac * span
h = clamp(h_req, SHROUD_MIN_WALL_MM, span)   # 0.8 mm printable floor
# if span < 0.8 mm, use span (cannot exceed the tip)
```

Place the cylinder:

- If `z_te ≥ z_le`: from `z_te − h` to `z_te` (grows in −Z)
- If `z_te < z_le`: from `z_te` to `z_te + h` (grows in +Z)

`shroud_height_frac = 1.0` must match today’s `(z0, z1)` cylinder (same solid
as stage 1, within float noise).

`frac = 0` with thickness on is **not** a second off: it clamps to the 0.8 mm
TE band (or full span if the tip is shorter than 0.8 mm).

Depth / Fit: a partial hoop sits inside today’s tip Z-span, so `blade_z_extent`
and frame depth checks do not change. OD still grows by `2 × thickness`.

## BEM

If `shroud_thick_mm > 0` **and** `shroud_height_frac == 1.0` (compare after
rounding to a reasonable float, e.g. `>= 1.0 - 1e-9`):

- Prandtl `F = 1`
- Skip `K_TIP_LEAK`

Otherwise keep the open-tip tip-loss (including any partial ring). A 30% hoop
must BEM-score the same as the same blade with the ring off.

`--bem-prescreen` uses `pq_curve` as today, so it automatically sees this.

## Cockpit

Tip accordion, after Shroud thickness:

- Slider **Shroud height (tip chord)**: 0–1, step **0.1**, default 1.0
- Inactive when thickness is 0
- Hint: below 1.0 the hoop starts at the trailing edge; BEM still treats it as
  an open tip. Winglets stay independent (no auto-zero).

`e_shroud_height` ↔ `shroud_height_frac` in `edit_flat` / `_init_editor`.
Preview concatenates the shorter ring mesh. Assess / export use the fused solid.

## Optimizer

No change. `--shroud` stamps `shroud_thick_mm = 1.6` and leaves
`shroud_height_frac = 1.0`. No `--shroud-height` flag. No `★` in CLI help.

## Tests (no CFD)

- `thick = 0` ignores `shroud_height_frac` (same `blade_max_dia` / no ring)
- `frac = 1.0` fused ring matches today’s full tip Z-span
- `frac = 0.3` hoop height ≈ `0.3 ×` tip Z-span (after the 0.8 mm floor), TE-anchored
- `frac = 0` with thickness on has axial height `max(0.8 mm, …)` not 0
- OD still grows by `2 × thickness` at any frac
- BEM: full ring shut-off > open-tipped; `frac = 0.3` equals open-tipped on the same blade
- Printability still rejects `0 < shroud_thick_mm < 0.8`
- `blade_from_flat` without the key defaults to 1.0
- `--shroud` help / flag unchanged (no new flag)

## Success

You can turn on a ring in the cockpit, drop height to 0.3, and see a TE-anchored
band in 3D. Fit still uses the same OD as a full ring of that thickness. BEM does
not call a partial hoop un-tipped. `--shroud` campaigns stay full-span 1.6 mm.
