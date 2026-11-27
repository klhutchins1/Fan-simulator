# Pre-registration: `fan_bem.py` `axial_force` Mean-Triangle & Energy-Bound Fix (#94)

- **Date:** 2026-11-27
- **Issue:** #94 (`[MATH MED] fan_bem axial_force mixes W1 thrust with Wm torque (causes η > 1 clamp and dp_static > dp_total)`)
- **Review source:** `docs/review/2026-11-25-rv3-fan-bem.md` (Finding F9)
- **Units affected:** `fan.bem_prescreen`
- **Snapshot case affected:** `fan_bem.stock_v3_axial_force` only (`fan_bem.stock_v3_euler` and `fan_bem.stock_v3_stator` must stay bit-for-bit identical)
- **Ruling:** Cursor (autonomous pre-registration under `AGENTS.md` Rule 1 — physics consistency fix on the opt-in exploit-guard branch; constants `AX_SLIP = 0.65`, `AX_K_FRICTION = 1.9`, `CD_90 = 1.8`, `K_TIP_LEAK = 9.0` are **not** re-tuned).

## Problem Statement

In `fansim/fan_bem.py::operating_point(..., pressure_model="axial_force")`:

1. **Inconsistent velocity triangles:** Swirl `vth` and shaft power `power` are solved on the mean relative triangle $(W_m, \phi_m)$ with $v_{\theta,m} = \tfrac{1}{2}v_\theta$, whereas axial blade force $f_x$ is evaluated on the inlet triangle $(W_1, \phi_1)$ with zero swirl. On high-solidity blades (`E_rand1396`, 11 blades, chords 48–58 mm), $W_1 > W_m$ and $\alpha_1 > \alpha_m$ inflate axial thrust past shaft work ($\eta = 115\%$), forcing an ad-hoc clamp `dp_static = min(dp_static, power / flow_m3s)`.
2. **Thermodynamically inconsistent `dp_total`:** In `"axial_force"` mode, `dp_total` is still computed from the unrelated `"euler"` branch (`SLIP = 0.71`), yielding `dp_static_pa > dp_total_pa` on **15 of 22 sweep points** of `E_rand1396`, violating AMCA 210-25 §4.1.25 / ISO 5801:2017 §3.34 ($\Delta p_{\text{static}} \le \Delta p_{\text{total}}$).
3. **Shaft power divergence under swirl clamps:** `power += dm * U * vth` diverges from true blade torque power $U f_\theta \, dr$ whenever `vth` hits the `0.95 * U` clamp or when $V_x < 0.05\text{ m/s}$.

## Pre-Registered Fix (Fixed Before Data; Zero Re-Tuning)

For `pressure_model == "axial_force"` only (default `"euler"` path untouched):

1. After the per-element swirl fixed-point iteration finishes at `vth`, re-evaluate $(\phi_m, W_m, C_l, C_d, f_\theta, f_x)$ once at the final converged `vth` on the **same mean relative velocity triangle** $(W_m, \phi_m)$:
   - $f_\theta = \tfrac{1}{2}\rho W_m^2 c B (C_l \sin\phi_m + C_d \cos\phi_m)$
   - $f_x = \tfrac{1}{2}\rho W_m^2 c B (C_l \cos\phi_m - C_d \sin\phi_m)$
2. Accumulate per-element blade-torque shaft power `power_ax += max(U * f_theta * dr, 0.0)` (equals $d\dot{m}\,U\,v_\theta$ identically whenever $0 \le f_\theta / \text{denom} \le 0.95\,U$ and $V_x \ge 0.05\text{ m/s}$, and stays consistent with blade torque when clamped).
3. Accumulate axial force `ax_force += k_ax * f_x * dr` and exit swirl KE `swirl_ke_ax += 0.5 * rho * (k_ax * vth)**2 * dm` with $k_{\text{ax}} = \text{AX\_SLIP} \cdot \text{leak} \in [0, 1]$ (constants `AX_SLIP = 0.65`, `AX_K_FRICTION = 1.9`, `CD_90 = 1.8`, `K_TIP_LEAK = 9.0` unchanged).
4. Compute:
   - `dp_static = (ax_force / area if B > 0 and area > 0 else 0.0) - AX_K_FRICTION * 0.5 * rho * Vx * Vx`
   - `dp_total = dp_static + swirl_ke_ax / mass`
