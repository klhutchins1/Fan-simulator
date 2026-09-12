# Affinity-correct probe pressure under motor derate

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep two CFD solves at rated RPM. After the existing CFM∝RPM derate, scale the probe pressure P∝RPM² before the system-curve intersection. The hose k is unchanged.  
**Roadmap:** §1.2 remainder (affinity P∝RPM²). Not third CFD, not circular AMCA, not BEM motor derate.  
**Amends:** `docs/superpowers/specs/2026-09-02-system-curve-design.md` (that spec left P1 = `load_pa` unscaled).

## Plain language

If the motor cannot hold rated RPM, we already slow the fan: flow scales with RPM. Pressure should scale with RPM². Today the hose intersection still treats the probe as the full preset Pa, as if a power-limited rotor still made 8 / 20 / 35 Pa. That overstates load CFM and operating pressure for motor-limited designs.

When derate is 1 (motor holds RPM), nothing changes.

## Problem

`evaluate_candidate` after the two RANS solves:

```text
derate = min(1, (budget / shaft_rated) ** (1/3))
Q0 = m_free.cfm * derate          # flow ∝ RPM  ✓
Q1 = m_load.cfm * derate          # flow ∝ RPM  ✓
score_operating_point(..., p_probe_pa=load_pa, load_pa=load_pa)
# P1 = load_pa                     # pressure not scaled  ✗
# k  = k_from_pa(load_pa)          # hose  ✓
```

`score_operating_point` already takes `p_probe_pa` and `load_pa` separately. Only the caller is wrong.

## Goal

1. `k = k_from_pa(load_pa)` stays the application hose (Pa at 50 CFM). The case does not care what RPM the fan reached.
2. Fan-line probe pressure becomes `p_probe_pa = load_pa * derate²`.
3. Q0 / Q1 stay CFM∝RPM as today. Efficiency stays unscaled (affinity: η ~ invariant).
4. Stamp `raw["p_probe_pa"]` (the scaled value) and keep `raw["derate"]`. `k` / `dp_op_pa` / `q_ref_cfm` stay the intersection result.
5. `derate == 1` → bit-identical to today’s intersection (same Q_op, P_op).
6. `derate < 1` → Q_op and P_op both **below** the unscaled intersection (weaker fan on the same hose).

No new CLI flag. Cockpit Assess already goes through `evaluate_candidate`, so it inherits this.

## Non-goals

- Third CFD at the predicted op
- Re-solving CFD at the derated RPM (affinity is the cheap stand-in)
- Derating the BEM prescreen (still rated RPM; a power hog can still pass BEM and fail later)
- Changing how `derate` is computed (still max of free/load shaft vs leeway budget, ∝ RPM³)
- Recalibrating presets 8 / 20 / 35
- Catalog backfill

## Algebra

λ = derate ∈ (0, 1].

```text
Q0 = Q0_rated * λ
Q1 = Q1_rated * λ
P1 = load_pa * λ²
k  = load_pa / Q_ref²          # unchanged
(Q_op, P_op) = intersect_fan_line(Q0, Q1, P1, k)
```

If λ = 0 or P1 ≤ 0 after scaling, keep the existing `system-curve:` infeasible path.

## Tests (no Docker)

- `score_operating_point` with λ=1 (P1 = load_pa): same as today’s 80/50/8 → 50 CFM, 8 Pa
- Same Q0/Q1 with P1 = load_pa * 0.8²: Q_op and P_op strictly below the λ=1 result
- `evaluate_candidate` post-process helper (extract if needed): derate=1 does not change P1; derate=0.5 sets P1 = 0.25 * load_pa
- Existing `tests/test_system_curve.py` numbers stay valid (they already pass explicit `p_probe_pa`)

No new optimizer flag, so CLI help is unchanged.

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/objectives.py` | `p_probe_pa=load_pa * derate**2`; stamp scaled P1 |
| `tests/test_system_curve.py` | scaled-P intersection inequalities |
| `docs/roadmap.md` | §1.2 remaining: third CFD only |

Do not add Python dependencies.
