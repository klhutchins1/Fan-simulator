<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

---
name: fan-sim-uneven-spacing
description: Future feature — uneven (non-symmetric) blade spacing to spread the tonal noise
metadata:
  node_type: memory
  type: project
  originSessionId: 9facc2be-ff12-44e2-9ede-0cced25b4756
---

USER IDEA (2026-08-27), flagged as a FUTURE feature (not to build now): **uneven / non-symmetric
blade spacing** instead of equally-spaced blades. User note: "can still be balanced if created
properly, might help with blade volume."

**Why it's good — attacks the exact tradeoff [[fan-sim-status]] design-rules found:** solidity/
overlap buys static pressure but drives the blade-pass TONE up (sol_tip -> noise +0.70). Equal
spacing concentrates all acoustic energy at BPF (=N*rpm/60) + harmonics = one strong tone. UNEVEN
spacing smears that spike into lower sidebands -> peak tone drops (tones carry a psychoacoustic
penalty), WITHOUT giving up solidity. So it can keep the high-solidity pressure and defuse its
tonal penalty — a real technique (automotive cooling fans, drone/heli rotors).

**Balance (user's concern — SOLVED IN CODE 2026-08-27):** identical blades stay statically balanced
iff Σ e^{i*theta_k} = 0. **`fansim/structural/balance.py` is BUILT + tested (19 tests):**
static_unbalance/is_balanced/required_counterweight/residual_force(=U*omega^2)/couple_unbalance, and
**`balanced_uneven_spacing(n, spread, rng)` GENERATES uneven-but-balanced patterns** (even N via
diametric pairing; odd N via minimal-norm Newton projection of the residual to 0). Verified: 7-blade
spread=0.5 -> gaps 42-60deg (vs equal 51.4) with unbalance ~1e-16. So the spacing-generation +
balance half is DONE. REMAINING for the feature: (1) per-blade angle DOF in fansim/geometry/blade.py
(pattern blades at an angle LIST not fixed 360/N); (2) a PEAK-TONE metric in fansim/acoustics (uneven
spacing lowers the peak, not the band level); (3) wire the spacing pattern into search_space. Avoid
1P couple: couple_unbalance() checks it for axially-staggered designs.

**FEATURE ~DONE COMPUTE-FREE (2026-08-27). (1) DONE: BladeParams.blade_angles_deg (None=equal 360/N;
list=custom); build_impeller uses it; geometry.set_uneven_spacing(params, spread, rng) sets a
balanced pattern (local import of balance to avoid cycle). Uneven impeller builds WATERTIGHT (verified
7-blade, 1 body). (2) DONE: fansim/acoustics/tonal.py — blade_passing_modes (array factor
A(m)=|Σ e^{-imθ}|), peak_tone_amplitude, tonal_peak_ratio (1.0=equal/concentrated, <1=spread),
peak_tone_reduction_db. Equal spacing -> A(N)=N spike; uneven spreads it. COMPUTE-FREE (pure algebra).
(3) DONE: WIRED into search_space — suggest_params(with_spacing=True) samples spacing_spread(0-0.6)
+ spacing_seed; _apply_spacing() sets a balanced pattern; blade_from_flat regenerates it
DETERMINISTICALLY (same spread+seed -> same angles, verified). Threaded through run_study(with_spacing)
+ run_optimization.py --spacing. set_uneven_spacing now enforces min_gap_deg (retry, fallback to
equal) so no collisions. 11 tonal tests. TOOL: scripts/design_uneven_spacing.py
searches balanced patterns (min-gap constraint to avoid collisions) minimizing tonal peak ->
build/uneven_spacing_n7.{json,png,stl}. RESULT: 7-blade, min-gap 30deg -> gaps 30-76deg, unbalance
~1e-16, -4.7 dB PEAK-TONE reduction vs equal, watertight STL. 10 tests (test_tonal.py). Remaining:
wire spacing into search (compute-free) + LBM confirm the dB benefit (compute-gated). 92 tests pass.**

**"Blade volume":** unequal gaps let a wide/overlapping blade fit sectors where equal spacing would
collide -> pack more blade area/pressure; decouples "how much blade" from "must be symmetric".

**Fits what's built:** CFD needs NO change (we mesh the FULL impeller, not a periodic passage).
Noise tool is READY — the CV-dipole spectrum (scripts/fan_noise_cv.py / evaluate_noise.py) would
directly show BPF splitting into sidebands; add a PEAK-TONE metric (max tone across BPF sidebands)
as the noise objective since uneven spacing lowers the peak, not the band level. Geometry work:
`fansim/geometry/blade.py` patterns blades at fixed 360/N today -> needs a per-blade angle list
(param it as a few offset DOFs or Fourier coeffs). Search: add the spacing pattern to search_space.

**Caveats:** lowers tonal PEAK not total energy; doesn't touch broadband (coarse-grid-uncertain
anyway); balance constraint trims design freedom; watch 1P imbalance.
