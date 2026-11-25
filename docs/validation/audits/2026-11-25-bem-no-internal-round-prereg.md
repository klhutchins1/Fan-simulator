# Pre-registration: stop rounding inside BEM / BEMT (#50) — 2026-11-25

**Ruling by Cursor.** Before removing `round(...)` from `fansim/fan_bem.py` and
`fansim/propeller/bemt.py`.

## Claim

Screening maths return full-precision floats. Display/export may round; the solver must not.

## Pass / fail (committed before the change)

| Id | Rule |
|----|------|
| P1 | `operating_point` Stock planar @ 2000 rpm, Q mid-band: `flow_cfm`, `dp_static_pa`, `efficiency`, `power_w` each differ from `round(x, n)` at the old bit-depths (cfm 1 / Pa 2 / η 3 / W 2) — i.e. at least one field has a fractional part the old round would have dropped. |
| P2 | `bemt` hover (or low-J) point: `thrust_n` / `power_w` / `figure_of_merit_raw` similarly retain sub-round precision vs old depths (T 3 / P 1 / FM 4). |
| P3 | Registered checks for `fan.bem_prescreen` and `propeller.bemt` green with `-m "not docker"`. |
| P4 | `scripts/physics_snapshot.py --write --reason` this file; snapshot test green. |
| P5 | `record_pass` for every unit `audit_status` marks CHANGED; dependants return PROVEN. |

INCONCLUSIVE is not a pass. Do not re-tune rounding back into the solvers to make a lock pass — widen test abs/rel instead.

## Result (after change)

P1–P5 **PASS**. `round()` removed from `operating_point` / `pq_curve` and `bemt.analyze`.
Physics snapshot rewritten. Units re-proven: `fan.bem_prescreen`, `propeller.bemt`,
`cfd.cfm_from_outlet_flow`, `cfd.duct_area` (latter two CHANGED only because
`tests/test_math_consistency.py` is a shared check and lost the `round(expected, 2)` lock).
Ledger: 33 PROVEN.
