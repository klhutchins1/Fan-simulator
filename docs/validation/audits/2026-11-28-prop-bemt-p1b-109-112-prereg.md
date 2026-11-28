# Pre-registration: Propeller BEMT & Polars Math Fixes (P1B: #109, #110, #111, #112)

- **Date:** 2026-11-28
- **Issues:** #109 (angular momentum omits Prandtl `F`, clamps windmill swirl `vth >= 0`, signed `sin(phi)`), #110 (`_analytic_section` constant `Cd`, half thin-airfoil camber lift, unphysical deep/negative stall), #111 (flat `[-5°, +18°]` polar clamping, `s1223` missing negative stall, radial camber/thickness mean), #112 (15 °C `RHO_ISA` mixed with 20 °C `NU_AIR`/`C0_AIR`, static hover `figure_of_merit` reported in forward flight)
- **Epic:** #169 (`docs/release/EPIC_V010.md`, Phase **P1B**)
- **Review source:** `docs/review/2026-11-26-rv3-propeller.md` (items F1, F2, F5, F7, F9, F10, F11, F14) and `docs/validation/audits/2026-09-29-audit-03-prop-bemt-uiuc.md`
- **Ruling by:** Cursor (lead; committed and pushed before any implementation or test edits per `AGENTS.md` Rule 1)

---

## 1. Defects & Mathematical Specification

### 1.1 Issue #109 — Prop BEMT Momentum Closure (`fansim/propeller/bemt.py:analyze`)
1. **Prandtl tip-loss factor `F` in angular momentum:**
   With circumferentially averaged induced swirl $\bar{v}_\theta = F v_\theta$ (Glauert 1935; Adkins & Liebeck 1994 Eq. 14; Drela QPROP 2006), the angular momentum balance per unit span is
   $$f_\theta = 2\pi r \rho |V_{\text{ax}}| v_\theta F,$$
   so `denom_th = 2.0 * math.pi * r * rho_f * max(abs(Vax), 0.1) * F` (previously omitted `* F`).
