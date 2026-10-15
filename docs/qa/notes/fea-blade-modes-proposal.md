# Proposal: optional 3-D FEA blade-mode check (lead #13)

QA research, 2026-10-14. Status: **proposed**. Nothing in `fansim/` has been changed. Reference prototype:
`handoff/2026-10-14_from-qa-research/fea_blade.py`. Research note: `research/notes/fea-blade-modes.md`.

## What it is
- An optional "FEA check" for **finalists**, added next to the beam gate in `fansim/structural/flutter.py`.
- How it works:
  1. Take the blade's surface STL and tet-mesh it with **pytetwild** (fTetWild).
  2. Clamp the root at the hub radius.
  3. Assemble linear elasticity with quadratic (P2) tets in **scikit-fem**.
  4. Run a generalized eigen-solve (`scipy.sparse.linalg.eigsh`, shift-invert) for the first 4 modes.
- Material is the same as the beam model: `MATERIALS[...]` E × `FDM_E_K`, with ν = 0.35.
- Optional Southwell spin stiffening: f_rot² = f0² + S·Ω², with S ≈ 1.17 (textbook value for a uniform cantilever's first flap mode).
- The beam formula stays as the fast screen for the optimizer.

## Evidence (Stock A12x25, PETG, 2000 rpm, BPF 300 Hz)
| model | f1 | f1/BPF |
|---|---|---|
| beam (`first_bending_hz`) | 400 Hz | 1.33 |
| 3-D FEA, two mesh densities | 357–365 Hz (modes 2–4: ≈1.0, 1.8, 2.0 kHz) | **1.19–1.22** |
| + Southwell at 2000 rpm | +1.7 Hz | negligible |

The beam model is about 10 % optimistic, so Stock sits *on* the 1.2 gate rather than clearing it. That is the shape error §19.18 worried about (tip aspect ≈ 0.98).

Cost:
- About 1 min wall time in total: fTetWild takes 48–62 s, the solve about 3 s.
- About 3k tets / 16–19k DOF.
- **Peak RSS 0.57 GB.**

## Caveats
- **The mesher isn't deterministic.** Node counts change between runs and f1 varies by about **±2 %**.
- **The hub is rigidly clamped.** The real plastic hub flexes, so the real f1 is probably a bit lower again (conservative direction for the gate is unknown until a tap test).
- The prototype tet-meshes the whole impeller and cuts out one blade as a wedge. A production version should mesh the single exported blade, which is cheaper and cleaner.
- Material is isotropic with a knockdown factor, which is not true layer-by-layer printed behaviour.
- **The licences of the third-party libraries compiled into fTetWild (e.g. Geogram, libigl) inside the pytetwild wheel are NOT checked.**

## Licences and dependencies
- scikit-fem 12.0.2 is BSD-3. scipy, numpy and meshio are BSD/MIT. The prototype is our own code, using only scikit-fem's public API; it does not copy ex21.
- **pytetwild 0.4.2 is MPL-2.0.** Use it only as an **unmodified pip dependency**: never vendor, copy or patch its files. certifi (also MPL-2.0) comes in via requests/pyvista under the same rule.
- pytetwild **imports pyvista but doesn't declare it** as a dependency, so we must declare it ourselves. fansim already depends on pyvista.
- Venv size: 252 MB without pyvista, **938 MB** with pyvista/VTK. That is another reason to keep it an optional extra.

## Suggested design
- **Packaging:** an extra `fansim[fea] = ["scikit-fem>=12", "pytetwild>=0.4", "meshio"]`, with pyvista already in core. Import it lazily and raise a clear "install fansim[fea]" error if it's missing.
- **API:** a new `fansim/structural/fea_modes.py`:
  ```python
  @dataclass
  class FeaModesReport:
      f_hz: list[float]          # first n modes, non-rotating
      f1_rot_hz: float           # Southwell-corrected at rpm
      f1_over_bpf: float
      n_tets: int; runtime_s: float; mesh_seed_spread: float | None
  def blade_modes_fea(params: BladeParams, material="PETG", rpm=None, n_modes=4,
                      edge_length_fac=0.03, clamp="hub_radius", southwell_s=1.17) -> FeaModesReport
  ```
  - It should build one blade's STL with the existing geometry exporter, into a temp directory.
  - `flutter.py` gets `check_flutter(..., fea=False)`. When `fea=True`, it attaches the FEA report and applies the gate (see the open question). The default path stays unchanged and fast.
- **Opt-in flag:** `structural.fea_check: false` in the problem YAML or cockpit settings. It runs only on finalists or on demand, never inside the optimizer loop.
- **Cockpit:** in the Assess structural panel, show "Blade f1: beam 400 Hz / FEA 361 Hz (±2 %) → f1/BPF 1.20 (gate 1.2)". Add a "Run FEA check (~1 min)" button with a spinner, and cache the result by geometry hash.
- **Tests:**
  - (a) Analytic check: a slender rectangular cantilever bar (aspect ≥ 10) has FEA f1 within 3 % of the Euler–Bernoulli value.
  - (b) Stock regression: f1 in 340–380 Hz (a wide band, because of the mesher).
  - (c) Southwell: f1_rot > f0, and the boost is < 1 % at 2000 rpm.
  - (d) Skipped gracefully when the `fea` extra isn't installed.
  - Mark (a) and (b) as `slow`.

## Open question for Kimball/Claude
**Should the 1.2 gate apply to FEA f1, and with what margin?**
- Today Stock passes the beam gate (1.33) but sits at 1.19–1.22 by FEA.
- Option 1: keep 1.2 on the beam value and show FEA as advisory.
- Option 2: apply 1.2 to FEA f1 minus the 2 % mesh spread. Stock would then fail marginally, which says more about the gate than about Stock, a fan that is shipping fine.
- Option 3: recalibrate to a lower FEA gate (e.g. 1.1) once a printed-blade tap test pins down the real f1.
- QA's suggestion: option 1 until a tap test exists.
