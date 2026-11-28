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

- **Pre-registration commit (pushed before data):** `4a39d05`
- **Verdict: FAIL (on E2(d) Stock v3 shut-off only).** Per `AGENTS.md` Rule 1, `fansim/fan_bem.py` was **not** modified and constants (`SLIP`, `K_FRICTION`, `K_TIP_LEAK`) were **not** re-tuned.

### Measured table — benchmarks & exploits (2000 rpm, `stator=False`, un-retuned viscous Euler)

| Case | Free CFM | Status | Shut-off Pa | Peak $\eta$ | Violations (`dp`, `en`, `eta`) | Converged |
|---|---:|---|---:|---:|---|---|
| Stock v3 (`a12x25_reference.yaml`) | 57.78 | `crossed` | 6.24 | 39.84 % | (0, 0, 0) | True |
| Stock v2 (`a12x25_reference_planar.yaml`) | 55.43 | `crossed` | 5.19 | 42.69 % | (0, 0, 0) | True |
| Stock v1 (`a12x25_reference_v1.yaml`) | 56.16 | `crossed` | 4.74 | 14.87 % | (0, 0, 0) | True |
| `lt120` | 89.58 | `crossed` | 8.06 | 19.65 % | (0, 0, 0) | True |
| `E_rand1396` (11-blade QA r4) | 71.23 | `crossed` | 17.55 | 46.95 % | (0, 0, 0) | True |
| Stock v3 paddle (`stagger = 89°`) | 2.32 | `crossed` | — | 0.00 % | (0, 0, 0) | — |
| Stock v3 reversed (`stagger = -45°`) | 0.00 | `no_rise` | — | 0.00 % | (0, 0, 0) | — |
| Stock v3 reversed (`stagger = -60°`) | 0.00 | `no_rise` | — | 0.00 % | (0, 0, 0) | — |

- Drag monotonicity on Stock v3 at $Q = 0.015\text{ m}^3/\text{s}$: $1\times C_d \to \Delta p_s = 11.700\text{ Pa}$; $2\times C_d \to \Delta p_s = 9.722\text{ Pa}$ ($\Delta = -1.978\text{ Pa}$, strictly decreasing).
- Reversed blades at $Q = 0.005\text{ m}^3/\text{s}$: `-45°` gives `-9.002 Pa`, `-60°` gives `-7.709 Pa`.
- Stock v2 loaded branch vs complete-setup CFD (`56.5 / 49.8 / 40.2 CFM` at `0 / 5 / 10 Pa`): viscous Euler `55.43 / 48.96 / 40.25 CFM` (`-1.9 % / -1.7 % / +0.1 %`; legacy Euler was `58.0 / 52.6 / 46.4 CFM`).

### Measured table — 16-design full-Assess CFD corpus (`handoff/2026-10-09_to-qa-2/cfd_designs.csv`)

| Design | CFD free CFM | Viscous Euler CFM | Legacy Euler CFM | `axial_force` CFM |
|---|---:|---:|---:|---:|
| `stock` | 54.79 | 57.78 | 60.42 | 63.06 |
| `stock_thin` | 58.10 | 55.43 | 58.18 | 59.84 |
| `t9000` | 54.58 | 54.77 | 57.65 | 59.49 |
| `t9002` | 59.84 | 52.75 | 55.51 | 56.46 |
| `t9003` | 67.09 | 60.13 | 61.97 | 65.82 |
| `t9005` | 74.02 | 60.56 | 62.43 | 66.26 |
| `t9006` | 55.06 | 58.55 | 60.67 | 63.68 |
| `t9008` | 57.57 | 59.05 | 61.14 | 64.45 |
| `t9012` | 23.94 | 33.13 | 39.12 | 36.48 |
| `t9015` | 57.65 | 54.39 | 57.54 | 59.07 |
| `t9016` | 82.71 | 67.35 | 70.11 | 71.56 |
| `bem_9501` | 61.51 | 60.80 | 63.22 | 67.49 |
| `bem_9502` | 69.40 | 61.67 | 64.11 | 67.34 |
| `bem_9503` | 67.81 | 60.86 | 63.02 | 66.69 |
| `bem_9504` | 67.65 | 61.44 | 63.40 | 67.91 |
| `bem_9505` | 69.90 | 62.47 | 64.30 | 68.51 |
| **Spearman $\rho$ (`n = 16`)** | — | **0.8294** | 0.8206 | 0.8029 |
| **Audit #4 Spearman $\rho$ (`n = 7`)** | — | **0.6071** | 0.8571 | — |

