# Lead #8: Koch (1981) stall pressure-rise limit (investigated 2026-10-08)

**Verdict: worth it as a small, opt-in fix for the shut-off number and the P–Q plot. It does not change design ranking and does not stop the paddle exploit.**

## Source
- The paper (J. Eng. Power 103:645) is **paywalled** and I did not read it. I used the write-up and the well-known form of the correlation.
- The form: the stalling static-pressure rise is a coefficient Ch times the inlet relative dynamic head. Ch falls as L/g2 grows (diffusion length divided by exit passage width), and has Reynolds-number and tip-clearance corrections.
- My Ch(L/g2) curve is a **smooth approximation**: about 0.6 at L/g2 = 0.2, falling to about 0.37 at 1.5. The Re knockdown is (Re/1.3e5)^0.1 and the clearance knockdown is 1 − 1.5·ε/g.
- **To do:** replace the curve with the digitised Koch figure once the paper is available.

## How the cap is applied
- For each element, compute g2 = pitch · sin(stagger + θ/2) and L = chord.
- The cap is the area average of Ch · ½ρW1² over the span, minus the friction term.
- The BEM static rise becomes min(BEM, cap).

## Results
Code: `proto/bem_variants.py` (`koch=True`). Uncalibrated is the raw curve; calibrated scales it ×1.67.

| case | base: free / shut-off / peak η | Koch, uncalibrated | Koch, calibrated ×1.67 |
|---|---|---|---|
| Stock (7-station) | 58.2 / **38.9** / 0.536 | 58.2 / **13.7** / 0.344 | 58.2 / **22.9** / 0.536 |
| top 5 / S03681 | 61.3–64.3 / 40.1–41.6 | 60.6–63.6 / 13.0–13.7 | unchanged / 21.7–22.9 |
| paddle 89° | 62.5 / 38.9 / 0.549 | 62.5 / 15.8 / 0.506 | 62.5 / **27.9** / 0.549 |
| reversed −45° | 7.6 / 38.0 / 0.528 | 7.5 / 11.5 / 0.16 | 7.6 / 19.2 / 0.267 |
| 0 blades | none / 0.07 | unchanged | unchanged |

**Against the references** (datasheet 22.9 Pa; parametric-Stock CFD shut-off proxy about 24 Pa, `docs/validation/a12x25_pq_report.md`):
- The uncalibrated curve has an error of −9 Pa, compared with +16 Pa today.
- The calibrated version hits 22.9 Pa by construction. That is a fit, not validation.
- It should be checked on a second fan, e.g. FAN-01, before trusting it.

**Re-ranking the 517 guarded screen designs** (calibrated): identical ranking (ρ = 1.000, 30/30 of the top 30 kept). The cap only acts well above the 8 Pa "case" hose point, so free and load CFM don't move.

## Effort vs gain
- Effort: S for the patch. M if you fetch the paper and digitise the real curve.
- Gain:
  - Stock shut-off goes from +70 % error to about 0 (calibrated).
  - It adds a stall-margin quantity the optimizer could use later.
  - It would matter for radiator-level hoses (35 Pa), which today sit past the predicted stall.
- What it doesn't fix: the paddle still out-pressures Stock.

## Patch
`patches/koch-stall-cap.diff`, adding `stall_cap=False` to `operating_point` and `pq_curve`.
- **Default off:** I checked that the default curve is byte-identical on all 11 cases.
- **Tests needed in `tests/test_fan_bem.py`:**
  - Default curve unchanged (regression).
  - Stock 7-station with `stall_cap=True`: shut-off within 22.9 ± 5 Pa and free CFM within ±0.5 of the uncapped value.
  - The cap never raises dp anywhere.
  - Zero blades: no crash, shut-off ≈ 0.
- **Also:** update the Audit-04 doc, and set `stall_cap=True` in the cockpit P–Q plot if he wants the shut-off displayed.
