# Pre-registration & Audit #5 Amendment: Structural Math Fixes (P1C: #123)

- **Date:** 2026-11-28
- **Issue:** [#123](https://github.com/klhutchins1/Fan-simulator/issues/123) (root bending uses tip station, uniform-bar centrifugal bias on tapered blades, solid-rectangular $I$/$A$ on NACA airfoils, `RESIN` layer-adhesion knockdown inconsistency)
- **Epic:** [#169](https://github.com/klhutchins1/Fan-simulator/issues/169) (`docs/release/EPIC_V010.md`, Phase **P1C**)
- **Amends:** `docs/validation/audits/2026-09-29-audit-05-structural.md` (Audit #5)
- **Review source:** `docs/review/2026-11-26-rv3-structural-acoustics.md` (RV-3 Module 7, items S2–S4)
- **Ruling by:** Cursor (lead; committed and pushed before any implementation or test edits per `AGENTS.md` Rule 1)

---

## 1. Defects & Mathematical Specification

### 1.1 Tapered Centrifugal Root Stress (`fansim/structural/stress.py`)
- **Defect:** `centrifugal_root_stress` assumes a uniform-section rotating bar $\sigma_{\text{root}} = \tfrac{1}{2}\rho\omega^2(r_{\text{tip}}^2 - r_{\text{hub}}^2)$, which under-predicts root tensile stress by ~1.48× on outward-flaring blades such as Stock v3 (`config/problems/a12x25_reference.yaml`, $A_{\text{tip}}/A_{\text{root}} = 1.80$).
- **Exact continuum formula:** For a blade of uniform section family along $[r_{\text{hub}}, r_{\text{tip}}]$ with local cross-sectional area $A(r) = K_A\,c(r)\,t(r)$, where $c(r)$ and $\tau(r) = t(r)/c(r)$ are piecewise-linear across sorted `params.stations` (clamped flat outside the station `r_frac` range):
  $$\sigma_{\text{root}} = \frac{\rho\omega^2}{A(r_{\text{hub}})}\int_{r_{\text{hub}}}^{r_{\text{tip}}} A(r)\,r\,dr = \frac{\rho\omega^2}{c(r_{\text{hub}})\,t(r_{\text{hub}})}\int_{r_{\text{hub}}}^{r_{\text{tip}}} c(r)\,t(r)\,r\,dr.$$
  Notice that any constant section-family factor $K_A$ cancels identically. Because $c(r)\,\tau(r)\,c(r)\,r$ is at most degree 4 in $r$ on each segment, 3-point Gauss-Legendre quadrature per sub-interval integrates it to machine precision.
- **Prismatic limit:** For constant $c(r), \tau(r)$, reduces identically to $\tfrac{1}{2}\rho\omega^2(r_{\text{tip}}^2 - r_{\text{hub}}^2)$.
- **Explicit scope:** Shroud-ring hoop-coupled loading (`shroud_thick_mm > 0`) and hub-fillet stress concentration $K_t$ remain outside this first-order screening gate and are documented in the module docstring.

### 1.2 Root Bending Stress at `_root_station` (`fansim/structural/deflection.py`)
- **Defect:** `root_bending_stress` called `_beam_section`, evaluating section modulus at `_tip_station` instead of `_root_station`, and used $M = \Delta P c_{\text{tip}} L^2 / 2$. On outward-flaring blades like Stock v3 ($Z_{\text{tip}}/Z_{\text{root}} = 1.80$), this under-predicts tapered root bending stress by ~1.53×.
- **Exact cantilever formula:** Under uniform pressure $\Delta P$ (`load_pa`) acting on spanwise chord $c(s)$ ($s = r - r_{\text{hub}} \in [0, L]$):
  $$M_{\text{root}} = \Delta P \int_0^L c(s)\,s\,ds, \qquad \sigma_{\text{root}} = \frac{M_{\text{root}}\,(t_{\text{root}}/2)}{I_{\text{root}}}, \qquad I_{\text{root}} = K_I\,\frac{c_{\text{root}}\,t_{\text{root}}^3}{12},$$
  evaluated at `_root_station(params)` (`min` `r_frac`). Piecewise Gauss-Legendre quadrature integrates $c(s)\,s$ (degree 2) to machine precision.
- **Prismatic limit:** For constant chord $c_0$, $M_{\text{root}} = \Delta P c_0 L^2 / 2$ identically.

### 1.3 Section-Family Area & Bending Inertia Factors ($K_A, K_I$) (`fansim/structural/deflection.py`, `fansim/structural/flutter.py`)
- **Defect:** `tip_deflection_mm`, `tip_deflection_point_load_mm`, `root_bending_stress`, and `first_bending_hz` treated every blade as a solid rectangle ($K_A = 1, K_I = 1$), ignoring the difference between `section_family = "naca"` and `"plate"`.
- **First-principles factors from `fansim/geometry/airfoil.py`:**
  - **`section_family == "plate"` (`rounded_plate`):** Constant-thickness plate across the flat body (`K_A = 1.0`, `K_I = 1.0`, matching the exact `rounded_plate` polygon within `< 1%` on Stock v3 `le=0.2, te=0.2`).
  - **`section_family == "naca"` (`naca4`, closed-TE Abbott & von Doenhoff 1959 §6.2 `-0.1036` polynomial in `fansim/geometry/airfoil.py`):** Exact analytic integrals of the symmetric thickness distribution $h(x)/t = 10(0.2969\sqrt{x} - 0.1260 x - 0.3516 x^2 + 0.2843 x^3 - 0.1036 x^4)$:
    - $K_A^{\text{NACA}} = \int_0^1 (h(x)/t)\,dx = 0.6808833333\ldots$ ($A = K_A\,c t$),
    - $K_I^{\text{NACA}} = \int_0^1 (h(x)/t)^3\,dx = 0.4706266577\ldots$ ($I = K_I\,c t^3 / 12 = 0.0392188881\,c t^3$).
    - Resulting stiffness and frequency ratios relative to a solid rectangle: deflection and bending stress increase by $1/K_I \approx 2.125\times$; first bending frequency scales by $\sqrt{K_I / K_A} \approx 0.8314$ (removing the +20.3% non-conservative rectangular overestimate on NACA sections).
- **Explicit scope:** `deflection_report` retains its conservative flapwise-vs-radial `tip_gap_mm` and solidity-free $q = \Delta P \cdot c$ screening proxy (Audit #5); `flutter_report` remains a $1\times\text{BPF}$ fundamental resonance gate (not a full Campbell diagram with $1\times$ shaft / strut / $2\times\text{BPF}$ orders). Both limits are stated explicitly in module docstrings.

### 1.4 Isotropic `RESIN` Layer-Adhesion Knockdown (`fansim/structural/stress.py`, `fansim/structural/deflection.py`)
- **Defect:** `_fdm_e_factor` already treats `RESIN` / `SLA` as isotropic (`e_k = 1.0`), but `centrifugal_root_stress` and `root_bending_stress` still defaulted `adhesion_k` to `LAYER_ADHESION_K = 0.60` for `RESIN`.
- **Fix:** Shared `_adhesion_factor(material)` returns `1.0` for isotropic `RESIN`/`SLA` materials (`name in ("RESIN", "ABS_RESIN", "SLA") or "RESIN" in name`) and `LAYER_ADHESION_K = 0.60` for FDM filaments. Explicit `adhesion_k` overrides continue to work unchanged.

---

## 2. Pre-Registered Acceptance Criteria (Fixed Before Implementation)

| ID | Criterion | Pass Rule |
|---|---|---|
| **S1** | Tapered centrifugal root stress | (a) Prismatic blades match $\tfrac{1}{2}\rho\omega^2(r_{\text{tip}}^2 - r_{\text{hub}}^2)$ to `rel <= 1e-9`; (b) linearly tapered outward-flaring and inward-tapering blades match independent 200,000-point trapezoidal numerical integration of $\frac{\rho\omega^2}{A(r_{\text{hub}})}\int_{r_{\text{hub}}}^{r_{\text{tip}}} A(r) r\,dr$ to `rel <= 1e-6`; (c) Stock v3 (`a12x25`) centrifugal root stress rises by `1.40x–1.55x` over the uniform-bar value (~1.48×). |
| **S2** | Tapered root bending stress at `_root_station` | (a) Prismatic plate blades match $M c / I$ with $M = q L^2/2$ to `rel <= 1e-9`; (b) tapered blades match exact $\Delta P \int_0^L c(s)\,s\,ds / Z_{\text{root}}$ to `rel <= 1e-9`; (c) Stock v3 (`a12x25`, plate) root bending stress rises by `1.45x–1.65x` over the old tip-station value (~1.53×). |
| **S3** | Section-family shape factors ($K_A, K_I$) | (a) `NACA_AREA_K` and `NACA_INERTIA_K` agree with Green's-theorem polygon integration of `fansim.geometry.airfoil.naca4(0, 0.4, 0.10, n_points=400)` to `rel <= 1e-3`; (b) `tip_deflection_mm`, `tip_deflection_point_load_mm`, `root_bending_stress`, and `first_bending_hz` match closed-form & 40-element Hermite FE solutions for both `"plate"` ($K_A=1, K_I=1$) and `"naca"` ($K_A=0.6809, K_I=0.4706$) to Audit #5 tolerances (`<= 1e-9` closed-form, `<= 1%` FE); (c) `"naca"` gives `~2.125x` larger deflection/stress and `~0.8314x` lower $f_1$ than `"plate"` at identical `(c, t/c)`. |
| **S4** | Isotropic `RESIN` adhesion knockdown | For `material="RESIN"` with default `adhesion_k=None`, both `centrifugal_root_stress` and `root_bending_stress` report `adhesion_k == 1.0`, `yield_mpa == MATERIALS["RESIN"].yield_strength_mpa`, and no `"layer-adhesion"` tag in failure reasons; FDM materials (`PETG`, `PLA`, `ABS`, `PLA+`, `TPU`) retain default `adhesion_k == 0.60`. |
| **S5** | Stock v3 (`a12x25`) structural gates | Stock v3 (`section_family="plate"`, PETG, 2000 RPM, 10 Pa hose, 0.5 mm tip gap) passes all three gates (`centrifugal.ok`, `root_bending.ok`, `deflection.ok`, `flutter.ok` with `margin >= 1.2`) and retains `beam_regime_ok == False` warnings. |
| **S6** | Hygiene, ledger & RV-1 snapshot | `ruff check` (critical + changed `.py` files), `mypy --config-file pyproject.toml` (51 files), `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`), `tests/test_physics_snapshot.py` (RV-1 regenerated with this audit file as `--reason`), and all structural + optimizer gate tests pass; tracked `.stl` files untouched. |

---

## 3. Results

- **Verdict:** **PASS (6/6: S1–S6 all PASS)**
- **Date evaluated:** 2026-11-28 (`cursor/epic-1c-structural`, pre-registered at `dff21b0`)

### Summary by Criterion

| ID | Verdict | Observed Evidence |
|---|---|---|
| **S1** | **PASS** | Prismatic blades match $\tfrac{1}{2}\rho\omega^2(r_{\text{tip}}^2 - r_{\text{hub}}^2)$ to `rel <= 1e-9`; outward-flaring and inward-tapering blades match 200,000-point trapezoidal integration to `rel <= 1e-6`; Stock v3 (`a12x25`) PETG centrifugal root stress rises `0.069858 -> 0.100482 MPa` (**1.4384×**, within pre-registered `1.40x–1.55x`; SF `429.4 -> 298.6`). |
| **S2** | **PASS** | Prismatic plate & NACA beams match closed-form $M c / I$ to `rel <= 1e-9`; linearly tapered plate blade matches exact $\Delta P L^2(c_r/6 + c_t/3) / Z_{\text{root}}$ to `rel <= 1e-9`; Stock v3 (`a12x25`, plate, 10 Pa) root bending stress rises `0.005351 -> 0.008018 MPa` (**1.4983×**, within pre-registered `1.45x–1.65x`; SF `5606.2 -> 3741.8`). |
| **S3** | **PASS** | `NACA_AREA_K = 0.6808833333` and `NACA_INERTIA_K = 0.4706266577` match Green's-theorem integration of `airfoil.naca4(0, 0.4, 0.10, n_points=400)` (`0.680876`, `0.470614`, rel `< 3e-5`). All Audit #5 uniform deflection, point-load deflection, root bending, and $f_1$ closed-form + 40-element Hermite FE tests pass for both `"plate"` and `"naca"`. NACA/plate ratios match `1/K_I = 2.1248x` and `sqrt(K_I/K_A) = 0.8314x` to `rel <= 1e-9`. Note: thin-mid NACA default `BladeParams()` (`t/c = 0.05`) drops from `312 Hz` to `259.5 Hz` (`1.11x BPF < 1.2`), exposing the prior non-conservative rectangular overestimate. |
| **S4** | **PASS** | `RESIN` defaults to `adhesion_k = 1.0` (`yield_mpa = 50.0 MPa`, no `"layer-adhesion"` tag in failure reasons) in both `centrifugal_root_stress` and `root_bending_stress`; all 5 FDM filaments (`PETG`, `PLA`, `ABS`, `PLA+`, `TPU`) retain default `adhesion_k = 0.60`. |
| **S5** | **PASS** | Stock v3 (`a12x25_reference.yaml`, `section_family="plate"`, PETG, 2000 RPM, 10 Pa, 0.5 mm tip gap): centrifugal `ok=True` (`SF=298.6`), root bending `ok=True` (`SF=3741.8`), deflection `ok=True` (`0.000802 mm`, `beam_regime_ok=False`), flutter `ok=True` (`f1=399.91 Hz`, `BPF=300.00 Hz`, `margin=1.333`, `beam_regime_ok=False`). |
| **S6** | **PASS** | `ruff check` (critical + all changed `.py` files) clean; `mypy --config-file pyproject.toml` clean (51 source files); `scripts/audit_status.py --strict` reports `PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`; RV-1 `tests/data/physics_snapshot.json` regenerated (only `structural.stock_v3` `bending_*` and `centrifugal_*` moved, `8 passed`); structural + audit + gate suite `168 passed, 0 failed`; zero tracked `.stl` changes. |
