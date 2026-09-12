# Realistic system curve (stage 1)

**Date:** 2026-09-02  
**Status:** draft  
**Approach:** A — two CFD solves as today; algebraic intersection of a 2-point fan line with ΔP = k Q²  
**Roadmap:** §1.2. Not a third CFD solve, not §7.5, not circular AMCA.

## Plain language

A PC case / heatsink / radiator is not a wall at 8 / 20 / 35 Pa. Resistance
rises with flow (a hose, not a brick). Today the optimizer scores `cfm_load`
at a **fixed** back-pressure. That punishes weak fans (they never climb the
wall) and under-fights strong fans.

Stage 1 keeps the same two CFD runs (free air, then the preset’s Pa). After
both numbers exist, it estimates where that fan would sit on a hose
ΔP = k Q² and uses **that** CFM and efficiency as the load objectives.
Free-air CFM stays the third objective. No extra CFD.

You do not need to sign off on the algebra. The behavior is: slightly more
flow and slightly less pressure than the wall, for a fan that was not
exactly at the 50 CFM calibration point.

## Problem

`--preset case|heatsink|radiator` sets `load_pa` to 8 / 20 / 35 Pa.
`evaluate_candidate` meshes once and solves at 0 Pa and at that Pa.
`cfm_load` is flow against a **horizontal** load line. Real impedance is
closer to ΔP ∝ Q². NSGA-II therefore ranks the wrong operating point.

## Goal

Every optimizer trial (and cockpit Assess, which calls `evaluate_candidate`):

1. Still meshes once and still solves twice (free + probe Pa).
2. Converts the preset / `--load-pa` into k via **Pa at 50 CFM**.
3. Replaces `cfm_load` and efficiency with the intersection of
   - fan line through (Q_free, 0) and (Q_probe, P_probe)
   - system curve ΔP = k Q²
4. Leaves `cfm_free` as the derated free-delivery CFM.
5. Stamps `k`, `dp_op_pa`, `q_ref_cfm` on the trial so catalog rows know
   the convention.

## Non-goals (this spec)

- Third CFD solve at the predicted operating point — done 2026-09-03: opt-in `--refine-op` (see `2026-09-03-refine-op-cfd-design.md`)
- Iterating CFD until ΔP matches k Q²
- CLI `--k` (humans still think in Pa at 50 CFM)
- Changing BEM `--bem-prescreen` — done 2026-09-03: floor is the system-curve operating CFM (see `2026-09-03-bem-prescreen-system-curve-design.md`)
- Circular AMCA 210 / ISO 5801 duct
- Shroud-to-frame gap / partial ring (§7.5)
- Affinity-correct pressure scaling under motor derate (P ∝ RPM²) — done 2026-09-03: `p_probe_pa = load_pa * derate²`; hose k unchanged (see `2026-09-03-affinity-derate-pressure-design.md`)
- Docker / extra CFD campaign
- Re-scoring the historical catalog (old rows stay wall-scored)

## Constants and presets

```text
REF_CFM = 50.0
```

k from a human Pa number:

```text
Q_ref_m3s = REF_CFM / CFM_PER_M3S    # CFM_PER_M3S = 2118.88 (fansim.fan_bem)
k = load_pa / Q_ref_m3s²             # Pa / (m³/s)²
```

Presets **stay** 8 / 20 / 35 Pa. Those numbers now mean **Pa at 50 CFM**,
not a wall. `--load-pa` is the same: Pa at 50 CFM. Historical default
remains 1 Pa at 50 CFM when neither flag is set.

`resolve_load` still returns `(load_pa, preset_name)`. Conversion to k
happens in `evaluate_candidate` (or a one-liner next to it). Do not store
raw k in the CLI.

## Module

`fansim/optimize/system_curve.py`:

- `REF_CFM = 50.0`
- `k_from_pa(load_pa: float, ref_cfm: float = REF_CFM) -> float`
- `intersect_fan_line(q_free_cfm, q_probe_cfm, p_probe_pa, k) -> tuple[float, float]`
  returns `(q_op_cfm, p_op_pa)`

