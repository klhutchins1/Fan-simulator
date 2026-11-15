# Lead 21: ECMA-74 22nd ed. (Dec 2025): home sound-power maths

Date: 2026-11-04 (MST). Status: **worth-it/proposed**, but small and parked until a printed fan and a measurement mic exist.
Prototype: `research/proto/lead21/ecma74_sketch.py` and `out.json`. This is our own code; no ECMA text was copied. The PDF is kept locally for reference only.

## What the standard actually gives us
- **No air-moving-device section.** Clause C.1 sends fans as components to ISO 10302-1/-2, which are paid. The lead's hope of a small ISO 10302-like annex is not met.
- **The maths is not in ECMA-74 itself.** Clause 7 (free field over a reflecting plane) says to follow ISO 3744 for microphone positions, K1/K2 and the LW calculation. Clause 6 follows ISO 3741/3745 for reverberation rooms. The write-up's claim that "ISO 3744 is not needed" is wrong, although the formulas themselves are standard textbook acoustics.
- **What ECMA-74 adds on top:**
  - K2 ≤ 2 dB;
  - 16 kHz is excluded from the A-weighted level;
  - reference conditions of 23 °C and 50 % RH;
  - Table B.1, a fixed 10-position hemisphere array for tonal sources (coordinates as x/r, y/r, z/r; numeric facts used in code, not text);
  - B.1 allows radius 0.5–1 m for small, quiet equipment if r ≥ 2× the source size, with a low-frequency limit of about 172 Hz at 0.5 m;
  - A-weighted reproducibility of about 1.5 dB (Table 9).
- **Licence:** the Ecma copyright licence explicitly allows "implementing … the functionality" in conformant products. It is not an NC/ND barrier to implementation; just don't reproduce the text.

## The sketch (our implementation)
- **Energy average:** Lp̄ = 10 lg(mean of 10^(0.1·Lpᵢ)).
- **Background correction:** K1 = −10 lg(1 − 10^(−0.1ΔL)), valid only for ΔL ≥ 6 dB.
- **Sound power:** LWA = Lp̄ − K1 − K2 + 10 lg(2πr²/1 m²).
- **Synthetic check:** a source of LW 33.6 dB(A) on the 10-point array, with ±1 dB scatter. "USB mic" means a measurement mic with a self-noise floor of about 18 dB(A). The self-noise figures for both mic types are typical data-sheet values and were not checked.

| case | Lp̄ | bg | ΔL | LWA result |
|---|---|---|---|---|
| lab, bg 10 dB(A), r 1 m | 26.1 | 10.0 | 16.0 | 33.9 |
| quiet night room bg 20, USB mic, r 0.5 m | 32.4 | 22.2 | 10.2 | 33.9 |
| room bg 25, USB mic, r 0.5 m | 32.9 | 25.9 | 7.1 | 34.0 |
| bg 20, **phone MEMS mic (floor ~30)**, r 0.5 m | 34.4 | 30.7 | 3.7 | **invalid** (≤ 36.3 upper bound) |
| bg 20, USB mic, **r 1 m** | 27.5 | 22.2 | 5.3 | **invalid** (≤ 35.5) |
| case 2 with +2 dB mic calibration bias | 34.4 | 24.2 | 10.2 | 35.9 |

## What this means for Fansim
- A Noctua-class fan, about 33.6 dB sound power, can only be measured at home under all of these conditions:
  - r = 0.5 m;
  - a quiet night room;
  - a real measurement mic. A phone mic's self-noise alone breaks the 6 dB rule.
- Accuracy is about ±1.5 dB at best, plus the mic calibration.
- The lead-12 target of 33.6 dB came from 22.6 dB(A) + 10 lg 4π, which assumes a 1 m free-field sphere. Over a reflecting table (hemisphere) the same reading would be 22.6 + 8.0 = 30.6 dB. That 3 dB ambiguity is about the size of the whole calibration we want. Noctua does not publish its method, so treat 22.6 dB(A) as ±3 dB.
- **Where it fits:**
  - a small `fansim/acoustics/sound_power.py`: energy mean, K1 with a validity flag, hemisphere LW, and the B.1 array;
  - a "mic positions" helper for the §5.1 measurement recorder;
  - one calibration offset per proxy (`tip_loading_swl_db`, `loading_noise_proxy`), replacing the lead-12 hand offsets.
- No patch now: there is nothing to calibrate until a print and a mic exist.

## Effort
S: about 0.5 day for the module plus tests (the maths above). Calibrating the proxies needs measurements, which is a hardware dependency.
