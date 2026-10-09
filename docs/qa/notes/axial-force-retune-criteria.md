# Axial-force pressure accounting: re-tune pass/fail criteria (PRE-REGISTERED)

Written 2026-10-09 before any tuning run. Do not edit these rules after the
pre-registration commit; results go in `axial-force-pressure-accounting.md`.
Proof: committed on branch `prereg/axial-force-criteria` in
`/workspace/fansim/research/repo_research` (path `research-notes/axial-force-retune-criteria.md`),
and its sha256 is recorded in `notes/axial-force-retune-criteria.sha256`.

## Setup common to all rules
- Solver: `fansim.fan_bem.pq_curve(params, 2000 rpm)`, default n_points=22, n_elem=20,
  default tip gap (0.5 mm open tip), new opt-in mode switched on.
- Stock = `config/problems/a12x25_reference.yaml` (7 stations).
- Paddle = Stock with every station's stagger set to 89 deg. Reversed = Stock with every
  station's stagger set to -45 deg and to -60 deg. 0-blade = `BladeParams(n_blades=0)`.
- "Screen top-5" = `/workspace/fansim/screen/designs/0[1-5]_*.flat.json` (built with
  `blade_from_flat`, curves at 2000 rpm with the design's default gap).

## Tuning protocol (decided now)
- Tune ONLY on two Stock targets: free CFM -> 60.1 and shut-off -> 22.9 Pa (Noctua datasheet).
- At most 2 tuned parameters for 2 targets (so it is a fit, not validation). Candidates, in
  order of preference, all physically meaningful loss buckets:
  1. a deviation / under-turning factor applied to the blade axial force (plays the role of
     SLIP), bounds [0.5, 1.2];
  2. the friction / secondary-loss coefficient on the axial dynamic head (plays the role of
     K_FRICTION), bounds [0.0, 3.0];
  3. (only if 1+2 cannot reach rule (a)) the tip-leakage coefficient, bounds [0, 15], replacing
     one of the above so the count stays at 2.
- Polar: the existing `_cl_cd` polar. A post-stall polar is NOT tuned here.
- If no parameter set inside the bounds meets (a), report that as a FAIL; do not widen bounds.

## Rule (a) Stock calibration (in-sample)
- PASS if Stock free CFM is in [54.1, 66.1] (60.1 +/- 10 %) AND shut-off is in
  [17.2, 28.6] Pa (22.9 +/- 25 %).

## Rule (b) exploits are dead (out-of-sample hold-out)
For each of paddle-89, reversed-45 and reversed-60, PASS if EITHER
- the curve has no positive static pressure (`free_status == "no_rise"`), OR
- free CFM < 0.5 x Stock free CFM AND peak efficiency < 0.5 x Stock peak efficiency
  (Stock numbers from the same tuned mode).
0-blade: PASS if `pq_curve` returns without raising and free CFM == 0.
Rule (b) passes only if all four cases pass.

## Rule (b2) real designs stay real (out-of-sample hold-out)
- PASS if every screen top-5 design has `free_status == "crossed"`, free CFM >= 0.8 x Stock
  free CFM, and peak efficiency >= 0.5 x Stock peak efficiency (no legit design is killed).
- Reported, not tuned against: whether the top-5 still beat Stock on free CFM.

## Rule (d) opt-in safety
- PASS if with the setting OFF (default) every case above gives byte-identical curves to master,
  and the existing `tests/test_fan_bem.py` + `tests/test_bem_no_rise.py` still pass.

## Rule (c) ranking vs CFD (PENDING: needs Kimball's CFD-scored designs)
- Script: `research/proto/eval_rank_vs_cfd.py designs.csv` (ready to run).
- Metric (same as Audit #4 b): Spearman rho between BEM free CFM (new mode) and CFD free CFM
  over all CFD-scored designs.
- PASS if n >= 5 AND rho_new >= 0.6 AND rho_new >= rho_base - 0.10 (the new mode must not rank
  materially worse than today's BEM on the same designs).
- Alternative PASS when rho_new is in [0.5, 0.6): top-3 overlap (BEM top-3 vs CFD top-3) >= 2.
- n < 5 -> INCONCLUSIVE.
