# Math accuracy audit (§10.1–§10.11) — recovered tree

**Date:** 2026-09-14  
**Scope:** Implement + verify `docs/superpowers/specs/2026-09-11-math-accuracy-fixes-design.md` §10.1–§10.11 on the recovered working tree.

## Results (PASS / FIXED / DEFERRED)

| ID | Topic | Verdict | Notes |
|---:|---|---|---|
| 10.1 | FWH + Curle kernels (far-field) | **FIXED** | Curle dipole corrected to \(1/r\); FW-H already \(1/r\) (doc fixed). Added distance-scaling test. |
| 10.2 | Delete extra \( \tfrac12 \rho W^3 c B C_d \) shaft-power term | **FIXED** | Removed double-counting term in `fansim/fan_bem.py`. |
| 10.3 | Ducted fan BEM: gap leakage only (no Prandtl) | **FIXED** | Removed Prandtl factor from ducted fan BEM; retained outer-span gap leakage. Recalibrated `SLIP`. |
| 10.4 | BEMT \(a'\) / \(V_t\) sign (\(V_t=\Omega r(1-a')\)) | **FIXED** | Added tangential induction iteration (swirl) and used \(V_t=\Omega r - \bar{V}_\theta\) in prop BEMT. |
| 10.5 | Analytic polar: \(c_d = c_{d0}\) only | **FIXED** | Removed induced-drag term from `_cl_cd_analytic`. |
| 10.6 | Re table: below-min Re returns None (no clamp-up) | **PASS** | Already implemented in `fansim/propeller/polars.py` (`re < min -> None`). |
| 10.7 | BEM shutoff = max(ΔP) | **PASS** | `fansim/fan_bem.pq_curve()` uses `max(dp_static)`. |
| 10.8 | Screening: “not grid-converged” stamp | **PASS** | `SCREENING_GRID_STAMP` present and applied (axial/mixed/CROR/volute). |
| 10.9 | Single `CFM_PER_M3S`; unify default ρ expectations | **FIXED** | `CFM_PER_M3S` now sourced from `fansim/cfd/metrics.py`; acoustics proxy default `ρ` aligned to 1.2. |
| 10.10 | Circular inlet area ≈ \( \pi R^2 \) check | **PASS** | `fansim/cfd/duct_area.py` implements `require_circular_inlet_area()` with tests. |
| 10.11 | FDM E knockdown on δ and f1 | **PASS** | `FDM_E_K=0.70` applied in `fansim/structural/deflection.py` and `flutter.py`. |

## Key code changes

- **10.1 (Curle / FW-H kernels)**:
  - `fansim/acoustics/farfield.py`: `dipole_pressure()` now uses \(1/(4\pi c_0 r)\).
  - `fansim/acoustics/fwh.py`: corrected docstring to match implementation.
  - `tests/test_farfield.py`: added `test_dipole_one_over_r_drops_six_db()`.

- **10.2 (double-counted Cd power)**:
  - `fansim/fan_bem.py`: removed the extra profile-drag dissipation term that duplicated drag already present in the blade-element tangential force / torque balance.

- **10.3 (ducted fan no Prandtl)**:
  - `fansim/fan_bem.py`: removed Prandtl finite-blade factor; retained gap leakage factor in outer span.
  - `fansim/fan_bem.py`: recalibrated `SLIP` to keep the reference efficiency band.

- **10.4 (prop BEMT swirl / \(a'\))**:
  - `fansim/propeller/bemt.py`: added a coupled iteration for axial induced velocity and swirl (`vth`), using \(V_t=\Omega r-\bar{V}_\theta\) with \(\bar{V}_\theta \approx vth/2\).

- **10.5 (analytic polar)**:
  - `fansim/propeller/bemt.py`: `_cl_cd_analytic()` now uses `cd = cd0` only.

- **10.9 (single CFM constant)**:
  - `fansim/fan_bem.py`, `fansim/optimize/system_curve.py`, `tests/test_system_curve.py`, `fansim/cfd/domain.py`: import `CFM_PER_M3S` from `fansim/cfd/metrics.py`.
  - `fansim/acoustics/proxies.py`: default `RHO_AIR` set to 1.2 per design.

## Tests run

```powershell
$venv = "$env:TEMP\fansim_py312_venv"
cd "T:\Projects\Fan Simulator"
& "$venv\Scripts\python.exe" -m pytest -q `
  tests/test_bemt.py `
  tests/test_fan_bem.py `
  tests/test_farfield.py `
  tests/test_fwh.py `
  tests/test_system_curve.py `
  tests/test_acoustics.py
```

Pytest summary: `35 passed, 1 skipped` (Windows OCCT teardown may still emit a non-zero process exit code after a green pytest summary; see `docs/validation/suite_baseline_2026-09-14.md`).

