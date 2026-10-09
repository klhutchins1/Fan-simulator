# QA-12: blended low-Re prop polar: result (2026-10-09, round 3)

**Verdict: FAIL (pre-registered).** The patch is offered only as a record. **Do not merge.**
Criteria: `docs/qa/notes/prop-lowre-blend-criteria.md`, sha256
`e91b280457a17f50f9e0b9c9a3e5375ebbba9ff6026e5899665abcfa2d426844`. The criteria were committed in the QA clone (branch
`prereg/round3`, 5913a74e) before anything was run.

## Plain-language summary
Below Reynolds number 40,000 (small, slow blade sections), the prop solver stops using measured
airfoil tables. Instead it jumps straight to a rough formula. At the switch point, lift drops by about 0.09
and drag rises by about 0.013. We replaced that jump with a smooth hand-over between Re 20,000 and
40,000. The jump is gone: lift and drag now change by 0.0% across Re 40,000, where they used to change by up to 66%.
However, the hand-over did **not** remove the "static thrust creeps up with rpm" problem (QA-12). It also made the match to the
measured GWS prop slightly **worse** on two of the pre-registered checks. So the jump at the switch point was a
real flaw, but it is **not** what causes the creep. The creep comes from the formula itself giving very different
numbers from the tables over the whole low-Re range, not from the step where the two meet.

## Numbers
Baseline is unpatched e48a32d. Geometry is exactly as in `tests/test_prop_uiuc_gws.py`, including the r/R 1.00
station. The script is `handoff/2026-10-09_from-qa-2/scripts/blend_eval.py`.

| rule | threshold | baseline | blend | pass? |
|---|---|---|---|---|
| R1 preset creep CT0(30k)/CT0(4k) − 1 | ≤ 20 % | +62.5 % (0.158 → 0.257) | +62.3 % (0.158 → 0.257) | **no** (expected, disclosed) |
| R2 GWS CT0 @ 7406.667 rpm vs 0.148983 | ±15 % | 0.1365 (−8.4 %) | 0.1419 (−4.8 %) | yes |
| R3 GWS CT0 ratio spread, rows ≥ 2500 rpm | ≤ 0.05 | 0.160 | 0.196 | **no** |
| R4 J-sweep CT rms @ 6047 rpm | ≤ baseline + 0.001 = 0.0090 | 0.0080 | 0.0100 | **no** |
| R5 prop test files (42 tests) + new test | pass | n/a | 42 + 4 passed | yes |
| R6 cl/cd jump Re 39,999 → 40,000, α 0/4/8° | < 1 % | 66.3 % | 0.0 % | yes |

R3 and R4 fail, so the verdict is **FAIL**, not a "Scoped PASS". Note that the baseline also fails R3 (0.160 > 0.05). In hindsight,
R3's threshold could not be reached by a polar blend alone. I did not change any threshold after seeing the numbers.

Preset CT0 vs rpm, baseline → blend: 4k 0.158 → 0.158; 8k 0.180 → 0.187; 15k 0.221 → 0.220; 22k 0.240 → 0.240;
30k 0.257 → 0.257. The blend changes only the 8k point. The rise from 4k to 30k is the same.

## Patch (record only)
`docs/qa/patches/prop-lowre-polar-blend.diff` passes `git apply --check` on e48a32d. It contains:
- `polars.lowest_table_re()`;
- an opt-in `low_re_blend` keyword on `bemt._section_aero` (`LOW_RE_BLEND_RATIO = 2`, so Re_a = Re_lo / 2 = 2e4), which only the prop
  `analyze()` passes;
- `tests/test_prop_lowre_blend.py` (4 tests).

The fan BEM path (`_cl_cd`) is unchanged on purpose. Fan sections sit at Re 1.5–4e4, so a shared change would
silently shift every fan BEM number and the Stock calibration.

## What would actually fix QA-12 (not done; needs new pre-registration)
The analytic low-Re polar disagrees with the e387 table at its own edge by about 0.09 in lift. A fix has to change
the low-Re model itself. Options:
- fit the analytic polar's Re-scaling to the 4e4/8e4 tables, or
- add a measured Re 2e4 table (e.g. Selig/UIUC low-Re E387 data), or
- use the NeuralFoil backend below 4e4.

Each option changes the fan BEM too, unless it is kept prop-only as done here.
