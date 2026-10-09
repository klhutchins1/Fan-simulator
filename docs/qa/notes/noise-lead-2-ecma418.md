# Noise lead #2: ECMA-418-1 tonality metrics (TNR / PR) + MoSQITo

Source: `INTEGRATION_LEADS.md` #2. QA note, 2026-10-09.

**Verdict: worth it / proposed (effort S), as a cockpit Assess readout. Not yet an optimizer objective.** It gives the app a
standard, citable answer to "will people hear a whine?". However, our noise signals are too short and too low-pass for the
standard's method, and the two metrics disagreed strongly in my quick test. Validate it first, then think about optimizing on it.

## What it is, in plain language
ECMA-418-1 (free, and the same method as ECMA-74 Annex D) asks whether a tone sticks out of the background noise
around it. It gives two numbers:
- **TNR** (tone-to-noise ratio): the tone vs the noise in the band of hearing around it;
- **PR** (prominence ratio): that band vs its neighbours.

Each has an official "prominent" threshold. Below 1 kHz these are about TNR ≥ 8 + 8.33·log10(1000/f) and
PR ≥ 9 + 10·log10(1000/f) dB. At the A12x25's 300 Hz blade-pass tone (2000 rpm) that is about 12.4 dB TNR and 14.2 dB PR.
Today's `tonal_peak_ratio` is a homemade, relative "how concentrated is the tone" number. ECMA gives an absolute yes/no.

## Licence check
- `mosqito` 1.2.1 (PyPI, released 2024-04-22) is classified **Apache-2.0**, which is fine for the MIT release as a dependency or vendored with its NOTICE.
  Wheel sha256: `c5370a729b12cb986ff39c71499e51201551b445623b5ca86aed66539d3cfe83`.
- Declared dependencies are numpy, scipy and `pyuff` (2.5.8, MIT).
- **Undeclared:** importing `mosqito.sq_metrics` also imports **matplotlib**, which fails without it.
  matplotlib has a PSF-style licence, which is OK, but it is a heavy hidden dependency. Pin `mosqito==1.2.1` and list matplotlib explicitly,
  or port the about 200 lines of TNR/PR ourselves. The standard is free, so a port is legally clean.
- The upstream repo has had little activity since 2024, so pin the version (as the lead says).
- No patents found (these are metrics, not fan geometry).

## Cheap prototype (done, outside the project venv)
Script: `handoff/2026-10-09_from-qa-2/scripts/ecma_tnr_demo.py`, run in a throwaway venv.

Signal: 2 s of white noise at 48 kHz plus a 300 Hz tone at three levels. Using `tnr_ecma_st` / `pr_ecma_st`:

| tone amplitude (noise rms 0.02) | TNR | PR |
|---|---|---|
| 0 | no tone | no tone |
| 0.005 | no tone | no tone |
| 0.02 | 2.9 dB at 300.5 Hz, *not* prominent | **19.9 dB at 300 Hz, prominent** |

The PR result is plausible. The TNR result is suspiciously low for a tone of that size in a roughly 100 Hz-wide band. It could be the
library's tone-bandwidth estimate, or my input set-up, so **check it against ECMA's own worked examples before trusting it**.

## What it changes for the A12x25
- The blade-pass tone sits at 300 Hz (at 2000 rpm). At that frequency the "prominent" bar is about 12–14 dB, much higher than at 1–2 kHz.
  So an ECMA check could tell us whether uneven spacing actually takes the tone *below audibility*, not just "x dB lower than equal spacing".
- **Signal-length problem:** ECMA's TNR/PR needs a fine frequency resolution, about 1 Hz bins over seconds of audio. The FluidX3D
  control-volume traces cover a few revolutions and are low-passed at 2.5 kHz. That is not enough on their own. The realistic input is a
  **synthetic spectrum**: tones from the tonal/strut model plus a broadband floor (lead #3 BPM). MoSQITo has spectrum-input variants
  (`*_freq`) for this.

## Effort and code touch points (S)
- New module `fansim/acoustics/tonality.py`: thin wrappers `tnr_prominence(spectrum)` / `pr_prominence(spectrum)`, with
  an import guard so MoSQITo stays optional (like the `neuralfoil` backend). Export from `fansim/acoustics/__init__.py` next to
  `a_weighting_db` (`farfield.py`).
- Cockpit Assess readout next to `peak_tone_reduction_db` (`fansim/cockpit/fan_viz.py:393`).
- `pyproject.toml`: an optional extra `acoustics = ["mosqito==1.2.1", "matplotlib"]`.
- Tests: ECMA worked examples, and pure tone in white noise → PR/TNR within ±1 dB of the analytic value.
- An optimizer objective comes later, once a synthetic-spectrum pipeline (tones from lead #1 + broadband from lead #3) exists.
