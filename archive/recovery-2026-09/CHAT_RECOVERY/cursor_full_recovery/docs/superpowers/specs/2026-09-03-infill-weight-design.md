# Infill-aware printed weight

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep solid volume from the STL. Convert to mass with a shell + infill fraction instead of 100% density. Default infill matches the print sheet (40%). `max_weight_g` stays 65 g and now means **printed** mass.  
**Roadmap:** §2.4. Not slicer-accurate wall volumes, not per-region hub-vs-blade infill, not changing the 65 g number.

## Plain language

The build gate weighs the impeller as a solid brick of PETG. Real prints are 4 walls plus ~40% hub infill, so the 65 g cap rejects designs that would print well under that. Use the same 40% infill the print sheet already recommends, plus a shell floor so thin blades are not treated as 40% air.

## Problem

```text
estimate_weight_g(volume_mm3, material) = volume * density   # 100% infill
```

`print_export.BLADE_PRINT_RULES["infill_pct"]` is already 40. The A12x25 comment even says realistic prints are lighter; the gate does not use that.

## Goal

1. Share the print-sheet infill default:

```text
DEFAULT_INFILL_PCT = 40          # BLADE_PRINT_RULES["infill_pct"]
SHELL_FRAC = 0.25                # walls/skins as a fraction of solid volume
```

2. Effective fill:

```text
f = infill_pct / 100
effective = SHELL_FRAC + (1 - SHELL_FRAC) * f    # clamp infill_pct to [0, 100]
# infill 100% → effective 1.0
# infill 40%  → effective 0.55
```

3. `estimate_weight_g(volume_mm3, material, infill_pct=DEFAULT_INFILL_PCT)`  
   `= solid_mass * effective`.

4. `evaluate_candidate` and cockpit weight use the default (no new CLI flag).
5. `max_weight_g = 65` unchanged; it is now compared to **printed** mass. Update the A12x25 comment.
6. `infill_pct=100` keeps today’s 10000 mm³ PETG = 12.7 g test.

## Non-goals

- Meshing walls vs infill in the STL
- Separate hub/blade infill
- Changing 65 g / 120 g caps
- Infill as an optimizer DOF

## Tests

- `infill_pct=100`: 10000 mm³ PETG still 12.7 g
- `infill_pct=40`: 0.55 × 12.7 g
- `infill_pct=0`: `SHELL_FRAC` × 12.7 g
- `check_build` still rejects 80 g against 65 g (that argument is already printed mass)

## Files

| Path | Responsibility |
|---|---|
| `fansim/manufacturability/print_export.py` | keep `infill_pct` as the source of the default (import, don’t duplicate 40) |
| `fansim/fan_spec.py` | `estimate_weight_g(..., infill_pct=)` |
| `tests/test_fan_spec.py` | 100% / 40% / 0% |
| `docs/roadmap.md` | §2.4 done |
