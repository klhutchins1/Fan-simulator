# Adversarial Review — Fan-simulator

> **historical, 2026-09; see docs/VALIDATION.md.** Snapshot from the first screening pass,
> not current method status.
>
> **Purpose.** A deliberately hostile audit of what we're building, what's real vs.
> aspirational, where the physics/math is wrong or untrustworthy, what's missing, and where
> we need to lean on published research. This is a **living document** — re-run this review at
> every major milestone (new fidelity tier, new objective, before any "showdown" claim) and
> update the verdicts. Bias here is toward finding fault, not celebrating progress.
>
> Last pass: after the screening optimizer + cockpit + first feature study (screening fidelity).

---

## 1. The overarching idea (steelmanned)

Automatically discover better axial-fan blades: parameterize geometry → run real CFD → score
CFM / static pressure / noise → search the design space (incl. bio-inspired features) → confirm
the best with high-accuracy CFD → distill transferable design rules → 3D-print and test. First
target: the Noctua NF-A12x25 envelope. It's a legitimate, well-scoped MDO (multidisciplinary
design optimization) problem, and the *architecture* (fidelity ladder, config-driven problem,
constraint gates, interactive cockpit) is sound.

**The honest one-line version of where we actually are:** we have a *fast, self-consistent,
low-fidelity ranking engine* and a nice UI on top of it — **not** a validated fan simulator.
Everything downstream (feature claims, design rules, "improvements") is only as trustworthy as
that low-fidelity core, and the core is currently **unvalidated against any ground truth.**

---

## 2. Current state — what is REAL vs. ASPIRATIONAL

