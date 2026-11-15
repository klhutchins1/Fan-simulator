# FluidX3D (GPU LBM) — build + status

The GPU transient tier: FluidX3D is a free GPU lattice-Boltzmann CFD code — the right tool for
the two things steady OpenFOAM RANS can't do (shut-off pressure near stall, and **noise** via
FW-H), and the only thing that uses the RTX 4070 Ti.

## Built & verified (2026-08-27)
- Repo cloned to `<local FluidX3D path>` (sibling of this project).
- Toolchain: **msys2 ucrt64 g++ 15.2.0**, OpenCL via the NVIDIA driver (`C:\Windows\System32\OpenCL.dll`).
  FluidX3D bundles its own OpenCL headers, so no SDK needed.
- FluidX3D ships only an MSVC `.lib` + Linux `.so`; **mingw-g++ links the driver DLL directly** instead.

### Build command
```bash
export PATH="/c/msys64/ucrt64/bin:$PATH"
cd "<local FluidX3D path>" && mkdir -p bin
g++ src/*.cpp -o bin/FluidX3D.exe -std=c++17 -pthread -O -Wno-comment \
    -I./src/OpenCL/include /c/Windows/System32/OpenCL.dll
```
Run (needs ucrt64 DLLs on PATH):
```bash
export PATH="/c/msys64/ucrt64/bin:$PATH"; ./bin/FluidX3D.exe
```
Default config = `#define BENCHMARK` in `src/defines.hpp` (headless, no graphics window).

### Result
- Device: NVIDIA GeForce RTX 4070 Ti, 12 GB VRAM; OpenCL C compiled OK.
- **Peak 4657 MLUPs/s**, 99% GPU utilization. Working.

## Rotating-fan LBM WORKS (2026-08-27)
Custom `src/setup.cpp` (backup: `setup.cpp.orig`) imports `build/a12x25_real_capped.stl` as a
**rotating solid boundary** and spins it in a duct. Extensions enabled in `defines.hpp`:
`MOVING_BOUNDARIES`, `EQUILIBRIUM_BOUNDARIES`, `SUBGRID`, `FP16S` (BENCHMARK off).

- **Moving-boundary recipe that works:** each step-block, `fan->rotate(Rz(omega*dt))` →
  `lbm.voxelize_mesh_on_device(fan, TYPE_S, center, 0, (0,0,omega))` → `lbm.run(dt)`, with
  `dt=4` (tip moves <1 cell/block). `read_stl(path, lbm.size(), center, I, 2*R)` scales the
  110 mm impeller to ~110 cells (1 cell ≈ 1 mm).
- **Domain** 120×120×300 cells (4.3M), cylindrical duct wall + small axial inflow inlet
  (TYPE_E, u_z=0.02) + fixed-density outlet (TYPE_E). `set_m_kg_s(R=55, u_tip=0.075, …)`.
- **Performance:** ~6300 MLUPs/s, ~1460 steps/s, GPU 99%, 2.5 GB VRAM. 12000 steps in ~15 s.
  **Stable** (no divergence), throughflow reached steady state.
- **First result: ~27 CFM, flat across steps 2k–12k (26.8→27.2, <2% drift).** This is a
  *loaded, over-viscous* operating point (Re=8000 for LBM stability; confined duct with
  back-pressure) — **NOT** free-delivery, so not yet directly comparable to the validated
  ~60 CFM. Proves the transient GPU tier runs, is stable, and pumps; quantitative match is
  the next tuning step. Velocity field exported: `bin/export/u-000012000.vtk` (51 MB).

## Free-delivery cross-check + the resolution finding (2026-08-27)
Switched to **free-air BCs** (fan + short shroud mid-domain, all 6 faces open equilibrium at
ambient rho=1, no back-pressure), flipped omega so the fan pumps +z, widened to 180×180×360
(11.6M cells) so the open faces sit far from the fan. Free-delivery result settles at
**~35–37 CFM (±10% unsteady), positive, stable** — right direction and order, but **~40% under**
the resolution-resolved OpenFOAM/published **60.1 CFM**.

