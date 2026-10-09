# Overnight checks (pre-registered 2026-10-08, run starts ~23:30)

Three questions, criteria fixed before any of tonight's data. Runner: `scripts/overnight_checks.py`
(resumable). Results: `runs/screen_rank_audit/` (`overnight_20261008.json`). Full Assess = cockpit
settings (8 ranks, 6 mm background, 500 + 500 iters, "case" hose 8 Pa, PETG, parallel snappy).

## A. Re-Assess what changed today

- **Stock**, now built from the signed-off 7-station, tapered-wall recipe (§23.1, §23.15). Last
  night's "stock" row used the 3-station build; it is kept as `stock_3station_20261007` for comparison.
- **t9001, t9002, t9003, t9005, stock_thin** — rejected last night by the blade-vibration gate, which
  is now a warning (§23.40). They get their first current-solver scores.

No pass/fail: these are measurements. The four saved designs' `design.json` are updated with the new
scores (previous result kept under `extra.rescored`), carrying the vibration warning.

## B. Quick screen with a load point (§23.38)

Tier **Q3**: 8 mm background, surface level 3 (as Q2), free-air **and** the 8 Pa "case" probe,
300 iters each. Quick scores are raw CFD CFM (no derate / print penalty).

Over every design with both a Q3 result and a feasible full Assess (stock_dimples excluded — it had
no dimples):

| id | rule |
|---|---|
| n | ≥ 8 designs, else INCONCLUSIVE |
| a | Spearman ρ(Q3 load CFM, full `cfm_load`) ≥ 0.80 |
| b | Spearman ρ(Q3 free CFM, full `cfm_free`) ≥ 0.90 |
| c | full-Assess top 3 by `cfm_load` all in the Q3 top 5 by load CFM |

PASS = a, b and c → Q3 may be used to pick which ideas get a full Assess. FAIL → it may not.
Thresholds are the same family as the 2026-10-07 audit and are not changed after seeing data.

## C. Mesh fairness for thick blades (§23.39)

The wall-adaptive surface level gives thick-walled designs the level-3 floor (~0.35M cells) and
thin-walled ones level 4 (~1M). Re-run the three thick designs (t9006, t9008, t9015) with the floor
raised to 4 (`surf_max_floor=4`) and compare with their level-3 results from 2026-10-08:

| id | rule |
|---|---|
| a | every design: \|Δ cfm_free\| ≤ 3 % and \|Δ cfm_load\| ≤ 3 % |
| b | their order by `cfm_load` is unchanged |

PASS (a and b) → the floor is fair; keep it. FAIL → rankings between thick and thin designs carry a
mesh bias; raise the Assess floor to 4 (≈ 3× cells for thick designs) or compare like with like.

## Result

_pending_
