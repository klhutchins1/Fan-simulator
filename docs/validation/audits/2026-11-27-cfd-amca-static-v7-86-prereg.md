# Pre-registration: AMCA 210 / ISO 5801 Fan Static Pressure (`CFD_VERSION = 7`) (#86)

- **Date:** 2026-11-27
- **Issue:** #86 (`CFD static_pressure_rise_pa mixes ISO 5801/AMCA 210 static and inlet dynamic pressure; eta_total unpopulated`)
- **Review source:** `docs/review/2026-11-25-rv3-cfd-metrics.md` (and prior non-breaking partial fix `docs/validation/audits/2026-11-26-cfd-metrics-eta-86-prereg.md` landed in PR #146)
- **Units affected:** `cfd.cfm_from_outlet_flow` (downstream `fan.bem_prescreen` unaffected once re-proven)
- **RV-1 physics snapshot impact:** None (`tests/data/physics_snapshot.json` has no CFD case parsing)
- **Ruling:** Cursor (Kimball approved proceeding with `#86` `CFD_VERSION = 7` on 2026-11-27; bumps `CFD_VERSION` `6 -> 7` so pre-v7 duct static-to-static catalog scores are cleanly flagged stale by `cfd_is_stale()`).

## Problem Statement

Under **ANSI/AMCA 210-16 §3.2 (Eq. 7.36)** and **ISO 5801:2017 §3.1.24**, for a fan drawing from inlet (section 1) to outlet (section 2):

$$P_t = p_{t2} - p_{t1} = (p_{s2} + p_{d2}) - (p_{s1} + p_{d1}), \qquad P_s = P_t - p_{d2} = p_{s2} - p_{t1}.$$

In `CFD_VERSION = 6`, `fansim/cfd/metrics.py::parse_fan_metrics` computed:

$$\Delta p_s = (p_{k,\text{out}} - p_{k,\text{in}})\rho = p_{s2} - p_{s1}.$$

On OpenFOAM pressure-driven cases (`0/p` `inlet { type totalPressure; p0 uniform 0; }`, used by all axial, CROR, mixed-flow, and volute solves), OpenFOAM enforces $p_{k,\text{in}} = p_{0,\text{in}} - \tfrac{1}{2}|\mathbf{U}_{\text{in}}|^2$ on inflow, so $(p_{k,\text{out}} - p_{k,\text{in}})\rho = p_{\text{back}} + \tfrac{1}{2}\rho|\mathbf{U}_{\text{in}}|^2$ adds inlet dynamic head:

1. **Free delivery (`p_back = 0`)** reports $+\tfrac{1}{2}\rho|\mathbf{U}_{\text{in}}|^2 \approx +1.8\text{–}4.5\text{ Pa}$ and nonzero static efficiency instead of AMCA 210 $P_s = 0\text{ Pa}$, $\eta_s = 0$.
2. **Loaded point (`p_back = 8 Pa`)** inflates `static_pressure_rise_pa`, `air_power_w`, and `efficiency` by ~15–25 % relative to $P_s = p_{s2} - p_{t1}$.
3. **Mixed two-point fan-line endpoints:** `objectives.py`, `cror/evaluate.py`, `centrifugal/evaluate.py`, `volute/evaluate.py`, and `rederate.py` pass `p_free_pa = m_free.static_pressure_rise_pa * derate**2` ($p_{s2} - p_{s1}$) alongside `p_probe_pa = load_pa * derate**2` ($p_{s2} - p_{t1}$), mixing two different pressure definitions on one fan line and rejecting legacy `1 Pa` hoses.

## Pre-Registered Fix (`CFD_VERSION = 7`)

In `fansim/cfd/metrics.py`:

1. Bump `CFD_VERSION = 7` (flags all pre-v7 scores stale via `cfd_is_stale()`).
2. Inspect `0/p`'s `inlet` patch block via `_inlet_p_bc(case_dir) -> tuple[str | None, float]`:
   - **`totalPressure` inlet** (`type totalPressure; p0 uniform <p0>;`, default `p0 = 0.0`):
     - $p_{t1} = \rho p_{0,\text{in}}$, so:
       $$P_s = (p_{k,\text{out}} - p_{0,\text{in}})\rho, \qquad P_t = P_s + \tfrac{1}{2}\rho (Q / A_{\text{out}})^2.$$
   - **`zeroGradient` inlet** (`type zeroGradient;`) with known `inlet_area_m2` from `constant/case_meta.json`:
     - $p_{t1} = \rho p_{k,\text{in}} + \tfrac{1}{2}\rho (Q / A_{\text{in}})^2$, so:
       $$P_s = (p_{k,\text{out}} - p_{k,\text{in}})\rho - \tfrac{1}{2}\rho (Q / A_{\text{in}})^2, \qquad P_t = P_s + \tfrac{1}{2}\rho (Q / A_{\text{out}})^2.$$
   - **`zeroGradient` inlet without `inlet_area_m2`:**
     - Cannot compute $p_{d1}$; fall back to duct static-to-static $(p_{k,\text{out}} - p_{k,\text{in}})\rho$ and leave `eta_total = None`.
   - **No `0/p` file** (minimal synthetic fixtures without OpenFOAM boundary files):
     - Retain $(p_{k,\text{out}} - p_{k,\text{in}})\rho$ for `static_pressure_rise_pa` and `p_out * rho + 0.5 * rho * (Q / A_out)^2` for `eta_total` when `outlet_area_m2` is given.
3. Preserve the `#86` double-negative air-power guard (`air_power = flow * static_rise_pa if flow > 0.0 else -abs(flow * static_rise_pa)`) and `eta_total = (flow * P_t) / shaft_power` when `P_t` is known and `flow > 0.0` and `shaft_power > 1e-9`.
4. Update `docs/how-scores-are-computed.md` to note the `CFD_VERSION = 7` AMCA 210 convention (`0 Pa` free static, `8 Pa` probe static) alongside the archived v6 walkthrough example.

## Acceptance Criteria

All criteria must pass:

1. **Pressure-driven (`totalPressure`) free delivery (`p_out = 0, p0 = 0, p_in = -3.125`):** `static_pressure_rise_pa == 0.0`, `air_power_w == 0.0`, `efficiency == 0.0`, and `eta_total == Q * (0.5 * rho * (Q / A_out)^2) / P_shaft`.
2. **Pressure-driven (`totalPressure`) loaded point (`p_out = 8/rho, p0 = 0, p_in = -3.125`):** `static_pressure_rise_pa == 8.0`, `efficiency == Q * 8.0 / P_shaft`, `eta_total - efficiency == Q * (0.5 * rho * (Q / A_out)^2) / P_shaft` identically (`P_t == P_s + p_d2`), and `sanity._check_energy_total` agrees identically.
3. **Pressure-driven nonzero `p0` (`p0 = 2.0`):** `static_pressure_rise_pa == (p_out - 2.0) * rho` and `P_t == P_s + p_d2`.
4. **Velocity-driven (`zeroGradient`) with `inlet_area_m2` (both constant-area and contracting/expanding duct):** `static_pressure_rise_pa == (p_out - p_in) * rho - 0.5 * rho * (Q / A_in)^2` and `P_t == P_s + p_d2` identically; without `inlet_area_m2`, `eta_total is None`.
5. **Reversed flow (`Q < 0`):** `air_power_w <= 0.0`, `efficiency <= 0.0`, `eta_total is None` across both `totalPressure` and `zeroGradient`.
6. **Versioning & consistency:** `CFD_VERSION == 7`, `cfd_is_stale(6) is True`, `cfd_is_stale(7) is False`; two-point fan line accepts `1 Pa` hose on `totalPressure` free delivery (`p_free_pa == 0.0 < p_probe_pa`).
7. **Hygiene & ledger:** `ruff check`, `mypy`, `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`), zero RV-1 snapshot changes, and all CFD/sanity/convergence/ring-duct/evaluate tests pass.

## Results

- **Pre-registration commit (pushed before code):** `4dc0d97`
- **Verdict: PASS** (criteria 1–7 all met).
- `fansim/cfd/metrics.py`: bumped `CFD_VERSION = 7`; replaced `_inlet_is_zero_gradient_p` with `_inlet_p_bc(case_dir)` parsing both `totalPressure` (including nonzero `p0`) and `zeroGradient` inlet BCs; `parse_fan_metrics` computes AMCA 210 / ISO 5801 `P_s = p_s2 - p_t1` and `P_t = P_s + p_d2` identically across both BC types (leaving `eta_total = None` on `zeroGradient` without `inlet_area_m2`, and preserving fallback for synthetic cases without `0/p`).
- `docs/how-scores-are-computed.md`: documented the `CFD_VERSION = 7` AMCA 210 convention beside the archived v6 Stock walkthrough.
- Re-proved `cfd.cfm_from_outlet_flow` in `docs/validation/audits/ledger.json`; `scripts/audit_status.py --strict` -> `PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`.
- `ruff check` (critical + all changed files) and `mypy` (51 source files) passed; targeted CFD/metrics/convergence/audit tests passed with zero RV-1 snapshot drift.