| Claimed capability | Reality |
|---|---|
| Parametric geometry → watertight STL | ✅ real, tested |
| Automated OpenFOAM MRF CFD, parallel | ✅ real, but low fidelity (see §3) |
| CFM / static-pressure / efficiency metrics | ⚠️ computed, but **metric definitions are physically muddled** (§3.1) |
| Multi-objective optimizer finds "better" designs | ⚠️ better than a *hand guess*; not a converged optimum, noisy (§3.6) |
| Bio-inspired features help | ❌ **not established** — signal is likely confounded/noise (§3.4) |
| Noise objective | ❌ **does not exist yet** (0 of the 3 stated objectives' "noise" is implemented) |
| High-accuracy tier | ❌ planned only |
| GPU (RTX 4070 Ti) doing work | ❌ **completely idle** — FluidX3D never built |
| Validated against the real A12x25 | ❌ never — we don't know if any number is within 2× of reality |
| Generality / archetype abstraction | ❌ claimed in plans; axial fan is effectively hardcoded |

---

## 3. RED TEAM — where the math/physics is wrong or untrustworthy
(ranked by how much it threatens the project's validity)

### 3.1 (CRITICAL) The pressure & efficiency metrics are physically muddled
`static_pressure_rise = (p_out − p_in)·ρ` mixes **static** and **total** pressure and behaves
differently under the two BC modes (it even flips the sign question). A fan is properly rated by
**total-pressure rise** Δp₀ = p₀,out − p₀,in (AMCA 210 / ISO 5801), or static-to-static between
*defined* measuring planes. Efficiency is built on this muddled number, and the reported
**10–20% efficiencies are implausibly low** for an axial fan (real total efficiency ~25–45%).
Either the metric is wrong, the MRF torque is inflated, or the blade is genuinely poor — we
haven't disambiguated. **Until this is fixed, the optimizer is partly maximizing a
meaningless quantity.** Fix: implement total-pressure function objects, define measuring planes,
adopt AMCA efficiency, and re-derive.

### 3.2 (CRITICAL) The screening CFD is too coarse to trust — even for *ranking*
- **No boundary-layer resolution.** 5–6 mm cells, wall functions, uncontrolled y+, **slip duct
  walls**, no prism layers on the blade. Fan performance is dominated by viscous losses,
  separation, and **tip-leakage flow** — none of which are resolved. The tip gap has ~1 cell.
- **No grid-convergence anywhere in the screening tier.** We have *zero* evidence that the
  ranking is resolution-independent. A coarse-mesh winner can be a fine-mesh loser. The entire
  premise "screening ranks designs correctly" is **asserted, never tested.**
- **MRF (frozen rotor)** is a steady approximation with known 10–30% error for fans and is
  position-dependent; it can't see unsteady rotor wake/tip-vortex dynamics.
- **Fully-turbulent SST at a transitional Reynolds number.** Chord Re ≈ 1–3×10⁴ (20 mm chord,
  ~12 m/s) — this is **transitional/low-Re**, where fully-turbulent RANS is known to be wrong.
  No transition model (γ-Reθ). Small-fan aero lives exactly in this regime.

### 3.3 (HIGH) The rotation-direction fix was patched, not derived
`spin = −1` was set **because the result looked backwards**, not from a derived
handedness/sign convention. That the coordinate math needed an empirical flip is a smell that
the geometry↔rotation↔flow sign chain was never rigorously validated. It "works," but we don't
*understand* it — which means other sign/orientation bugs could be hiding.

### 3.4 (CONFIRMED, CRITICAL) The screening solver is NON-REPRODUCIBLE
Investigated directly (2025 probes). Findings, in order:
- The **same geometry (trial 2)** produced **cfm_load = 49.3 / 65.9 / 71.1** across nominally
  similar runs — a **~45% spread**. Rankings built on this cannot be trusted.
- It is **NOT initial-velocity bistability**: a probe solving one fixed mesh from initial
  guesses 0.5 / 2.5 / 4.5 m/s converged to **71.1 ± 0.9%** — insensitive to the initial field.
- The steady solve **never reaches residualControl** (p residual *oscillates* ~1e-2↔1e-3),
  i.e. a true steady solution may not exist — the flow at the load point is near a
  **stall/separation bifurcation** where steady RANS wanders.
- **"More iterations" makes it WORSE, not better.** Same geometry, load point: 65.9 (600 it),
  ~48 (700 it), 71.1 (1000 it, load-only), **41.6 (1500 it)**. It does not converge to a value.
  The 2 Pa load objective — the one the optimizer leaned on hardest — is **meaningless.**
- **But `cfm_free` (free delivery, back-pressure 0) stayed ~70 across every run.** Free
  delivery is on the *stable* part of the P–Q curve; the 2 Pa load is in the near-stall region.
  The instability is operating-point-specific, not global.
- **A SECOND effect — the DUCT LENGTH (domain size), not a bug.** `evaluate_candidate` used
  short ducts (inlet 2.0×… no: 1.0×/1.5× diameter) for speed; the diagnostic scripts used the
  default long ducts (2.0×/4.0×). Same geometry, same operating point: short ducts gave ~65/71
  CFM (unconverged), long ducts ~77/81 (converged). The outlet boundary sat too close to the
  fan and under-predicted flow ~15%. **Honest note: I first mis-diagnosed this as a solve-
  carryover bug and "fixed" it by isolating case dirs — which changed nothing, disproving the
  carryover theory and pointing to the real cause.** Fix: `evaluate_candidate` now uses long
  ducts (2.0×/4.0×) and mesh-once reuse (verified reproducible, no carryover).
- Trustworthy converged values for trial 2 (long ducts, 1000 it, base_cell 0.005): free delivery
  ~81 CFM, 1 Pa load ~77 CFM, efficiency ~27% — reproducible and physically plausible.
- **Methodological lesson for this review:** two wrong hypotheses (initial-condition bistability;
  solve carryover) before the mundane truth (near-stall operating point + truncated domain).
  Always change one variable at a time and confirm the fix reproduces the target before believing
  the mechanism.
- The **feature-study verdict ("features helped") is therefore not credible** — almost certainly
  a convergence/branch artifact, not aerodynamics. (Also: the features are smooth deformations,
  not real geometry — "dimples" are thickness thinning; high-amp tubercles render as serrations —
  so we may be testing the wrong geometry *and* reading noise.)
- **Silver lining:** at the converged high branch, efficiency is **26.7%** — physically
  plausible, which partially walks back §3.1's "efficiency is definitely wrong" (it was mostly
  *under-converged*, though the definition should still be fixed).

**Consequence:** every screening ranking to date (the "76 CFM winner," the Pareto front, the
feature verdict) is unreliable — they were dominated by a non-convergent load objective. This is
a screening-*objective* failure, not an architecture failure.
**Fix (Tier-2 first job), in priority order:**
1. **Redefine objectives on the STABLE part of the curve.** Drop the near-stall 2 Pa load
   point. Use free-delivery CFM (reproducible) + total-pressure rise + efficiency at free/mild
   load. Find the max back-pressure that still converges (the capture at back=0/1/2 Pa answers
   this) and stay below it.
2. **Report convergence per candidate** (now implemented: flow-drift flag) and reject/flag
   non-converged evaluations instead of trusting them.
3. **Add grid convergence** to pin `cfm_free` (it drifts ~70↔76 with mesh).
4. **Go transient (URANS/pimpleFoam + time-average)** only if a loaded operating point is truly
   required near stall — the physically correct but expensive tool.

### 3.5 (HIGH) Zero validation against ground truth
Nothing is calibrated: not against Noctua's published A12x25 P–Q + acoustic curves, not against a
CFD benchmark (e.g. an AMCA test fan or the ERCOFTAC/【advanced noise control fan】cases), not
against experiment. We literally do not know if 76 CFM is 50% high or 50% low. The baseline
"A12x25-envelope" blade isn't even the real A12x25 geometry.

### 3.6 (MEDIUM) The optimization is statistically thin
24 evaluations over a ~10-D space with NSGA-II (pop 16) is **barely past random sampling**; the
"Pareto front" of 2 points is not converged. No repeat runs, no objective-noise quantification,
no surrogate. With ~10% noise, the front is unstable run-to-run. "The optimizer found better
designs" is true only relative to a single hand-guess.

### 3.7 (MEDIUM) Printed-part physics is ignored — and it's first-order
A printed blade's dominant realities are **(a) large tip clearance** (can't hit Noctua's
<0.1 mm) and **(b) FDM surface roughness** (layer lines ~0.1–0.2 mm act as distributed
roughness/riblets). Both strongly affect CFM, efficiency, and noise. Neither is modeled. Ironic,
since the "dimple/roughness helps" hypothesis is *about* surface roughness — which we don't
simulate.

