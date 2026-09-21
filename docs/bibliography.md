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
- **Sharland, I. J. (1964).** *Sources of noise in axial flow fans.* J. Sound and Vibration
  **1**(3), 302–322. — The classic breakdown of axial-fan noise sources (incidence/turbulence
  ingestion, boundary-layer/vortex-shedding self-noise, tip effects); the physical companion to
  Curle's compact-dipole model for the **broadband** side our proxies approximate. **→ code:**
  context for the loading/Curle proxies in `fansim/acoustics/` (broadband still coarse-grid-limited,
  roadmap §1.4).

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

## 7. Fan & propeller aerodynamics — BEM, losses, low-Re polars, tip geometry

- **Axial-fan blade-element / free-vortex design & optimization** — Winterberg et al.,
  [FAN2018](https://www.fan2025.org/archives/fan2018/papers/FAN2018-7-WINTERBERG.pdf);
  [model-based low-pressure axial-fan blade design (Elsevier 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0140700724003116);
  [ducted counter-rotating axial fans, design + validation (arXiv:1208.6396)](https://arxiv.org/pdf/1208.6396).
  — Euler turbomachinery pressure rise + blade-element lift/drag + slip/endwall losses give a
  fan's CFM / static rise / efficiency **analytically, in milliseconds**. **→ code:** the analytic
  screening tier `fansim/fan_bem.py` + `--bem-prescreen` (roadmap §7.1; ranking Spearman ~0.62 vs CFD).
- **Lissaman, P. B. S. (1983).** *Low-Reynolds-number airfoils.* Annu. Rev. Fluid Mech. **15**,
  223–239. — Foundational review of the low-Re regime (early separation, reduced lift slope, earlier
  stall, steep profile-drag rise) that the polar model reproduces. Tabulated data: the
  [UIUC/Selig low-speed airfoil database](https://m-selig.ae.illinois.edu/ads.html). **→ code:** the
  Re-aware `_cl_cd` polar + `fansim/data/polars/` CSVs (roadmap §7.2, §1.6).
- **Storer, J. A. & Cumpsty, N. A. (1991).** *Tip leakage flow in axial compressors.*
  J. Turbomachinery **113**(2), 252–259. — Canonical tip-leakage mechanism. **Denton, J. D. (1993).**
  *Loss mechanisms in turbomachines* (IGTI Scholar Lecture). J. Turbomachinery **115**(4), 621–656.
  — The comprehensive loss taxonomy (endwall / tip-leakage / mixing) behind a design-dependent
  knockdown. Applied: [tip-gap analysis](https://www.sciencedirect.com/science/article/abs/pii/S0045793019300088),
  [energy dissipation in the blade-tip region](https://www.sciencedirect.com/science/article/abs/pii/S0022460X16302772).
  **→ code:** the Prandtl finite-blade tip-loss + gap-leakage knockdown in `fansim/fan_bem.py`
  (roadmap §7.3, §1.1 — the lever that moved fan ranking 0.52→0.62).
- **Tip geometry — shroud/ring, optimal clearance, winglets, casing treatment / recirculation for
  stall margin:** [tip geometry on a low-speed axial fan](https://www.sciencedirect.com/science/article/abs/pii/S0140700721003273);
  [winglet designs for small axial fans (exp+num, 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0003682X24005991);
  [tip clearance, winglets & shroud height on tip leakage](https://www.sciencedirect.com/science/article/abs/pii/S0140700718302470).
  — Max static efficiency at a shroud height ≈30% of axial chord (not zero gap); winglets help a
  partially-shrouded fan but hurt a fully-shrouded one. **→ code:** the winglet×shroud policy in
  `suggest_params` / `blade_from_flat` (roadmap §2.1, §7.5).
- **Sim→print penalty — printed-impeller performance & blade-thickness effects:**
  [tip-vortex manipulators, num vs experimental on a printed condenser fan (arXiv:2309.13195)](https://arxiv.org/pdf/2309.13195);
  [experimental blade-thickness effects on axial-fan performance](https://www.academia.edu/70824092/Experimental_study_of_blade_thickness_effects_on_the_global_and_the_local_performances_of_axial_flow_fans).
  **→ code:** `fansim/optimize/print_penalty.py` (CFM/η knockdown; provisional until §5 hardware, §1.3/§7.6).
- **Swept / sickle (forward-swept) cooling-fan noise** — automotive cooling-fan studies motivating the
  sickle planform's noise trade (URANS-LES+FW-H serrated/swept fans; see the §3 applied list and the
  plan history for the specific DOIs — re-verify before publication). **→ code:** `apply_sickle` /
  `--sickle` (roadmap §2.3).
- **Propeller / open-rotor BEMT & noise** — **Drela, M. (2006).** *QPROP Formulation* (MIT) —
  prop/windmill blade-element method with Reynolds and Mach corrections; **Hepperle, M.** *JavaProp*
  (BEMT with compressibility/Re corrections); **Hanson, D. B. (1985).** *Noise of counter-rotation
  propellers.* J. Aircraft **22**(7), 609–617. **→ code:** the prop BEMT + relative noise proxy
  (`fansim/propeller/`) and the CROR tier (`fansim/cror/`); compressible open-air prop CFD is roadmap §4.3.
- **PyThrust (`setuav-pythrust`)** — optional motor–prop–battery equilibrium against bundled APC
  catalogs; Apache-2.0; pin **0.2.3**. [GitHub](https://github.com/Setuav/PyThrust) ·
  [docs](https://setuav.github.io/PyThrust/) · [PyPI](https://pypi.org/project/setuav-pythrust/).
  **→ code:** optional adapter in `fansim/propeller/power.py` (`uv sync --extra propulsion`); quorum
  Q3–Q5 behind `@pytest.mark.propulsion`; custom-blade BEMT→CSV bridge in
  `fansim/propeller/pythrust_export.py` (Analyze **Export CT/CP (PyThrust)** +
  `scripts/export_prop_pythrust_csv.py`); specs
  `docs/superpowers/specs/2026-09-21-prop-pythrust-power-design.md`,
  `docs/superpowers/specs/2026-09-21-prop-pythrust-bemt-export-design.md`.
- **Drela first-order DC brushless motor model (MIT / QPROP lineage)** — Kv, winding resistance, and
  no-load current in the propulsion equilibrium PyThrust uses; full equations and Drela pointers in
  [Propulsion and Battery Theory](https://setuav.github.io/PyThrust/theory/). **→ code:** adapter
  `MotorSpec` mapping in `solve_catalog_operating_point` (quorum Q2 — witness, not a second motor
  solver in-tree).
- **UIUC Propeller Data Site** — measured static/wind-tunnel CT/CP for many propellers; witness
  corpus for geometry-honest BEMT cross-check (Track A **A3**).
  [propDB](https://m-selig.ae.illinois.edu/props/propDB.html). **→ code:** `fansim/propeller/bemt_catalog.py`
  (A3 Q7 fixture `validation/reference/uiuc_propdb/apcsf_9x4.7_static.json`; Q6 via PyThrust APC).

---

*Maintenance: when a method lands in the code, add its paper here with a **→ code** back-reference.
When a **→ code (planned/future)** item ships, drop the qualifier. Re-verify applied-paper DOIs/URLs
before any external publication — the foundational entries (§1, §4 Menter/Roache) are stable.*
