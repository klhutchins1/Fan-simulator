# RV-3 Module 3 Review: CFD Metrics, Flow Report, and Flow Verdicts

Date: 2026-11-25 · Branch: `cursor/rv3-cfd-metrics` · Plan: `docs/review/2026-11-24-review-plan.md`

Modules reviewed:
- `fansim/cfd/metrics.py` (237 lines -> 238 lines after fixes)
- `fansim/cfd/flow_report.py` (198 lines -> 208 lines after fixes)
- `fansim/cfd/flow_verdicts.py` (203 lines -> 205 lines after fixes)

Cross-checked against: `fansim/cfd/templates.py`, `fansim/cfd/openfoam_case.py`, `fansim/cfd/sanity.py`,
`fansim/cfd/spanwise.py`, `fansim/cfd/flow_report_case.py`, `fansim/physics/air.py`,
`fansim/acoustics/proxies.py`, `fansim/optimize/objectives.py`, `fansim/optimize/system_curve.py`,
`fansim/cror/evaluate.py`, and `fansim/audit/registry.yaml`.

---

## 1. Formula Re-Derivation and Findings Table

| file:line | formula / subject | source / standard | verdict | action |
|---|---|---|---|---|
| `metrics.py:13` | `CFM_PER_M3S = 2118.882` vs exact $\frac{60}{0.3048^3} = 2118.87997276\ldots$ | International Yard & Pound Agreement (1959); NIST SP 811 ($1\text{ ft} \equiv 0.3048\text{ m}$ exact) | **+0.96 ppm rounding error** (likely $1/0.000471947$); moves `physics_snapshot.json` at its `1e-6` tolerance | Filed `math` issue [#87](https://github.com/klhutchins1/Fan-simulator/issues/87) |
| `metrics.py:14` | `RHO_AIR = RHO_AMCA = 1.2` kg/m³ | ANSI/AMCA 210-16 §3.1; ISO 5801:2017 §3.1.1 (standard air $\rho_0 = 1.2\text{ kg/m}^3$) | **OK** (single-sourced from `fansim/physics/air.py`; moved to top imports) | Fixed import order (E402) in this PR |
| `metrics.py:55-57` | `_last_data_row` | Code hygiene | **Dead code** (zero callers across `fansim/`, `tests/`, `scripts/`) | Removed in this PR |
| `metrics.py:77-89` | `latest_pp_file` numeric time sort | QA-39 (OpenFOAM time dirs `"20"` vs `"100"`) | **OK** (`float(path.parent.name)` with `-inf` fallback) | Keep |
| `metrics.py:141-145` | `_flow_trajectory` line parsing `(float(parts[0]), float(parts[-1]))` | OpenFOAM `surfaceFieldValue.dat` (`time value`) | **BUG**: 1-column truncated line (`"18"`) passes without `IndexError` and injects iteration index as $Q = 18\text{ m}^3/\text{s}$ | **Fixed test-first** in this PR (`if len(parts) < 2: continue`) |
| `metrics.py:156-181` | `convergence()` / `oscillation_pct()` on `outletFlow` tail (25%, two-half mean shift $< 2\%$) | ASME V&V 20-2009; Roache (1998) iterative convergence on all QoIs | **MODELLING GAP**: (1) always `True` (`0%` drift) in velocity-driven `FIELD_U` P–Q sweeps because continuity pins `outletFlow`; (2) singular as $Q \to 0$ (shut-off); (3) ignores pressure/torque drift & phase-aliases limit cycles | Filed `math` issue [#88](https://github.com/klhutchins1/Fan-simulator/issues/88) |
| `metrics.py:184-215` | `parse_fan_metrics` `omega_rad_s` & `rho` inputs; `shaft_power = torque * omega_rad_s` | $P_{\text{shaft}} = |M_z|\,\omega$ ($\omega \ge 0$, $\rho > 0$); OpenFOAM `forces` uses `rhoInf` | **BUG** on invalid signs: `omega_rad_s < 0` (e.g. signed MRF $\omega$) silently yields $P_{\text{shaft}} < 0$ and $\eta = 0$; also custom `rho != RHO_AIR` rescales `p` but NOT `forces` (`rhoInf` baked in by OpenFOAM) | **Fixed test-first** validation (`omega_rad_s >= 0`, `rho > 0`, finite) in this PR; `rho`/`rhoInf` mismatch filed in [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `metrics.py:194-206` | `torque = abs(moment[3])` (+ `abs(moment_r[3])` for CROR); `thrust = force[3]` (+ `force_r[3]`) | OpenFOAM v2406 `forces` layout `time total(x,y,z) pressure(x,y,z) viscous(x,y,z)` with `rhoInf`; Audit #7 | **OK** for equal-speed CROR (`|\omega_1|=|\omega_2|`) when neither rotor windmills (checked by `sanity._check_power_sign`); equal-speed assumption undocumented | Documented; equal-speed precondition noted in [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `metrics.py:208, 221-222` | `flow = sum(phi)` on `+Z` outlet; `cfm = flow * CFM_PER_M3S` | OpenFOAM `fvc::flux` ($\phi_f = \mathbf{U}_f\cdot\mathbf{S}_f$, outward normal $+Z$ on `outlet`); AMCA 210 signed delivery | **OK** (signed flow preserved, never `abs()`) | Keep |
| `metrics.py:209-217, 118` | `static_rise_pa = (p_out - p_in) * rho`; `air_power = flow * static_rise_pa`; `efficiency = air_power / shaft_power`; `eta_total = None` | ANSI/AMCA 210-16 §3.2 Eq. 7.36; ISO 5801:2017 §3.1.24 ($P_s = p_{s2} - p_{t1}$, $P_t = p_{t2} - p_{t1}$); OpenFOAM `totalPressure(p0=0)` inlet BC | **DEFINITION MISMATCH**: in pressure-driven mode ($p_{k,\text{in}} = -\tfrac{1}{2}|U_{\text{in}}|^2$), `(p_out - p_in)*rho = p_back + 0.5*rho*U_in^2` ($p_{s2}-p_{s1}$, not AMCA $P_s = p_{s2}-p_{t1} = p_{\text{back}}$). Free delivery reads $+1.8\text{--}4.5\text{ Pa}$ & $\eta>0$; loaded $\eta$ inflated 15–25%; `objectives.py:562-565` mixes $p_{s2}-p_{s1}$ (free) with $p_{s2}-p_{t1}$ (load); `eta_total` always `None`; `flow<0` & `dp<0` gives `air_power>0` | Filed `math` issue [#86](https://github.com/klhutchins1/Fan-simulator/issues/86) (needs Kimball decision + `CFD_VERSION` bump) |
| `flow_report.py:87-118` | `slab_half_width`, `slab_centres`, `exit_slab_mask`, `inlet_slab_mask` | Audit `2026-10-17-push-row-planes.md` (v4 blade-relative slabs disjoint from `[LE, TE]`) | **OK** (slabs guaranteed outside `[LE, TE]` by `PLANE_GAP_FRAC * r_tip`; fallback to `z_fan ± 0.18 r_tip` stamped in `missing["planes"]`) | Keep; slab-constant duplication in `spanwise.py:42,384` filed in [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `flow_report.py:143` | `cylindrical_velocity` ($\hat{e}_\theta = (-y/r, x/r, 0)$, $U_z = u_z$) | Right-handed cylindrical coordinates $(r, \theta, z)$ | **OK** (exact) | Keep |
| `flow_report.py:152-153` | `mean_uz = _wmean(uz_e, we)`; `backflow = _wmean(uz_e < 0, we)`; `net_reversed = mean_uz < 0` | Volume-weighted slab average (area proxy) | **OK** within slab-volume approximation | Keep |
| `flow_report.py:154-157` | `swirl_frac = sum(w * Uth^2) / sum(w * (Uz^2 + Uth^2))` | Spatial kinetic-energy density ratio in $(z,\theta)$ plane vs kinetic-energy flux ratio (Cumpsty & Horlock 2006) | **MODELLING CHOICE**: volume-weighted (not mass-flux-weighted), omits $U_r^2$ (contrast `flow_report_viz.py:35`), counts $U_z < 0$ positively | Filed `math` issue [#89](https://github.com/klhutchins1/Fan-simulator/issues/89) |
| `flow_report.py:159-160` | `dead_lim = 0.10 * abs(mean_uz)`; `dead = _wmean(abs(uz_e) < dead_lim, we)` | Relative low-speed share | **BUG**: when `mean_uz == 0` (stagnant `U = 0` or balanced opposing flow), `dead_lim == 0` and `|uz| < 0` is all `False` -> silently returns `dead_frac = 0.0` with no `missing` entry | **Fixed test-first** in this PR (`nan` + `missing["dead_frac"]`) |
| `flow_report.py:164-187` | Zero-volume cells inside `tip_sel` or a radial band `se`/`si` | No-swallowed-failure rule (`missing` stamp) | **BUG**: `_wmean` returns `nan` when cells exist (`np.any` is True) with `sum(w) == 0`, without recording the reason in `missing` | **Fixed test-first** in this PR (stamp `missing` when non-finite) |
| `flow_report.py:173-186, 55-56` | `p0 = p + 0.5 * uz^2`; `band_dp0_pa` & `mean_dp0_pa = RHO_AMCA * (_wmean(p0_e) - _wmean(p0_in))` | Incompressible Bernoulli without swirl; Cumpsty & Horlock (2006); Dixon & Hall Ch. 1 & 6 | **MODELLING GAP**: (1) volume-weighted rather than mass-flux-weighted $\frac{\int p_0 U_z dA}{\int U_z dA}$; (2) `0.5 * uz^2 > 0` counts reversed flow ($U_z < 0$) as positive push; (3) comment claiming radial-equilibrium swirl tilt cancels in area mean is false for a wall-anchored pressure ($\Delta \bar{p}_A < 0$, confirmed empirically in `2026-10-17-push-row-planes.md`) | Filed `math` issue [#89](https://github.com/klhutchins1/Fan-simulator/issues/89) |
| `flow_report.py:189-193` | `noise_swl_db` via Proudman `P_A = alpha * rho * (Cmu * k * omega) * (sqrt(2k)/c0)^5` integrated over `|z-z_fan| <= 1.5 r_tip, r <= 1.2 r_tip`, $L_W = 10\log_{10}(W / 10^{-12})$ | Proudman (1952); Sarkar & Hussaini (1993) $\alpha = 0.1$; Menter (1994) $C_\mu = 0.09$; ISO 3740 $W_{\text{ref}} = 1\text{ pW}$ | **OK** dimensionally ($\text{W/m}^3 \cdot \text{m}^3 = \text{W} \to \text{dB}$); rotor box still uses `z_fan` not `blade_z` midpoint, and `proxies.py:34` does not clamp `omega < 0` undershoot (unjudged due to 36 dB mesh scatter) | Noted in `review` issue [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `flow_verdicts.py:15-34` | `CLOSE_*` (R0.3 $\max(\text{margin}, \lceil \sqrt{2}\cdot 2\sigma \rceil)$ on v4 Stock meshes) vs legacy `BACKFLOW_MARGIN`, `BAND_TOL`, `SWIRL_FACTOR`, `DEAD_MARGIN`, `TIP_FACTOR`, `HINT_MARGIN_DB` | Pre-registered audits `2026-10-17-push-row-planes.md` (R0.2), `2026-10-17-too-close-to-call-prereg.md` (R0.3), `2026-10-16-flow-noise-mesh-robust-prereg.md` (R0.4) | Active `CLOSE_*` and `BAR_TOL = 0.12` match pre-registrations; 4 legacy constants are dead and 2 (`BAND_TOL`, `HINT_MARGIN_DB`) are test-only | Filed in `review` issue [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `flow_verdicts.py:48-49` | `_bad(x)` checks only `math.isnan(x)` | Non-finite float hygiene | **BUG**: `±inf` slips past `_bad()` into `ok`/`warn` verdicts and `"inf %"` strings | **Fixed test-first** in this PR (`not math.isfinite(x)`) |
| `flow_verdicts.py:60-74` | `_direction(d, s)` missing `_bad(s.backflow_frac)` check | Parity with `_push`, `_spin`, `_dead` | **BUG**: `s.backflow_frac = nan` evaluates `abs(nan) <= CLOSE` as `False` and `nan < 0` as `False` -> emits false `warn` (`better=False`, `"Stock nan %"`) | **Fixed test-first** in this PR (returns `na`) |
| `flow_verdicts.py:77-88` | `_band_labels` uses `a > b * (1 + BAR_TOL)` / `a < b * (1 - BAR_TOL)` | Relative tolerance around signed reference $b$ | **BUG**: when $b < 0$ (e.g. hub swirl depression $b = -5\text{ Pa}$), $b(1+\text{BAR\_TOL}) = -5.6 < b$, so an identical band $a = b = -5$ is labelled `"stronger"`! | **Fixed test-first** in this PR (`b ± BAR_TOL * abs(b)`) |
| `flow_verdicts.py:130-148` | `_dead(d, s)` fallback `tip_rel = 0.0` when `s.tip_band_uz_ratio <= 0`; `better_tip` text | Edge-case & UX clarity | Minor edge case: `s.tip_band_uz_ratio <= 0` pretends tip matches Stock; `better_tip`-only `ok` text omits tips | Filed in `review` issue [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |
| `flow_verdicts.py:157-170` | `_noise(d, s)` checks `is None` rather than `_bad(...)` | Non-finite float hygiene | **BUG**: `noise_swl_db = nan` or `noise_hint_db = nan` passes `is not None` and prints `"nan"` or emits false `warn` if `NOISE_JUDGED=True` | **Fixed test-first** in this PR (uses `_bad(...)`) |
| `flow_verdicts.py:190-203` | `overall_line(rows, compared)` | Summary honesty | Minor edge cases: all-missing `na` rows read `"About the same as Stock on every check."`; `compared=False` ignores `bad` (`net_reversed`) in summary text | Filed in `review` issue [#90](https://github.com/klhutchins1/Fan-simulator/issues/90) |

---

## 2. Detailed Derivations (Key Topics)

### 2.1 OpenFOAM Incompressible Pressure & ISO 5801 / AMCA 210 Conventions
In OpenFOAM v2406 `simpleFoam` (`templates.py:278, 448`), the solved field `p` is kinematic pressure $p_k = p / \rho$ ($[\text{m}^2/\text{s}^2]$), while the `forces` functionObject (`templates.py:295-305`) multiplies integrated pressure and viscous stresses by `rhoInf = 1.2` before writing `force.dat` [N] and `moment.dat` [N·m].

For a pressure-driven case (`FIELD_P_PDRIVEN`, `templates.py:447-457`):
- Inlet patch (`-Z`, outward normal $-\hat{z}$): `totalPressure` with $p_{0,k} = 0 \implies p_{k,\text{in}} = -\frac{1}{2}|\mathbf{U}_{\text{in}}|^2$ on inflow ($\phi < 0$), and $p_{k,\text{in}} = 0$ on reversed outflow ($\phi \ge 0$).
- Outlet patch (`+Z`, outward normal $+\hat{z}$): `fixedValue` with $p_{k,\text{out}} = p_{\text{back}} / \rho$.

Comparing with **ANSI/AMCA 210-16 §3.2 (Eq. 7.36)** and **ISO 5801:2017 §3.1.24**:
- **Fan total pressure**: $P_t = p_{t2} - p_{t1} = (p_{s2} + p_{d2}) - p_{t1} = p_{\text{back}} + \frac{1}{2}\rho U_{\text{out}}^2$ (for $p_{t1} = 0$, matching `sanity.py:263`).
- **Fan static pressure**: $P_s = P_t - p_{d2} = p_{s2} - p_{t1} = p_{\text{back}}$ (zero at free delivery $p_{\text{back}} = 0$).
- **What `metrics.py:214` computes**: $\Delta p_s = (p_{k,\text{out}} - p_{k,\text{in}})\rho = p_{s2} - p_{s1} = p_{\text{back}} + \frac{1}{2}\rho |\mathbf{U}_{\text{in}}|^2$.

Hence `static_pressure_rise_pa` adds the inlet dynamic head to $p_{\text{back}}$, whereas `objectives.py:562-565` and `cror/evaluate.py:325-326` pass `load_pa` ($= p_{s2} - p_{t1}$) for the probe endpoint and `m_free.static_pressure_rise_pa` ($= p_{s2} - p_{s1}$) for the free endpoint. Tracked in [#86](https://github.com/klhutchins1/Fan-simulator/issues/86).

### 2.2 Area/Volume-Weighted vs Mass-Flux-Weighted Averaging
By **Cumpsty & Horlock (2006)** (*J. Turbomachinery* 128(1):120–129) and **Dixon & Hall** (Ch. 1):
- Static pressure across a nearly parallel plane is area-averaged ($\bar{p}_A = \frac{1}{A}\int p\,dA$), matching `inletP` / `outletP` (`operation areaAverage`).
- Total pressure (stagnation enthalpy) must be **mass-flow-weighted** ($\bar{p}_{0,m} = \frac{\int p_0 \rho U_z\,dA}{\int \rho U_z\,dA}$) so $Q\Delta\bar{p}_{0,m}$ equals mechanical power added.
- `flow_report.py:173-185` uses cell-volume weighting over a centre-selected slab $|z - z_0| \le h$ on $p_u = p + \frac{1}{2}U_z^2$, which gives reversed-flow cells ($U_z < 0$) positive weight and positive dynamic head $+\frac{1}{2}U_z^2 > 0$. Tracked in [#89](https://github.com/klhutchins1/Fan-simulator/issues/89).

### 2.3 Unit Conversions
- $\text{CFM\_PER\_M3S}$: exact NIST SP 811 value is $60 / 0.3048^3 = 2118.8799727596794\ldots$; current literal `2118.882` is $+0.96\text{ ppm}$ high ([#87](https://github.com/klhutchins1/Fan-simulator/issues/87)).
- $\text{Pa}$: $(p_{k,\text{out}} - p_{k,\text{in}}) \cdot \rho$ has units $(\text{m}^2/\text{s}^2)(\text{kg}/\text{m}^3) = \text{kg}/(\text{m}\cdot\text{s}^2) = \text{Pa}$. Exact.
- $\text{W}$: $P_{\text{shaft}} = |M_z|\,\omega$ has units $(\text{N}\cdot\text{m})(\text{rad}/\text{s}) = \text{W}$; $P_{\text{air}} = Q\,\Delta p$ has units $(\text{m}^3/\text{s})(\text{N}/\text{m}^2) = \text{W}$. Exact.

---

## 3. RV-3 Checklist Summary

| Checklist item | `metrics.py` | `flow_report.py` | `flow_verdicts.py` |
|---|---|---|---|
| Equations cited; units & signs consistent | Units consistent; ISO 5801 static-rise mismatch ([#86](https://github.com/klhutchins1/Fan-simulator/issues/86)), 1 ppm CFM ([#87](https://github.com/klhutchins1/Fan-simulator/issues/87)), `omega<0` fixed | Units consistent; mass-flux vs volume weighting ([#89](https://github.com/klhutchins1/Fan-simulator/issues/89)); `dead_frac` at `mean_uz==0` fixed | Thresholds trace to R0.2–R0.4 pre-regs; negative-band sign flip fixed |
| No swallowed failures | 1-col trajectory & negative `omega`/non-pos `rho` fixed; missing files raise | Zero-volume tip/band `missing` stamps fixed; empty exit raises `FlowReportUnavailable` | `nan` `s.backflow_frac`, `±inf`, and `nan` noise fixed -> `na` |
| Constants single-sourced | `RHO_AIR` from `air.py`; `CFM_PER_M3S` single source here | `RHO_AMCA` from `air.py`; `spanwise.py` duplicates slab constants ([#90](https://github.com/klhutchins1/Fan-simulator/issues/90)) | 4 dead legacy constants + 2 test-only constants ([#90](https://github.com/klhutchins1/Fan-simulator/issues/90)) |
| Numeric tests (not only bands/greps) | Direct numeric tests in `test_cfd.py`, `test_cror_power.py`, `test_convergence_rule.py`, `test_cfd_direction_contract.py` | Exact synthetic numeric tests in `test_flow_report.py` | Exact edge-value tests in `test_flow_verdicts.py` & `test_stock_flow_repeats.py` |
| Audit ledger coverage | 100% (`cfd.cfm_from_outlet_flow` + `FanMetrics` exempt) | 100% (`cfd.flow_report` + dataclasses exempt) | 100% (`cfd.flow_report` + `RowVerdict` exempt) |
| Max function length ($\le 150$ lines) | `parse_fan_metrics`: 58 lines (PASS) | `compute_metrics`: 74 lines (PASS) | `_noise`: 33 lines (PASS) |

---

## 4. Verification & Ledger Re-Prove

- Touched unit tests:
  - `.venv/bin/python -m pytest tests/test_convergence_rule.py tests/test_flow_report.py tests/test_flow_verdicts.py -q` -> **54 passed**
  - `.venv/bin/python -m pytest tests/audit/test_cfd_direction_contract.py tests/test_math_consistency.py -q` -> **14 passed**
- Audit ledger re-proved for `cfd.cfm_from_outlet_flow` and `cfd.flow_report` in `docs/validation/audits/ledger.json`:
  - `.venv/bin/python scripts/audit_status.py --strict` -> **33/33 PROVEN, 0 CHANGED, 0 AFFECTED, 0 NEW, 0 UNREGISTERED**.