---

## 4. What's MISSING (features) — and how to get there

| Missing | Severity | Path to get there |
|---|---|---|
| **Noise objective** (Proudman/Curle proxy; LES/LBM + FW-H) | CRITICAL | Curle surface-acoustic proxy first (cheap FO); FW-H via FluidX3D on the GPU |
| **Grid-convergence / y+ control / prism layers** | CRITICAL | snappy addLayers, GCI study module (`gridindep.py`) — do on ONE design first |
| **Total-pressure / AMCA efficiency metrics** | CRITICAL | total(p) FOs + defined planes; re-derive efficiency |
| **Validation vs A12x25 + a benchmark case** | CRITICAL | digitize Noctua P–Q/noise; run a published test fan; calibrate |
| **GPU utilization (FluidX3D LBM)** | HIGH | idle 4070 Ti; fastest route to transient aero + acoustics |
| **Circular AMCA/ISO duct + no-slip walls** | HIGH | O-grid blockMesh (`testrig_cylinder.py`) |
| **Solution-uniqueness / convergence hygiene** | HIGH | potentialFoam init (done), residual monitoring, multiple-restart check, report iterative UQ |
| **Real feature geometry** (boolean dimples, literature-matched tubercles) | HIGH | trimesh boolean dimples; match Miklosovic/Howe amplitudes+wavelengths exactly |
| **Transition-sensitive turbulence (γ-Reθ SST) / low-Re** | HIGH | switch model; verify vs low-Re data |
| **Tip-clearance sensitivity study** | HIGH | parametric gap sweep — it's a dominant driver for printed parts |
| **FDM surface-roughness modeling** | MEDIUM | wall-function roughness height ks ≈ layer height |
| **Surrogate / ML models** (GP, FNO) | MEDIUM | build after objectives are trustworthy (GIGO otherwise) |
| **Motor torque–speed constraint** | MEDIUM | enforce shaft power ≤ Noctua envelope |
| **Full structural FEA (finalists)** | MEDIUM | CalculiX/FEniCS on Pareto set |
| **Print export** (STEP + slicer profile + motor mount) | MEDIUM | CadQuery STEP + OrcaSlicer CLI + adapter |
| **Real `Problem`/archetype abstraction** | LOW-now | refactor before adding a 2nd archetype |
| **Physical digital-twin loop** | LOW-now | deferred; keep `ingest.py` hook honest |

---

## 5. Where we need more RESEARCH — and how to apply it

Current bibliography is thin and features were parameterized with **arbitrary** amplitudes.
Needed, with the discipline of *replicating the paper's exact parameters/conditions*:

1. **Low-Re / transitional small-fan aerodynamics** — validate turbulence + transition choices
   in our actual Re regime (cooling fans, not aircraft).
2. **Tip-leakage flow & its noise** — dominant loss/noise source; sets required tip-gap
   resolution.
3. **MRF vs sliding-mesh (AMI) error for axial fans** — quantify the frozen-rotor penalty so we
   know screening's error bar.
4. **AMCA 210 / ISO 5801 fan-test method + fan efficiency definitions** — to fix §3.1 correctly.
5. **Tubercle (Miklosovic 2004; Fish 2011) & TE-serration (Howe 1991; the fan-specific studies)
   parameterizations** — use *their* amplitude/wavelength/Strouhal, not ours; replicate a case.
6. **LBM + FW-H aeroacoustic validation benchmarks** (e.g. Advanced Noise Control Fan) — before
   trusting any dB number.
7. **Surface roughness / riblet drag** (shark-skin, golf-ball) — to model FDM roughness and to
   test the roughness hypothesis honestly.
8. **Surrogate-assisted multi-objective optimization** (the neural-field / FNO / ShapeBench work)
   — for sample efficiency once objectives are sound.

