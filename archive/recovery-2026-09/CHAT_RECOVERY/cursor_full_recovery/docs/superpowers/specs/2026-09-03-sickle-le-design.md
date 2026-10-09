# Forward-swept sickle leading edge (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Add an LE-only circumferential offset (`le_skew`, mm) so the leading edge can sickle in the rotation plane without moving the trailing edge. `--sickle` stamps a fixed tip recipe (default off). Not a traced Noctua planform, not an NSGA variable, not cockpit sliders.  
**Roadmap:** §2.3 stage 1. Sweep/lean/skew move the **whole** section; `le_sweep` bends the LE in **Z**. The missing sickle is LE in **θ**.

## Plain language

A Noctua-style sickle is a banana planform: the leading edge curves in the disk, the trailing edge stays calmer. Today we can rake the whole blade in Z (`sweep`), wrap the whole chord around the hub (`lean`), nudge the whole chord in θ (`skew`), or rake only the LE in Z (`le_sweep`). None of those makes a scimitar LE.

Stage 1 is the same trick as `le_sweep`, in the other direction: a weight that is 1 at the LE and 0 by mid-chord, added to the tangential coordinate. `--sickle` turns it on with a fixed 8 mm tip (mid 40% of that, hub 0). Default NSGA stays unsickled. Do not claim quieter BPF until an LBM pass.

## Problem

```text
_section_loop:
  t     = chord-tangential + skew          # whole section
  axial = chord-axial + sweep + le_sweep*w_le
  w_le  = 1 at LE, 0 by mid-chord
```

`lean` rotates the whole loop. A sickle needs `t += le_skew * w_le`.

## Goal

1. **`RadialStation.le_skew`** (mm, default **0.0**), last field after `le_sweep` so existing positional callers stay valid. Interpolate in `_interp_stations`. Thread through `_section_loop` / `_section_points_3d`, `build_blade_solid`, winglet/tip-round station copies, `open_tip_rmax_mm`.

```text
w_le = 1 at LE, 0 for x >= 0.5   # already in _section_loop
t    = a*cos(β) - b*sin(β) + skew + le_skew * w_le
```

Positive `le_skew` is +t (same sign as `skew`).

2. **`apply_sickle(params, tip_mm) -> BladeParams`** in `fansim/geometry/blade.py` (mutates, like `apply_winglet`):

```text
SICKLE_DEFAULT_MM = 8.0
hub le_skew = 0
mid le_skew = 0.40 * tip_mm
tip le_skew = tip_mm
```

Only the three control stations (r_frac 0 / 0.5 / 1). If extra stations exist (winglet/tip-round), set them by interpolating that 0 / 0.4 / 1 recipe on r_frac. `tip_mm <= 0` is a no-op.

3. **`blade_from_flat`** reads `le_skew_mid` / `le_skew_tip` (default 0). Root stays 0. After stations are built, if `sickle_mm` is in the dict and > 0, `apply_sickle(bp, sickle_mm)` so a stamped trial round-trips.

4. **CLI** — `scripts/run_optimization.py --sickle` (store_true, default off) → `run_study(..., sickle=False)` → after `suggest_params`, `apply_sickle(params, SICKLE_DEFAULT_MM)`. Stamp `trial.set_user_attr("sickle_mm", 8.0|0.0)`. No `★`. Cockpit sliders stay off this cycle (LE curve in the UI remains axial `le_sweep`).

5. **Envelope** — `open_tip_rmax_mm` already walks section points, so a sickled LE that bulges outboard shrinks the per-trial tip cap. No special case. Do not change Fit-on-export.

## Honesty

This is **LE tangential rake**, not a digitised A12x25 planform and not AAO. Sign is a convention (+t), not “matches Noctua when viewed from the intake.” Do not claim noise until a campaign compares `--sickle` vs default on one design.

## Tests (no Docker mesh)

- `le_skew=0`: tip LE (x=0) 3D point matches a clone with the field omitted (within 1e-6).
- `apply_sickle(p, 8)`: tip LE moves in +t (at lean 0, +Y on the +X station) by about 8 mm vs unsickled; tip TE (x=1) stays within 0.3 mm.
- Hub LE does not move (> 0.3 mm) when sickle is applied.
- `tip_mm=0` leaves `le_skew` at 0.
- `blade_from_flat({..., "sickle_mm": 8})` has tip `le_skew == 8`.
- Default `BladeParams()` builds one solid; `apply_sickle(..., 8)` still one solid; bbox diameter still ≤ 120 mm on defaults (not the 110 cap — defaults are the old 113 mm envelope).
- `--sickle` in `run_optimization.py`; no `★`.

## Non-goals

- Searching `le_skew` in OPEN/GUIDED
- Cockpit slider
- Matching a photographed Noctua LE
- Changing `le_sweep` (axial LE curve stays)
- Noise objective / LBM
- Mixed-flow sickle
