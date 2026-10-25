# Lead #16: phone tap test → measured blade f1 (sdypy-EMA vs scipy peak-pick), 2026-10-21

**Verdict: worth it as a scipy-only tap-test → `FDM_E_K` calibration (effort S). sdypy-EMA itself is not needed.**
- A plain FFT peak-pick plus half-power damping finds the blade f1 to **≤0.4 %** at phone-realistic SNR (≥10 dB). That is far tighter than anything
  the flutter gate or the E calibration needs.
- sdypy-EMA (LSCF) is 3–10× more precise on f and roughly 2× better on ζ. That precision is unused: fansim does not use damping, and the boundary condition
  (how the part is held) dominates the error.
- Without a measured input force it is output-only anyway.
- Keep sdypy-EMA, at most, as an optional extra for users with an impact hammer.
- Proposal: `../proposals/lead-16-tap-test-calibration.md`.

## Prototype (`proto/lead16/tap_modal.py`, throwaway venv /tmp/ema-venv, sdypy-EMA 0.31.0)
- **Synthetic tap:** four decaying modes at the lead-13 FEA frequencies 357 / 1009 / 1777 / 2024 Hz, ζ 2.5 / 1.8 / 1.2 / 1.0 %, amplitudes 1 / 0.5 / 0.3 / 0.25, 0.6 s, fs 44.1 and 48 kHz.
  - The "phone" variant adds a finger click transient, 60/120 Hz hum, the phone's 120 Hz high-pass and 16-bit quantisation.
  - White noise is added at SNR 40/20/10/0 dB, with 10 seeds per cell (320 runs).
- **Method A (scipy/numpy only):**
  - Zero-padded FFT, with about 3 Hz smoothing of the power spectrum.
  - Peaks with prominence ≥ 10 dB, ranked by prominence. Half-power width ≥ 6 Hz rejects noise spikes; peaks must be ≥ 8 % apart.
  - ζ from the half-power width. A Hilbert-envelope decay ζ is also computed.
- **Method B:** sdypy-EMA `Model(frf=spectrum, lower=150, upper=3000, pol_order_high=60)`, then `get_poles('lscf')`, then `select_closest_poles(A's peaks, 50 Hz)`.
  The response spectrum is used as a pseudo-FRF because a phone tap has no force channel. Fit time is about 0.22 s.
- **Fix during the run:** Savitzky–Golay smoothing produced small negative power values, giving NaN after the sqrt. These are now clipped and the run was redone (the numbers below are from the clean rerun).

## Results (`results_summary.json`): f1 found (within 3 %) / median |f1 error| / median |ζ1 error|

| Signal | A (scipy) | B (sdypy-EMA) | Modes found, A / B |
|---|---|---|---|
| clean, 40 dB | 10/10, 0.02–0.03 %, 0.2–0.3 % | 10/10, 0.003 %, 0.1–0.2 % | all 4 (mode 4: 6–7/10) |
| phone, 40 dB | 10/10, 0.05 %, 0.3–0.4 % | 10/10, 0.01–0.02 %, 0.4–0.5 % | modes 1–3 |
| phone, 20 dB | 10/10, 0.20–0.24 %, 2.7–3.3 % (p90 6–10 %) | 10/10, 0.03–0.04 %, 1.1–1.5 % | modes 1–2 (3–4 ≈ 3–4/10 both) |
| phone, 10 dB | 10/10, 0.38 %, 8–13 % (p90 15–21 %) | 10/10, 0.04–0.08 %, 5–9 % | f1 only (B: f2 1–5/10) |
| phone, 0 dB | 2–6/10, 0.7–1.2 %, ~50 % | 8–9/10, 0.2–0.4 %, ~55 % | f1 marginal |

- Both sample rates behave the same. B had a few fit errors at 0 dB (1–2/10).
- The Hilbert-envelope ζ is good for mode 1 only. It is contaminated by beating with other modes, so use half-power instead.
- **I expect a real phone tap to land around 20–40 dB SNR at 357 Hz** (a blade flick in a quiet room, phone 5–10 cm away). This was not measured here; a real recording is the first step of the proposal. In that regime both methods are well inside requirements.

## What the requirement actually is
- **Flutter gate:** `MIN_F1_OVER_BPF = 1.2` (`flutter.py`). Lead 13's FEA puts Stock at f1/BPF 1.19–1.22 (357–365 Hz FEA, against a beam estimate of 400 Hz).
  To decide pass/fail you need f1 to about ±1–2 %. Method A at ≤0.4 % is plenty.
- **`FDM_E_K` calibration** (currently 0.70 in `stress.py`): f ∝ √E, so **E_k,new = E_k·(f_meas/f_pred)²**, and f error ×2 gives the E error. Method A then gives ≤0.8 % E error from the signal.
  The dominant error is **boundary condition and model:**
  - hand-held vs mounted on the motor (±5–10 % on f1, from lead 13's clamp caveat);
  - the prediction model used (beam vs FEA differs by 10 %).
  Calibrate against **the same model the gate uses**, with the impeller mounted on its motor and the hub held.
- **Damping:** not used anywhere in fansim, so there's no value in fitting it precisely.

## Relation to lead 13 (FEA)
- The tap test is the cheap physical check that lead 13's note asked for.
  - If a tapped Stock print shows f1 ≈ 357–365 Hz, the FEA is confirmed and the beam's 400 Hz is too stiff by 10 %.
  - If it shows ≈ 400 Hz, `FDM_E_K` = 0.70 is too low or the FEA root clamp is off.
- Either way it calibrates one number instead of trusting two models. Suggested order:
  1. tap-test 1–2 printed Stocks;
  2. per-material E_k from the beam model;
  3. compare with FEA.

## Licences
- sdypy-EMA **MIT** (I checked the LICENSE file in the wheel: "Copyright (c) 2018 - 2019 Ladisk"). pyuff MIT, tqdm MPL-2.0 AND MIT, matplotlib PSF, numpy/scipy BSD (pip-licenses).
- Method A needs only numpy and scipy, which fansim already has.

## Effort / gain
- **Effort S:** WAV loader + method A + "measured vs beam vs FEA" + suggested E_k. About 1 day with tests.
- Adding sdypy-EMA as an optional extra would be +½ day, and **not recommended now**.
- **Gain:** it turns the flutter gate from "trust the model" into "measured", for about 5 minutes of user effort per material.
