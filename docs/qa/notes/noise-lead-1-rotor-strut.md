# Noise lead #1: rotor–strut interaction tone + Tyler–Sofrin blade/strut-count rule

Source: `INTEGRATION_LEADS.md` #1 (Huang 2003; Huang & Wang 2005; Lu et al. 2007; Tyler & Sofrin 1962). QA note, 2026-10-09.

**Verdict: worth it / proposed (effort S for the count rule).** It is pure algebra and adds no compute. It also points to the
A12x25's real tonal weak spot: the frame struts, not the blades. Huang's full force model (effort M) can wait.

## What it is, in plain language
Each time a blade passes one of the four motor-holding struts behind it, it gets a small push. Added up over
all blades and struts, these pushes form spinning pressure patterns. Each pattern has a "lobe count" m = n·B − k·V
(B blades, V struts, n = which blade-pass harmonic, k = any whole number). A PC fan is tiny compared with the
wavelength (kR ≈ 0.33 at the A12x25's 300 Hz blade-pass tone at 2000 rpm). Because of that, only two kinds of pattern escape well:
- m = 0, a net push/pull along the axis;
- |m| = 1, a net sideways shake.

Patterns with |m| ≥ 2 mostly cancel themselves out. So the rule is simple: **pick B and V so that the low
harmonics can't make m = 0 or ±1.**

## Cheap prototype: the count table
Script: `handoff/2026-10-09_from-qa-2/scripts/tyler_sofrin.py`. Settings: 2000 rpm, R = 60 mm.

The dB figures are a rough cancellation estimate, (kR/2)^(|m|−1)/|m|!, relative to a radiating dipole. They are for **ranking only**.
Bold entries are the ones that radiate well. A large k means the tone needs a fine-grained (k·V-lobe) part of the strut's
disturbance, which is weaker. For example, the 9/4 tone at 4×BPF needs k = 9, a 36-lobe strut pattern.

| B blades | V struts | n=1 (BPF) | n=2 | n=3 | n=4 |
|---|---|---|---|---|---|
| 7 | 3 | **1** (k=2, side dipole) | **1** (k=5, side dipole) | **0** (k=7, axial dipole) | **1** (k=9, side dipole) |
| 7 | 4 | **1** (k=2, side dipole) | 2 (k=3, -18 dB) | **1** (k=5, side dipole) | **0** (k=7, axial dipole) |
| 7 | 5 | 2 (k=1, -24 dB) | **1** (k=3, side dipole) | **1** (k=4, side dipole) | 2 (k=6, -12 dB) |
| 7 | 6 | **1** (k=1, side dipole) | 2 (k=2, -18 dB) | 3 (k=3, -32 dB) | 2 (k=5, -12 dB) |
| 7 | 7 | **0** (k=1, axial dipole) | **0** (k=2, axial dipole) | **0** (k=3, axial dipole) | **0** (k=4, axial dipole) |
| 9 | 3 | **0** (k=3, axial dipole) | **0** (k=6, axial dipole) | **0** (k=9, axial dipole) | **0** (k=12, axial dipole) |
| 9 | 4 | **1** (k=2, side dipole) | 2 (k=4, -16 dB) | **1** (k=7, side dipole) | **0** (k=9, axial dipole) |
| 9 | 5 | **1** (k=2, side dipole) | 2 (k=4, -16 dB) | 2 (k=5, -12 dB) | **1** (k=7, side dipole) |
| 9 | 6 | 3 (k=1, -47 dB) | **0** (k=3, axial dipole) | 3 (k=4, -28 dB) | **0** (k=6, axial dipole) |
| 9 | 7 | 2 (k=1, -22 dB) | 3 (k=3, -35 dB) | **1** (k=4, side dipole) | **1** (k=5, side dipole) |
| 11 | 3 | **1** (k=4, side dipole) | **1** (k=7, side dipole) | **0** (k=11, axial dipole) | **1** (k=15, side dipole) |
| 11 | 4 | **1** (k=3, side dipole) | 2 (k=5, -14 dB) | **1** (k=8, side dipole) | **0** (k=11, axial dipole) |
| 11 | 5 | **1** (k=2, side dipole) | 2 (k=4, -14 dB) | 2 (k=7, -10 dB) | **1** (k=9, side dipole) |
| 11 | 6 | **1** (k=2, side dipole) | 2 (k=4, -14 dB) | 3 (k=5, -24 dB) | 2 (k=7, -8 dB) |
| 11 | 7 | 3 (k=2, -43 dB) | **1** (k=3, side dipole) | 2 (k=5, -10 dB) | 2 (k=6, -8 dB) |

## What it changes for the A12x25 (9 blades, 4 struts)
- **At the blade-pass tone itself (300 Hz at 2000 rpm), 9/4 lets a sideways-shake pattern through** (m = 9 − 2·4 = 1).
  The same happens at 3×BPF (m = 27 − 7·4 = −1). 2×BPF is partly self-cancelling (|m| = 2). So with 4 struts the
  blade-pass tone does reach the listener. This is true for any odd blade count (7, 9, 11) with 4 struts.
- 9/4 is still far better than the obvious bad pairs:
  - 9 blades with 3 struts, or 8 blades with 4 struts, give m = 0 at **every** harmonic. That is the loudest possible
    choice. Never let the optimizer pick B as a multiple of V.
- The quietest-looking options for 9 blades are 6 struts (|m| = 3 at BPF, but m = 0 at 2×BPF) and 7 struts (|m| = 2 at BPF,
  |m| = 3 at 2×BPF). Fewer, thinner, or further-back struts matter more than the exact count. Huang found that the
  tonal power tracks the number of struts more than the number of blades. The frame here has a very small rotor–strut
  axial gap (`STRUT_AFTER_MRF_MM = 0.5` mm behind the rotor zone in `fansim/cfd/frame.py`), so the strut "kick" is large.
- **Uneven blade spacing (the current noise feature) interacts with this.** `tonal.py` scores spacing from the rotor's array factor
  A(s) alone. With V struts, a shaft order s only radiates well if s mod V ∈ {0, 1, V−1}. So a spacing pattern
  that moves energy into, say, s = 8 or 12 looks "spread out" in today's metric, but it lands straight on an m = 0 strut mode. The
  fix is to weight A(s) by that rule.

## Licence / patents
- The math comes from papers, and we implement it ourselves. No code or figures are copied. The JASA papers are paywalled except the HKU
  open PDF of Lu et al. 2007.
- Intel US7300244B2 (irregular blades *and* struts) and Comair Rotron US4089618A have both **expired**, according to the lead's Google Patents
  check. No live patent was found on choosing blade/strut counts. That search was not exhaustive, and this is not legal advice.

## Effort and code touch points
- **S (about 1 day):**
  - `fansim/acoustics/tonal.py`: add `strut_count: int | None` to `blade_passing_modes` / `tonal_peak_ratio`, and weight
    shaft order s by the radiating rule above (default `None` = today's behaviour). Export it from `fansim/acoustics/__init__.py`.
  - Add a pure-function `tyler_sofrin_modes(B, V, n_max)` with unit tests from the table above.
  - `fansim/cfd/frame.py`: the four struts are hard-coded (`for ang in (0, 90, 180, 270)`), and the docstring says "Four radial struts". Expose `n_struts`
    (and `STRUT_THICK_MM`/axial gap) as parameters if the strut count is to become a design input. Until then, 4 is a constant the metric can import.
  - Optimizer: add a cheap guard or penalty rejecting B ≡ 0 (mod V). This is `fansim/optimize/search_space.py` / `study.py`, next to `with_spacing`.
  - Cockpit Assess readout: `fansim/cockpit/fan_viz.py:393` already calls `peak_tone_reduction_db`. Pass the strut count.
- **M:** Huang's force-component model (strut wake/potential field amplitude vs axial gap and strut width) to rank strut designs, not just counts.
- **No CFD needed for S.** Validating it would need the FluidX3D control-volume force trace split by strut, which is out of scope here.

## Caveats
- The dB numbers are order-of-magnitude, compact-source estimates. They don't include the strut's actual disturbance strength (which falls with k)
  or the casing/duct.
- At higher rpm, kR grows and |m| = 2 modes start to radiate too.
- This ranks configurations. It does **not** predict dBA.
