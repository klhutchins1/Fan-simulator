# High-Accuracy Validation & Design-Transfer Plan

## Context

The screening optimizer (Phase 3, working) evaluates many blade designs cheaply and ranks
them. Its numbers are trustworthy for **relative** ranking but are screening-grade in
absolute terms (square box duct, ~5–6 mm mesh, ~10% convergence noise, feature wavelengths
near mesh size). This plan adds the **middle and end of the fidelity ladder**:

```
Tier 1  SCREENING        fast, many designs, relative ranking          (done)
   │  confidence gate  → promote the best, robust, diverse handful
Tier 2  HIGH-ACCURACY    few designs, trustworthy absolute numbers + real noise + UQ   (this plan)
   │  design-knowledge extraction → transferable rules for other fans
Tier 3  PHYSICAL         print winners, measure, calibrate the sim      (hooks now, rig later)
```

**Goal:** turn screening winners into *high-confidence, defensible* results — with real
dB(A) noise, quantified uncertainty, and cross-solver agreement — then (a) distill
**transferable design principles** ("what drives CFM / static pressure / noise") that apply
to other fans, and (b) print the validated winners for real-world testing.

Honest driver: only Tier-2 numbers are strong enough for a "fan showdown" claim; Tier-1 is
for search, not for reporting absolute performance.

---

## Tier 1 → Tier 2 promotion (the confidence gate)

Not every screened design is worth an expensive run. Promote ~**6–12 finalists** chosen for:

1. **Pareto rank** — on the screening front for (CFM_free, CFM_load, efficiency).
2. **Robustness** — re-evaluate each candidate 2–3× (or at one step finer mesh) and keep
   those whose objectives are *stable* (not sitting on convergence-noise knife-edges). This
   directly implements "high-confidence results" — a design that only looks good because of
   screening noise is filtered out here.
3. **Diversity** — cluster the design vectors and pick representatives across the space
   (e.g. a high-flow design, a high-pressure design, a balanced one), not near-duplicates.
4. **Manufacturability confirmed** — printability + centrifugal gates already passed.

Module: `fansim/optimize/ladder.py` — `select_finalists(study, k, reeval=…)`.

---

## Tier 2: high-accuracy CFD

Per finalist, a rigorous ducted-fan analysis:

- **Circular duct test rig** (replaces the square box) sized per **AMCA 210 / ISO 5801**
  ducted-fan method: O-grid `blockMesh` cylinder, straight settling lengths, honeycomb-free
  ideal inlet. → `fansim/cfd/testrig_cylinder.py`.
- **Boundary-layer resolution** — prism layers on the blade + hub (snappy `addLayers`) to a
  turbulence-model-appropriate y+ (low-Re SST, y+≈1, or wall-function y+≈30–50, chosen and
  documented), plus explicit **tip-gap** cell count (≥8 cells across the printed clearance).
- **Grid-independence** — 3 systematically refined meshes; report **GCI** (Grid Convergence
  Index, Roache) and Richardson-extrapolated values so discretization error is *quantified*,
  not assumed. → `fansim/cfd/gridindep.py`.
- **Full P–Q curve** — 6–10 operating points (reuse the sweep infra), giving free delivery,
  shutoff, best-efficiency point, and the curve shape — not just 2 points.
- **Tight convergence** — residuals to 1e-6, or time-averaged if scale-resolving.
- **Uncertainty quantification** — combine discretization (GCI), iterative, and
  turbulence-model-form uncertainty (e.g. SST vs k-ε spread) into an error bar on each
  reported number.
- **Cross-solver check** — run the same finalist in **FluidX3D (GPU LBM)** and OpenFOAM;
  agreement within tolerance is itself a confidence signal, disagreement flags a problem.

Modules: `fansim/cfd/hifi.py` (case + orchestration), extend `openfoam_case.py` for layers +
cylinder rig, `fansim/cfd/lbm_fluidx3d.py` (GPU driver).

---

## Tier 2: real acoustics (the honest noise number)

Screening uses RANS proxies (Proudman/Curle). Tier 2 produces true noise:

- **Transient scale-resolving flow** — DES/DDES (OpenFOAM `pimpleFoam`) or LES, sliding-mesh
  (AMI) rotor rather than steady MRF, run long enough to time-average.
- **Ffowcs-Williams–Hawkings acoustic analogy** — permeable-surface FW-H → far-field
  pressure → **dB(A) + 1/3-octave spectrum** with the blade-passing-frequency tones and
  broadband floor separated. → `fansim/acoustics/fwh.py`.
- **GPU fast path** — FluidX3D LBM is a proven, much faster route to transient fan
  aeroacoustics on the RTX 4070 Ti (literature: LBM+FW-H for axial fans). Use it as the
  primary noise engine; cross-check 1–2 finalists with OpenFOAM DES+FW-H.
