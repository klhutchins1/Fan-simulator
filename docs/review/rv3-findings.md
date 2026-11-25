# RV-3 findings log

Module-by-module review (`docs/review/2026-11-24-review-plan.md`, RV-3). Each module gets the plan's checklist:
are equations sourced, are units and signs right, are failures swallowed, are constants defined once, are there
numeric tests, is it in the audit ledger, is anything over-long. "Fixed" means the change is on branch
`claude/rv3-review`, with a test that fails on the old code.

## 1. `fansim/optimize/objectives.py` (`evaluate_candidate`), reviewed 2026-11-24

| # | severity | finding | status |
|---|---|---|---|
| O1 | **high** | The structural gates (centrifugal stress ∝ rpm², resonance vs blade-pass ∝ rpm) ran **before** `params.rpm = target_rpm`, so they judged the stale `params.rpm` (BladeParams default 2000). For the 3900 rpm Delta AFC1212DE model, stress was under-stated by about 3.8× and blade-pass by 2× (300 Hz, not 585 Hz, which is above Stock's ~400 Hz first bending mode), so resonant designs passed. A12x25 `--search-rpm` (450–2000) was conservative. It also mutated the caller's params. | fixed `e349624` (`tests/test_objectives_gate_rpm.py`) |
| O2 | medium | A BEM pre-screen crash was `pass`ed: the design went to CFD with no trace. | fixed `d6097c4` (`raw.bem_prescreen_error`) |
| O3 | medium | A sanity-check crash became `[]`, and the status read `SKIP`, the same as "never ran". | fixed `d6097c4` (status `ERROR`, `raw.sanity_error`) |
| O4 | low | "solve failed" dropped the exception message. | fixed `d6097c4` |
| O5 | low | The free-air salvage failure was `pass`ed. | fixed `d6097c4` (`raw.free_salvage_error`) |
| O6 | low | If trimesh cannot read the STL volume, the weight gate is skipped with no stamp (`weight_g = None`). | open |
| O7 | low | The loading-noise proxy uses free-air thrust at **rated** rpm; it is not derated with the motor (thrust ∝ λ²). It is ranking-only, so the order holds within one derate, but a motor-limited design reads louder than it runs. | open |
| O8 | code health | `evaluate_candidate` is ~490 lines: gates, pre-screens, geometry, CFD, scoring. | RV-5 (split into stages) |

Checked and fine: derate (flow ∝ λ, power ∝ λ³, probe pressure ∝ λ²); signed CFM is never `abs()`-ed (a reversed
probe reads as a stall); system-curve failure reasons; the surrogate pre-screen already refuses rather than falling
through to CFD (§9.6).

## Next modules

2. `fansim/fan_bem.py`
3. `fansim/cfd/metrics.py`, `flow_report.py`, `flow_verdicts.py`
4. `fansim/geometry/blade.py`, `airfoil.py`
5. `fansim/propeller/bemt.py`, `polars.py`
6. `fansim/optimize/search_space.py`
7. `fansim/structural/*`, `fansim/acoustics/*`
8. cockpit

Carried in from earlier work (see the plan): the CFM factor is defined twice more (`optimize/meanline.py:20`,
`optimize/multi_point.py:132`); the physics rounds its own outputs (`fan_bem.py:246`, `bemt.py:202`);
`NU_AIR` is not `MU_AIR / RHO_AMCA`; PETG and PLA share a 50 MPa yield.
