# Audit #6: acoustics models vs analytic results (2026-09-29)

Question: do `fansim/acoustics/` (farfield, proxies, tonal, fwh, loading), `fansim/cfd/des_fwh.py`,
`fansim/propeller/noise.py` and the `scripts/fan_noise_*.py` / `evaluate_noise.py` reductions compute what they
claim (Curle dipole, BPF, Proudman, FW-H, dB / A-weighting), and do the docstrings and `docs/bibliography.md` say
what the code really does? Scope: VERIFICATION and CLAIMS only.

## Plain-language verdict

- **acoustics.curle_dipole: PASS** (verification). Amplitude F0 w cos(th)/(4 pi c0 r), 1/r decay (1, 2, 4 m),
  retarded-time waveform, cos(th) directivity (null at 90 deg), and radiated power 1/(12 pi rho c0^3) all match hand
  calculations to < 0.5%. dB re 20 uPa, IEC 61672 A-weighting (11 table points, within 0.1 dB) and the
  control-volume force pipeline (tone level within 0.3 dB) are correct. The kernel is the far-field term only.
- **acoustics.tonal_bpf: PASS.** BPF = B rpm/60 exact; equal-spacing array factor is exactly N at m = kN and 0
  elsewhere; A(m) matches an FFT of synthesized pulse trains to 1e-9; dB reduction formula exact.
- **acoustics.proudman: PASS** (as a ranking proxy). alpha rho eps Mt^5 equals the hand value to 1e-12; Mt^5, linear
  eps, rho, c0^-5 scalings exact; SWL re 1 pW exact; eps = 0.09 k omega.
- **acoustics.fwh: PASS as a stationary loading kernel only.** An offset panel dipole and a superposition of panels
  match the analytic retarded-time solution to < 1%. It is NOT moving-source FW-H (see claims).
- **Validation: INCONCLUSIVE by design.** Measured FAN-01 acoustics exist (Zenodo 10787093), but the source terms
  (unsteady blade / surface forces) need transient CFD (DES / LES / LBM), which is not viable on this machine
  (roadmap 19.6). Nothing here shows the absolute dB(A) or the ranking is right for the real fan. The repo's own
  docs already say absolute levels are coarse-grid limited; this audit does not change that.

## Pre-registered tolerances (fixed before any comparison)

| unit | quantity | tolerance |
|---|---|---|
| curle_dipole | amplitude vs F0 w cos(th)/(4 pi c0 r); 1/r (r = 1, 2, 4); cos(th) directivity | rel err <= 0.5%; null <= 1e-9 of peak |
| curle_dipole | radiated power vs <Fdot^2>/(12 pi rho c0^3) (numeric sphere integral) | rel err <= 0.5% |
| curle_dipole | dB refs (20 uPa), sine dB(A), CV pipeline tone level | 0.05 dB / 0.15 dB / 0.3 dB |
| curle_dipole | A-weighting vs IEC 61672-1 table (10 Hz to 10 kHz) | 0.1 dB |
| tonal_bpf | BPF, harmonics | exact (1e-12) |
| tonal_bpf | array factor equal spacing; FFT synthesis | 1e-9 |
| proudman | alpha rho eps Mt^5 hand value, scalings | 1e-12 |
| fwh | offset panel vs analytic retarded dipole; superposition | rel err <= 1% |
| all | c0, rho single-sourced from `fansim.physics.air` | identity |

Tolerances were not changed after seeing data.

## 1. Inventory

- `acoustics/farfield.py`: Curle compact dipole `p' = r_hat . dF/dt /(4 pi c0 r)`, F = -(dP/dt + Fs) from an LBM control
  volume, Welch band SPL, dB(A), BPF tone, peak tone over shaft harmonics.
- `acoustics/fwh.py` + `cfd/des_fwh.py`: same kernel summed over panels with `t - r/c0` delay; six-face / 24-patch
  permeable box; DES adapter builds face forces as rho * areaIntegrate(p) * n_hat.
- `acoustics/proxies.py`: Proudman power density / SWL, Curle surface power index, k-omega epsilon.
- `acoustics/tonal.py`: blade array factor. `acoustics/loading.py`: 7-point LBM-calibrated linear loading proxy
  (its own docstring is candid: LOO rho ~0.54). `acoustics/case.py`: OpenFOAM adapter (needs reconstructed case).
- `propeller/noise.py`: relative tip-speed / loading / compressibility proxy; `prop_fwh_from_mean_thrust`.
- Scripts: three copies of the A-weighting and Curle reduction (`fan_noise_curle.py`, `fan_noise_cv.py`,
  `evaluate_noise.py`).

## 2. Verification results (`tests/audit/test_acoustics_audit.py`)