- Output: A-weighted SPL at a standard distance + spectrum, per operating point — the number
  a "showdown" actually needs.

Recommendation: **FluidX3D (GPU) for the noise workhorse, OpenFOAM DES for spot cross-checks.**

---

## Design-knowledge extraction (transfer to other fans)

The point of "what can be used in other fan designs" — turn the trial database into rules:

- **Global sensitivity analysis** — Sobol indices (SALib) over the accumulated trials:
  which parameters (blade count, stagger, sweep, camber, each feature) most drive CFM,
  static pressure, and noise, and which interact. → `fansim/analyze/sensitivity.py`.
- **Surrogate model + interpretation** — fit a Gaussian-process / gradient-boosted surrogate
  to (design → objectives); use feature importance + partial-dependence to state principles
  ("solidity above ~0.8 buys load capability at an efficiency cost", "TE serrations cut
  broadband noise ≥ X dB above Strouhal Y", etc.).
- **Transfer** — express the principles as archetype-independent guidance and feed them into
  the `Problem`/archetype layer so a centrifugal or wind-turbine run starts from learned
  priors, and into the optimizer as informed bounds/seeds.
- Deliverable: `docs/design-rules.md` — a living, evidence-linked list of principles, each
  tagged with the fidelity that supports it (screening vs high-accuracy vs measured).

---

## Tier 3: physical validation (print → measure → calibrate)

Deferred build (no calibrated instruments / no Noctua on hand yet), but designed for:

- **Print** finalists in PETG (default), balance the rotor, mount on the Noctua motor.
- **Measure** (when equipped): airflow (anemometer/flow bench), static pressure (manometer +
  plenum), noise (calibrated mic, A-weighted + spectrum), RPM (tach). Even now, the regular
  mic supports **relative A/B** noise deltas, and an anemometer supports relative airflow.
- **Calibrate** — `validation/ingest.py` fits sim constants (tip-clearance loss, turbulence,
  LBM viscosity) to the measurements, closing the digital twin. Report sim-vs-measured error.

---

## Compute strategy

- **GPU (RTX 4070 Ti)** → FluidX3D transient LBM + FW-H (the noise + cross-check workhorse).
- **CPU (8 cores)** → OpenFOAM fine RANS grid-independence + DES spot checks; already parallel.
- **Batching** → Tier-2 runs are hours each; run finalists overnight; a small cloud burst is
  optional for a larger finalist set. Budget ~a handful of finalists per overnight batch.

---

## Modules to build (extends the current tree)

```
fansim/cfd/testrig_cylinder.py   # O-grid circular duct (AMCA/ISO)
fansim/cfd/gridindep.py          # 3-mesh GCI / Richardson
fansim/cfd/hifi.py               # high-accuracy case + full P-Q + UQ orchestration
fansim/cfd/lbm_fluidx3d.py       # GPU LBM driver (flow + cross-check)
fansim/acoustics/fwh.py          # transient FW-H -> dB(A) + spectrum
fansim/optimize/ladder.py        # confidence-gated finalist selection
fansim/analyze/sensitivity.py    # Sobol + surrogate + transferable rules
validation/ingest.py             # measured-data calibration (Tier 3 hook)
scripts/run_hifi_validation.py   # promote finalists -> Tier-2 report
scripts/extract_design_rules.py  # trial DB -> design-rules.md
```

---

## Suggested sequencing

1. **Circular duct + layers + grid-independence** on one known design (establish GCI, y+,
   and how much the absolute numbers move vs the box duct). *This is the credibility keystone
   — do it first.*
2. **Confidence gate** (`ladder.py`) — re-eval-based finalist selection from the current
   screening study.
3. **Tier-2 RANS full-P–Q** on finalists (trustworthy CFM/static-pressure + UQ).
4. **GPU LBM acoustics** (FluidX3D + FW-H) for real dB(A); OpenFOAM DES cross-check on 1–2.
5. **Design-rule extraction** (Sobol + surrogate) → `design-rules.md`.
6. **Print** top finalists; wire `ingest.py`; add instruments later to close Tier 3.

## Verification / definition of done

- Grid-independence: GCI below a stated threshold (e.g. < 3%) on CFM and static pressure.
- Cross-solver: OpenFOAM vs FluidX3D agree within a stated tolerance on the P–Q curve.
- Every reported Tier-2 number carries an uncertainty bar.
- Acoustics: A-weighted SPL + spectrum reproduced within tolerance across a mesh refinement.
- Design rules each cite the trials/fidelity that support them.
- (Tier 3) sim-vs-measured within a documented error band after calibration.
