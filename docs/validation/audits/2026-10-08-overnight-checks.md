# Overnight checks (pre-registered 2026-10-08; run 2026-10-09 07:36–11:17)

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

## Result (2026-10-09)

The 2026-10-08 23:30 launch died before starting (the background process was tied to the session);
re-run as a Windows Scheduled Task 07:36–11:17. Report: `runs/screen_rank_audit/overnight_20261008.json`.
The runner exited 0xC0000005 *after* writing the report (the known CPython teardown crash on this box).

### A. Re-Assess (measurements)

| design | free | load | η % | note |
|---|---|---|---|---|
| Stock, 7-station tapered (§23.1/§23.15) | 49.6 | 40.7 | 17.9 | 3-station build was 50.3 / 41.5 / 19.9 |
| stock_thin | 54.6 | 44.4 | 24.0 | |
| t9001 | — | — | — | rejected: depth 27.7 mm > 25 mm (envelope, not vibration) |
| t9002 | 56.6 | 46.0 | 31.5 | was 48.7 / 43.4 |
| t9003 | 62.1 | 48.0 | 31.3 | was 56.2 / 50.7 |
| t9005 | 65.8 | 48.6 | 32.0 | was 61.0 / 26.5 |

New scores written to the three saved designs' `design.json` (previous under `extra.rescored`).

### B. Quick screen Q3 (free + 8 Pa load, coarse) — **PASS**

| id | rule | result |
|---|---|---|
| n | ≥ 8 | 11 |
| a | ρ(Q3 load, full load) ≥ 0.80 | **0.936** |
| b | ρ(Q3 free, full free) ≥ 0.90 | **0.964** |
| c | full top 3 by load in Q3 top 5 | t9005, t9003, t9016 all in Q3 top 5 ✓ |

→ Q3 may be used to choose which ideas get a full Assess (§23.38). Q3 numbers run high (raw, no
derate/print penalty; e.g. t9016 85 vs 68 free) — rank only, never quote them.

### C. Mesh fairness for thick blades — **FAIL** (rule a)

| design (wall) | free L3 → L4 | Δ | load L3 → L4 | Δ |
|---|---|---|---|---|
| t9006 (2.69 mm) | 52.47 → 50.43 | −3.9 % | 42.83 → 41.42 | −3.3 % |
| t9008 (2.70 mm) | 55.14 → 51.25 | −7.1 % | 44.28 → 41.68 | −5.9 % |
| t9015 (2.36 mm) | 54.45 → 51.25 | −5.9 % | 44.38 → 42.18 | −5.0 % |

Rule b (order unchanged) holds, but every Δ exceeds 3 %: the level-3 floor scores thick-walled designs
**3–7 % high** against thin-walled ones meshed at level 4. Wall → level today: every other design here
(Stock 2.22 mm, the BEM top 5 1.06–1.54 mm) is level 4; walls above ~2.25 mm drop to 3. Per the
pre-registered consequence, thick-vs-thin comparisons carry a mesh bias until the Assess floor is raised to
4 or like is compared with like (§23.39).