Acquisition: arXiv (physics.flu-dyn) + AIAA/ISO for standards; keep every applied result in
`docs/bibliography.md` tagged with the fidelity it justifies.

---

## 6. What would make this materially better (prioritized)

1. **Stop trusting numbers; start validating.** Reproduce the A12x25 published P–Q curve (or a
   benchmark fan) to within a stated tolerance **before** any further optimization claims. This
   single step converts the project from "plausible demo" to "credible tool."
2. **Prove the ranking is resolution-stable.** One grid-convergence study; re-rank the current
   Pareto set at 2× resolution and see if the order survives. If it doesn't, screening needs
   rework.
3. **Fix the metric math** (total pressure, defined planes, AMCA efficiency).
4. **Quantify objective noise** (repeat 3× a few designs) and investigate the bimodal
   solution-branch hypothesis directly (restart from different init, watch convergence).
5. **Use the GPU** — FluidX3D for transient flow + noise; it's the biggest idle asset.
6. **Model the printed reality** (tip gap + roughness) — otherwise we optimize a fan we can't
   build.

---

## 6b. VALIDATION RESULT (real A12x25 STL) — the big update

Ran the CFD on the **actual A12x25 impeller geometry** (user-supplied STL, reoriented/centered):
**free-air 61.5 CFM vs published 60.1 CFM = +2%, converged.** The earlier "~30–35% over-
prediction" was **geometry, not CFD** — it came from the paddle-blade parametric approximation,
a different/higher-flow shape. On the real geometry the idealized CFD (slip walls, no frame,
open bore) is accurate to ~2% at free delivery. This substantially answers §3.5/§6.1.

**Full P–Q update (capped bore):** free-air 57.6 CFM vs 60.1 = **−4%** (bore-open was +2%, so
the true error is bracketed within ±5%). Low-load points (0–4 Pa) converge and track well. BUT
the near-shut-off region (8–20 Pa) is largely **unconverged / flow reverses**, and the sim
"shut-off" (~13 Pa) badly under-predicts the published **22.9 Pa (−45%)**. Verdict: **flow side
validated (±5%); the high-pressure / near-stall side is beyond steady RANS** (exactly as §3.4
predicted) and needs the transient (URANS/LBM) tier. The convergence gate correctly flagged the
untrustworthy points.

**Grid convergence (capped STL, free delivery):** 6mm→100k cells→56.8 CFM; 4mm→258k→57.7;
3mm→550k→**59.6** (−1% vs published 60.1). Monotonic convergence TOWARD the real value — strong
validation. NOT fully flat yet (last step 3.2%), so the screening mesh (4–5mm) carries a
**screening mesh, GCI ≈ 21 %; ranks designs, ±1 % run to run on Stock**. A finer ~2mm mesh would likely land ~60–61 CFM but
costs a lot (550k cells ≈ 16 min/point). Practical: use the screening mesh to rank designs, not as absolute CFM.
Remaining: the transient tier (URANS/LBM) for shut-off pressure + noise (GPU).


## 7. Bottom line (updated after the screening-reliability fix)

**Progress:** the screening core is now *self-consistent, converged, and reproducible* — the
biggest threat (§3.4) is resolved. Root causes were a near-stall operating point, a truncated
domain (short ducts), and under-iteration — plus convergence gating so they can't recur silently.
Trial 2 now reproduces at cfm_free 81.5 / cfm_load 76.8 / eff 27% (0.1% spread, converged), all
physically plausible. All prior rankings (opt_run1, the feature verdict) were built on the broken
setup and are **void**; a re-optimization on the fixed pipeline is running.

**Still unresolved (do not skip):**
- **Absolute validation** — the numbers are self-consistent but NOT validated against the real
  A12x25 or a benchmark; and they still move with mesh (**grid convergence** pending).
- **Noise objective still doesn't exist**; the **GPU is still idle** (FluidX3D unbuilt).
- **Features** are still smooth deformations, not real geometry; any feature claim must be
  re-tested on the fixed pipeline before it means anything.
- Metric definitions (total-pressure/AMCA) still worth tightening, though efficiency is now
  plausible.

The most dangerous failure mode remains: **believing self-consistent numbers are accurate.**
Self-consistent ≠ validated. Grid convergence + A12x25 comparison are the next non-negotiables.

## 8. Revisit checklist (run at each milestone)
- [ ] Has anything been validated against ground truth since last pass?
- [ ] Is the current headline claim resolution-stable and noise-quantified?
- [ ] Are all reported numbers using correct (total-pressure/AMCA) definitions?
- [ ] Does the GPU do useful work yet?
- [ ] Are features real geometry with literature-matched parameters?
- [ ] Any new patched-not-understood fixes (like the spin flip) to go back and derive?
- [ ] Update the tables in §2–§5 and the bottom line in §7.
