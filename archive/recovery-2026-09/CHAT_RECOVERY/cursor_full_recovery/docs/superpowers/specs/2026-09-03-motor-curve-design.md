# Linear motor torque–speed (stage 1)

**Date:** 2026-09-03  
**Status:** accepted  
**Approach:** Replace the cube-root power derate with a testable linear T–ω motor intersected with fan torque ∝ RPM². No-load RPM is 1.15× rated so the motor still has torque at `spec.rpm`. Calibrate stall torque so available shaft power at rated speed equals `max_shaft_power_w_leeway`. Do not add RPM to the NSGA search.  
**Roadmap:** §2.5 stage 1. Affinity Q∝n, P∝n² after the RPM is known stays.

## Plain language

Today, if CFD shaft power at rated RPM exceeds the budget, we set `derate = (budget/P)^(1/3)`. That is a constant-power motor, not a torque–speed curve. A PC fan motor is closer to a linear T–ω line: stall torque at 0 RPM, zero torque at no-load RPM. Stage 1 intersects that line with the fan’s quadratic torque so a slightly over-torque blade slows a little instead of taking the cube-root shortcut.

## Problem

```text
derate = min(1, (budget / shaft_rated) ** (1/3))
actual_rpm = spec.rpm * derate
```

`shaft_rated` is max(free, load) CFD power. Cube-root affinity assumes the motor can deliver `budget` at every RPM.

## Goal

1. **`fansim/optimize/motor_curve.py`** (no Docker):

```text
NL_OVER_RATED = 1.15

stall_torque_nm(spec) -> float
  T_stall = P_budget / (ω_rated * (1 - 1/NL_OVER_RATED))
  so T_motor(rated) * ω_rated = P_budget

motor_torque_nm(rpm, spec) -> float
  0 if rpm >= no-load; else T_stall * (1 - rpm/rpm_nl)

motor_operating_rpm(torque_nm_at_rated, spec) -> float
  if T_cfd <= T_motor(rated) → spec.rpm
  else solve T_motor(n) = T_cfd * (n/n_rated)² for n in (0, n_rated)
  (quadratic in n/n_rated; take the physical root)
```

Use `max_shaft_power_w_leeway` as `P_budget`.

2. **`evaluate_candidate`** — `actual_rpm = motor_operating_rpm(max(free, load) torque, spec)`, then `derate = actual_rpm / spec.rpm`. Keep affinity on CFM / probe Pa. Do not change objective names.

## Tests (no Docker)

- At `T_cfd = T_motor(rated)` → rated RPM.
- Below that torque → rated RPM.
- 2× rated available torque → RPM in `(0.5 * rated, rated)` and `motor_torque_nm(n) ≈ T_cfd * (n/rated)²`.
- `stall_torque_nm` such that `motor_torque_nm(rated)*ω_rated == budget`.

## Non-goals

- RPM as an NSGA decision variable
- Kv / current-limit / PWM tables
- Cockpit motor editor
- Changing `FanSpec.rpm`
- Prop motors
