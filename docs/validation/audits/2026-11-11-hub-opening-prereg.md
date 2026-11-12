# Pre-registration: put the A12x25 pad tips back on the opening that fits

Written before changing `grip_protrude_mm`. No CFD. No new boss diameter.

## What was measured (files, not a new run)

| opening | pad-tip diameter |
|---|---|
| `validation/reference/a12x25_impeller.stl` (the reference print's mesh) | 37.24 mm inscribed, median sector 37.26 mm |
| 2026-08-31 note in `fansim/fan_spec.py` | 37.25 mm inner diameter, the cup that slipped over the motor |
| App export 2026-09-15 morning, thin pads already present (`design_9003_20260915-093536.stl`) | 36.51 mm |
| App export 2026-09-15 15:01, and every stock export after it including 2026-10-08 and H7MQ8 | 36.55 mm |

H7MQ8 is the same 36.55 mm as the 15 Sep afternoon file. Nothing after that afternoon pulled the tips in further. The plastic (caliper 36.21 mm) matches that file. The motor boss is still the 2026-08-31 measurement; "about 38 mm" is not a new `cavity_dia_mm`.

## Pass / fail

Pass only if all of these hold:

1. `mount_grip_pad_layout` on the A12x25 mount gives a pad-tip diameter equal to `cavity_dia_mm` (37.25 mm) within 0.02 mm.
2. `cavity_dia_mm` stays 37.25. `grip_count` stays 20. `grip_dia_mm` stays 2.4. `grip_clearance_mm` stays 0.35.
3. Stock YAML, wrap, loft, and `_capped_loft` are untouched.

Fail if the tip diameter is still 36.55 mm. INCONCLUSIVE is not a pass.

## Result

PASS. `grip_protrude_mm` 0.7 → 0.35 on the A12x25 mount. Layout tip diameter 37.25 mm. `cavity_dia_mm` 37.25, grip count 20, grip diameter 2.4 mm, clearance 0.35 mm. Mount minimum hub radius moved 20.725 → 21.075 mm (Stock hub is 21.5 mm). Tests: `test_a12x25_pad_tips_match_the_opening_that_fits`, `test_mount_min_hub_radius`, `test_fan_spec_motor_mount_roundtrips` — 3 passed. No mesh rebuild in the 4–9 PM window.

## Printed coupon (Kimball, 2026-11-12)

`exports/hub_fit_37.25mm_20261111-215225.stl` (6 mm ring, pad tips 37.25 mm in the file) **fits the motor better** than H7MQ8 and E0MWW. Those two stay the T1 fail (pad IDs 36.21 mm and 36.73 mm). This coupon is not T1: T1 is a full impeller, seated, spinning, with the tip gap checked.
