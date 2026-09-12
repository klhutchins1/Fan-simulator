<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Fan-simulator — Engineering Roadmap & TODO

**Master plan of open work.** Combines the 2026-09-01 engineering review (major sim-fidelity and
feature gaps) with the standing backlog. Check items off as they land; keep the "why" so we don't
re-litigate decisions. **This is the source of truth for what's left — read it at the start of a work
session.**

- Last reviewed: **2026-09-02** (+ open-literature deep-dive — see §7 for implementable methods)
- Tags: **[impact]** how much it changes results · **[effort]** rough build cost · owner *me* unless noted.
- Related: `docs/known-issues.md` (historical cockpit fixes), `docs/high-accuracy-plan.md` (fidelity
  ladder), `docs/design-rules.md` (extracted levers), the memory index.

---

## ★ Recommended sequence

1. **Tip shroud refinement** — partial-height ring, ring-to-frame CFD gap, and the
   winglet×shroud policy done 2026-09-03 — tip-shroud thread closed (remaining:
   circular AMCA rig / absolute pressure, tracked in §1.1/§1.5).
   §1.1 stage 1 (pinned frame ID + four-bar `frame.stl`) and §1.2 stage 1 (system curve) done 2026-09-02.
2. **ML surrogate on the catalog** (§7.4) once more CFD at application loads exists.

§3.1 application presets (`--preset case|heatsink|radiator`) and §7.1–7.3 BEM + `--bem-prescreen`
are **done**. Use a conservative BEM floor (30–35 CFM on 120 mm) when screening; default remains off.

Secondary but valuable: ML surrogate trained on the existing 110-design catalog (§7.4); FDM anisotropy +
print-penalty calibration (§1.3 / §7.6); stator vanes (§2.2); centrifugal archetype (§4.1).
**Do NOT** re-optimize tip-round or bio-features — tested null on flow AND noise.

---

## 1. Simulation fidelity — are the numbers real?

- [x] **1.1 Tip clearance + frame struts in the optimizer CFD (stage 1). DONE 2026-09-01**
  Optimizer uses **0.5 mm** min leftover (`--tip-gap`) and a four-bar stationary `frame.stl`
  downstream of the MRF zone. Spec-backed CFD pins the square duct to the frame ID
  (leftover = frame/2 − built r). Remaining: circular AMCA rig.
- [x] **1.2 Realistic operating point / system curve (stage 1). DONE 2026-09-02**
  Presets / `--load-pa` are **Pa at 50 CFM** on ΔP = k Q². Two CFD solves stay
  (free + that Pa); `cfm_load` / efficiency are the 2-point fan line ∩ parabola.
  Remaining: third CFD at the predicted op, affinity-correct P∝RPM² under derate,
  BEM prescreen on the curve.
- [ ] **1.3 FDM anisotropy in the structural gate.** **[impact: med]** **[effort: low]**
  `structural/stress.py` uses isotropic stiffness, but printed blades are weak *between layers* (~50–70%
  of in-plane). A thin swept blade can delaminate at speed. Add a layer-adhesion knockdown so the gate
  doesn't green-light un-printable-in-practice blades. Also consider a flutter/first-mode check.
- [ ] **1.4 Absolute noise (FW-H), fan + prop.** **[impact: med]** **[effort: high]**
  Fan noise is a band-limited *relative* proxy (Curle/loading); prop noise is a *relative* analytic
  proxy (`propeller/noise.py`). Both lack calibrated dB(A). A porous FW-H surface (GPU LBM) or a bench
  mic would give absolute numbers. Tonal (BPF) is validated via uneven spacing; broadband is
  coarse-grid-limited (~0.5 mm cells needed, >12 GB VRAM).
- [ ] **1.5 Full P–Q curve + shut-off pressure + grid convergence** for the buildable a12x25 designs.
  **[impact: med]** **[effort: med]** Free-air is validated (+2%); shut-off (~22.9 Pa) via steady RANS
  reads ~13 (transient GPU LBM gets ~21). Needed before any *absolute* pressure claim. See
  `docs/high-accuracy-plan.md`.
- [ ] **1.6 Low-Reynolds-number airfoils.** **[impact: high]** **[effort: med]**
  A 120 mm fan blade runs at **Re ≈ 20k–80k**; small props lower. NACA4 + standard polars are wrong
  there (laminar separation bubbles dominate). BEMT `_cl_cd` is a thin-airfoil model with no Re term.
  Fold in real low-Re airfoil data (UIUC/Selig) for both fan camber selection and prop BEMT.

## 2. Missing geometry / features fans need

