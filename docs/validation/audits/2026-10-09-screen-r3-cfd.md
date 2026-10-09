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

## Result

_pending_