| check | result |
|---|---|
| Dipole amplitude at 0/30/60/90/120/180 deg; absolute 0.6803 Pa hand number | PASS, < 0.5% |
| 1/r and retarded waveform (1, 2, 4 m) | PASS |
| Sphere-integrated power vs 1/(12 pi rho c0^3) | PASS, < 0.5% |
| CV force sign F = -(dP/dt + Fs); pipeline BPF tone level | PASS |
| A-weighting vs IEC table, 11 frequencies | PASS, all within 0.1 dB (1 kHz within 0.01) |
| Sine 1 Pa: 90.97 dB, dB(A) | PASS |
| BPF and harmonics; equal / uneven array factor; FFT synthesis | PASS |
| Proudman hand value, Mt^5, units, SWL | PASS |
| Panel offset dipole, superposition, compact vs panel consistency | PASS |
| c0 / rho single-sourced across acoustics, DES, propeller noise | PASS |
| Script A-weighting copies identical to the module | PASS |

## 3. Bugs and findings

1. **`proxies.curle_surface_swl` is dimensionally W/m^2, not W.** It integrates <(dp/dt)^2> dS but omits the eddy
   correlation area: for a coherent uniform patch the true Curle power is A x the returned linear value. The
   constant 1/(12 pi rho c0^3) is right. Ranking is unaffected; the docstring claim "radiated power ... dB re 1 pW"
   was wrong. Docstring corrected; no numeric change. Left unregistered (no PASS recorded).
2. **Near-field term omitted.** The exact compact dipole has an extra F/r^2 term in quadrature; amplitude error is
   sqrt(1 + 1/(kr)^2). At the BPF tone (233 Hz): 0.2 dB at 1 m (scripts, LBM: fine), but **~3.8 dB under-prediction
   at 0.2 m, the default `des_fwh.DEFAULT_X_OBS`.** DES FW-H numbers at 0.2 m are inside the near field; treat as
   relative only.
3. **Latent:** `scripts/fan_noise_curle.observer_pressure` divides by R_OBS^2 while r_hat is a unit vector; it equals
   the far-field 1/r law only at R_OBS = 1 m (hard-coded), and is low by a factor R_OBS otherwise. Not fixed (recovered
   script, no caller varies R_OBS).
4. **Duplication:** `farfield.py` says it is "the single, tested home" of the A-weighting, but three script copies
   remain. They agree numerically (tested).
5. `des_fwh` face force = rho * areaIntegrate(p) * n_hat uses only pressure loading on the box faces (no
   rho u (u.n) terms); mean is removed and the overall sign does not change SPL.

## 4. Claims

- **Bibliography said "planned" for something implemented**: Proudman is implemented
  (`proudman_power_density` / `proudman_swl`, not the cited name `proudman_power`). Fixed.
- **Bibliography said "future" for something partly implemented**: FW-H exists in `fwh.py` / `des_fwh.py` but only as a
  stationary pressure-loading (Curle-type) kernel. There is no moving-source Doppler factor, no thickness or
  quadrupole / permeable momentum-flux terms; `fwh.py` claimed "Farassat 1A". Docstring and bibliography reworded;
  full rotating FW-H remains unimplemented. Tested absence: no Mach or velocity argument.
- **Curle pointer stale**: bibliography pointed to the scripts; the tested home is `farfield.py`. Fixed. Also the
  `evaluate_noise` docstring implied Curle is 1/r^2 and FW-H 1/r; both are the same far-field kernel. Fixed.
- **`proxies.py` cites Sarkar & Hussaini (1993) for alpha = 0.1, which is not in the bibliography.** The constant is
  used as cited (Mt = sqrt(2k)/c0 convention); not independently derived. Proudman's original constant is defined with
  a different velocity scale, so the absolute power is uncertain by roughly an order of magnitude; ranking only.
- **`propeller.noise.prop_fwh_from_mean_thrust` is not FW-H**: it is a RECONSTRUCTED placeholder (`20 log10(T) + 40`,
  independent of rpm and blade geometry) yet returns `analogy="fwh_prop_synthetic"` and `noise_dba_band`. Do not treat
  as acoustics. `estimate_prop_noise` uses a 30 log10(U_tip) term (the dipole scaling is U^6, i.e. 60 log10); the
  coefficients are heuristic, defensible only as relative ranking (its docstring says so).
- Tonal array factor assumes equal per-blade loading and no harmonic roll-off of the blade force spectrum; it is a
  relative peak-tone proxy, not a level.
- `acoustics.loading` proxy: stated as 7-point calibration (LOO rho ~0.54); claims are already appropriately hedged.
- Not audited: `fansim/cror/noise.py`, `cfd/des_fwh.py` OpenFOAM parsing beyond the sign/unit logic.

## 5. Registry / ledger

Units registered: `acoustics.curle_dipole`, `acoustics.tonal_bpf`, `acoustics.proudman`, `acoustics.fwh` (PASS
recorded for verification only). The Curle surface proxy, loading proxy, DES adapter and propeller noise are left
unregistered / unproven.