Units inside the quadratic are SI (m³/s, Pa); CFM only at the edges.

## Fan line and intersection

Probe CFD is still at `load_pa` (8 / 20 / 35 or `--load-pa`).

After the existing motor derate (CFM ∝ RPM, efficiency invariant):

- Q0 = derated free-delivery CFM
- Q1 = derated probe CFM
- P1 = imposed `load_pa` (not scaled — matches today’s derate)

Fan line (CFM, Pa), with P(Q0) = 0 and P(Q1) = P1:

```text
P_fan(Q) = P1 * (Q0 - Q) / (Q0 - Q1)
```

System:

```text
P_sys(Q) = k * (Q / CFM_PER_M3S)²
```

Convert Q to m³/s for the quadratic, or equivalently use
`k_cfm = k / CFM_PER_M3S²` so `P = k_cfm * Q_cfm²`.

Closed form in SI, Q in m³/s:

```text
a = k * (Q0 - Q1)
b = P1
c = -P1 * Q0
a Q² + b Q + c = 0
```

Take the unique root in `(0, Q0)`. (Monotone decreasing fan line vs
monotone increasing parabola through the origin: one crossing in that
open interval when Q0 > Q1 > 0 and P1 > 0.)

**Efficiency:** linear interpolate `m_free.efficiency` and
`m_load.efficiency` vs CFM to Q_op, then `* 100` as today. Do not keep
the probe-point efficiency as if it were the operating point.

## Infeasible

Return `_infeasible("system-curve: ...")` when:

- Q0 ≤ 0
- Q1 ≤ 0
- Q1 ≥ Q0 (probe flow not below free delivery — stalled or inverted)
- P1 ≤ 0
- k ≤ 0
- discriminant < 0 or no root in `(0, Q0)`

Unconverged CFD: keep the existing `UNCONVERGED` note on a **feasible**
result; do not add a new gate.

## Provenance

`run_study` / `evaluate_candidate` already stamp `tip_gap_mm` and
`frame_stl`. Add:

- `trial.set_user_attr("k", k)`
- `trial.set_user_attr("dp_op_pa", p_op)`
- `trial.set_user_attr("q_ref_cfm", 50.0)`

`pareto_summary` and `fansim/cockpit/data.py` `load_designs` extra dict
include those keys when present (None/absent on historical studies).

`ObjectiveResult.raw` also stores `k`, `dp_op_pa`, `q_ref_cfm`,
`cfm_probe` (wall CFM before intersection).

## CLI help

`--preset` / `--load-pa` help text: Pa at 50 CFM, system curve ΔP = k Q².
No `★` in Windows CLI help. No `--k` flag.

## Tests (no Docker)

`tests/test_system_curve.py`:

- `k_from_pa(8.0)` equals `8.0 / (50/2118.88)²`
- Fixture: Q0=80, Q1=50, P1=8, k from 8 Pa @ 50 CFM → op is **50 CFM, 8 Pa**
- A weaker probe (Q1=40 at 8 Pa) → Q_op > 40 and P_op < 8
- Q1 ≥ Q0 raises/returns the infeasible condition the helper exposes
- `--load-pa` / `--preset` help mentions 50 CFM; no `★`; no `--k`

A thin test that `evaluate_candidate` (or a extracted post-process helper
it calls) maps (cfm_free, cfm_probe, eta_free, eta_load) through the
intersection — mock/no CFD.

Existing `tests/test_presets.py` numbers stay 8 / 20 / 35; add that they
mean Pa at `REF_CFM`.

## Files

| Path | Responsibility |
|---|---|
| `fansim/optimize/system_curve.py` | k and intersection |
| `fansim/optimize/presets.py` | document Pa @ 50 CFM; keep 8/20/35 |
| `fansim/optimize/objectives.py` | after derate, replace load CFM/eta |
| `fansim/optimize/study.py` | user attrs |
| `fansim/cockpit/data.py` | extra keys |
| `scripts/run_optimization.py` | help text |
| `tests/test_system_curve.py` | math + CLI |
| `docs/roadmap.md` | §1.2 stage 1 done after implementation |