- [x] **2.1 Tip shroud / ring (stage 1). DONE 2026-09-01** (`BladeParams.shroud_thick_mm`,
  cockpit slider, `--shroud`). Printable full-span ring on the built tip envelope;
  BEM drops tip-loss when the ring is on. Remaining: partial-height ring (cockpit
  `shroud_height_frac`, TE-anchored) done 2026-09-02; ring-to-frame CFD gap
  (pinned frame ID + leftover ≥ 0.5 mm) done 2026-09-02; winglet interaction
  (§7.5) done 2026-09-03 — full ring disables the winglet.
- [ ] **2.2 Stator / outlet guide vanes.** **[impact: high]** **[effort: high]** A stationary vane row
  recovers rotor swirl → more static pressure + efficiency. Every high-pressure axial fan has one.
  Needs a second (stationary) blade row in the geometry + CFD.
- [ ] **2.3 Sickle / forward-swept planform.** **[impact: med]** **[effort: med]** The real Noctua uses
  swept "AAO" sickle blades for noise. We have sweep/lean/skew but not a true forward-swept sickle LE.
- [ ] **2.4 Infill-aware weight.** **[impact: low]** **[effort: low]** Weight uses solid volume; real
  prints use infill, so the 65 g cap is pessimistic (rejects buildable designs). Make it infill-%-aware.
- [ ] **2.5 RPM as a lever / real motor torque–speed curve.** **[impact: med]** **[effort: med]** RPM is
  pinned to rated; a lighter printed rotor could spin faster on the same motor. Model the motor curve or
  optimize RPM within it. (Over-voltage leeway exists but is a manual knob.)
