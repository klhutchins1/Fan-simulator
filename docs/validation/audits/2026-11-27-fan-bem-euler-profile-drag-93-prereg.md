# Pre-registration: `fan_bem.py` Viscous Euler Profile-Drag & Deviation Consistency Fix (#93)

- **Date:** 2026-11-27
- **Issue:** #93 (`[MATH HIGH] fan_bem Euler model omits airfoil profile-drag loss and misapplies SLIP as hydraulic efficiency`)
- **Review source:** `docs/review/2026-11-25-rv3-fan-bem.md` (Findings F1, F2)
- **Units affected:** `fan.bem_prescreen`
- **Snapshot cases affected:** `fan_bem.stock_v3_euler` and `fan_bem.stock_v3_stator` only (`fan_bem.stock_v3_axial_force` and all other 14 RV-1 cases must stay bit-for-bit identical)
- **Ruling:** Cursor (autonomous pre-registration under `AGENTS.md` Rule 1 — first-principles viscous Euler + angular-momentum consistency fix; existing constants `SLIP = 0.71`, `K_FRICTION = 1.7`, `K_TIP_LEAK = 9.0`, `CD_90 = 1.8` are **not** re-tuned).

## Problem Statement

In `fansim/fan_bem.py::operating_point(..., pressure_model="euler")`:

1. **Omitted airfoil profile-drag loss:** Per **Wallis (1983)** (*Axial Flow Fans and Ducts*, §4.3 Eq. 4.17) and **Dixon & Hall (2014)** (*Fluid Mechanics and Thermodynamics of Turbomachinery*, 7th ed., Ch. 3 Eq. 3.17), the viscous blade-element total-pressure rise of an annular element with solidity $\sigma = B c / (2\pi r)$ and mean relative flow angle $\phi_m$ is:
   $$\Delta p_0 = \rho U v_\theta - \Delta p_{0,\text{profile}}, \qquad \Delta p_{0,\text{profile}} = \frac{D}{2\pi r \sin\phi_m} = \frac{1}{2}\rho W_m^2 \frac{\sigma C_d}{\sin\phi_m}.$$
   The current `"euler"` mode omits $\Delta p_{0,\text{profile}}$ while retaining $+C_d \cos\phi_m$ in $f_\theta$, so higher blade drag *increases* predicted swirl, total pressure, static pressure, and airflow (enabling the QA-4 paddle $\beta = 89^\circ$ and reversed-blade exploits).
2. **Inconsistent `SLIP` application (angular-momentum violation):** `SLIP = 0.71` and outer-span tip-leakage factor `leak` are currently applied post-hoc to `vth_eff = SLIP * leak * vth` in `dp0_num` and `swirl_ke`, while shaft power `power += dm * U * vth` uses un-slipped `vth` and the swirl iteration uses isolated (un-slipped) lift $C_l$. By angular-momentum conservation, cascade lift unloading / flow deviation reduces blade lift, induced swirl $v_\theta$, and shaft torque $U f_\theta \, dr$ together, rather than acting as a constant post-hoc hydraulic efficiency $\eta_h = 0.71$.

## Pre-Registered Formulation (Fixed Before Data; Zero Re-Tuning)

For `pressure_model == "euler"` only (`"axial_force"` path left untouched; constants `SLIP = 0.71`, `K_FRICTION = 1.7`, `K_TIP_LEAK = 9.0`, `CD_90 = 1.8` **not** re-tuned):

1. **Polar:** Use `_cl_cd_post_stall` (identical to `_cl_cd` inside the attached stall band $[-\alpha_s, +\alpha_s]$, continuous Viterna–Corrigan continuation to $C_{D,90} = 1.8$ past stall so high-incidence paddles and reversed blades experience realistic profile drag instead of clamped $18^\circ$ lift).
2. **Cascade lift unloading + tip-leakage factor inside the momentum balance:** Compute `leak` (existing outer-span formula for `rf > 0.65`) before the element swirl loop, and apply `k_lift = SLIP * leak` to blade lift only inside the iteration (`cl_eff = k_lift * cl`), leaving profile drag `cd` un-reduced:
   $$f_\theta = \tfrac{1}{2}\rho W_m^2 c B (C_{l,\text{eff}} \sin\phi_m + C_d \cos\phi_m)$$
   solving $\rho \max(V_x, 0.05) (2\pi r) v_\theta = f_\theta$ with $v_\theta \in [0, 0.95 U]$ using the existing damped fixed-point loop (`N_ITER_MAX = 50`, tolerance `1e-3`).
3. **Consistent post-convergence triangle & viscous Wallis Eq. 4.17 total pressure rise:** At the converged `vth`, re-evaluate $(\phi_m, W_m, C_l, C_d, C_{l,\text{eff}}, f_\theta, f_x)$ once on the same mean relative velocity triangle:
   - $f_x = \tfrac{1}{2}\rho W_m^2 c B (C_{l,\text{eff}} \cos\phi_m - C_d \sin\phi_m)$
   - $\Delta p_{s,\text{elem}} = \dfrac{f_x}{2\pi r}$
   - $\Delta p_{0,\text{elem}} = \Delta p_{s,\text{elem}} + \tfrac{1}{2}\rho v_\theta^2$
   - **Algebraic identity:** Whenever $0 < v_\theta < 0.95 U$ and $V_x \ge 0.05\text{ m/s}$, $\rho V_x v_\theta = f_\theta / (2\pi r)$ implies $\Delta p_{0,\text{elem}} = \rho U v_\theta - \tfrac{1}{2}\rho W_m^2 \sigma C_d / \sin\phi_m$ identically (Wallis §4.3 Eq. 4.17), while remaining smooth and free of the $1/\sin\phi_m \to \infty$ singularity if $v_\theta$ hits the $0.95 U$ clamp near shut-off.