**Bracket test falsified the tip-clearance hypothesis:** ran 1-cell clearance (r_in=56) vs
**sealed tip** (r_in=55, 0 clearance) — both settle to the *same* ~35–36 CFM. So the shortfall
is **not** tip leakage. The cause is **coarse blade resolution**: at 1 cell ≈ 1 mm the ~2 mm-thick
blade is only ~2 cells thick, so the voxelized blade does less aerodynamic work than the 0.25 mm
OpenFOAM mesh. Closing it needs ~0.5 mm cells → ~8× cells (~90M) → ~50 GB VRAM, beyond the
4070 Ti's 12 GB. **Conclusion: the LBM at feasible resolution is not the tool for absolute FLOW
accuracy — OpenFOAM already nails that (+2%). The LBM's unique value is TRANSIENT physics
(shut-off pressure, noise via FW-H) that steady RANS cannot give.** Pivot the GPU tier there.

## SHUT-OFF PRESSURE — validated (2026-08-27)
Fan in a duct, intake open to ambient, discharge into a **sealed** capped chamber (no outlet).
The chamber pressurizes until the fan stalls (net flow → 0); Δρ across the fan → static rise via
`units.si_p((rho_disch-rho_intake)/3)`. 48000 steps: an early transient **overshoot** (~29–32 Pa
while the chamber fills) **settles** by step ~28k to **~20–23 Pa (mean ~21 Pa)** at residual flow
~0.0 CFM (true dead-head). **vs published 22.9 Pa = −8%; steady RANS gave ~13 Pa = −43%.** The
transient GPU tier captures the near-stall dead-head pressure steady RANS fundamentally can't.
Must run long + read the *settled* value, not the fill transient. `rho.write_device_to_vtk()`.

## NOISE tier — pipeline built; tonal + relative work, absolute far-field blocked (2026-08-27)
Goal: dB(A) as the 3rd optimizer objective. Two routes tried:

**(a) Curle compact-dipole from blade force — BLOCKED.** Plan was `object_force(TYPE_S)` → log F(t)
→ analytic far-field dipole (rigorous: BPF 233 Hz, wavelength 1.47 m ≫ 0.11 m fan = compact). But
`update_force_field()`/`object_force()` return **NaN on the re-voxelized MOVING boundary** (the flow
is fine — only the momentum-exchange force kernel NaNs). FluidX3D ships **no example of force on a
rotating/re-voxelized object** (all force examples are static: sphere-drag, Ahmed body, both
`TYPE_S|TYPE_X`). This is a real FluidX3D limitation, not a quick fix.

**(b) Fixed pressure probes (numerical mics) — WORKS, but near-field only.** 6 probes sample
p=(ρ−1)·cs²·si_p at fixed fluid points over ~12 revs. `scripts/fan_noise_probes.py` → Welch PSD,
A-weighting, BPF tone + harmonics, spectrum plot (`build/fan_noise_probe_spectrum.png`). **Clean
result: BPF 233 Hz + harmonics resolved, strongest at the tip-radius probe (physical); tonal
content + spectrum shape are robust.** BUT the domain is only ~0.12 m and the acoustic near-field
of this compact source extends to λ/2π ≈ 0.23 m, so **no probe is in the acoustic far field** —
near-field is dominated by non-propagating hydrodynamic pseudo-sound (SPL 112–120 dB near-field).
The 1/r extrapolation to 1 m over-reads by ~70 dB → **absolute far-field dB(A) is NOT recoverable
this way** (published is 22.6 dB(A)). What IS trustworthy: the **BPF tone level and RELATIVE noise
deltas between blade designs** — which is exactly what the optimizer needs (project north star =
relative gains). Good enough to wire noise as a relative 3rd objective.

