# Screen r3 under CFD — does the axial-force BEM hold in new territory? (pre-registered 2026-10-09)

Written before any CFD of these designs. Shortlist: the QA bot's axial-force BEM screen with
`max_camber` ≤ 0.10 (`handoff/2026-10-09_from-qa-2/screen_r3/`, 30 designs, trials 9601–9630). Its top 5
(9601–9605) beat Stock under the axial model (score 1.067–1.325) while the Euler BEM puts them below
Stock; they sit at search-space edges no CFD-scored design has covered.

## Runs

1. **Q3 quick screen** (passed its audit 2026-10-09: ρ_load 0.936) on all 30, same settings as
   `scripts/overnight_checks.py` part B (8 mm, level 3, free + 8 Pa, 300 iters). Stock's Q3 is the
   2026-10-09 run (`runs/screen_rank_audit/stock/quick_load`).
2. **Full Assess** (level-4 floor, "case" hose) on the top 4 by Q3 load CFM. Scores written to the
   cockpit designs.

## Questions and rules (fixed now)

| id | question | metric | verdict rule |
|---|---|---|---|
| A | Does the axial model's "beats Stock" hold for its top 5? | # of 9601–9605 with Q3 load CFM > Stock's Q3 load CFM | **SUPPORTED** ≥ 4/5 · **REFUTED** ≤ 1/5 · otherwise MIXED |
| B | Does the axial score rank designs in this region? | Spearman ρ(axial screen score, Q3 load CFM) over the 30 | **USABLE** ρ ≥ 0.5 · **NOT USABLE** ρ < 0.3 · otherwise INCONCLUSIVE (n = 30) |
| C | What do the best of them really do? | full-Assess free / load / η of the Q3 top 4 vs Stock (49.6 / 40.7 / 17.9) and the best so far (t9005 65.8 / 48.6 / 32.0) | measurement, no pass/fail |

Q3 numbers are rank-only (raw, run high); A compares Q3 with Q3, so the offset cancels. No rule is
changed after seeing data. A or B decide only how much weight the axial BEM gets as a *ranker*; its
adoption as an exploit guard (opt-in, rejecting paddle / reversed designs) does not depend on this run.

## Result (2026-10-09; run 15:07–16:02 + 17:13–19:28, resumed after a session-end kill)

**4 of 30 designs got no CFD.** 9605, 9606, 9620 and 9630 were refused by the builder rotor direction
cross-check. All four are low-camber with strong tip lean (camber 0.004–0.016, tip lean 22–42°), and the
proof reads lean curvature as camber. This is a known false refusal; a first fix failed its own checks
(`2026-10-09-direction-crosscheck.md`). Stock's Q3 load: **38.56 CFM**.

| id | verdict | evidence |
|---|---|---|
| A | **INCOMPLETE (4/5 run)** | 9601, 9603 and 9604 beat Stock on Q3 load (54.3 / 45.8 / 55.4 vs 38.6). **9602 does not (28.5).** 9605 not run. With 9605 the verdict can only be SUPPORTED (if it beats Stock) or MIXED (if not), never REFUTED |
| B | **USABLE** (ρ = **0.536**, n = 26) | Just above the 0.5 bar: the axial score ranks this region's Q3 load weakly but usably |
| C | measurement | below |

**C: full Assess of the Q3 top 4** (scored free / load / η; Stock 49.6 / 40.7 / 17.9; best so far t9005 65.8 / 48.6 / 32.0):

| design | Q3 load | full free | full load | full η | note |
|---|---|---|---|---|---|
| 9604 | 55.36 | 55.9 | **46.1** | **27.9 %** | best of the four; ≈ bem_9504 |
| 9613 | 57.67 | **62.5** | 43.6 | 20.9 % | |
| 9608 | 54.60 | 55.3 | 42.5 | 20.3 % | |
| 9610 | **59.06** | 52.3 | **37.1** | 13.2 % | Q3's #1; full 8 Pa probe solve UNCONVERGED (osc 4.6 %), 35.0 CFM raw vs Q3's 59.1: near stall on the fine mesh |

**Reading:**
- Three of the four beat Stock on load, but **none beats the best existing designs** (t9005, t9003).
  The axial BEM's large predicted gains (scores up to 1.33) did not show up.
- Within the top 4, Q3's order is nearly reversed by the full Assess. Q3's pre-registered PASS
  (2026-10-09, ρ_load 0.936 on 11 designs) came from the old search region. Here its #1 pick (9610)
  sits near stall under load, and the coarse mesh does not see that.
- Treat Q3 as a filter for clearly bad designs, not as a way to pick a winner, until it is re-audited
  on designs like these.
