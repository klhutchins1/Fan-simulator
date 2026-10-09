# Smooth span interpolation (optional) + extra stations

**Date:** 2026-09-09  
**Status:** Stage 1 done; Stage 2 deferred  
**User choice:** Both (spline first, extra stations later)

## Problem

Blade stations are hub / mid / tip with **linear** `_interp_stations`. Mid outliers create a sharp elbow (esp. skew/sweep/wrap). Literature favors smooth sweep; the kink is a 3-point linear artifact.

## Stage 1 (this pass)

1. `BladeParams.span_interp: str = "linear"` — `"linear"` | `"pchip"`.
2. `_interp_stations` uses `scipy.interpolate.PchipInterpolator` when `pchip` (fallback: cubic Hermite / numpy if scipy missing — prefer scipy already in stack).
3. Apply to all lofted station fields (chord, stagger, thickness, camber, sweep, skew, lean, le_*).
4. Cockpit Design: toggle **Smooth span curves** under “3-D shape”; persists via `edit_flat` / `blade_from_flat` as `span_interp`.
5. Default **off** (`linear`) — no change to existing designs / Optimize unless stamped.
6. Tests: linear unchanged; pchip removes mid kink for skew mid ≠ linear blend.

## Stage 2 (later)

- Optional 25% / 75% span editable stations for skew/sweep/wrap (or advanced panel).
- Still respects `span_interp`.

## Out of scope (stage 1)

- NSGA searching `span_interp`
- More than 3 editable stations
- Changing default Optimize behavior
