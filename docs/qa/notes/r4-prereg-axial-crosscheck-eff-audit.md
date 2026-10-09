# Round 4 pre-registration: axial-force cross-check, guard break test, efficiency and scored-vs-raw audits

Written 2026-10-09 (MDT) **before** any model run in round 4. It is hashed (sha256) and committed in the QA clone before running.
Code read beforehand (reading only): the `5396796` diff of `fan_bem.py`, `system_curve.py` and `objectives.py`; `cfd/metrics.py`;
`print_penalty.py`; `fan_spec.py`; `bem_screen.py`; the cockpit editor slider ranges.

Inputs:
- `cfd_designs.csv`, sha256 `cb8955e9ce798ecf75a5332997a4d134e6de90db7e9519cf50875b52e02ae624`.
- Screen-r3 designs: `research/screen_r3/all_designs.jsonl` (6,596 rows).

## Prior knowledge (disclosed)
- The two implementations look line-for-line the same in the diff: same constants AX_SLIP 0.65, AX_K_FRICTION 1.9 and CD_90 1.8, same inlet-W1
  axial force and same Viterna. The only code difference I saw is `area > 0` in Claude's `dp_static` branch.
- The masters differ (e48a32d vs f238f54). The only other files changed in between are `geometry/_build_worker.py` and `isolated.py`.
  So I expect agreement to round-off. A difference would point to the base, not the model.
- From round 3 I know:
  - axial Stock (screen settings) is 56.8 / 48.3 CFM at η_op 29.4 %;
  - Euler Stock is 25.7 %;
  - CFD Stock scored_eff is 17.888, with raw free 54.794 and raw load 41.75.
- I have **not** computed the implied derate, k_fsi or k_eta for any CSV row yet. The CSV has no raw η, torque or free static
  pressure, so I expect some of request 3 to be "not reproducible from the CSV alone".

## Request 1: implementation cross-check
Compare `pq_curve(bp, 2000 rpm, tip_gap_mm = screen gap, pressure_model="axial_force")` on both clones for:
- all 6,596 screen-r3 designs;
- Stock (7-station YAML);
- the round-1 paddle and reversed-blade cases.

Quantities: free CFM, shut-off Pa, peak η, and the guard verdict. My clone has no guard, so I apply the same rule to it:
`free_status == "no_rise"` or peak η < 5 %. Also compared: the screen score from `bem_screen.evaluate` with axial mode in each clone.

**EQUIVALENT** if all of:
- max |Δ free CFM| ≤ 0.1;
- max |Δ shut-off| ≤ 0.1 Pa;
- max |Δ peak η| ≤ 0.1 percentage points;
- Spearman ρ of the screen score ≥ 0.999;
- 0 guard-verdict disagreements;
- 0 screen-feasibility disagreements that are caused by the BEM.

Otherwise **NOT EQUIVALENT**. Each difference is then traced to model code or to the base commit.

## Request 1b: guard break test
Two settings: *editor ranges* (cockpit sliders) and, separately labelled, *file-loadable* designs outside the editor ranges.
- Editor ranges: 5–11 blades; stagger 15–55° per station; chord 14–50/60/70 mm; camber 0–0.06; t/c sliders.
- File-loadable examples: per-station paddles at ≥ 70°, a negative stagger station, 2 blades.

Physically-junk criteria (independent of the guard; BEM only, no CFD). They are evaluated at the axial-model **peak-η flow** and at
**free/2**:
- **J1 churn:** ≥ 50 % of span elements past stall (|α| > the post-stall band edge used by `_cl_cd_post_stall`).
- **J2 turbine:** ≥ 30 % of span elements at negative incidence (α < 0, so they extract work).
- **J3 paddle/reversed:** ≥ 1/3 of the span with stagger ≥ 70° or < 0° (file-loadable only).

Outcomes:
- **Slip-through:** guard passes AND (J1 or J2 or J3).
- **False refusal:** guard refuses a design inside the editor ranges with J1, J2 and J3 all false and Euler free CFM ≥ 20.

Report every slip-through and false refusal, and the 5 closest calls on each side, by peak η margin to 5 %.
The guard is judged **robust** if there are 0 slip-throughs in editor ranges and 0 false refusals.

## Request 2: efficiency-definition audit
Decomposition, fixed now:
- (a) BEM η "direct": `operating_point` at the un-derated hose intersection, before print. This is the screen's number.
- (b) BEM η "by the CFD procedure": η_free and η_probe from BEM at the free and 8 Pa probe flows; derated line; `score_operating_point`
  linear-in-flow η interpolation; then the same k_eta print knockdown. Done for both Euler and axial.
- (c) CFD scored η.

- **Definition/procedure part** = (b) − (a), plus any print-factor difference.
- **Model part** = (c) − (b).
- Verdict "**same quantity**" if |definition part| ≤ 1.0 pp; otherwise "**partly apples vs oranges**", with sizes.
- I also list scope differences that can't be computed without CFD raw data (e.g. which surfaces enter the CFD torque) as
  qualitative.

## Request 3: scored-vs-raw hand recompute
Rows: **stock**, **t9005** (best scored_load and scored_eff) and **bem_9504**.
- Documented factors only: `PRINT_K_CFM` 0.95; `k_eta` lerp by tip t/c; `k_fsi`; motor derate λ = min(1, (budget/shaft)^(1/3)); hose
  intersection with p_free and p_probe scaled by λ²; η linear-in-flow interpolation; optional third CFD.
- A value is **reproduced** if the hand number is within 0.5 % relative.
- Where a needed raw input is missing from the CSV (λ via torque, p_free, refine CFD), I back out the implied value and judge it
  plausible if 0.80 ≤ λ ≤ 1, and 0 ≤ p_free < 8λ² Pa. That case is labelled "consistent, not reproducible from the CSV".
- **Undocumented** = a correction a user cannot find in `README.md`, `docs/*.md` or the cockpit help/tooltips (search by name and value).