4. **Consistent shaft power (angular-momentum conservation) & annulus integration:**
   - `dp0_num += dp0_elem * dm`
   - `swirl_ke += 0.5 * rho * vth * vth * dm`
   - `power += max(U * f_theta * dr, 0.0)` (equals $d\dot{m}\,U\,v_\theta$ identically whenever unclamped)
   - `dp_total = dp0_num / mass`
   - `swirl_loss = 0.0 if stator else (swirl_ke / mass)`
   - `dp_static = dp_total - swirl_loss - K_FRICTION * 0.5 * rho * Vx * Vx`
   - No ad-hoc energy clamp. By algebra, $U f_\theta \, dr - (V_x f_x \, dr + \tfrac{1}{2} d\dot{m} v_\theta^2) = D W_m \, dr + \tfrac{1}{2} v_\theta (f_\theta \, dr - d\dot{m} v_\theta) \ge D W_m \, dr \ge 0$ for every element with $v_\theta \le f_\theta / (\rho V_x 2\pi r)$.

## Acceptance Criteria (Fixed Before Running Data)

All criteria E1–E3 must pass. If any fails, record **FAIL** honestly in the Results section below, leave `fansim/fan_bem.py` unchanged, and do **not** re-tune `SLIP`, `K_FRICTION`, or `K_TIP_LEAK`.

- **E1 — Exact viscous Euler & momentum invariants (zero clamps):**
  - Across `Stock v3` (`config/problems/a12x25_reference.yaml`), `Stock v2` (`config/problems/a12x25_reference_planar.yaml`), `Stock v1` (`config/problems/a12x25_reference_v1.yaml`), `lt120` (`docs/qa/benchmarks/lt120/fansim_params.json`), and `E_rand1396` (11-blade QA r4 design) at 1000 / 2000 / 3500 rpm, both `stator=False` and `stator=True`:
    - `dp_static_pa <= dp_total_pa + 1e-12` at 100% of sweep points,
    - `flow_m3s * dp_total_pa <= power_w * (1.0 + 1e-12)` and `0.0 <= efficiency <= 1.0` at 100% of sweep points,
    - `pq_curve` converges (`converged is True`) up to free delivery on Stock v1/v2/v3.
  - On any unclamped element ($0 < v_\theta < 0.95 U$, $V_x \ge 0.05$), $\Delta p_{0,\text{elem}}$ matches $\rho U v_\theta - \tfrac{1}{2}\rho W_m^2 \sigma C_d / \sin\phi_m$ to relative error $< 10^{-10}$.
  - Drag sign check: doubling $C_d$ at a positive-rise Stock v3 operating point strictly reduces `dp_static_pa` (never increases it).
- **E2 — Audit #4 & 16-design CFD corpus validation:**
  - **(a) Stock v2 free-air & P-Q slope (Audit #4 criterion a):** `BEM(Stock v2)` free-air CFM within **±25%** of CFD `56.5 CFM` (`[42.375, 70.625] CFM`), and flow order `Q(0 Pa) > Q(5 Pa) > Q(10 Pa)`.
  - **(b) Audit #4 ranking (criterion b, `n = 7`):** Over `{Stock v1, Stock v2, t9000, t9005, t9006, t9008, t9012}` against `docs/validation/audits/bem_vs_cfd_audit4.json` `cfd_cfm`, Spearman **$\rho \ge 0.60$**.
  - **(b2) Full 16-design CFD corpus ranking (`handoff/2026-10-09_to-qa-2/cfd_designs.csv`):** Over all 16 full-Assess CFD designs (`cfd_free_cfm`), Spearman **$\rho \ge 0.75$** (also report legacy Euler $\rho$ side-by-side).
  - **(c) Stock v1 vs v2 ordering (Audit #4 criterion c):** `BEM(Stock v1) > BEM(Stock v2)` (matching CFD `77.4 > 56.5 CFM`).
  - **(d) Published benchmark sanity:** `BEM(lt120) > BEM(Stock v3)` (matching published `84+ > 60.1 CFM`), `Stock v3` `free_status == "crossed"` with free delivery within **±25%** of published `60.1 CFM` (`[45.075, 75.125] CFM`), and `Stock v3` shut-off within **±50%** of published `22.9 Pa` (`[11.45, 34.35] Pa`).
- **E3 — QA-4 anti-exploit behavior in `"euler"` mode:**
  - Stock v3 paddle (`stagger = 89°` at all stations): `free_delivery_cfm < 0.25 * stock_v3.free_delivery_cfm` AND `peak_efficiency < 0.05`.
  - Stock v3 reversed blades (`stagger = -45°`, `-60°`): `free_status == "no_rise"` (`free_delivery_cfm == 0.0`) and `dp_static_pa < 0.0` at `0.005 m³/s`.
- **E4 — Snapshot & audit ledger (if E1–E3 PASS):**
  - `tests/data/physics_snapshot.json` updated via `scripts/physics_snapshot.py --write --reason docs/validation/audits/2026-11-27-fan-bem-euler-profile-drag-93-prereg.md`, changing only `fan_bem.stock_v3_euler` and `fan_bem.stock_v3_stator` (`fan_bem.stock_v3_axial_force` and all other cases bit-for-bit identical).
  - `fan.bem_prescreen` re-proved in `docs/validation/audits/ledger.json`; `ruff`, `mypy`, and `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0`) pass.

## Results

*Pending pre-registration commit and push before running data.*