### Per-criterion verdicts

- **E1 (Exact viscous Euler & momentum invariants, zero clamps): PASS.** 0 violations across 30 curves (`5 fans × 3 rpms × 2 stator`), converged on Stock v1/v2/v3, drag monotonicity `-1.978 Pa` at `2× Cd`.
- **E2(a) (Stock v2 free-air & P-Q slope vs CFD): PASS.** Free-air `55.43 CFM` (`-1.9 %` vs CFD `56.5 CFM`); loaded points `55.43 / 48.96 / 40.25 CFM` match CFD `56.5 / 49.8 / 40.2 CFM` within 2 %.
- **E2(b) (Audit #4 `n = 7` Spearman $\rho \ge 0.60$): PASS** (`0.6071`).
- **E2(b2) (16-design CFD corpus Spearman $\rho \ge 0.75$): PASS** (`0.8294`, beating both legacy Euler `0.8206` and `axial_force` `0.8029`).
- **E2(c) (Stock v1 > Stock v2): PASS** (`56.16 > 55.43 CFM`).
- **E2(d) (Published benchmark sanity): FAIL on shut-off.** `Stock v3` free delivery `57.78 CFM` (`-3.9 %` vs `60.1 CFM`) and `lt120 > Stock v3` (`89.58 > 57.78 CFM`) both passed, **but** `Stock v3` shut-off collapsed to `6.24 Pa` (`-72.7 %` vs published `22.9 Pa`, below `[11.45, 34.35] Pa`).
- **E3 (QA-4 anti-exploit behavior in `"euler"` mode): PASS.** Paddle `89°` dropped to `2.32 CFM` (`4.0 %` of Stock) and `0.00 %` peak $\eta$; reversed `-45°` / `-60°` returned `no_rise` (`0.00 CFM`, `-9.002` / `-7.709 Pa` at `0.005 m³/s`).
- **E4 (Snapshot & ledger): N/A (`fansim/fan_bem.py` unchanged on E2(d) FAIL).**

### Diagnosis

1. **Unstalled branch & ranking strongly improved:** Moving `SLIP * leak` onto lift inside the momentum balance and subtracting Wallis Eq. 4.17 profile-drag loss nailed Stock v2's complete-setup CFD loaded curve (`0 / 5 / 10 Pa` within 2 %), improved 16-design CFD ranking (`0.8294 > 0.8206`), eliminated the QA-4 paddle and reversed-blade exploits directly inside `"euler"` mode, and enforced every thermodynamic/momentum bound without clamps.
2. **Shared 1-D shut-off collapse (same root cause as `#94`):** On `Stock v3`, static rise peaks at `11.76 Pa` (`34.3 CFM`, `0/20` clamped elements) and then falls to `6.40 Pa` at `2.3 CFM` where `20/20` elements saturate `vth = 0.95 * U` (cutting $W_m^2 \approx 0.276 U^2$) while Viterna post-stall drops $C_l$. Legacy Euler only reached `40.6 Pa` at shut-off because it held clamped $18^\circ$ lift and credited stalled drag as positive pressure. In reality, an axial fan near shut-off builds pressure via radial/centrifugal recirculation ($\Delta p \sim \rho \omega^2 (r_t^2 - r_h^2)$), which constant-$V_x$ 1-D annular BEM cannot represent.
3. **Path forward for v0.2 (`#93` + `#94` + `#95`):** Either (a) adopt the viscous Euler formulation for the unstalled operating range while explicitly documenting/scoping `shutoff_dp_pa` as unvalidated deep-stall (or pairing it with a radial-equilibrium / centrifugal shut-off model), or (b) replace the empirical `SLIP` + 1-D swirl-clamp scaffold with a full cascade + radial-equilibrium BEM in v0.2 — under a fresh pre-registration approved by Kimball.
