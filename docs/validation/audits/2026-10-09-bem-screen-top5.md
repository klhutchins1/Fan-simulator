# BEM-screen top 5 under full CFD (2026-10-09)

Measurements, not a pre-registered test. The QA bot's 6,596-design BEM screen (2026-10-08,
`handoff/2026-10-08_fan-sim-qa/screen_results.zip`, `screen/README.md`) concluded that **nothing in the
guarded guided space beats Stock** under the project objective (best BEM score 0.978 × Stock). Its top 5
(trials 9501–9505) were run through the full cockpit Assess (CFD_VERSION 5, level-4 mesh, "case" hose,
PETG; `scripts/assess_bem_top5.py`, results `runs/screen_rank_audit/bem_95xx/full`).

| design | BEM rank | BEM score | CFD free | CFD load | CFD η % | raw CFD free / load |
|---|---|---|---|---|---|---|
| Stock (7-station) | — | 1.000 | 49.6 | 40.7 | 17.9 | 54.8 / 41.8 |
| 9501 (S00948) | 1 | 0.978 | 57.1 | 46.1 | 28.3 | 61.5 / 49.5 |
| 9502 (T06567) | 2 | 0.976 | 58.2 | 46.2 | 26.6 | 69.4 / 58.6 |
| 9503 (T06478) | 3 | 0.966 | 58.2 | 46.0 | 27.0 | 67.8 / 56.2 |
| 9504 (T06559) | 4 | 0.962 | **60.0** | **46.6** | **28.6** | 67.7 / 54.7 |
| 9505 (T05663) | 5 | 0.955 | 58.1 | 46.2 | 26.5 | 69.9 / 59.4 |

## Reading

- **The BEM screen's headline was wrong.** All five beat Stock in CFD: +15–21 % free, +13–15 % load,
  ~1.5× efficiency. The (Euler) BEM rated Stock's high-camber recipe as the most efficient design in
  the space; CFD disagrees. Consistent with QA-4 / §23.5 (the BEM credits churned swirl as pressure) and
  with the weak Audit #4 ranking (ρ 0.714 on 7 designs, fragile — `2026-10-09-station-mapping.md`).
- **Within the five, BEM order carries no information** (CFD load spread 46.0–46.6; BEM's #4 is CFD's best).
- They land just below the best CFD designs so far (t9005 48.6 load, t9003 48.0) and above t9016 / t9002.
- All five are now scored in the cockpit (`runs/bem_screen_top5`), previous BEM objectives kept under
  `extra.rescored`.

## Consequence

A BEM pre-screen cannot currently say "this beats Stock" or rank near-ties. The QA bot's axial-force
BEM mode is to be judged on these designs (rule (c), `handoff/2026-10-09_to-qa-2/cfd_designs.csv`).
Until a BEM mode passes, ideas should be ranked with the Q3 quick CFD screen (passed 2026-10-09,
ρ_load 0.936), not the BEM.
