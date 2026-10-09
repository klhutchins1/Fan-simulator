# Third CFD at the predicted operating point

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Keep the 2-point algebraic intersection as the default. Opt-in `--refine-op` adds a third RANS solve at the rated-RPM equivalent of that operating pressure and replaces `cfm_load` / efficiency with the measured point.  
**Roadmap:** §1.2 remainder (third CFD). Not circular AMCA, not iterating until ΔP = k Q², not BEM.  
**Amends:** `docs/superpowers/specs/2026-09-02-system-curve-design.md` (that spec’s non-goal “third CFD solve”).

## Plain language

The hose operating point is still a straight line between free air and the probe Pa. Real P–Q is curved, so `cfm_load` is an estimate. A third solve at that pressure measures it. It costs ~50% more Docker time per trial, so it is **off by default**. Cockpit Assess stays two solves (you asked to score this design, not to pay an extra RANS unless you opt in later).

## Problem

After affinity derate, `cfm_load` is `intersect_fan_line` on two RANS points. The 2-point line is the stage-1 stand-in. Remaining §1.2 is to actually solve at the predicted op.

Always-on would slow every optimizer campaign. Proudman noise needs the **free** field last on disk, so a third solve has to be ordered carefully.

## Goal

1. Default (`refine_op=False`): bit-identical to today — two solves, algebraic `cfm_load`.
2. `--refine-op`: after a successful intersection, one more `solve_at` at
   `back_pressure = p_op / derate²` (rated-RPM equivalent of the derated hose pressure).
   Then `cfm_load = m_op.cfm * derate`, `efficiency = m_op.efficiency * 100`.
   `cfm_free` stays the derated free-delivery CFM. `dp_op_pa` stays the algebraic `p_op`
   (that is the hose pressure we aimed at; we do not chase a new intersection).
3. If that back-pressure is within **0.05 Pa** of `load_pa`, skip the extra solve and
   use `m_load` as `m_op` (already computed).
4. If the third solve throws: keep the algebraic `cfm_load` / eta, stamp
   `raw["op_cfd"] = "failed"`, stay **feasible**. Do not fail the trial for a
   refinement miss.
5. Proudman path: run the third solve **after** `proudman_swl_from_case` so the
   free field on disk is not overwritten before noise. Loading-proxy path: third
   solve after the two existing solves, before building `ObjectiveResult`.
6. Stamp `raw["cfm_op_alg"]` (algebraic Q_op, always) and `raw["op_cfd"]` =
   `"solved"` | `"reused-probe"` | `"failed"` | absent when refine is off.

`k` / `q_ref_cfm` unchanged. Catalog provenance does not grow a new convention.

## Rated-RPM back-pressure

CFD always spins at `spec.rpm`. The hose operating pressure `p_op` is at actual RPM
(`derate`). Affinity: P ∝ RPM², so the rated-RPM boundary that corresponds to that
hose point is

```text
p_rated = p_op / derate²     # derate == 0 already infeasible on the system-curve path
```

When `derate == 1`, `p_rated == p_op`. Helper: `rated_op_back_pressure(p_op_pa, derate)`.

Do **not** re-mesh. Do **not** change RPM for the third solve. Do **not** loop until
the measured ΔP equals k Q².

## Non-goals

- Default-on for optimizer or Assess
- A cockpit checkbox this cycle
- Fourth solve / Newton on the hose
- Changing BEM or the GP surrogate
- Circular AMCA duct

## CLI

`--refine-op` flag, default off. Help: third RANS at the system-curve operating
pressure (rated-RPM equivalent); replaces algebraic `cfm_load`. Off by default.
No `★`. No `--k`.

`run_study(..., refine_op=False)` → `evaluate_candidate(..., refine_op=False)`.

## Tests (no Docker)

- `rated_op_back_pressure(8.0, 1.0) == 8.0`
- `rated_op_back_pressure(5.12, 0.8) == pytest.approx(8.0)`  # 5.12 / 0.8²
- derate ≤ 0 raises `SystemCurveError`
- `evaluate_candidate` with `refine_op=True` and a stub `solve_at`: after the two
  existing solves, a third call at `p_rated`; `cfm_load` is third.cfm * derate
  (monkeypatch — no Docker). `raw["op_cfd"] == "solved"` and `raw["cfm_op_alg"]`
  is the algebraic Q
- Within 0.05 Pa of `load_pa`: no third call, `op_cfd == "reused-probe"`
- Third solve raises: feasible, algebraic `cfm_load`, `op_cfd == "failed"`
- `refine_op=False`: `solve_at` called twice, no `op_cfd` key
- CLI help mentions `--refine-op`; no `★`

The existing BEM / gap tests do not pass `refine_op` (default off).

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/system_curve.py` | `rated_op_back_pressure` |
| `fansim/optimize/objectives.py` | optional third `solve_at` |
| `fansim/optimize/study.py` | pass `refine_op` |
| `scripts/run_optimization.py` | `--refine-op` |
| `tests/test_system_curve.py` / `tests/test_optimize.py` | helper + stubbed solves |
| `docs/roadmap.md` | §1.2 remaining empty / stage 1 leftovers closed |

Do not add Python dependencies. Do not commit `catalog/catalog.db`.
