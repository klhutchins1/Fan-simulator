# Tap-test f1 measurement → FDM_E_K calibration (lead #16, proposed 2026-10-21)

**Status:** Proposal only. Research prototype is in `research/proto/lead16/` (not in the repo). Awaiting a hand-off decision.
**Scope:** a scipy-only WAV → f1 analysis, plus a "measured vs beam vs FEA" readout and a suggested per-material `FDM_E_K`. **sdypy-EMA is not added.**

## Problem

The flutter gate (`MIN_F1_OVER_BPF = 1.2`) rests on a beam f1 that uses `FDM_E_K = 0.70`. Lead 13's FEA puts the Stock blade at 1.19–1.22, right on the gate,
and the beam and FEA disagree by 10 %. There's no measured number to settle it. Roadmap §19.18 asks for "shell FEA or a printed-blade tap test".

## Approach

1. **`fansim/validation/tap_test.py`** (numpy/scipy only):
   - load a mono WAV (44.1/48 kHz);
   - skip the click transient;
   - zero-padded FFT with ~3 Hz power smoothing;
   - peaks with prominence ≥ 10 dB, half-power width ≥ 6 Hz and ≥ 8 % separation;
   - report f1..f3 and the half-power ζ as information only.
   - Multiple taps → median and spread.
2. **Readout:** measured f1 against `first_bending_hz` (beam) and, when available, FEA (lead 13). Also shows the f1/BPF margin at the design rpm.
3. **Calibration hint:** E_k,suggested = FDM_E_K·(f1_meas/f1_beam)², per material.
   - Print it; don't apply it automatically.
   - Store it with the §5.1 measurement ingest (`validation/measurements/`) so it is traceable.
4. **Protocol text:**
   - impeller mounted on its motor, frame clamped;
   - flick the blade tip;
   - phone 5–10 cm away in a quiet room;
   - 5 taps per blade, 2 blades.

## Non-goals

- Damping-based flutter criteria. fansim doesn't use ζ.
- sdypy-EMA / LSCF. It is 3–10× more precise on f, but that's unneeded: the signal error is already ≤0.4 % against a ±5–10 % mounting effect. It also adds matplotlib/pyuff/tqdm.
  Revisit as an optional extra only if impact-hammer FRFs are ever ingested.
- Automatic change of `FDM_E_K`.

## Verification

- Synthetic tests (from the proto): 4 modes at 357/1009/1777/2024 Hz with phone artefacts (click, hum, high-pass, 16-bit).
  - At 20 dB SNR, f1 must be within 0.5 % in 10/10 seeds, and f2 found.
  - At 10 dB, f1 must be within 1 %.
- One real recording of a printed Stock before merge, as the first data point. Expected 357–400 Hz.
- **Effort: S** (about 1 day).