2. **Symmetric windmill swirl induction:**
   In power-extracting windmill / braking states ($f_\theta < 0$), $v_\theta < 0$ ($a' < 0$, increasing $V_t = \Omega r - \tfrac{1}{2}v_\theta > \Omega r$). Replace `max(0.0, min(vth_new, 1.9 * U))` with `max(-1.9 * U, min(vth_new, 1.9 * U))` so $V_t \in [0.05\,U, 1.95\,U]$.
3. **Unsigned inflow sine in Prandtl `f`:**
   Use `max(r * abs(math.sin(phi)), 1e-4)` so negative axial inflow ($V_{\text{ax}} < 0$) does not collapse $F \to 1$.
   *(Prandtl tip loss stays floored at `0.15` without hub loss or Glauert turbulent-wake correction, matching the documented scope in `bemt.py` and `tests/audit/test_prop_bemt_audit.py`.)*

### 1.2 Issue #110 — Analytic Polar Physics (`fansim/propeller/bemt.py:_analytic_section`)
For $\text{Re} < 40{,}000$ (or `re=None`), replace the constant-$C_d$ / half-camber / 0.55-floor analytic polar with standard thin-airfoil + quadratic attached drag + Viterna–Corrigan (1982) post-stall continuation (`CD_MAX = 1.11 + 0.018 * 10 = 1.29`, matching `neuralfoil_polars.py`):
- **Thin-airfoil camber lift (Abbott & von Doenhoff 1959 §4.2):**
  $\alpha_{L=0} = -2m \implies C_{l,\text{lin}} = \text{slope}\cdot(\alpha + 2m)$ ($C_{l,0} = 4\pi m$ at $\text{slope} = 2\pi$).
- **Attached drag rise:** $C_d = C_{d0} + 0.025\,C_l^2$ for attached flow.
- **Symmetric positive & negative post-stall (Viterna–Corrigan 1982):**
  Positive stall edge $\alpha_p = +\alpha_{\text{stall}}$; negative stall edge $\alpha_n = \min(-\alpha_{\text{stall}}, -2m - 0.5\,\alpha_{\text{stall}})$ (guarantees $C_l(\alpha_n) < 0$ for all cambers). Beyond $[\alpha_n, \alpha_p]$, continue continuously via Viterna–Corrigan (`CD_MAX = 1.29`) so $C_l(\pm 90^\circ) = 0$, $C_d(\pm 90^\circ) = 1.29$, and `stalled = True`.

### 1.3 Issue #111 — Polar Table Post-Stall Extrapolation & Radial Station Interpolation
1. **Post-stall extension outside vendored CSV bounds (`fansim/propeller/polars.py`):**
   - Multi-row tables (`len(a) >= 2`):
     - Above `a[-1]` (`+18°`, already past positive stall on all 6 families): Viterna–Corrigan (`CD_MAX = 1.29`) matched continuously at `(a[-1], cl[-1], cd[-1])`, driving $C_l(90^\circ) \to 0$ and $C_d(90^\circ) \to 1.29$.
     - Below `a[0]` (`-5°`, still attached on all 6 vendored CSVs): linear attached lift continuation at edge slope `slope_lo = max((cl[1]-cl[0])/(a[1]-a[0]), 0.04)` down to negative stall `a_neg` where `cl` reaches `-min(0.85 * cl_peak, 1.1)` (step clamped to `[3°, 14°]` below `a[0]`), with smooth quadratic drag rise from `cd[0]` to `cd_neg = max(cd[0] + 0.06, cd[-1])`; below `a_neg`, Viterna–Corrigan (`CD_MAX = 1.29`) matched continuously at `(a_neg, cl_neg, cd_neg)` down to $-90^\circ$ ($C_l \to 0, C_d \to 1.29$).
     - `_curve_limits` reports this finite `a_neg` for every multi-row family (fixing `s1223` where `a_neg` was previously `None` and avoiding false stall flagging at attached `-5°`).
   - Single-row CSVs (`len(a) == 1`) retain flat clamping.
2. **Radial interpolation of camber and thickness (`fansim/propeller/bemt.py:_interp_geom`):**
   Interpolate `max_camber(r)` and `thickness(r)` linearly across stations via `np.interp(r, rs, ...)` (matching `chord(r)` and `stagger_deg(r)`), instead of collapsing to unweighted `np.mean`.
3. **Transonic compressibility scope (`_compressibility_cl_cd`):**
   Retain subsonic Prandtl–Glauert + soft wave-drag formula (no high-Mach validation data exists in the repo) and document its subsonic validity scope ($M \le 0.7$) explicitly in the docstring.

### 1.4 Issue #112 — Consistent 15 °C ISA Air Properties & Hover FM Guard
1. **ISA 15 °C air constants (`fansim/physics/air.py`, ISO 2533:1975):**
   Add `T_ISA_K = 288.15`, `MU_ISA = 1.7894e-5`, `NU_ISA = MU_ISA / RHO_ISA`, and `C0_ISA = math.sqrt(GAMMA_AIR * R_AIR * T_ISA_K)` (`~340.294 m/s`). Import `RHO_ISA`, `NU_ISA`, and `C0_ISA` in `fansim/propeller/bemt.py` so density, viscosity, and speed of sound share one consistent 15 °C ISA state.
2. **Hover-only `figure_of_merit` (`fansim/propeller/bemt.py`):**
   Static hover Figure of Merit $T^{3/2} / (P\sqrt{2\rho A})$ (Leishman 2006 Eq. 2.40) is defined only at $V_\infty = 0$. Return `figure_of_merit = None` and `figure_of_merit_raw = None` whenever `v_forward > 0` (mirroring `prop_efficiency = None` when `v_forward == 0`). Update `fansim/validation/physics_snapshot.py` to handle `None` on forward-flight points.

---

## 2. Pre-Registered Acceptance Criteria (Fixed Before Running Code)

All 7 criteria must pass to merge. Any failure is recorded honestly in Section 3 without re-tuning thresholds or empirical constants:

| ID | Check | Pass Criterion |
|---|---|---|
| **C1** | `#109` Momentum equations | 1-element closed-form BEMT check passes with `denom_th = 2*pi*r*rho*|Vax|*F`; APC SF 9×4.7 windmill (`J=0.75, 4008 rpm`) produces negative swirl (`vth < 0`) and `T < 0`; `abs(sin(phi))` keeps $F < 1$ when $V_{\text{ax}} < 0$. |
| **C2** | `#110` Analytic polar physics | `_analytic_section(0, m, re=None)` gives $C_l = 4\pi m$ (within `1e-9`); attached $C_d > C_{d0}$ when $C_l \ne 0$; at $\alpha = \pm 90^\circ$, `stalled is True`, $|C_l| < 10^{-6}$, and $C_d = 1.29 \pm 10^{-6}$; continuous across both stall edges. |
| **C3** | `#111` Table extrapolation & radial geometry | Above `+18°` and below `a_neg`, `section_table` continues smoothly via Viterna–Corrigan to $C_l(\pm 90^\circ) \approx 0$ and $C_d(\pm 90^\circ) \approx 1.29$; `s1223` flags `stalled is True` at `-30°`; `naca4412` is not stalled at `-5°`; `_interp_geom` passes radially interpolated `thickness(r)` and `camber(r)` to `_section_aero`. |
| **C4** | `#112` ISA air & hover FM guard | `MU_ISA`, `NU_ISA`, `C0_ISA` match ISO 2533 / Sutherland / ideal-gas speed of sound at `288.15 K` (`tests/audit/test_air_properties.py` passes); `bemt.py` uses `RHO_ISA`, `NU_ISA`, `C0_ISA`; `analyze(..., v_forward > 0)` returns `figure_of_merit is None` and `figure_of_merit_raw is None`; hover (`v_forward == 0`) preserves $0 < \text{FM}_{\text{raw}} < 1$. |
| **C5** | UIUC Audit #3 & GWS validation | **APC E 9×6:** static $|e_{C_T}| \le 15\%$, static $|e_{C_P}| \le 20\%$, worst $C_T(J)$ RMS $\le 0.015$ (all 3 PASS). **APC SF 9×4.7:** static $|e_{C_T}| \le 15\%$ (PASS), worst $C_T(J)$ RMS $\le 0.020$ regression guard (report honest PASS/FAIL vs `0.015` and honest static $C_P$ vs $\pm 20\%$ without regressing past `-25%`). **GWS 5×4.3:** peak $\eta$ within $\pm 0.10$ and static $C_{T0}$ within $\pm 15\%$. **Registry props & Q7 quorum** pass (`tests/test_bemt.py`, `tests/test_bemt_catalog.py`). |
| **C6** | Fan BEM Audit #4 non-regression | Because `fan_bem.py` shares `_cl_cd`, `tests/audit/test_fan_bem_audit.py` passes (Stock v2 free air within $\pm 25\%$ of CFD, P–Q slope order, v1 > v2, momentum bound), Audit #4 Spearman $\rho \ge 0.60$ on the 7 designs, and `tests/test_fan_bem.py` + `tests/test_bem_exploit_guard.py` pass without retuning `SLIP`/`AX_SLIP`. |
| **C7** | Hygiene, ledger, RV-1 & RV-2 | `ruff check` (critical + changed `.py` files), `mypy` (51 source files), and `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`) pass; RV-1 `tests/data/physics_snapshot.json` regenerated with this audit file as `--reason` and RV-2 `docs/validation/scoreboard.md` synced via `scripts/scoreboard.py --write`; `tests/test_physics_snapshot.py` and `tests/test_scoreboard.py` pass. |

---

## 3. Results

*(To be recorded after implementation and verification.)*
