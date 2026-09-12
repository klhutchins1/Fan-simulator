<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Bibliography — the papers behind the physics

A living, working reference: every method in the codebase should trace to a source here, and every
entry names **where in the code it is used** (or where it *will* be, for planned work). Foundational
papers (Lighthill, Curle, Proudman, FW-H, Menter, Roache) are cited from the primary literature;
modern/applied refs carry a URL. When you add a method, add its paper here and the back-reference.

Legend: **→ code** points at the module/script that implements or relies on the result.

---

## 1. Aeroacoustics — analogies & proxies

- **Lighthill, M. J. (1952).** *On sound generated aerodynamically. I. General theory.* Proc. R.
  Soc. Lond. A **211**, 564–587. — The acoustic analogy: recasts the flow equations as a wave
  equation with turbulence as the source. The root of everything below.
- **Curle, N. (1955).** *The influence of solid boundaries upon aerodynamic sound.* Proc. R. Soc.
  Lond. A **231**, 505–514. — Adds solid surfaces to Lighthill: the surface term is a **dipole**
  whose strength is the unsteady force the body exerts on the fluid. **→ code:** the compact-dipole
  far-field model in `scripts/fan_noise_cv.py` / `scripts/evaluate_noise.py` (control-volume force →
  `p' = (x_i/4πc₀r²)·dF_i/dt`), valid because the fan is acoustically compact (λ_BPF ≈ 1.47 m ≫ 0.11 m).
- **Proudman, I. (1952).** *The generation of noise by isotropic turbulence.* Proc. R. Soc. Lond. A
  **214**, 119–132. — Acoustic power of isotropic turbulence from RANS quantities (k, ε) — the
  cheap **broadband** noise proxy. **→ code (planned):** `fansim/acoustics/proxies.py::proudman_power`.
- **Ffowcs Williams, J. E. & Hawkings, D. L. (1969).** *Sound generation by turbulence and surfaces
  in arbitrary motion.* Phil. Trans. R. Soc. Lond. A **264**, 321–342. — Generalises Curle to
  *moving* surfaces (the FW-H equation); the standard route for rotating-machinery far-field noise.
  **→ code (future):** permeable-surface FW-H as the finalist noise upgrade beyond the compact dipole.
- **Blake, W. K. (1986).** *Mechanics of Flow-Induced Sound and Vibration.* Academic Press. —
  Reference text tying the analogies to real flow-noise mechanisms (loading vs. thickness vs.
  broadband). Context for interpreting the dipole spectra.

## 2. Fan noise & UNEVEN blade spacing (the tonal lever)

- **Cattanei, A., Ghio, R. & Bongiovì, A. (2007).** *Reduction of the tonal noise annoyance of
  axial flow fans by means of optimal blade spacing.* Applied Acoustics **68**(11–12), 1323–1345.
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0003682X06001666) — The
  canonical fan result: uneven circumferential spacing spreads the blade-pass tone into many lower
  sidebands (less perceived tonalness) **without hurting aerodynamic performance**, and generates
  only *balanced* geometries. Directly supports the planned feature.
