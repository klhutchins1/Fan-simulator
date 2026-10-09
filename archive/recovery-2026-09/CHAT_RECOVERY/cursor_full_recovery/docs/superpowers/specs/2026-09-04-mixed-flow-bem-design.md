# Mixed-flow BEM via axial adapter (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Map `MixedFlowParams` → a synthetic `BladeParams` and reuse axial `pq_curve` / `bem_screen_cfm` as a cheap screen before mixed-flow CFD. Optional `bem_prescreen_cfm` on `evaluate_mixed_flow` + CLI. Not a meridional BEM, not NSGA, not cockpit switch this cycle.  
**Roadmap:** §4.1 remaining (mixed-flow BEM).

## Plain language

Mixed-flow already scores in the axial duct via CFD. Stage 1 adds the same kind of millisecond BEM gate the axial path has: treat the diagonal rotor as an approximate axial fan (same annulus / chord / stagger) so clearly dead designs can skip Docker. Ranking is coarse; the stamp says so.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Adapter → existing axial BEM | Small; reuses tip-loss / polars |
| **2** | Meridional diagonal BEM | Better physics; large |
| **3** | Area × tip-speed heuristic | Weak ranking |

## Goal

### 1. Adapter (`fansim/centrifugal/bem.py`)

```text
mixed_to_blade_params(params: MixedFlowParams) -> BladeParams
```

- `n_blades` from mixed
- `hub_radius = r_back_mm` (motor-end hub; mount-sized)
- `tip_radius = _loft_tip_radius_mm(params)` (built tip, not raw `r_tip_mm` if they differ)
- Three stations at r_frac 0 / 0.5 / 1 with constant `chord_mm`, `stagger_deg`, `thickness`, `max_camber`, `camber_pos`; lean/sweep/skew/le_* = 0
- `rpm` left default / caller-set

### 2. Screen helpers

```text
mixed_bem_screen_cfm(params, rpm, load_pa, tip_gap_mm) -> (q_free, q_op)
```

Calls `bem_screen_cfm(mixed_to_blade_params(params), ...)`.

### 3. `evaluate_mixed_flow`

- Add `bem_prescreen_cfm: float = 0.0`
- After tip-gap gate, before STL/CFD: if floor > 0, run `mixed_bem_screen_cfm` with `remaining` tip gap and `spec.rpm`; if op CFM &lt; floor → infeasible `bem-prescreen:…` (same wording style as axial)
- Stamp `raw["bem_adapter"] = "axial"` when the screen runs (or always when mixed evaluate stamps topology)

### 4. CLI

`scripts/evaluate_mixed_flow.py --bem-prescreen CFM_FLOOR` (default 0). No `★`.

### 5. Docs

- Spec accepted; roadmap §4.1: mixed-flow BEM stage 1 done; remaining volute / campaign / true meridional BEM.

## Honesty

- Adapter is an **axial** stand-in for a diagonal machine. Do not claim calibrated mixed-flow CFM.
- No stator recovery path for mixed-flow this cycle (evaluate still uses frame).

## Tests (no Docker)

- Adapter: hub/tip/chord/stagger match expectations on defaults.
- `pq_curve(adapter)` free CFM finite and in a wide band.
- Larger tip gap → lower or equal free CFM.
- `evaluate_mixed_flow` with high `bem_prescreen_cfm` returns infeasible without calling export (monkeypatch).
- CLI help mentions `--bem-prescreen`; no `★`.

## Non-goals

- Meridional element loop
- Cockpit Assess BEM switch
- NSGA `--archetype centrifugal`
- Recalibrating axial SLIP for mixed-flow
- Stator on mixed-flow BEM

## Success

With `--bem-prescreen FLOOR`, default mixed-flow can be rejected before CFD when the axial-adapter op CFM is below the floor; floor 0 matches today’s evaluate path.
