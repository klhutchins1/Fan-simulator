# Compact FW-H loading kernel (stage 1)

**Date:** 2026-09-04  
**Status:** accepted  
**Approach:** Add `fansim/acoustics/fwh.py`: Farassat 1A **loading** (far-field 1/r, retarded time) on a compact force **or** a discrete panel set. Opt-in on `scripts/evaluate_noise.py --fwh`. Default stays today’s Curle 1/r² band-limited ranking. Not a permeable LBM surface dump, not OpenFOAM DES, not calibrated dB(A), not an NSGA objective.  
**Roadmap:** §1.4 stage 1. Bibliography already points FW-H at a future `fwh.py`. The GPU pipeline today is compact Curle from a control-volume force.

## Plain language

The noise we can already compute is a **compact Curle dipole** from the LBM control-volume force, using `p' = (r̂ · Ḟ) / (4π c₀ r²)`. That 1/r² kernel is the near-field / incompressible form. It ranks designs when the band-limit is fixed; it is **not** Ffowcs Williams–Hawkings, and it is **not** 22.6 dB(A).

Stage 1 puts the **far-field loading term** in one module: `p' = (r̂ · Ḟ) / (4π c₀² r)` at retarded time `t − r/c₀`, plus a small **panel sum** so a later surface dump can call the same kernel. Default `evaluate_noise` stays Curle. `--fwh` re-reduces an existing CSV (or a synthetic panel table). Do not claim the published A12x25 dB(A). Do not change NSGA.

A compact source at the origin: retarded time is a pure delay and **does not change SPL**. The new physics that *can* change a spectrum is several panels at different `r`. That is why the kernel is a panel sum, not a rename of `dipole_pressure`.

## Problem

```text
fansim/acoustics/farfield.py::dipole_pressure
  p' = (r_hat · dF/dt) / (4 π c0 r²)     # compact Curle, 1/r²
evaluate_noise.py                        # LBM CV force → that kernel → noise_dba_band
fansim/acoustics/fwh.py                  # missing
```

FluidX3D does not dump a permeable FW-H surface. Blade `object_force` NaNs on the rotating solid. Absolute broadband is still 1 mm-grid-limited.

## Goal

1. **`fansim/acoustics/fwh.py`**

```text
C0_AIR = 343.0   # reuse farfield.C0_AIR; do not fork A-weighting
```

- `loading_pressure_compact(F, dt, *, r_hat=(0,0,1), r_obs=1.0, c0=C0_AIR) -> p[t]`
  Far-field compact loading: `p = (r_hat · Ḟ) / (4 π c0² r_obs)`, then delay by `r_obs/c0` (pad / roll; document that SPL is unchanged by the delay).
- `loading_pressure_panels(t, panels) -> p[t]`
  Each panel: `r0` (m), `area` unused this cycle, `n_hat`, `f[t,3]` (force on fluid, N). Observer at `x_obs=(0,0,1)` m unless passed. For panel `i`: `r = |x_obs − r0|`, `r_hat = (x_obs − r0)/r`, `p_i(t) = (r_hat · Ḟ_i(t_ret)) / (4 π c0² r)` with linear interpolation to `t_ret = t − r/c0`. Sum panels. Skip a panel if `r < 1e-6`.
- `noise_from_compact_force(t, F, **kw) -> dict`
  Same keys as `noise_from_cv_force` (`noise_dba_band`, `noise_dba_full`, `bpf_tone_db`, `peak_tone_db`, `thrust_n`, `cutoff_hz`, `samples`) plus `"analogy": "fwh_compact"`. Reuse `farfield.dba_from_pressure` / `tone_level_db` / `peak_tone_over_harmonics` / `blade_pass_frequency`. Default cutoff **2500 Hz**. Thrust = mean `F_z`.

Do **not** duplicate A-weighting. Do **not** change `dipole_pressure`.

2. **Collapse** — one panel at the origin with force `F(t)` must match `loading_pressure_compact` within 1e-6 * rms(p).

3. **`scripts/evaluate_noise.py --fwh`** (store_true, default off). After the CSV exists (run LBM as today, or `--csv path` if that flag already exists; if not, add `--csv` to skip the exe when a file is given):

```text
default  → noise_from_cv_force        stamp analogy omitted / "curle"
--fwh    → F from force_from_cv, then noise_from_compact_force
           stamp "analogy": "fwh_compact"
```

No `★`. Do not run LBM in unit tests. Do not change `evaluate_candidate` / NSGA.

4. **Bibliography** — FW-H entry `→ code (future)` becomes `→ code (stage 1): fansim/acoustics/fwh.py` (compact / panel loading). Permeable surface stays future.

## Honesty

This is the **loading far-field term** for a compact (or few-panel) force, not a permeable FW-H surface around a rotating rotor. Thickness noise, quadrupole, Doppler from moving blades, and 22.6 dB(A) are out. Switching 1/r² → 1/r **shifts absolute level by tens of dB**; do not mix `--fwh` numbers with catalog Curle rows. Relative ranking inside one analogy is still only as good as the 1 mm LBM force.

## Tests (no GPU, no Docker)

- Compact 1/r: doubling `r_obs` drops `dba_from_pressure` by **6 dB** (±0.3).
- Compact vs one origin panel: pressures match (rms relative error < 1e-5).
- Two panels at `z=±0.05 m` with equal `F_z(t)`: on-axis `p` is finite; not required to equal 2× compact (different `r`).
- Synthetic BPF force (same recipe as `test_farfield.py`): `noise_from_compact_force` has finite `noise_dba_band` and `bpf_tone_db` above an off-tone.
- `--fwh` in `evaluate_noise.py`; no `★`.
- Existing `tests/test_farfield.py` stays green (`dipole_pressure` unchanged).

## Non-goals

- FluidX3D `setup.cpp` permeable surface / probe sphere dump
- OpenFOAM DES + `libAcousticAnalogy` / `libffowcsWilliamsHawkings`
- Replacing NSGA `loading` / Proudman proxies
- Claiming 22.6 dB(A) or mixing analogies in the catalog
- Prop FW-H
- Thickness (volume) term
- Cockpit control
