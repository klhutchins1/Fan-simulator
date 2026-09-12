# Notched blade tips (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Optional **tip-only trailing-edge bites** on the loft: three cut-only teeth in the outer 12% of span. Default **off**. `--notched-tips` stamps a fixed recipe. Not spanwise owl serrations (`Features.serration_*`, tested null — do not re-open), not boolean cuts, not an NSGA variable, not cockpit sliders.  
**Roadmap:** §2.6 remainder. Noctua’s notched tips are a few nicks at the **outer TE**, not a wavy trailing edge all the way to the hub.

## Plain language

Noctua notches the blade **tip** to break up the tip vortex / tones. We already have spanwise TE serrations in the bio-feature layer; those were a null on flow **and** noise and must stay off the search. Stage 1 is a different stamp: three triangular bites that only **remove** TE (never add), only outboard of `r_frac = 0.88`. Default NSGA stays un-notched. Do not claim quieter BPF until an LBM pass.

## Problem

```text
apply_features serrations:  sawtooth along the WHOLE span, amp * chord, ± both ways
tip-round:                  shrinks the whole chord (LE and TE) over the outer span
```

Neither is a few TE-only nicks at the tip. Re-searching `serration_amp` is forbidden.

## Goal

1. **Fields on `BladeParams`** (not `RadialStation`, not `Features`):

```text
tip_notch_count: int = 0          # 0 = off
tip_notch_depth_mm: float = 0.0   # TE bite, mm; 0 = off
```

2. **`_section_loop`** after `apply_features`. Cut-only, TE-weighted, outer span only:

```text
START = 0.88
u     = clip((r_frac - START) / (1 - START), 0, 1)
w_te  = clip((x - 0.5) / 0.5, 0, 1)          # 0 at mid-chord, 1 at TE (same idea as serrations)
tooth = max(0, sin(2π * count * u))          # three positive lobes in the outer band; 0 at hub
a    -= depth_mm * tooth * w_te              # pull TE toward mid-chord; never grow the chord
```

Skip when `count <= 0` or `depth_mm <= 0`. Hub (`r_frac < 0.88`) is a no-op (`u = 0` → `sin 0 = 0`). Thread `count` / `depth_mm` through `_section_points_3d`, `build_blade_solid`, `open_tip_rmax_mm` / tip helpers (they already walk `_section_loop`).

3. **`apply_notched_tips(params) -> BladeParams`** in `fansim/geometry/blade.py` (mutates, like `apply_sickle`):

```text
NOTCH_COUNT = 3
NOTCH_DEPTH_MM = 1.5
NOTCH_START_FRAC = 0.88   # used in _section_loop, not stored on params
```

Sets `tip_notch_count = 3`, `tip_notch_depth_mm = 1.5`. Calling it twice is idempotent.

4. **Loft resolution** — when `tip_notch_count > 0`, `build_blade_solid` uses `n_span = max(n_span, 48)` so the outer 12% has enough sections to read as three teeth, not one facet.

5. **`blade_from_flat`** — if `notched_tips` is truthy or `tip_notch_count > 0`, call `apply_notched_tips` (or set the two fields from the dict). Stamped trials round-trip.

6. **CLI** — `scripts/run_optimization.py --notched-tips` (store_true, default off) → `run_study(..., notched_tips=False)` → after `suggest_params` / sickle / shroud stamps, `apply_notched_tips(params)`. Stamp `trial.set_user_attr("notched_tips", True|False)`. No `★`. Cockpit stays un-notched this cycle.

## Honesty

This is a **loft TE bite in the outer span**, not a digitised A12x25 photo and not Howe spanwise serrations. Positive `sin` lobes only remove material. Do not claim tone reduction. Do **not** turn `--features` serrations back on. `--notched-tips` and `--features` are independent; if both are on the bites add after the bio layer.

## Tests (no Docker mesh)

- `apply_notched_tips(p)`: hub TE (`r_frac=0`, `x=1`) stays within 0.3 mm of the un-notched section.
- At the first tooth peak (`u = 0.25 / 3`, `r_frac ≈ 0.89`) the TE (`x=1`) moves toward mid-chord by about 1.5 mm (±0.3 mm). LE (`x=0`) stays within 0.3 mm.
- Default `BladeParams()` is one solid; after `apply_notched_tips` still one solid; bbox diameter still ≤ 120 mm on defaults.
- `blade_from_flat({..., "notched_tips": True})` has `tip_notch_count == 3` and `tip_notch_depth_mm == 1.5`.
- Does **not** set `features.serration_amp` / `serration_waves`.
- `--notched-tips` in `run_optimization.py`; no `★`.

## Non-goals

- Re-opening bio-feature / tip-round search
- Boolean-cut notches after the loft
- Tracing a photographed Noctua tip
- Cockpit slider
- NSGA variable for count/depth
- LBM tone campaign
- Mixed-flow notches
