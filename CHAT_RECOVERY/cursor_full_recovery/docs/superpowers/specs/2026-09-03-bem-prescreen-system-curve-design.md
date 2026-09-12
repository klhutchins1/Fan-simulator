# BEM prescreen on the system curve

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep `--bem-prescreen CFM_FLOOR`. Score the floor on BEM ∩ ΔP = k Q², the same operating point CFD uses for `cfm_load`. Two-point fan line from BEM free delivery and BEM flow at the probe Pa — not a new BEM-vs-parabola solver, not a third CFD.  
**Roadmap:** §1.2 remainder (BEM on the curve). Not third CFD, not affinity P∝RPM², not circular AMCA.  
**Amends:** `docs/superpowers/specs/2026-09-02-system-curve-design.md` (that spec's non-goal "Changing BEM `--bem-prescreen` (still free-delivery CFM)" is this cycle).

## Plain language

`--bem-prescreen 30` skips CFD when the mean-line BEM predicts **free-air** CFM below 30. After system-curve stage 1, the optimizer ranks **load** CFM on a hose ΔP = k Q². A fan that looks fine in free air and dies on a radiator still burns five minutes of Docker.

This cycle scores the same floor on the same operating point the CFD score uses. No extra CFD. No second flag. Default stays off.

## Problem

`evaluate_candidate` (after the gap gate):

```text
bem_cfm = pq_curve(...).free_delivery_cfm
if bem_cfm < bem_prescreen_cfm: infeasible
```

`load_pa` / `--preset` already mean Pa at 50 CFM. CFD `cfm_load` is `score_operating_point` on the 2-point RANS line. BEM never sees k.

## Goal

When `bem_prescreen_cfm > 0`:

1. Still one `pq_curve` call (milliseconds). Still before `export_stl`.
2. Build the same 2-point fan line CFD uses, from BEM:
   - Q0 = BEM free-delivery CFM
   - Q1 = BEM flow at static pressure `load_pa` (interpolate the BEM P–Q points)
   - P1 = `load_pa`
3. `q_op, _ = intersect_fan_line(Q0, Q1, P1, k_from_pa(load_pa))`
4. Reject when `q_op < bem_prescreen_cfm`. Reason still starts with `bem-prescreen` and says it is the system-curve operating point, not free air.
5. Exceptions other than a failed intersection still `pass` (screen must never break the eval). A failed intersection (BEM shutoff below the probe Pa, inverted, non-positive flows) **is** infeasible when the floor is on — that fan cannot sit on this hose.

`--bem-prescreen` default **0 = off**. Cockpit Assess still passes 0. `--surrogate-prescreen` stays free-delivery CFM (catalog GP is trained on `cfm_free`).

## Non-goals

- Third CFD at the predicted op
- Affinity-correct P∝RPM² under motor derate
- A second CLI flag (`--bem-prescreen-load`)
- Intersecting the full BEM polyline with k Q² (would be a third convention)
- Changing the GP surrogate target
- Recalibrating the suggested 30–35 CFM example for 120 mm — still conservative; it now applies to load CFM so it is slightly stricter on `--preset heatsink|radiator`

## Probe interpolation

BEM `FanCurve.points` run low flow (high static) → high flow (low static).

Q1 = linear interpolate `flow_cfm` vs `dp_static_pa` at P = `load_pa`.

- `load_pa <= 0`: screen on Q0 only (no hose)
- `load_pa >= shutoff_dp_pa`: no probe flow → infeasible (cannot reach the calibration Pa)
- Q1 ≥ Q0 (numerically, a 1 Pa probe sitting on free delivery): treat as Q1 = 0.999·Q0 so `intersect_fan_line` still has a unique root; Q_op ≈ Q0

Reuse `k_from_pa` / `intersect_fan_line` / `SystemCurveError`. Do not duplicate the quadratic.

Helper, testable without CadQuery:

```text
bem_load_cfm(params, rpm, load_pa, tip_gap_mm) -> float
```

raises `SystemCurveError` on the infeasible cases above. `evaluate_candidate` catches that and returns `_infeasible("bem-prescreen: ...")`.

Stamp `raw["bem_cfm_free"]` and `raw["bem_cfm_load"]` when a prediction ran.

## CLI

`--bem-prescreen` help: skip CFD when the fan-BEM **system-curve operating point** (same Pa @ 50 CFM hose as `cfm_load`) is below CFM_FLOOR. Conservative; BEM ranks CFD ~0.62. 0 = off. No `★`. No `--k`.

Existing `test_bem_prescreen_rejects_below_floor_before_geometry` (floor 500) still passes: load CFM < free CFM << 500.

## Tests (no Docker)

- `bem_load_cfm` on a fixture whose BEM free delivery is well above the probe: Q_op is between Q1 and Q0, P_op < load_pa (same inequalities as `test_weaker_probe_moves_op_to_higher_flow_lower_pressure`)
- BEM shutoff below `load_pa` raises `SystemCurveError`
- `evaluate_candidate` with floor 500: still infeasible, `bem-prescreen` in reason, no `impeller.stl`
- A floor **between** BEM free CFM and BEM Q_op: infeasible (today that floor would pass on free air)
- Help text mentions system-curve / 50 CFM / operating point; no `★`

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/system_curve.py` or `fansim/fan_bem.py` | `bem_load_cfm` + probe interp |
| `fansim/optimize/objectives.py` | screen on Q_op; stamp raw |
| `scripts/run_optimization.py` | help text |
| `tests/test_system_curve.py` / `tests/test_optimize.py` | math + gate |
| `docs/roadmap.md` | §1.2 remaining line |

Do not add Python dependencies.
