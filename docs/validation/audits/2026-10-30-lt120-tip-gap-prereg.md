# lt120 tip-gap sensitivity (follow-up to R1.1b): pre-registration

Written 2026-10-30, **before** any of these runs. Kimball asked for the follow-up on 2026-10-30.

## Why

lt120 came back **TRENDS**: CFD is +8.1 % at 6.85 Pa but +25.8 % at 13.71 Pa (`2026-10-18-lt120-validation-prereg.md`,
Results). CFD gives this fan too much pressure capability.
- The leading suspect is the **tip gap**. Lin & Tsai do not report it, and the freeze assumed 0.5 mm.
- A bigger gap leaks more flow round the tips under load, which lowers pressure capability and steepens the curve.

**The question:** is the loaded over-prediction explained by a tip gap within the plausible range, or is it a CFD or
modelling issue that would also affect our scores?

## This is not a retune

- **The lt120 verdict stays TRENDS whatever this shows.** A gap chosen after seeing how well it fits is a fitted gap,
  not a validated one.
- Nothing in the shipped setup changes. The cockpit's own tip-gap rule is not touched.
- The only output is what the release text says about *why* loaded flow reads high on lt120.

## Setup (fixed)

- Exactly the frozen lt120 case (`validation/reference/lt120/`, `scripts/validate_lt120.py`). The **rotor is unchanged**:
  only the duct grows, with duct ID = 2 × r_tip + 2 × gap (the frozen case is 121 mm at 0.5 mm).
- **Gaps:** 1.0 mm and 1.5 mm, plus the existing 0.5 mm runs as the baseline. The range is fixed now as the plausible
  span for a CNC prototype in a test duct of this size (about 0.8–2.5 % of the radius). No other gap is run.
- **Points:** the two high-flow points only, 6.85 Pa and 13.71 Pa.
- **Mesh:** 5.8 mm only (the 0.5 mm runs showed the two meshes agree within 3 %).
- Same convergence gate (oscillation ≤ 2 %, mass imbalance ≤ 1 %). A point that fails it is INCONCLUSIVE.
- Results go to `runs/lt120_tipgap/summary.json`. Day CPU, about an hour; the runner stops before 15:30.

## Outcome rules (fixed now)

Let e(g) be the CFD error at 13.71 Pa for gap g, against the measured 60.0 CFM (e(0.5 mm) = +24.6 % on the 5.8 mm mesh).

| outcome | rule | release text |
|---|---|---|
| **G1, explained** | at some gap ≤ 1.5 mm, e(13.71) ≤ +10 % **and** the 6.85 Pa error stays within ±10 % | "lt120's loaded airflow is sensitive to its tip gap, which the source doesn't report; with a plausible gap, CFD matches within 10 %" |
| **G2, partly** | e(1.5 mm) ≤ ½ × e(0.5 mm), i.e. ≤ +12.3 %, but G1 not met | "a plausible tip gap explains about half the loaded over-prediction on lt120; the rest is unexplained" |
| **G3, not explained** | anything else | "CFD over-predicts loaded airflow on lt120 by about 25 %, and the tip gap does not explain it" |

- Under G3 the over-prediction is a CFD or modelling question that also bears on the scores' loaded airflow. That becomes
  a roadmap item, not a v0.1.0 blocker, because the scores rank designs and the release text already says so.
- Monotonicity check, report only: e(13.71) should fall as the gap grows. If it doesn't, say so.