- **Aeroacoustic Prediction and Optimization of Unevenly Spaced Blades in Axial Fans.** Int. J.
  Turbomachinery Propulsion and Power (MDPI) **11**(2):17. [mdpi.com](https://www.mdpi.com/2504-186X/11/2/17)
  — A modern optimization treatment of exactly our proposed feature (predict + optimize the spacing
  pattern). Closest published analogue to how we'd wire it into the search.
- **Psychoacoustic Optimization of the Spacing of Propellers, Helicopter Rotors, and Axial Fans.**
  J. Propulsion and Power. [doi:10.2514/1.B35960](https://doi.org/10.2514/1.B35960) — Frames spacing
  choice as a *psychoacoustic* optimization; motivates using a peak-tone / tonalness metric rather
  than overall SPL. **→ code (future):** `[[fan-sim-uneven-spacing]]` feature + a peak-tone objective.
- **Balance constraint:** for identical blades, static balance holds iff Σₖ e^{iθ_k} = 0 (blade
  position vectors sum to zero). **→ code (future):** `fansim/structural/balance.py`.

## 3. Bio-inspired blade features

- **Miklosovic, D. S., Murray, M. M., Howle, L. E. & Fish, F. E. (2004).** *Leading-edge tubercles
  delay stall on humpback whale flippers.* Physics of Fluids **16**(5), L39–L42. — Tubercles → later
  stall / higher usable angle of attack. Seeds the LE-tubercle feature.
- **Fish, F. E., Weber, P. W., Murray, M. M. & Howle, L. E. (2011).** *The tubercles on humpback
  whales' flippers: application of bio-inspired technology.* Integr. Comp. Biol. **51**(1), 203–213.
  — Review of the mechanism and engineering transfer.
- **Howe, M. S. (1991).** *Aerodynamic noise of a serrated trailing edge.* J. Fluids and Structures
  **5**(1), 33–45. — Analytic basis for trailing-edge serrations reducing edge noise.
  **→ code:** the tubercle / serration / dimple perturbations in `fansim/geometry/features.py`.
- Applied fan/CAA studies (leading- & trailing-edge serrations): AIAA J. J056355; ICA2019 CAA study
  ([pub.dega-akustik.de](https://pub.dega-akustik.de/ICA2019/data/articles/000052.pdf)); URANS-LES+FW-H
  automotive-fan serrations, SAGE 2023; wavy blades, JAFM 2024. *(URLs in git history of the plan;
  re-verify DOIs before any publication.)*

## 4. CFD methods — RANS, LBM, verification

- **Menter, F. R. (1994).** *Two-equation eddy-viscosity turbulence models for engineering
  applications.* AIAA Journal **32**(8), 1598–1605. — The **k-ω SST** model. **→ code:** the
  turbulence closure in the OpenFOAM `simpleFoam` MRF cases (`fansim/cfd/`).
- **Roache, P. J. (1994).** *Perspective: A method for uniform reporting of grid refinement studies.*
  J. Fluids Engineering **116**(3), 405–413. — The **Grid Convergence Index (GCI)** — how to report
  discretization error honestly. **→ code:** `scripts/run_grid_convergence.py`,
  `scripts/grid_convergence_stl.py` (the 6/4/3 mm study → ~3–5% quantified error).
- **Krüger, T. et al. (2017).** *The Lattice Boltzmann Method: Principles and Practice.* Springer. —
  Standard LBM text (BGK/MRT collision, boundary conditions, unit conversion). **→ code:** the
  FluidX3D setups in `FluidX3D/src/setup.cpp` and the lattice↔SI conversions.
- **Lehmann, M. (2022).** *Esoteric Pull and Esoteric Push: Two Simple In-Place Streaming Schemes
  for the Lattice Boltzmann Method on GPUs.* Computation **10**(6), 92.
  [mdpi.com](https://www.mdpi.com/2079-3197/10/6/92) — The in-place streaming + FP16S scheme behind
  FluidX3D's speed/memory (why 4.3–11.6 M cells fit the 4070 Ti's 12 GB). **→ code:** the whole
  GPU tier ([docs/fluidx3d-setup.md](fluidx3d-setup.md)).

## 5. Test standards & validation

- **ISO 5801** / **AMCA 210** — standardized fan pressure–flow (P–Q) test methods. Define
  free-delivery and shut-off operating points. **→ code:** the P–Q sweep + free-delivery/shut-off
  targets validated against the Noctua A12x25 (60.1 CFM, 22.9 Pa) — see [[fan-sim-a12x25-specs]].

## 6. ML surrogates (the future cost-reduction tier)

- **Li, Z. et al. (2020).** *Fourier Neural Operator for Parametric Partial Differential Equations.*
  arXiv:2010.08895 (ICLR 2021). — Learns a resolution-independent solution operator; candidate for a
  flow-field surrogate. **→ code (future):** `fansim/surrogate/`.
- **Lu, L. et al. (2021).** *Learning nonlinear operators via DeepONet.* Nature Machine Intelligence
  **3**, 218–229. — Operator-learning alternative. Frontier: transformer / neural-field aero
  surrogates (see the plan's arXiv scan; re-verify IDs before relying on them).

---

*Maintenance: when a method lands in the code, add its paper here with a **→ code** back-reference.
When a **→ code (planned/future)** item ships, drop the qualifier. Re-verify applied-paper DOIs/URLs
before any external publication — the foundational entries (§1, §4 Menter/Roache) are stable.*
