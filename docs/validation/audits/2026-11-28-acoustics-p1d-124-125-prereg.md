# Pre-registration & Audit #6 Amendment: Acoustics Math Close-Out (P1D: #124, #125)

- **Date:** 2026-11-28
- **Issues:** [#124](https://github.com/klhutchins1/Fan-simulator/issues/124) (remaining items 1, 3, 4 after PR #160 landed item 2) & [#125](https://github.com/klhutchins1/Fan-simulator/issues/125) (remaining item 2 after PR #163 documented item 1)
- **Epic:** [#169](https://github.com/klhutchins1/Fan-simulator/issues/169) (`docs/release/EPIC_V010.md`, Phase **P1D**)
- **Amends:** `docs/validation/audits/2026-09-29-audit-06-acoustics.md` (Audit #6)
- **Review source:** `docs/review/2026-11-26-rv3-structural-acoustics.md` (RV-3 Module 7, items A2, A3, A5, A9)
- **Ruling by:** Cursor (lead; committed and pushed before any implementation or test edits per `AGENTS.md` Rule 1)

---

## 1. Defects & Mathematical Specification

### 1.1 Control-Volume Force Sign Convention (`fansim/acoustics/farfield.py::force_from_cv`, #124 item 1)
- **Defect:** Reynolds Transport Theorem for a fixed control volume $V$ enclosing the fan with outward boundary normal $\mathbf{n}$ gives:
  $$\mathbf{F}_{\text{fan}\to\text{fluid}} = +\!\left(\frac{d\mathbf{P}}{dt} + \mathbf{F}_s\right), \qquad \mathbf{F}_s = \oint_{\partial V}\!\left(\rho\mathbf{u}(\mathbf{u}\cdot\mathbf{n}) + p\mathbf{n} - \boldsymbol{\tau}\cdot\mathbf{n}\right)dS.$$
  `force_from_cv` documented *"Fan force on the fluid"* while returning `-(dP/dt + Fs)` (the fluid-on-fan reaction force), inverting `thrust_n` and flipping dipole pressure phase by $180^\circ$ (SPL unaffected).
- **Fix:** Return `+(np.gradient(P_arr, dt, axis=0) + Fs_arr)` so `force_from_cv` matches Reynolds Transport Theorem and its own docstring; update `tests/test_farfield.py` and `tests/audit/test_acoustics_audit.py` sign assertions accordingly.

### 1.2 Short-Window Tone Bandwidth (`fansim/acoustics/farfield.py::tone_level_db`, #124 item 3)
- **Defect:** On short DES windows where Welch frequency spacing $\Delta f = f_1 - f_0 > 2\,\text{half\_bw}$ (e.g. `N = 200, fs = 20 kHz` → $\Delta f = 100\text{ Hz}$ vs `half_bw = 8.0 Hz`), `|f - f0| <= half_bw` matches zero bins even when `f0` is well below Nyquist, returning `NaN` and causing `peak_tone_over_harmonics` to drop resolved harmonics.
- **Fix:** Preserve exact behavior whenever `|f - f0| <= half_bw` is non-empty (normal windows) and whenever `f0 > f[-1] + half_bw` (past Nyquist → `NaN`). When `f0 <= f[-1] + half_bw` and `|f - f0| <= half_bw` is empty due to coarse $\Delta f$, integrate the single nearest frequency bin (`argmin(|f - f0|)`).

### 1.3 `proxies.py` Physical Guards & Scope (`fansim/acoustics/proxies.py`, #124 item 4)
- **Defects:**
  1. `proudman_power_density` did not clamp negative `epsilon` or validate positive finite `rho`/`c0` and non-negative finite `alpha`.
  2. `turbulent_mach`, `curle_surface_swl`, `curle_dpdt_estimate`, and `sound_power_level` did not guard non-positive/non-finite physical constants (`rho`, `c0`, `w_ref`, `cp`).
  3. `sound_power_level(float("nan"))` silently returned `-inf` instead of `NaN`.
  4. `curle_surface_swl` omitted eddy correlation area $A_c$ (dimensionally $\text{W/m}^2$ vs `W_REF = 1e-12 W`), and `curle_dpdt_estimate` did not warn about wall $\omega^2 \propto y_1^{-4}$ $y^+$ mesh sensitivity.
- **Fixes:**
  1. Clamp negative `epsilon` to `0.0` in `proudman_power_density` (matching `epsilon_from_komega` and `turbulent_mach`).
  2. Validate finite `rho > 0`, `c0 > 0`, `alpha >= 0`, `w_ref > 0`, finite `cp` across `proxies.py` (raising `ValueError`).
  3. Return `float("nan")` from `sound_power_level` when `w` is `NaN` (`float("inf")` for `+inf`, `float("-inf")` for finite `w <= 0`).
  4. Add optional `corr_area_m2: float | None = None` to `curle_surface_swl` (default `None` preserves existing relative $\text{W/m}^2$ ranking index; positive finite `corr_area_m2` yields true watts `[W]`) and document the wall $\omega^2 \propto y_1^{-4}$ $y^+$ mesh sensitivity in `curle_dpdt_estimate`.

### 1.4 `tonal.py` Unweighted Geometric Scope (`fansim/acoustics/tonal.py`, #125 item 2)
- **Scope ruling (mirroring PR #163 for `tip_loading.py`):** Per `docs/VALIDATION.md`, sound levels are unvalidated in v0.1.0 and no measured blade-force harmonic spectrum $|F_m|$ exists yet. Rather than inventing an unsourced harmonic roll-off exponent, `tonal.py` explicitly documents that `blade_passing_modes` / `tonal_peak_ratio` measure the **unweighted geometric array factor** $A(m) = |\sum_k e^{-i m \theta_k}|$ over `m = 1..m_max` (`4*N` default), that Dirichlet's theorem makes the peak sensitive to `m_max`, and that weighted tonal loudness ($|F_m|$, Curle $\propto m$, IEC A-weighting) is deferred to v0.2 once rig spectra exist. This closes `#125` cleanly with zero unvalidated heuristics.

---

## 2. Pre-Registered Acceptance Criteria (Fixed Before Implementation)

| ID | Criterion | Pass Rule |
|---|---|---|
| **A1** | `force_from_cv` RTT sign (#124.1) | For constant momentum growth $P_z = a t$ ($a = +3\text{ N}$) and outward flux $F_{sz} = +1\text{ N}$, `force_from_cv(t, P, Fs)` returns $F_z = +(a + F_{sz}) = +4.0\text{ N}$ (`allclose` to `1e-12`); steady positive outward flux $F_s = +F$ yields `thrust_n == +F` and preserves Curle dipole SPL to `0.3 dB`. |
| **A2** | Short-window `tone_level_db` (#124.3) | For a short window (`N = 200, fs = 20000 Hz`, $\Delta f = 100\text{ Hz} > 2\times 8\text{ Hz}$) containing a `233.33 Hz` sine, `tone_level_db(p, dt, 233.33, half_bw=8.0)` returns a finite SPL (within `3 dB` of exact RMS SPL, not `NaN`) and `peak_tone_over_harmonics` returns a finite level; frequencies past Nyquist (`f0 > fs/2 + half_bw`) still return `NaN`; normal-resolution windows (`df <= 2*half_bw`) are bit-for-bit identical. |
| **A3** | `proxies.py` guards & `corr_area_m2` (#124.4) | `proudman_power_density(1.0, -5.0) == 0.0`; non-positive/NaN `rho`, `c0`, `w_ref`, or negative/NaN `alpha` raise `ValueError`; `sound_power_level(float("nan"))` returns `NaN` (not `-inf`); `curle_surface_swl(..., corr_area_m2=A_c)` shifts SWL by exactly $+10\log_{10}(A_c)$ dB (`rel=1e-12`) and rejects `corr_area_m2 <= 0` or `NaN`. |
| **A4** | `tonal.py` scope doc (#125.2) | `fansim.acoustics.tonal` docstring explicitly documents unweighted geometric array factor, Dirichlet `m_max` sensitivity, and v0.2 deferral of $|F_m|$/Curle/A-weighting; zero numeric change to `blade_passing_modes` / `tonal_peak_ratio` / `peak_tone_reduction_db`. |
| **A5** | Hygiene, ledger & RV-1 invariance | `ruff check` (critical + changed `.py` files), `mypy --config-file pyproject.toml` (51 files), `scripts/audit_status.py --strict` (`PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`), `tests/test_physics_snapshot.py` (**zero diff** to `tests/data/physics_snapshot.json`), and all acoustics tests pass. |

---

## 3. Results

- **Verdict:** **PASS (5/5: A1–A5 all PASS)**
- **Date evaluated:** 2026-11-28 (`cursor/epic-1d-acoustics`, pre-registered at `9548e47`)

### Summary by Criterion

| ID | Verdict | Observed Evidence |
|---|---|---|
| **A1** | **PASS** | `force_from_cv(t, P, Fs)` now returns `+(dP/dt + Fs)` per Reynolds Transport Theorem (`F[:, 2] == +4.0` to `1e-12` for `P_z = 3t, Fs_z = 1`); `noise_from_cv_force` reports positive `thrust_n == +0.05` for positive outward flux `Fs = +F` while preserving Curle dipole SPL to `< 0.3 dB`. |
| **A2** | **PASS** | Short window (`N = 200, fs = 20 kHz, df = 100 Hz > 2*8 Hz`) returns finite `tone_level_db` within `3 dB` of exact RMS SPL and finite `peak_tone_over_harmonics`; frequencies past Nyquist (`f0 > fs/2 + half_bw`) still return `NaN`; normal-resolution windows (`df <= 2*half_bw`) are bit-for-bit identical. |
| **A3** | **PASS** | `proudman_power_density(1.0, -5.0) == 0.0`; invalid `rho`, `c0`, `alpha`, `w_ref`, `cp`, `corr_area_m2` raise `ValueError`; `sound_power_level(NaN)` returns `NaN` (not `-inf`); `curle_surface_swl(..., corr_area_m2=A_c)` shifts SWL by exactly `+10*log10(A_c)` dB (`rel=1e-12`). |
| **A4** | **PASS** | `fansim/acoustics/tonal.py` explicitly documents unweighted geometric array factor scope, Dirichlet `m_max` sensitivity, and v0.2 deferral of $|F_m|$ / Curle $\propto m$ / IEC A-weighting; zero numeric change to tonal outputs. |
| **A5** | **PASS** | `ruff check` (critical + changed `.py` files) clean; `mypy --config-file pyproject.toml` clean (51 source files); `scripts/audit_status.py --strict` reports `PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`; `tests/test_physics_snapshot.py` passes with **zero diff** to `tests/data/physics_snapshot.json`; acoustics + flow_report + snapshot suite `160 passed, 0 failed`. |
