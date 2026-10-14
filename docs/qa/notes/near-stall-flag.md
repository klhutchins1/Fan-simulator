# 25.10 near-stall flag — hold-out (2026-10-14)

Prereg: `docs/qa/notes/near-stall-flag-prereg.md`. Thresholds were not changed after this table.

Case hose 8 Pa @ 50 CFM, 2000 rpm, BEM default tip gap.

| design | CFD note | flagged | rule | max α deg | α_stall | DF | BEM free/load |
|---|---|---|---|---|---|---|---|
| Stock | reference | no | — | 7.46 | 9.07 | 0.548 | 60.4 / 50.5 |
| 9604 | best of Q3 top 4 | no | — | 4.62 | 9.65 | 0.560 | 63.3 / 53.4 |
| 9608 | ok | no | — | 6.48 | 8.73 | 0.547 | 61.0 / 52.2 |
| **9610** | Q3 #1, CFD near stall | **yes** | lieblein | 9.56 | 9.66 | **0.605** | 63.7 / 53.9 |
| 9613 | CFD ok (43.6 CFM) | **yes** | incidence | 11.42 | 9.97 | 0.600 | 64.7 / 53.8 |
| t9005 | best scored | no | — | 4.49 | 9.61 | 0.506 | 62.4 / 52.2 |

**Hold-out: MIXED.** 9610 is caught. 9604, 9608, Stock, t9005 stay quiet. 9613 also flags
(BEM incidence past stall) even though its full Assess did not unconverge. Do not retune.
The caption is a warning; scores are unchanged.
