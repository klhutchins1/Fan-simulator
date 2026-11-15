# Lead #30: Amiet / Sears gust-response noise via `amiet_tools` (BSD-3)

Date: 2026-11-09 (America/Denver). Prereg: `prereg/research-lead30` @ `067eb89` (before any prototype).
Clone: `/workspace/fansim/repo-lead30` @ master `83681c2`. No CFD/Docker/Assess/Sweep/Optimize.
No commits in the clone; nothing on Kimball's PC. Separate from the #23–29 zip (untouched).

## Verdict
**worth-it/proposed** (S for strut-tone ranking; broadband LE term is M and parked on a gust/turbulence input).

Thin Sears/Amiet ranking proxy for strut tones vs gap/skew is sensible and **stable under ±2× assumed gust**. Absolute levels still need a wake model fansim lacks. Do not vendor the whole `amiet_tools` tree yet — use it as the BSD-3 reference; ship a thin in-tree helper.

## Licence / patents
- **amiet_tools:** BSD-3-Clause re-checked (`LICENSE.txt`, Copyright 2020 Fabio Casagrande Hirono). Deps numpy + scipy only. Last push ~2022 (stable/unmaintained).
- **Amiet 1975 JSV:** paywalled — implement maths, do not copy figures.
- **Patents (sanity):** Amiet/Sears is a classical analytical prediction method (1941/1975 academic literature). Quick search found papers/implementations, not a live patent claiming the *method*. No geometry is claimed by adopting the maths. Not legal advice. (Distinct from Active US8333559B2 tip-lean OGV geometry in lead #25.)

## Prototype
`research/proto/lead30/strut_tone_amiet.py` (numpy/scipy via repo venv):
- Sears |S(k)| × exponential wake deficit × skew sinc coherence → relative 20·log₁₀(lift/ref).
- **Gap sweep (skew 0):** 0.5→8 mm → 0 … −16.3 dB re baseline (monotone quieter).
- **Skew sweep (gap 1 mm):** 0°→60° → −1.1 … −32 dB (skew strongly cuts coherent tone — aligns with Ito/lead 22 qualitative).
- **Robustness:** quietest-first ranking of five (gap,skew) configs **identical** at w₀ = 0.025 / 0.05 / 0.10.
- Prereg criterion (c) **PASS**.

`amiet_tools.delta_p` is also ∝ gust amplitude `w0`, so the same linearity/robustness holds if the full library is used later.

## Fit to the app
| Piece | Today | Lead #30 |
|---|---|---|
| `acoustics/tonal.py` | blade-spacing array factor only | needs an **amplitude** for strut interaction — this lead |
| `cfd/frame.py` | depth/thick; skew patch from lead 22 not on master yet | gap / chord / skew get a noise score |
| `acoustics/proxies.py` | Proudman/Curle RANS | LE broadband beside BPM (lead 3) needs a turbulence spectrum — **parked** |

## Patch
`docs/qa/patches/amiet-strut-tone.patch` — adds `fansim/acoustics/strut_gust.py`, `tests/test_strut_gust.py` (4 passed), exports `strut_tone_level_db`. `git apply --check` clean on 83681c2. **Not applied.**

## Effort / gain
- **Strut-tone ranking:** S (~1 d) — done as patch; wire to frame params / lead-1 tone report when skew lands.
- **LE broadband:** M — needs inlet turbulence intensity + length scale (or CFD probe); revisit with lead 3 BPM.
- **Gust input:** document stub (`w0_over_U`, `wake_width_mm`); calibrate later from a wake probe or print+mic.

## Revisit if
- A wake-deficit / tip-vortex estimator lands, or
- BPM (lead 3) is adopted and wants a matching LE term from `amiet_tools` spectra.
