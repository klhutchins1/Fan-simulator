# fansim: integration leads (recurring scout)

This file is the running list of outside things (papers, code, data) that could be integrated into
the Fan Simulator. It is **deduplicated across weekly runs**. Each run adds only *new* leads (stamped
with the run date), updates the verdicts on existing ones if something changed, and never re-suggests
anything already in `src/docs/bibliography.md` or already shipped per `src/docs/roadmap.md`. Rejects
are kept at the bottom so they don't get re-researched. No app code was touched to produce this.

**Hard filter:** the app ships on GitHub under MIT. Code and data count only with a verified MIT, BSD,
Apache-2.0, CC-BY or public-domain license (the actual license file was checked). GPL/LGPL code is
flagged as copyleft. Equations from papers are fine to implement ourselves, but don't copy code,
text, or figures from paywalled papers. Patents are reported only when the number and status were
seen on Google Patents. None of this is legal advice.

**Run log**
- 2026-10-08: first pass. Inputs: `src/docs/bibliography.md`, `src/docs/roadmap.md` (last reviewed 2026-09-30),
  `src/docs/known-issues.md` (archived/stale, points to roadmap), `src/memory/*.md` (incl. `fan-sim-roadmap`,
  `fan-sim-uneven-spacing`). Note: there is no top-level `docs/` or `memory/`. Both live under `src/`.

**Gaps targeted this run** (from the docs): broadband noise is coarse-grid-limited (roadmap §1.4); the app
has no standard tonality metric (the uneven-spacing work uses an ad-hoc peak-tone ratio); FW-H covers only
the stationary/compact kernel (bib §1); the fan BEM uses a constant `SLIP = 0.71` and over-predicts shut-off
(40.6 vs 22.9 Pa, §19.16); the BEM ignores plate sections; the loaded branch and stall are weak (§19.6); the
frame struts exist in CFD but nothing in the acoustics models them; and expensive CFD runs inside the NSGA-II loop.

**Already used, so not re-suggested:** Lighthill, Curle, Proudman, FW-H 1969, Blake, Sharland, Cattanei 2007,
the MDPI uneven-spacing paper, the JPP psychoacoustic spacing paper, Howe serrations, tubercles, Menter SST,
Roache GCI, Krüger LBM, FluidX3D/Lehmann, ISO 5801/AMCA 210, FNO/DeepONet, Winterberg/FAN2018,
Lissaman/UIUC polars, Storer & Cumpsty, Denton, tip/winglet/shroud papers, arXiv:2309.13195, QPROP/JavaProp,
Hanson, Prandtl/Glauert, PyThrust, UIUC propDB, NeuralFoil/AeroSandbox, Lieblein DF / de Haller / Cordier
(meanline seed), FAN-01, Optuna NSGA-II, scikit-learn GP surrogate.

Legend: **Effort** S = a day or two, M = about a week, L = multi-week. **Confidence** = how sure we are it
will actually help fansim (not whether the source is real; every link below was opened or returned by search).

---

## Leads (most useful first)

