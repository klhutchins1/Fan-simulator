# QA-12: blended low-Re polar, pre-registered rules (2026-10-09, round 3)

This extends `prop-ct0-rpm-creep-criteria.md` (sha256 428c808e…cea4), which stays unchanged.
Written BEFORE implementing or evaluating any blend.

## Disclosure
The round-2 diagnosis (`prop-ct0-rpm-creep.md`) found:
- Removing the fallback entirely, by clamping to the 4e4 table, still leaves +35 % creep. That
  residue comes from the table trend from 4e4 to 1.6e5 plus Mach.
- The same clamp worsened the GWS J-sweep CT rms from 0.010 to 0.024.

So any change limited to the Re < 4e4 branch is expected to FAIL R1. The real tests are R3 and R4.

## The change (fixed now, not tuned)
- Below the lowest table Re (Re_lo = 4e4 for every family), return
  `w·table(Re_lo, α) + (1 − w)·analytic(Re, α)` instead of switching hard to the analytic polar.
  This applies to cl and cd; `stalled` comes from the dominant branch and `cl_cap` is blended.
- The weight is `w = smoothstep((log10 Re − log10 Re_a) / (log10 Re_lo − log10 Re_a))`, with
  `Re_a = Re_lo / 2 = 2e4` and smoothstep(x) = 3x² − 2x³ clipped to [0, 1].
- At Re ≥ Re_lo nothing changes. At Re ≤ 2e4 the result is pure analytic, as today.
- One variant only. If I try any other form, I report it as exploratory, and it cannot be the
  proposed patch.

## Measurements
- Geometry is built exactly as `tests/test_prop_uiuc_gws.py` on e48a32d builds it, including the
  r/R 1.00 station.
- The baseline is measured on unpatched e48a32d with the same script.

## Rules
- **R1 creep:** preset `fpv_5inch` static CT0(30,000 rpm) / CT0(4,000 rpm) − 1 ≤ 20 %.
- **R2 static:** GWS 5×4.3 static CT0 at 7406.667 rpm within ±15 % of 0.148983, AND
  `tests/test_prop_uiuc_gws.py` passes unmodified.
- **R3 matched-geometry flatness:** the GWS model/measured CT0 ratio, max − min over static rows
  ≥ 2500 rpm, is ≤ 0.05.
- **R4 forward flight:** GWS J-sweep CT rms at 6047 rpm ≤ baseline + 0.001 ("no worse than today").
- **R5 regression:** test_prop_polar, test_bemt, test_uiuc_polars, test_prop_uiuc_gws and
  test_propeller all pass.
- **R6 continuity:** the cl and cd jump between Re 39,999 and 40,000 at α = 0°, 4° and 8° is below
  1 % of the value (camber 0.04, thickness 0.0633).

## Verdicts
- **Full PASS:** R1–R6 all pass.
- **Scoped PASS** ("removes the hard switch without hurting anything"): R2–R6 all pass, R1 fails.
  Proposed as a patch with that caveat.
- **FAIL:** any of R2–R6 fails. The patch is then still written as requested, but clearly marked
  FAILED and not recommended.
