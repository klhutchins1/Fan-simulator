# Tip shroud / ring (stage 1)

**Date:** 2026-09-01  
**Status:** draft  
**Approach:** A — ring adds OD; blades unchanged; BEM drops tip-loss when shrouded  
**Roadmap:** §2.1 (printable ring) + the BEM half of §7.5. Not the CFD / partial-height / winglet study.

## Problem

High-static axial fans leak over the open blade tip. A ring joining the tips
blocks that path. This tool can curl a winglet (~+4% flow, noise-floor) but
cannot build or screen a rotating shroud, so the optimizer never rewards the
geometry that actually wins on static pressure.

## Goal

An impeller can carry a **printable full-span tip ring**. Turning it on:

1. Fuses a hoop at the blade tips (cockpit slider, optimizer `--shroud`).
2. Grows the built OD by `2 × shroud_thick_mm`; Fit / frame / catalog use that OD.
3. Makes the mean-line BEM treat the fan as **un-tipped** (no Prandtl / gap leak).
4. Leaves existing recipes unchanged (`shroud_thick_mm = 0`).

## Non-goals (this spec)

- Partial-height ring (literature ~30% of axial chord) — later §7.5
- Designed ring-to-frame gap in optimizer CFD — §1.1
- Winglet × shroud interaction study (winglets help open tips, hurt a full ring)
- Catalog backfill of old runs
- Searching ring thickness as an optimizer DOF
- Changing the Propeller tab

## Geometry

New field on `BladeParams`:

```text
shroud_thick_mm: float = 0.0   # 0 = no ring
```

When `shroud_thick_mm > 0`, after hub + blades are fused, fuse a hoop.
Wrapped tip sections already bulge past `tip_radius` (today’s built dia is
~4 mm past `2 * tip_radius`). The ring must sit on that **built** envelope,
not on the nominal radius — otherwise a 1.6 mm hoop would sit *inside* the
blade tips.

Let `r_max` = `blade_max_dia(open) / 2` from the same section-point walk
used for frame checks (ignore the ring itself to avoid a cycle).

| Dim | Value |
|---|---|
| Outer radius | `r_max + shroud_thick_mm` |
| Inner radius | `r_max − 0.8 mm` (embed into the outermost blade metal) |
| Axial span | Z min/max of the **tip section** only (not the whole-blade bbox) |

Default when the operator turns the ring on: **1.6 mm** (~four 0.4 mm FDM walls).
Printability rejects `0 < shroud_thick_mm < 0.8` (below two walls).

`shroud_thick_mm = 0` is a no-op: same solid as today.

Winglets stay independent. The Tip-panel hint says they usually hurt a full
ring; the code does not auto-zero them.

## Diameter and placement

`blade_max_dia` (and therefore Fit, Scale, `nominal_fits_spec`, catalog
classify) must include the ring: **open `blade_max_dia` + `2 * shroud_thick_mm`**.
Fast path, no CadQuery solid.

`--shroud` shrinks the sampled `max_tip_radius` by `1.6 mm` on top of the
existing ~4 mm bulge margin so new trials still land inside the frame.

## BEM

If `params.shroud_thick_mm > 0`:

- Prandtl finite-blade factor `F = 1`
- Skip the outer-span `K_TIP_LEAK` knockdown

The rotating ring kills the blade-tip vortex. Remaining leak is **ring-to-frame**,
which this stage still leaves to CFD. A shrouded design must screen **higher
shut-off** (and usually higher loaded CFM) than the same blade open-tipped.

`--bem-prescreen` uses `pq_curve(params, …)` as today, so it automatically
sees the shrouded curve.

## Optimizer

`--shroud` (opt-in, like `--winglet`):

- Every trial sets `shroud_thick_mm = 1.6`
- `max_tip_radius` reduced by 1.6 mm
- Thickness is **not** a search DOF

`blade_from_flat` reads `shroud_thick_mm` (default 0) so catalog / cockpit
round-trip.

## Cockpit

Tip accordion, after winglet:

- Slider **Shroud thickness (mm)**: 0–3, step **0.8**, 0 = off. First on-step is two FDM walls;
  1.6 mm is four walls. A value in (0, 0.8) snaps up to 0.8 mm (a 0.2 mm nudge used to draw
  a hair-thin ring that failed printability).
- Hint: winglets usually hurt a full ring

`e_shroud_thick` ↔ `shroud_thick_mm` in `edit_flat` / `_init_editor`. Preview
concatenates a ring mesh (no boolean), same pattern as the hub. Assess / export
use the fused solid.

## Tests (no CFD)

- `shroud_thick_mm = 0` → same `blade_max_dia` as today
- `shroud_thick_mm = 1.6` → `blade_max_dia` grows by **3.2 mm** (exactly `2 × thickness` on top of the open-tip dia)
- Fused impeller with a ring is watertight, one body
- Printability rejects `shroud_thick_mm = 0.4`
- BEM: shrouded shut-off > open-tipped on `BladeParams()` at the same RPM
- `--shroud` is a recognized flag on `scripts/run_optimization.py`

## Success

You can turn on a ring in the cockpit, see it in 3D, Fit it to the A12x25
frame, and the BEM screen scores it as a high-static machine. The optimizer
can search shrouded designs with `--shroud` without blowing the 110 mm frame.