### 1. Rotor–strut interaction tone + blade/strut-count rule (Huang; Tyler & Sofrin)
- **Sources:** Huang, L. (2003) *Characterizing computer cooling fan noise*, JASA 114:3189, doi:10.1121/1.1624074
  ([page](https://pubs.aip.org/asa/jasa/article/114/6/3189/544318/Characterizing-computer-cooling-fan-noise));
  Huang & Wang (2005) *Acoustic analysis of a computer cooling fan*, JASA 118:2190, doi:10.1121/1.2010367;
  Lu, Huang, So & Wang (2007) *A computational study of the interaction noise from a small axial-flow fan*,
  JASA 122:1404 ([open PDF, HKU repository](https://hub.hku.hk/bitstream/10722/57190/1/142738.pdf));
  Tyler & Sofrin (1962) *Axial flow compressor noise studies*, SAE Trans. 70:309–332, doi:10.4271/620532.
- **Date added:** 2026-10-08
- **What it adds:** In a PC fan the loudest tones mostly don't come from the blades alone. They come
  from the blades sweeping past the motor-holding **struts** right behind them. Each pass gives the blade a
  small "kick", and the pattern of kicks spins around the fan as pressure "modes". Tyler & Sofrin's
  counting rule (mode number m = n·B − k·V, with B blades and V struts) tells you which blade/strut
  combinations send a strong tone straight out of the fan and which ones partly cancel. Huang found that
  total tonal power depends more on the **number of struts** than on the number of blades. Huang & Wang
  also found that an oversized wiring strut and the square frame's sharp inlet corners each made about as
  much noise as the rest of the strut set. Fixing them was worth up to about 10 dB. This is all algebra, so
  it costs no compute.
- **Improves:** `fansim/acoustics/tonal.py` (extends the array-factor and peak-tone metric from rotor-only
  to rotor + struts); the uneven-spacing search (a spacing pattern that looks good rotor-only can still line up
  badly with 4 struts); `fansim/cfd/frame.py` (strut count, thickness, and axial gap become meaningful design
  inputs); a cheap "blade/strut count" check in the optimizer.
- **License:** Math from papers, implement ourselves (JASA papers are paywalled except the HKU PDF; don't copy figures).
- **Patents:** Seen on Google Patents. Intel **US7300244B2** (irregularly spaced blades and struts) has status
  *Expired – Lifetime* (adjusted expiration 2025-11-22). Comair Rotron **US4089618A** (strut/blade interaction,
  notched TE) has status *Expired – Lifetime*. No live patent found on choosing blade/strut counts (search not exhaustive).
- **Effort:** S (count rule plus strut term in the tonal metric) to M (Huang's force-component model).
- **Confidence:** high

### 2. Standard tonality metrics: ECMA-418-1 (TNR/PR) + MoSQITo
- **Sources:** [ECMA-418 (free standard, parts 1 & 2)](https://ecma-international.org/publications-and-standards/standards/ecma-418/);
  [MoSQITo on GitHub](https://github.com/Eomys/MoSQITo), [docs](https://mosqito.readthedocs.io/), PyPI `mosqito` 1.2.1.
- **Date added:** 2026-10-08
- **What it adds:** The app's uneven-spacing work currently scores noise with its own "peak tone"
  ratio. ECMA-418-1 is the industry's standard way to ask "does this fan have an annoying whine?" It
  compares each tone with the background noise in the band of hearing around it: the tone-to-noise
  ratio (TNR) and the prominence ratio (PR), with official pass/fail thresholds. ECMA-418-2 adds a
  hearing-model tonality and loudness. MoSQITo is a Python library that already computes TNR/PR,
  Zwicker loudness (ISO 532-1), sharpness and roughness from a time signal **or a spectrum**. You could
  feed it the FluidX3D control-volume pressure trace or the synthetic spectrum from the tonal model, and
  get a "would a listener notice the whine" number you can cite instead of a homemade one.
- **Improves:** `fansim/acoustics/` (new objective next to `a_weighting_db`); the noise objective for the
  uneven-spacing search (the spacing memo explicitly wants a peak-tone/tonalness objective); cockpit Assess readout.
- **License:** MoSQITo is **Apache-2.0** (checked the LICENSE file). It's fine to use as a dependency or to vendor.
  ECMA standards are free to download. Implementing the formulas ourselves is also fine.
- **Patents:** none found (metrics, not a fan geometry).
- **Effort:** S
- **Confidence:** high (caveat: the repo's last push was 2024-09-10, so pin the version, or port the
  ~200-line TNR/PR routines if it rots).

### 3. BPM airfoil self-noise model: compute-free broadband noise (NASA RP-1218)
- **Sources:** Brooks, Pope & Marcolini (1989) *Airfoil Self-Noise and Prediction*, NASA RP-1218
  ([NTRS record](https://ntrs.nasa.gov/citations/19890016302), marked "Work of the US Gov. Public Use Permitted");
  validation data [UCI Airfoil Self-Noise dataset](https://archive.ics.uci.edu/dataset/291/airfoil+self+noise)
  (the NASA measurements, 1,503 rows, doi:10.24432/C5VW2C);
  reference implementations: [OpenFAST AeroAcoustics module](https://openfast.readthedocs.io/en/main/source/user/aerodyn-aeroacoustics/index.html)
  (Fortran, `modules/aerodyn/src/AeroAcoustics*.f90`) and [BroadbandBPM.jl](https://github.com/byuflowlab/BroadbandBPM.jl).
- **Date added:** 2026-10-08
- **What it adds:** The roadmap says broadband ("whoosh") noise can't be trusted because the LBM grid is
  too coarse. BPM is NASA's classic recipe for estimating the hiss a blade section makes from things the
  BEM already knows at each radius: speed, chord, angle of attack, Reynolds number, and trailing-edge
  thickness. It has separate terms for turbulent trailing-edge noise, stall/separation noise,
  **laminar vortex-shedding "whistle"** (relevant here because the blades run at a very low Reynolds
  number, roughly 30k), blunt-trailing-edge hum, and tip-vortex noise. Adding up the sections gives a
  broadband spectrum in milliseconds, which is good for *ranking* designs, though not for absolute dB(A).
  It also links directly to the existing `te_thick_scale` knob, so it would show whether a blunter printed
  trailing edge costs noise.
- **Improves:** `fansim/acoustics/proxies.py` (a physics-based companion to the Proudman proxy); `fan_bem.py`
  per-station outputs; the noise objective in the optimizer; roadmap §1.4 (still relative, but it no longer
  depends on grid resolution).
- **License:** NASA report is US-government work (public use permitted). UCI dataset is **CC BY 4.0**
  (attribution required). OpenFAST is **Apache-2.0**; BroadbandBPM.jl is **MIT** (both LICENSE files checked).
  Avoid the Python port `EricGreenwood2/BPM` (**GPL-3.0**).
- **Patents:** none found.
- **Effort:** M
- **Confidence:** medium-high (BPM was fit on NACA 0012 at higher Re; treat as ranking-only and check
  it against the UCI data first).

### 4. Uneven-spacing classics + the live-patent map for that feature
- **Sources:** Mellin & Sovran (1970) *Controlling the tonal characteristics of the aerodynamic noise generated
  by fan rotors*, J. Basic Eng. 92(1):143–154, doi:10.1115/1.3424923 (paywalled);
  Pierpoint (1973) *Reducing blade tonal noise generated by vane-axial fans*, JASA 53:386
  ([free abstract](https://pubs.aip.org/asa/jasa/article/53/1_Supplement/386/665283/Reducing-Blade-Tonal-Noise-Generated-by-Vane-Axial)).
- **Date added:** 2026-10-08
- **What it adds:** Mellin & Sovran is the original "how to space blades unevenly" method, still widely
  used. It gives tabulated spacings for 4–15 blades that make the noise as "white" as possible with the
  smallest change from even spacing, including naturally balanced layouts. Those tables are a ready-made
  benchmark for `scripts/design_uneven_spacing.py`: if our optimizer can't match them, something is off. Pierpoint
  measured 10–20 dB drops at blade-pass frequency and "little effect on the ability of the fan to move air."
  **The bigger value here is the patent map** (below), because the app already ships this feature.
- **Improves:** `fansim/structural/balance.py` / `acoustics/tonal.py` / the spacing search (benchmark + sanity test).
- **License:** math only, so implement it ourselves. Don't reproduce the paper's tables verbatim in the repo;
  regenerate them with our own code.
- **Patents (all seen on Google Patents 2026-10-08):**
  - Bosch **US10480527B2**, "Axial fan with unbalanced blade spacing". Status *Active*, adjusted expiration 2038-02-02.
    Claim 1 covers blades spaced in a pattern that is **not** balanced, with balance restored by **varying blade
    thickness** between blades. fansim balances with identical blades via Σe^{iθ}=0, so it doesn't use that
    combination. **Avoid adding per-blade thickness scaling to fix balance.**
  - Champ Tech Optical (Foshan) **US11635088B1**, "Cooling fan". Status *Active*, anticipated expiration 2042-05-26.
    Claim 1 covers unequal intervals **plus** specific per-blade surface geometry where adjacent blades differ in shape
    (inlet/outlet angles). **Avoid combining uneven spacing with deliberately different blade shapes per blade.**
  - Nidec **US11231045B2**, "Impeller and axial fan" (≥5 blades, all pitch angles different, balanced). Google Patents
    status *Expired – Fee Related*.
  - ITT/Valeo **US5681145A** (unequal spacing + unequal setting angles). *Expired – Lifetime*.
  - Our reading of claim 1 only; this is not a freedom-to-operate opinion.
- **Effort:** S
- **Confidence:** high

### 5. Optuna 5 `GPSampler`: constrained multi-objective Bayesian optimization (already installed)
- **Sources:** [Optuna v5.0.0 release (2026-09-07)](https://github.com/optuna/optuna/releases/tag/v5.0.0);
  [GPSampler docs](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.GPSampler.html);
  optional heavier option: [BoTorch](https://github.com/meta-pytorch/botorch) via `optuna-integration`.
- **Date added:** 2026-10-08
- **What it adds:** Every axial CFD evaluation takes about 5 minutes, and NSGA-II is a "throw lots of
  darts" method that needs many of them. A Gaussian-process sampler builds a statistical guess of the
  whole design landscape after each run and picks the next design where it expects the most gain. With
  only tens to a few hundred evaluations, it usually finds a better Pareto front. `uv.lock` already pins
  **optuna 5.0.0**, where `GPSampler` is stable and supports **constrained multi-objective** search
  (qLogCEHVI), which fits the printability/balance gates. It's a one-line sampler swap behind a flag,
  plus a head-to-head against NSGA-II on the BEM stub. (Also note: v5 made TPE the default
  multi-objective sampler. fansim passes `NSGAIISampler` explicitly everywhere, so that change doesn't affect it.)
- **Improves:** `fansim/optimize/study.py` and the archetype `optimize.py` files; complements §20.5 surrogate-guided search.
- **License:** Optuna is **MIT**, `optuna-integration` is **MIT**, BoTorch is **MIT** (checked).
- **Patents:** n/a.
- **Effort:** S
- **Confidence:** medium (benefit has to be measured; GP cost grows with trial count and mixed/categorical params).

### 6. Design-dependent deviation (Carter's rule) to replace the constant `SLIP = 0.71`
- **Sources:** Carter's deviation rule (Carter 1950, cascade work), as applied to low-speed rotor-only fans in
  van der Spuy & von Backström (2002) *Performance of rotor-only axial fans designed for minimum exit kinetic energy*,
  R&D Journal 18 ([open access, SciELO SA](https://scielo.org.za/scielo.php?pid=S2309-89882002000100012&script=sci_arttext)),
  with the design procedure from Wallis, *Axial Flow Fans and Ducts* (book).
- **Date added:** 2026-10-08
- **What it adds:** Air leaving a blade never turns quite as much as the blade's shape suggests. That
  shortfall is the "deviation". Right now the fan BEM charges every design the same flat 29% swirl loss
  (`SLIP = 0.71`). Carter's rule makes the shortfall depend on the design: deviation ≈ m·(camber angle)·√(pitch/chord),
  with m depending on stagger. Thin, widely spaced, highly cambered blades lose more turning, while
  dense, overlapping blades lose less. That's the blade-count/solidity trade the BEM currently can't tell
  apart, which is probably part of why mid-pack ranking is weak (ρ 0.54 without `t9012`, §19.16).
- **Improves:** `fansim/fan_bem.py` (per-station deviation instead of global SLIP); `optimize/meanline.py` seed.
- **License:** classic math, implement ourselves. The SciELO article is open access (license terms on the page not checked).
- **Patents:** none (1950s method).
- **Effort:** S–M (needs re-running Audit #4 to show ranking doesn't get worse)
- **Confidence:** medium

### 7. Broadband + moving-surface FW-H reference: AcousticAnalogies.jl (NASA)
- **Source:** [OpenMDAO/AcousticAnalogies.jl](https://github.com/OpenMDAO/AcousticAnalogies.jl)
  ([docs](https://openmdao.github.io/AcousticAnalogies.jl/dev/)).
- **Date added:** 2026-10-08
- **What it adds:** The bibliography admits fansim's FW-H is only the *stationary* Curle-type kernel:
  no motion (Doppler) terms and no blade-thickness noise. This NASA package implements the standard
  full rotating-blade formula (Lopes' compact form of Farassat 1A) **and** the Brooks–Burley rotor
  broadband method (BPM applied to spinning blades). It's in Julia, so the realistic uses are (a) a
  reference to port the formulas from, with its test cases as known-good answers, or (b) an optional
  external cross-check. It's most useful for the **prop** archetype (tips at Mach 0.4–0.58, where motion
  terms matter) and as a sanity check on fan tonal predictions.
- **Improves:** `fansim/acoustics/fwh.py`, `fansim/propeller/noise.py`, roadmap §1.4.
- **License:** **Apache-2.0** (LICENSE file: "Copyright 2023 National Aeronautics and Space Administration… Apache License 2.0").
- **Patents:** none found.
- **Effort:** M (port compact F1A) to L (full integration)
- **Confidence:** medium

### 8. Stall pressure-rise limit (Koch 1981) for the loaded branch and shut-off
- **Source:** Koch, C. C. (1981) *Stalling pressure rise capability of axial flow compressor stages*,
  J. Eng. Power 103(4):645–656, doi:10.1115/1.3230787 (paywalled).
- **Date added:** 2026-10-08
- **What it adds:** The BEM predicts a shut-off pressure of 40.6 Pa where the real fan does 22.9 Pa,
  and CFD falls apart near stall (§19.6). Koch's correlation estimates the **highest pressure rise a
  blade row can reach before it stalls**, from blade-row geometry: solidity, stagger, tip clearance,
  Reynolds number. Used as a cap on the BEM P–Q curve, it could make the loaded end of the curve
  believable without days of URANS. It also gives the optimizer a "stall margin" constraint.
- **Improves:** `fansim/fan_bem.py` (P–Q cap / shut-off), `optimize/meanline.py` gates, cockpit P–Q plot.
- **License:** math only, implement ourselves.
- **Patents:** none.
- **Effort:** M
- **Confidence:** low-medium (built for compressors; low-Re 120 mm fans are outside its data, so check it against
  the A12x25 22.9 Pa and FAN-01 first).

### 9. Cambered-plate lift/drag formulas (Balla & Vad 2021)
- **Source:** Balla, E. & Vad, J. (2021) *An empirical model to determine lift and drag coefficients of cambered plates
  at moderate Reynolds numbers*, Proc. IMechE Part A 235(2):202–210, doi:10.1177/0957650920915317
  ([accepted manuscript, MTAK repository](https://real.mtak.hu/137628/1/REALba_IMech_Manuscript_Balla_Vad_resubmit_200123.pdf)).
- **Date added:** 2026-10-08
- **What it adds:** The Stock A12x25 recipe uses **cambered-plate** blade sections, but the BEM only has
  airfoil polars (NACA/Eppler/Selig) and its own docstring says it ignores plate sections. This paper,
  written for low-speed axial fans, gives simple polynomial formulas for plate lift and drag as a function
  of angle, camber (0–8%), and Reynolds number, based on measurements. That would let the BEM use a
  plate-specific polar when `rounded_plate` is active.
- **Improves:** `_cl_cd` / `fansim/data/polars/` polar backends, `fan_bem.py`.
- **License:** math/empirical formulas, so implement ourselves. Note: the manuscript PDF says "Reuse is restricted to
  non-commercial and no derivative uses". That covers the paper itself, so **don't copy its text, tables, or
  figures into the repo**. Implementing the formulas with a citation is within our math-from-papers rule.
- **Patents:** none.
- **Effort:** S
- **Confidence:** low-medium (**range is Re 60k–300k**; a 120 mm fan at ~2000 rpm runs roughly Re 25–45k near the
  tip, so this is an extrapolation. Compare against NeuralFoil on a plate section before adopting it).

### 10. Ducted-rotor solver: DuctAPE.jl (open re-take on Drela's DFDC)
- **Sources:** [byuflowlab/DuctAPE.jl](https://github.com/byuflowlab/DuctAPE.jl) ([docs](https://flow.byu.edu/DuctAPE.jl/stable/));
  theory: Drela, *Axisymmetric Analysis and Design of Ducted Rotors* ([DFDC theory PDF, MIT](https://web.mit.edu/drela/Public/web/dfdc/DFDCtheory12-31.pdf)).
- **Date added:** 2026-10-08
- **What it adds:** A fan in its frame is a *ducted* rotor. The duct and hub change the air speed the
  blades see, which a plain blade-element model treats crudely through constants. DuctAPE couples an
  axisymmetric panel model of duct and hub with a blade-element rotor, so it captures that interaction in
  well under a second. It could serve as an independent check on the BEM's free-air and loaded numbers,
  and on the shroud/frame-gap levers.
- **Improves:** `fansim/fan_bem.py` (cross-check or upgrade), shroud/frame studies, archetype CROR/stator stacks.
- **License:** DuctAPE.jl **MIT** (checked). DFDC itself is **GPL**. Read the theory, but don't use its code.
- **Patents:** none found.
- **Effort:** L (Julia; porting the panel method is substantial)
- **Confidence:** low-medium (built for open-air ducted propulsors; a 25 mm square-frame PC fan is a short, stubby "duct")

### 11. Robust BEM solve: Ning's guaranteed-convergence method (CCBlade)
- **Sources:** [NREL/WISDEM CCBlade (Python/Fortran)](https://github.com/NLRWindSystems/CCBlade),
  [CCBlade.jl](https://github.com/byuflowlab/CCBlade.jl); method from Ning (2014) *A simple solution method for the
  blade element momentum equations with guaranteed convergence*, Wind Energy (citation from memory, DOI **not checked**).
- **Date added:** 2026-10-08
- **What it adds:** Blade-element solvers sometimes fail to converge or jump to a wrong answer at odd
  operating points (windmilling, high load, stall). Ning rewrote the problem as one equation in one angle
  that can always be bracketed, so the solver **always** finds the answer. That's a robustness upgrade
  for the prop BEMT (`propeller/bemt.py`), which already handles windmill/negative-thrust cases, and it
  fits optimizer sweeps where one crash wastes a trial.
- **Improves:** `fansim/propeller/bemt.py` (and possibly the fan BEM's inner loop).
- **License:** NREL CCBlade **Apache-2.0**; CCBlade.jl **MIT** (both LICENSE files checked).
- **Patents:** none.
- **Effort:** S–M
- **Confidence:** medium (only worth it if the current BEMT shows convergence failures; check logs first)

---

## Notable rejects / parked (don't re-research unless the license changes)

| Item | Why parked |
|---|---|
| XFOIL (Drela) | **GPL**. Fine only as a separate optional external tool. NeuralFoil already covers this. |
| DFDC ducted fan code | **GPL** (MIT page says download = GPL acceptance). Use the theory PDF / DuctAPE.jl (MIT) instead. |
| T-Blade3 (GTSL-UC) | **GPL-2.0+** (license.txt checked). Blade-geometry builder, which fansim already has. |
| turbigen (jb753) | **GPL-3.0** (COPYING checked). |
| foamlib | **GPL-3.0**. OK only as a separate tool (like OpenFOAM itself), not vendored. |
| EricGreenwood2/BPM (Python BPM) | **GPL-3.0**. Use NASA RP-1218 + OpenFAST/BroadbandBPM.jl instead (lead 3). |
| MULTALL-open mirrors | Provenance unclear. The most-starred mirror has no license; one mirror claims Apache-2.0 but whether the original author released it that way is **not checked**. |
| Bellelli, Arina & Avallone (2025) analytic rotor–stator tonal model (NOISE-CON) | Relevant math (Sears + FW-H, handles uneven spacing), but the PDF is access-restricted ([record](https://iris.polito.it/handle/11583/3002522)). Revisit if an open version appears. |
| airfoiltools.com cambered-plate polars | XFOIL predictions, not measurements. Site terms **not checked**. |
| Noctua-specific features (Flow Acceleration Channels, Stepped Inlet) | Searched; **no Noctua/Rascom patent number found** (search not exhaustive). Marketing pages only. "Stepped leading edge" hit US12209595B2 (Go Fan Yourself LLC, *Active*) is a ceiling-mounted HVLS fan claim, so not relevant. |
| Serrated trailing-edge patents | Bio-features tested NULL in fansim, so low priority. Seen: Rolls-Royce US9951626B2 *Expired – Fee Related*; Nidec US20190226492A1 *Abandoned*; Carrier US20200240431A1 *Abandoned*; REM US11795975B2 *Active* but claim 1 is limited to industrial fans >900 mm diameter with adjustable pitch. |
