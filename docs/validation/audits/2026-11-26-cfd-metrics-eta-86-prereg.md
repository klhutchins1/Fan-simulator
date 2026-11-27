# Pre-registration: CFD Metrics Double-Negative Air Power & `eta_total` Alignment (#86)

- **Date:** 2026-11-26
- **Issue:** #86 (`RV-3: cfd/metrics.py — pressure rise drops inlet dynamic head; eta_total unpopulated; air_power double-negative`)
- **Review source:** `docs/review/2026-11-25-rv3-cfd-metrics.md`
- **Units affected:** `cfd.cfm_from_outlet_flow`, `cfd.sanity_checks`
- **Ruling:** Cursor (autonomous pre-registration under `AGENTS.md` Rule 1 — non-breaking bug fixes; `CFD_VERSION` stays at `6` for v0.1.0 compatibility).

## Problem Statement

1. **Double-negative `air_power`:** In `fansim/cfd/metrics.py`, `air_power = flow * static_rise_pa`. When a stalled/reversed fan produces `flow < 0` and `static_rise_pa < 0`, `air_power > 0` and `eta_static > 0` — reporting positive aerodynamic work and positive efficiency for a fan pumping backwards.
2. **Dead `eta_total` field & duplicated efficiency math:** `FanMetrics.eta_total` was always `None` when returned by `parse_fan_metrics()`, forcing `fansim/cfd/sanity.py:_check_energy_total` to re-implement total-pressure efficiency separately.
3. **Undocumented static-to-static convention (`CFD_VERSION = 6`):** `static_pressure_rise_pa = (p_out - p_in) * rho` measures duct static-to-static pressure rise rather than AMCA 210 fan static pressure `p_out - p_t_in` (which differs by the inlet dynamic head `0.5 * rho * (Q / A_in)^2` for pressure-driven `totalPressure` inlet cases where `p_in = p_t_in - 0.5 * u_in^2`).

## Pre-Registered Fix & v0.1.0 Compatibility Boundary

1. **Guard `air_power` sign:** Compute `air_power = flow * static_rise_pa if flow > 0.0 else -abs(flow * static_rise_pa)` so reversed flow can never yield positive air power or positive `eta_static`.
2. **Populate `FanMetrics.eta_total` (ISO 5801 / AMCA 210 total efficiency):**
   - Read `(inlet_area_m2, outlet_area_m2)` from `constant/case_meta.json` (with optional `outlet_area_m2` override on `parse_fan_metrics`).
   - For pressure-driven inlets (`totalPressure`, `p_total_in = 0`): `dp_total = p_out * rho + 0.5 * rho * (Q / A_out)^2`.
   - For velocity-driven inlets (`zeroGradient` on `0/p`): `dp_total = (p_out - p_in) * rho + 0.5 * rho * Q^2 * (A_out^-2 - A_in^-2)`.
   - Compute `eta_total = (flow * dp_total) / shaft_power` when `shaft_power > 0` and `flow > 0` (clamping reversed flow cleanly via `-abs(flow * dp_total)`).
3. **Unify `sanity.py:_check_energy_total`:** Consume `metrics.eta_total` when populated, retaining the existing fallback when `metrics.eta_total is None` (e.g. legacy callers constructing `FanMetrics` without `case_meta.json`).
4. **Keep `CFD_VERSION = 6` and `static_pressure_rise_pa` unchanged for v0.1.0:** `docs/how-scores-are-computed.md`, `tests/test_convergence_rule.py` (`assert CFD_VERSION == 6`), and the validated v6 CFD catalog rely on the v6 definition. Document the duct static-to-static convention explicitly in `fansim/cfd/metrics.py` and defer any `p_out - p_t_in` (`CFD_VERSION = 7`) schema break to v0.2 with Kimball's sign-off.

## Acceptance Criteria

- Reversed flow (`flow < 0`, `static_rise_pa < 0`) yields `air_power_w < 0` and `eta_static < 0`.
- Pressure-driven (`totalPressure`) and velocity-driven (`zeroGradient`) cases with `constant/case_meta.json` populate `FanMetrics.eta_total` to the exact ISO 5801 total-to-total formula, and `run_sanity(case, metrics=m)` reports the identical value on `energy_total`.
- Existing CFD, sanity, convergence (`CFD_VERSION == 6`), fan curve, CROR, direction contract, and physics snapshot tests pass unchanged.
- `ruff check` on all touched files, `mypy`, and `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0`) pass.
