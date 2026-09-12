# BEM stator swirl-recovery credit (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** When BEM is told `stator=True`, recover a fixed fraction **η = 0.55** of rotor swirl dynamic head into static pressure. Wire the flag through `pq_curve` / `bem_screen_cfm` / `--bem-prescreen` so it matches CFD `--stator`. Not stagger-aware, not 100% recovery, not vane-count blockage.  
**Roadmap:** §2.2 remaining (BEM Euler credit).

## Plain language

Today the fan BEM assumes all rotor swirl energy is dumped (no outlet guide vanes). That under-ranks `--stator` designs at the cheap BEM gate even when CFD would see more static pressure. Stage 1 gives a fixed, conservative recovery fraction so BEM and CFD agree on whether OGVs are “on,” without pretending we have a calibrated cascade model.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **1 (chosen)** | Fixed η = 0.55 of swirl KE → static when `stator=True` | Simple; honest; enough for prescreen |
| **2** | Stagger-matched recovery | Needs exit-angle model; deferred |
| **3** | Ideal 100% recovery | Over-screens weak designs |

## Goal

### 1. `fansim/fan_bem.py`

```text
STATOR_SWIRL_RECOVERY = 0.55   # fraction of swirl_ke recovered into dp_static

operating_point(..., tip_gap_mm=..., stator: bool = False) -> FanPoint
pq_curve(..., tip_gap_mm=..., stator: bool = False) -> FanCurve
```

When `stator` is False (default):

```text
dp_static = dp_total - swirl_ke/mass - K_FRICTION * 0.5 * rho * Vx²
```

When `stator` is True:

```text
dp_static = dp_total - (1 - STATOR_SWIRL_RECOVERY) * swirl_ke/mass
            - K_FRICTION * 0.5 * rho * Vx²
```

`dp_total`, power, and tip-loss / shroud logic unchanged. Document that η is a stage-1 constant, not calibrated to CFD.

### 2. Screen wiring

- `bem_screen_cfm(params, rpm, load_pa, tip_gap_mm, *, stator=False)` → pass into `pq_curve`
- `bem_load_cfm` same kwarg
- `evaluate_candidate`: when calling `bem_screen_cfm` under `--bem-prescreen`, pass `stator=stator` (the same flag used for STL export)

### 3. Docs

- Spec accepted; roadmap §2.2: BEM Euler credit stage 1 done; remaining = frame+stator stack / stagger-aware η later.

## Honesty

- η = 0.55 is a **placeholder** mid-cascade recovery, not AMCA-validated.
- Searched stagger / `n_extra` do not change BEM this cycle.
- Frame studies must keep `stator=False` so credit is not applied to four-bar blockage.

## Tests (no CFD)

- Same `BladeParams` + flow: `operating_point(..., stator=True).dp_static_pa` > `stator=False`.
- Free-delivery CFM from `pq_curve` is higher (or equal only if already zero) with stator on.
- `stator=False` matches today’s numbers within tight tolerance on a fixed fixture (or recovery=0 path).
- `bem_screen_cfm(..., stator=True)` returns higher op CFM than False on a loaded hose when the curve has margin.
- No `★`.

## Non-goals

- Stagger- or incidence-dependent recovery
- Stator vane drag / solidity knockdown
- Recalibrating SLIP or tip-loss
- Changing CFD
- Catalog backfill

## Success

With `--stator` and `--bem-prescreen`, the BEM gate uses swirl recovery; without `--stator`, BEM matches today’s no-stator law.
