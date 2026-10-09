# Per-candidate frame tip-radius cap

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** After sampling planform, iterate `open_tip_rmax_mm` (same shrink as cockpit Fit) to find the largest `tip_radius` whose built envelope still leaves the 0.5 mm leftover. Replace `frame/2 − 4`. Not a CAD loop. Not Fit-on-export.  
**Roadmap:** §3.3. Not §3.4 auto-fit, not changing `check_build`, not catalog `2r+4` rows.

## Plain language

The optimizer samples `tip_radius` up to **frame/2 − 4 mm** (51 mm on A12x25) because the built tip bulges past `2 × tip_radius`. That 4 mm is a worst-case guess. Low-lean blades leave unused radius; high-lean blades can still overshoot and get gated. Cockpit Fit already shrinks against the real section-point diameter. Do that once per trial, then sample up to *that* cap.

## Problem

```text
# fansim/optimize/study.py
max_tip_radius = spec.tip_dia_mm[1] / 2.0 - 4.0   # 55 − 4 = 51
if with_shroud:
    max_tip_radius -= SHROUD_DEFAULT_MM
suggest_params(..., max_tip_radius=max_tip_radius)
```

`open_tip_rmax_mm` is cheap (section points, no CadQuery). The CFD leftover gate is already 0.5 mm to the same frame ID. The 4 mm pad throws away ~3 mm of blade on a typical planform.

## Goal

1. Helper (no CAD), same shrink as `snap_tip_to_frame`:

```text
CLEARANCE_MM = 0.5          # matches OPTIMIZER_TIP_GAP_MM
# allowed built radius = frame_half - shroud - CLEARANCE
# start tr = that radius; 12 steps:
#   built = open_tip_rmax_mm(probe at tr) + shroud
#   if built <= allowed: return tr
#   tr -= (built - allowed) + 0.15
# floor at 48 mm (today’s search lo)
```

`shroud` is `SHROUD_DEFAULT_MM` when `--shroud`, else 0. Height frac does not change OD.

2. `suggest_params` samples chords/lean/hub **first**, then:

```text
cap = tip_radius_cap_mm(stations, hub, frame_half, shroud)
tip = trial.suggest_float("tip_radius", min(48.0, cap - 1.0), cap)
```

If `cap < 48`, still sample in `[cap - 1, cap]` (same pattern as today when the 4 mm cap is tight).

3. `run_study` passes `frame_half_mm=spec.tip_dia_mm[1] / 2.0` instead of pre-subtracting 4. Drop the `max_tip_radius = frame/2 - 4` line. `--shroud` no longer subtracts ring thickness in `study.py` (the helper does).

4. Keep the `max_tip_radius=` kwarg as an explicit override (tests / isolation studies). When both are set, `frame_half_mm` wins for the cap; override is only if `frame_half_mm` is None (today’s path).

Simplest: replace `max_tip_radius` with `frame_half_mm`. Callers that passed a pre-shrunk cap pass `frame_half_mm=that_cap + 4` — there are no tests on `max_tip_radius`. **Replace the kwarg.**

5. Cockpit Fit / editor sliders unchanged.

## Non-goals

- Fit-on-export (§3.4)
- Changing `check_build` or catalog `2*tip_radius + 4` classifiers
- Sampling past the leftover floor (would just fail the CFD gap gate)
- CadQuery in the cap helper
- Changing default `BladeParams.tip_radius` when `frame_half_mm` is None (unconstrained / no `--extended`)

## Tests (no Docker, no CAD)

- Zero lean, short tip chord: cap is **greater than** `frame/2 - 4` (the old pad was too conservative).
- High tip lean + wide tip chord: cap is **smaller than** the low-lean cap (wrap costs radius). The 4 mm pad is still conservative even at 45° lean in this section-point model.
- Capped probe: `open_tip_rmax_mm + shroud + 0.5 <= frame_half` (within 0.2 mm).
- `--shroud`: cap drops by at least ~80% of ring thickness vs the same planform without a ring.
- `suggest_params(..., frame_half_mm=55)` sampled `tip_radius` ≤ that cap.

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/search_space.py` | `tip_radius_cap_mm`, sample after planform, `frame_half_mm=` |
| `fansim/optimize/study.py` | pass `frame_half_mm`; remove `- 4` |
| `tests/test_search_space.py` | cap vs 4 mm pad; leftover inequality |
| `docs/roadmap.md` | §3.3 done |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