**(c) Control-volume force — BUILT, far-field propagation SOLVED, absolute broadband still coarse-
grid-limited.** `setup.cpp` CV version: net fan force on fluid from a momentum balance over a FIXED
box surface enclosing the fan, F_i=-(d/dt∫_V ρu_i dV + ∮_S(ρu_i u_n + p'n_i)dA), pure fluid data →
no moving-boundary NaN. `build/fan_cv_force.csv` (SI volume-momentum P + surface-flux Fs);
`scripts/fan_noise_cv.py` differentiates → F(t) → Curle dipole to **any** distance (compact source).
Results: **mean thrust Fz = −0.076 N (physically sane → validates the momentum balance)**; on-axis
**BPF tone ≈ 20 dB @1 m (close to published 22.6 dB(A))**; directivity front>45°>side (correct).
BUT overall dB(A) ≈ 60, and it is **cutoff-sensitive** (62→32 dB(A) as low-pass goes 4 kHz→700 Hz):
at 1 mm the grid can't separate real broadband from numerical floor, and dF/dt × A-weighting (peak
2.5 kHz) over-weights it. So **absolute broadband dB(A) is NOT trustworthy**; the surface term (not
the volume term) carries the broadband, so it's the resolved flow field, not integration jitter.
**TRUSTWORTHY: mean thrust, BPF tone level, directivity, and — with a CONSISTENT band-limit applied
to every design — RELATIVE noise ranking** (the optimizer's actual need; cutoff cancels in ranking).
Absolute broadband would need finer cells (push grid cutoff up + resolve turbulence) → ~0.5 mm →
~90M cells → >12 GB, infeasible on the 4070 Ti. Far-field spectrum: `build/fan_noise_cv_spectrum.png`.

## FINALIST NOISE EVALUATOR — built + wired (2026-08-27)
The CV-noise setup is **generalized** to any impeller STL via a job config the Python side writes:
`build/noise_job.cfg` (`stl=`, `dia_mm=`, `out=`); the setup scales any STL to 1 mm/cell (axis Z),
auto-sizes the CV box, falls back to the A12x25 if no config. **Surface-only force** now (volume
term dropped — measured 61.5 vs 62.0 dB(A), negligible) + sampling every 16 steps ⇒ **~2.5 min/
design** (was ~7–8). `subprocess` must NOT capture FluidX3D's progress stdout (`DEVNULL` it — capturing
deadlocks the pipe).

- `scripts/evaluate_noise.py` — `evaluate_noise(stl, dia_mm=auto)` → runs the LBM, returns
  `{noise_dba_band, noise_dba_full, bpf_tone_db, thrust_n}`. `noise_dba_band` = A-weighted on-axis
  dB(A) @1 m, low-passed at 2500 Hz — the **same band for every design**, so the uncertain absolute
  offset cancels and it's a valid **relative** noise objective. Also a CLI.
- `scripts/score_finalists_noise.py <run_dir>` — scores every `pareto.json` finalist's STL, ranks
  quietest-first, writes `runs/<dir>/finalist_noise.json`. Noise stays finalist-only (cheap RANS
  proxy screens every candidate; the GPU LBM scores the Pareto front) — the plan's fidelity ladder.

## Done / next
1. **~~Match free-delivery~~ — as far as resolution allows (~36 CFM; blade under-resolved at 1 mm).**
2. **~~Shut-off pressure~~ — ~21 Pa settled, −8% vs published (RANS was −43%).**
3. **~~Noise pipeline~~ — built; BPF tone + relative noise robust; absolute far-field via CV-force dipole.**
4. **~~Finalist noise evaluator~~ — any STL → relative dB(A); wired to score Pareto finalists.**
5. Next: extract transferable design rules (do quieter finalists share geometry traits?); the
   physical print+measure loop remains the ultimate validation.
2. Add **shut-off** point (closed outlet) → static-pressure rise near 22.9 Pa (the number
   steady RANS under-predicts at ~13 Pa).
3. Record blade-surface pressure history → **Ffowcs-Williams–Hawkings** for far-field
   dB(A) + spectrum (FluidX3D + FW-H is a proven axial-fan aeroacoustics route).
4. Wire noise in as the 3rd optimizer objective.

Editing `defines.hpp`/`setup.cpp` requires a recompile (the g++ command above).
