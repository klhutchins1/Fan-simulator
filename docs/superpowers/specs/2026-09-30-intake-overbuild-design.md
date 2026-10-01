# Intake overbuild (+Z) — Design Spec

**Date:** 2026-09-30  
**Status:** accepted  
**Roadmap:** soft UX / design-freedom follow-on after §21 (not CFD honesty)  
**Approach:** (2) Design switch + intake overbuild budget

## Problem

Stock PC-fan envelopes (e.g. A12x25 depth ≤ 25 mm) clamp blade/hub axial placement. Users exploring non-drop-in shapes want blades and hubs to extend further toward the **intake (+Z)** without being forced back by Fit / Assess / red-highlight / green envelope. Library `leeway_depth` already grows total depth symmetrically; it does not express “extra on the inlet face.”

## Goals

1. Opt-in switch on Fan Design: **Allow intake overbuild (+Z)**.
2. Slider **extra intake mm** (default **10**, range 0–20).
3. When on, effective depth budget = `spec.depth_mm[1] + extra` for Fit, Assess gates, red highlight, and green envelope.
4. Extra length is attributed to the **intake (+Z) side** in viz (envelope / highlight), not mirrored past the outlet face.
5. Widen Hub sliders (`blade_hub_z`, hub height / nose as needed) so the UI can actually fill that room.
6. Honesty: still flag `over_spec` vs **nominal** frame depth; caption that the part won’t seat in a stock frame; CFD duct remains the stock frame for v1.

## Non-goals (v1)

- Growing the OpenFOAM domain / MRF with the overbuild (asymmetric CFD domain = later approach 3).
- Changing tip OD or radial leeway.
- Auto-on for Optimize search (optimizer stays nominal-envelope unless a later Adopt says otherwise).
- Prop / Mixed / Volute (Fan only).

## Behavior

### State

| State | Default | Notes |
|-------|---------|--------|
| `intake_overbuild` | `False` | Design switch |
| `intake_overbuild_mm` | `10.0` | Used only when switch on; clamped 0–20 |

### Effective depth helper

```text
nominal_depth_max = spec.depth_mm[1]
effective_depth_max = nominal_depth_max + (intake_overbuild_mm if intake_overbuild else 0)
```

Call sites that today use `spec.depth_mm[1]` for **allow/fit/viz** (not for datasheet readout) should use `effective_depth_max` when evaluating the editor design:

- `fit_envelope` max depth clamp
- Assess pre-check / `check_build` depth hi (pass via temporary leeway **or** explicit effective max — prefer one helper so Library leeway and intake overbuild compose: `depth_hi = nominal + lee_depth + intake_extra`)
- `nominal_fits_spec` / Results “fits this fan” when filtering **current editor** is unchanged for **saved** designs; saved designs keep their measured depth and existing over_spec flags
- Viz `_spec_limits` / envelope / highlight: use effective depth; **anchor outlet (−Z) face** of the green cylinder to the mesh outlet-ish side (or to `zmid - nominal/2` and extend only +Z by `extra`) so growth is intake-sided

### Over-spec honesty

- `over_spec_flags` continues to compare against **nominal** `spec.depth_mm[1]` (not effective). Designs that use overbuild still show `depth +N mm`.
- Assess done message / Actions chip: when switch on, show e.g. `intake +10 mm overbuild · won’t drop into stock frame`.
- Library `lee_depth` still applies globally; intake overbuild is Design-session and additive.

### Slider ceilings (when switch on)

| Control | Nominal UI | With overbuild |
|---------|------------|----------------|
| `e_blade_hub_z` | −8 … +8 | −8 … +(8 + extra/2) or similar so +Z shift can use the budget |
| `e_hub_height` | 0 … 30 | raise max by ~extra (e.g. 0 … 30+extra) |
| `e_hub_nose` | 0 … 15 | raise max by ~extra/2 (nose is +Z intake spinner) |

Exact numbers can be tuned; intent is “enough travel to spend the extra mm,” not a new DOF.

### Fit & seed panel UI

Under **Fit & seed**:

- Switch: `Allow intake overbuild (+Z)`
- Slider/field: `Extra intake (mm)` (disabled when switch off)
- Caption: stock depth stays N mm; on = allow blades/hub past inlet face by Extra; CFD duct still stock; Export may not fit a stock frame.

`Fit envelope` when overbuild is on clamps to **effective** depth (so Fit doesn’t yank the blade back into 25 mm).

### Export

No change to STL writer. Checklist / export caption should warn when measured depth > nominal (already partially covered by over_spec / fit switches).

## Tests

- Helper: `effective_depth_max(spec, overbuild=False, extra=10) == nominal`; with overbuild True adds extra; composes with leeway if helper includes it.
- Viz anchor unit test or pure function: given `z_out`, `nominal`, `extra`, envelope z-range is `[z_out, z_out+nominal+extra]` (or equivalent mid/height math) — outlet fixed, +Z grows.
- Fit: with overbuild on and depth between nominal and effective, `fit_envelope` does not shrink; with overbuild off, still clamps to nominal.

## Risks

- Users may Assess overbuilt geometry inside a stock-length duct → tip/hub near inlet BC; document in caption.
- Red highlight currently uses symmetric `|z-zmid| > depth/2`; must switch to outlet-anchored or asymmetric band or overbuild looks “red” incorrectly on +Z.

## Acceptance

1. Switch off → behavior identical to today.
2. Switch on + 10 mm → green envelope taller on +Z; Fit/Assess allow depth up to nominal+10; over_spec still flags past nominal.
3. Hub sliders can place material into that +Z band without the UI fighting back.
4. Short honesty caption visible when on.