5. Remove the ad-hoc energy clamp `dp_static = min(dp_static, power / flow_m3s)`. By **Wallis (1983) §4.3 Eq. 4.17** and **Dixon & Hall (2014) Ch. 3 Eq. 3.17**, on every element $k_i f_{x,i} V_x \, dr_i + \tfrac{1}{2} k_i^2 d\dot{m}_i v_{\theta,i}^2 \le \max(U_i f_{\theta,i} \, dr_i, 0)$, so $\Delta p_{\text{static}} \le \Delta p_{\text{total}}$, $Q \Delta p_{\text{total}} \le P_{\text{shaft}}$, and $0 \le \eta_s \le 1$ hold identically by algebra.

## Acceptance Criteria (Fixed Before Running Data)

All four criteria must pass. If any fails, record **FAIL** honestly in the Results section below and do **not** re-tune `AX_SLIP` or `AX_K_FRICTION` to force a pass.

- **A1 — Thermodynamic & momentum invariants (zero clamps):** Across `Stock v3` (`config/problems/a12x25_reference.yaml`), `Stock v2` (`config/problems/a12x25_reference_planar.yaml`), `Stock v1` (`config/problems/a12x25_reference_v1.yaml`), `lt120` (`docs/qa/benchmarks/lt120/fansim_params.json`), and `E_rand1396` (11-blade QA r4 design) at 2000 rpm:
  - `dp_static_pa <= dp_total_pa + 1e-12` at 100% of sweep points (0 violations; previously 15/22 violations on `E_rand1396`),
  - `flow_m3s * dp_total_pa <= power_w * (1.0 + 1e-12)` and `0.0 <= efficiency <= 1.0` at 100% of sweep points with the ad-hoc clamp removed,
  - `E_rand1396` `peak_efficiency < 1.0` (strictly below unity, not pegged at the old energy clamp).
- **A2 — QA-4 exploit-guard contract (`fansim/optimize/system_curve.py::bem_exploit_reason`):**
  - Paddles (`stagger = 89°`) and reversed blades (`stagger = -45°, -60°`) on Stock v3 are refused by `bem_exploit_reason(...)` (non-empty string) and satisfy `free_status == "no_rise"` OR (`free_delivery_cfm < 0.5 * stock.free_delivery_cfm` and `peak_efficiency < 0.5 * stock.peak_efficiency`).
  - Reversed `-45°` at `0.005 m³/s` gives `dp_static_pa < 0.0`.
  - Real fans (`Stock v3`, `Stock v2`, `Stock v1`, `lt120`, `E_rand1396`) all pass `bem_exploit_reason(...) == ""` (zero false refusals; `peak_efficiency >= EXPLOIT_MIN_PEAK_EFF = 0.05`).
- **A3 — Un-retuned physical plausibility & ordering:**
  - `Stock v3` has `free_status == "crossed"`, free delivery within ±25% of published 60.1 CFM (`[45.1, 75.1] CFM`), and shut-off within ±35% of published 22.9 Pa (`[14.9, 30.9] Pa`). (Also record exact comparison against the old fitted QA rule (a) `±10% / ±25%` transparently without re-tuning.)
  - `Stock v1` free delivery > `Stock v2` free delivery (matching CFD 77.4 > 56.5 CFM).
  - `lt120` free delivery > `Stock v3` free delivery (matching published 84+ > 60.1 CFM).
- **A4 — Default `"euler"` bit-exact preservation & audit ledger:**
  - `fan_bem.stock_v3_euler`, `fan_bem.stock_v3_stator`, and `test_default_pressure_model_is_euler_and_unchanged` remain bit-for-bit identical.
  - `tests/data/physics_snapshot.json` updated via `scripts/physics_snapshot.py --write --reason docs/validation/audits/2026-11-27-fan-bem-axial-force-94-prereg.md` changes only `fan_bem.stock_v3_axial_force`.
  - `fan.bem_prescreen` re-proved in `docs/validation/audits/ledger.json`; `ruff`, `mypy`, and `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0`) pass.

## Results

*(To be filled in after the pre-registered run is executed.)*