- [ ] **2.6 Stepped inlet / notched tips** (Noctua's own tone tricks). **[impact: low]** **[effort: med]**

## 3. Objectives, constraints & settings to revisit

- [x] **3.1 Application presets (case / heatsink / radiator). DONE 2026-09-01**
  (`fansim/optimize/presets.py`, `--preset` on `scripts/run_optimization.py`). **[impact: high]**
  **[effort: low]** ★ Each preset sets the application impedance: **case = 8 Pa**, **heatsink = 20 Pa**,
  **radiator = 35 Pa** are **Pa at 50 CFM** on ΔP = k Q². The CFD probe is still that Pa; scored
  `cfm_load` / efficiency are the 2-point fan line ∩ system curve operating point. NSGA-II still
  maximizes (free CFM, load CFM, efficiency); the impedance is what changes which designs win.
  `--load-pa` still overrides. Historical default remains 1 Pa when neither flag is set.
- [ ] **3.2 Re-open `max_camber` (guided 0–0.02) + blade count (5–8).** **[impact: med]** **[effort: low]**
  Those bounds were tuned for the *free-air* objective; under real back-pressure, more camber and more
  blades (9–13) earn their keep. Widen per the radiator preset.
- [ ] **3.3 Smarter frame tip cap.** **[impact: low]** **[effort: low]** `max_tip_radius = frame/2 − 4 mm`
  is a flat, conservative margin that throws away blade length. Compute the *actual* bulge from chord/lean
  per candidate instead of a fixed 4 mm.
- [ ] **3.4 Auto-fit on export (optional).** **[impact: low]** **[effort: low]** The cockpit has manual
  hub/tip/depth fitters; consider an opt-in "fit to frame on export" (like the hub-grow toggle), with the
  aero-cost caveat.

## 4. New archetypes (design classes the axial fan can't cover)

- [ ] **4.1 Centrifugal / mixed-flow impeller.** **[impact: high]** **[effort: high]** At high
  back-pressure an axial fan *cannot* compete with a centrifugal/mixed-flow one. The Problem/archetype
  layer was built for exactly this — highest-value *new archetype*.
- [ ] **4.2 Counter-rotating stacked rotors.** **[impact: med]** **[effort: high]** Big static gains.
- [ ] **4.3 Prop compressible open-air CFD tier.** **[impact: med]** **[effort: high]** BEMT screens
  props; a real CFD pass refines finalists (tips run Mach 0.4–0.58, where BEMT/incompressible is weak).

## 5. Physical validation loop — the north star (needs hardware; owner: **user**)

- [ ] **5.1 Print a real-frame design + measure** CFM / static / noise / weight. Recorder is built
  (material/print-type/weight fields). **Nothing is measured yet** — the whole design layer is unvalidated
  (only the CFD *engine* is, on the real STL). One measurement changes "hypothesis" → "result."
- [ ] **5.2 Calibrate the sim** from the measurement (the store's sim-vs-real + calibration hooks exist).

## 6. Research / papers to fold into `docs/bibliography.md`

- [ ] Tip leakage physics — **Storer & Cumpsty (1991)**, Denton loss mechanisms (→ §1.1, §2.1).
- [ ] Low-Re airfoils — **UIUC/Selig low-Reynolds-number database**, Lissaman review (→ §1.6).
- [ ] Shrouded/ducted fans; casing treatments / recirculation for stall margin (→ §2.1).
- [ ] Fan broadband noise — **Sharland (1964)** (complements Curle/FW-H).
- [ ] Swept/sickle automotive cooling-fan noise studies (→ §2.3).
- [ ] 3D-printed impeller performance — FDM surface-roughness & anisotropy (→ §1.3, sim→print penalty).
- [ ] Props — **Hanson** open-rotor/CROR noise; QProp/JavaProp Re + compressibility BEMT corrections.

---

## 7. Researched implementable methods (2026-09-01 literature deep-dive)

Concrete, open-source / academically-usable methods found in the literature. These are the
"groundbreaking" levers — several are directly implementable and cross-reference the sections above.

- [x] **7.1 Axial-fan BEM screening tier — a COMPUTE-FREE fan performance model (the fan analog of our
  prop BEMT). DONE 2026-09-01** (`fansim/fan_bem.py` + `--bem-prescreen CFM_FLOOR` on
  `scripts/run_optimization.py`). Blade-element + Euler + slip/endwall + Re-aware polar (§7.2) +
  Prandtl/gap tip loss (§7.3). **Validated: reference free-delivery ~63 CFM vs CFD ~65.** Ranking vs
  CFD Spearman **~0.62** after §7.3 — usable as a **coarse** pre-screen, not a CFD replacement.
  Pre-screen is **off by default** (floor 0). Set a conservative floor (e.g. 30–35 CFM on 120 mm) so
  only clearly-dead designs skip the ~5 min CFD. A BEM crash never fails the eval (falls through to
  CFD). **[impact: very high]** **[effort: high]** ★★
  A blade-element + free-vortex method predicts a fan's CFM / static-pressure rise / efficiency / power
  *analytically, in milliseconds* — no CFD — using the **Euler turbomachinery equation** for pressure
  rise, blade-element lift/drag (with low-Re polars, §7.2), and empirical loss correlations (incl. tip
  clearance, §7.3). Lets the optimizer screen thousands of fan designs instantly and spend CFD only on
  finalists — exactly what made the prop side instant. Also directly *corrects* the pressure/CFM the
  question asked about (Euler + loss models are physically grounded, not slip-wall RANS). Refs:
  [FAN2018 low-pressure axial-fan blade design/optimization](https://www.fan2025.org/archives/fan2018/papers/FAN2018-7-WINTERBERG.pdf),
  [model-based low-pressure axial-fan blade design](https://www.sciencedirect.com/science/article/abs/pii/S0140700724003116),
  [ducted counter-rotating axial fans (design+validation)](https://arxiv.org/pdf/1208.6396). → feeds §1, §3.
- [x] **7.2 Reynolds-aware airfoil polar. DONE 2026-09-01** — `_cl_cd(alpha, camber, re=)` now applies
  low-Re trends (max-lift ↓, stall earlier, profile drag ↑ steeply, lift slope ↓ as Re falls), keyed to
  the local Re = W·c/ν; both fan BEM and prop BEMT feed it. **[impact: high as physics; effort: med]**.
  Grounded in the UIUC/Selig low-Re data ([site](https://m-selig.ae.illinois.edu/ads.html),
  [low-speed data v1](https://m-selig.ae.illinois.edu/uiuc_lsat/Low-Speed-Airfoil-Data-V1.pdf)).
  OUTCOME (honest): made the physics correct (prop FM 0.78→0.71 = more realistic; fan ref free-delivery
  stable 64.5 CFM) but did **NOT** move the fan ranking (Spearman 0.55→0.52) — so the airfoil polar was
  *not* the fan-ranking bottleneck. That points at §7.3 (tip clearance = design-dependent loss) and/or
  the global constant deviation/SLIP + un-modelled 3-D wrap/lean/radial-equilibrium effects the CFD sees.
  FUTURE (optional): tabulate real UIUC polars per airfoil family instead of the analytic low-Re model.
  15 BEM/prop tests pass. → implements §1.6; ranking still needs §7.3.
- [x] **7.3 Tip-clearance loss in the fan BEM. DONE 2026-09-01.** Added a **Prandtl finite-blade tip-loss
  factor** (design-dependent — fewer blades / higher tip loading = more loss) + a gap-based leakage
  knockdown in the outer span (`tip_gap_mm`), reducing the useful swirl near the tip. **[impact: high]**
  OUTCOME: this was the ranking lever the polar wasn't — **fan ranking Spearman 0.52 → 0.62** (design-
  dependent loss differentiates the blade-count/loading the CFD sees), free-delivery still validated
  (63 vs 65). The BEM is now a usable **coarse pre-screen**. Honest ceiling: ~0.6-0.7 is likely the limit
  for a mean-line BEM — the rest is genuine 3-D flow (radial equilibrium, wrap/lean) a 1-D radial model
  can't capture. Pre-screen is wired (`--bem-prescreen`); optionally borrow the same tip-loss as a
  post-hoc correction on the CFD numbers (§1.1). Refs:
  [tip-gap analysis](https://www.sciencedirect.com/science/article/abs/pii/S0045793019300088),
  [energy dissipation in the blade tip region](https://www.sciencedirect.com/science/article/abs/pii/S0022460X16302772).
- [ ] **7.4 ML / kriging surrogate tier trained on our own catalog.** **[impact: high]** **[effort: med-high]**
  We already have **110+ CFD-evaluated designs** catalogued — enough to train a surrogate (kriging/RBF/GP
  now; CNN or neural-field field-predictor later) that predicts CFM/eff/pressure from the geometry vector,
  cutting CFD calls per optimizer generation. Interpretable XGBoost is a low-risk start. Refs:
  [ML-in-CFD-for-turbomachinery review](https://doi.org/10.3390/ijtpp7020016),
  [C(NN)FD deep-learning turbomachinery CFD](https://arxiv.org/pdf/2306.05889),
  [airfoil ML + surrogate modelling](https://pmc.ncbi.nlm.nih.gov/articles/PMC11024608/). → speeds §1, the optimizer.
- [x] **7.5 Tip shroud/ring — with the RIGHT clearance, and the winglet interaction. DONE 2026-09-03.** **[impact: high]**
  **[effort: med]** CFD clearance (pinned frame ID, leftover ≥ `--tip-gap`) is in.
  Winglet×shroud policy DONE 2026-09-03: `--shroud` searches a TE-anchored
  `shroud_height_frac ∈ [0.30, 1.0]`; a winglet is applied only when the ring is not
  full-span (`shroud_is_full`), enforced in `suggest_params` and `blade_from_flat`
  (cockpit inherits it). See `docs/superpowers/specs/2026-09-03-winglet-shroud-policy-design.md`.
  Refines §2.1: a tighter shroud raises static pressure + static efficiency, but there's
  an **optimal** tip clearance (max efficiency at shroud height ≈ 30% of axial chord — not zero), and
  **winglets HELP a partially-shrouded fan but HURT a fully-shrouded one** (so our ~+4% winglet result is
  shroud-dependent). Winglets are the fallback when the tip gap can't be tightened. Refs:
  [effect of tip geometry on low-speed axial fan](https://www.sciencedirect.com/science/article/abs/pii/S0140700721003273),
  [winglet designs for small axial fans (exp+num, 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0003682X24005991),
  [tip clearance, winglets & shroud height on tip leakage](https://www.sciencedirect.com/science/article/abs/pii/S0140700718302470). → refines §2.1, §2.x winglet.
- [ ] **7.6 Sim→print penalty calibration from published printed-impeller studies.** **[impact: med]**
  **[effort: low]** Studies comparing metal vs FDM-plastic impellers quantify the roughness + deflection
  penalty — use them to set a knockdown so the tool predicts *printed* performance, not idealized. Bonus
  finding: **thick blades give a flatter efficiency curve + more stable operation across impedance** (a
  robustness lever). Refs:
  [tip-vortex manipulators, num vs experimental on printed condenser fan](https://arxiv.org/pdf/2309.13195),
  [blade-thickness effects on axial-fan performance](https://www.academia.edu/70824092/Experimental_study_of_blade_thickness_effects_on_the_global_and_the_local_performances_of_axial_flow_fans). → feeds §1.3, §5.

---

## Recently shipped (context, so we don't re-add)
Corrected a12x25 spec (37.25 mm hub / 110 mm / 25 mm) + generic_120 model · frame-aware search + real-frame
optimization (~54 CFM buildable) · 3 frame fitters + "fits this fan" plot filter + fan-model manager ·
prop archetype (spec→geometry→BEMT→optimizer→graph) + relative prop-noise model · print-detail measurement
recording · radius-aware printability · fast non-fused preview · `--reload` process/container reaping ·
honest scorecard. Axial-fan BEM screen + `--bem-prescreen` · `--preset case|heatsink|radiator` ·
tip shroud / ring (stage 1) + `--shroud` · TE-anchored partial ring + shroud height slider
(stage 2) · honest optimizer CFD (stage 1): 0.5 mm tip gap +
four-bar `frame.stl` + `--tip-gap` · realistic system curve (stage 1): Pa @ 50 CFM presets,
2-point fan line ∩ ΔP = k Q² for `cfm_load` / efficiency · pinned frame-ID CFD duct +
leftover `--tip-gap` floor · winglet×shroud policy (§7.5): `--shroud` searches a partial-ring
height and the winglet is gated off on full rings, in `suggest_params` + `blade_from_flat`.
Tip-round and bio-features (tubercles/serrations/dimples) = tested NULL on flow AND
noise — **do not re-optimize for tip shape.**
