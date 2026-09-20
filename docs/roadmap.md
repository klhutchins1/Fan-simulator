<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Fan-simulator — Engineering Roadmap & TODO

**Master plan of open work.** Combines the 2026-09-01 engineering review (major sim-fidelity and
feature gaps) with the standing backlog. Check items off as they land; keep the "why" so we don't
re-litigate decisions. **This is the source of truth for what's left — read it at the start of a work
session.**

- Last reviewed: **2026-09-16**. **§12** + **§13** + **§7.6** + **§14.1–14.6** closed in code.
  Stock close-ref fidelity (§2.7–2.8). **§13.22–13.24** / **§14.3b** /
  **§14.6** / **§15.1–15.6** landed 2026-09-16. Still **not shippable** until Validation P–Q /
  print+measure — see `a12x25_pq_report.md`
- Tags: **[impact]** how much it changes results · **[effort]** rough build cost · owner *me* unless noted.
- Related: `docs/known-issues.md` (historical cockpit fixes — **stale**, see §13.4), `docs/high-accuracy-plan.md` (fidelity
  ladder), `docs/design-rules.md` (extracted levers), the memory index.
  Canvases: `math-application-audit.canvas.tsx` (fidelity) · `production-readiness-review.canvas.tsx` (hygiene).

---

## ★ Recommended sequence

1. ~~**§13 hygiene**~~ — parse/CI/ruff critical/fan_tab UI split/mypy/MIT — closed 2026-09-15.
   Leftover geometry perf: ~~**13.22**~~ / ~~**13.23**~~ / ~~**13.24**~~ (2026-09-16).
2. ~~Math audit / §12~~ — cockpit thickness, Fit, scoring honesty closed 2026-09-15.
3. ~~Noctua reference geometry (Phase 2)~~ — envelope + Stock yaml; close-ref STL under `validation/reference/`.
   Stock gold ✕ cylinder-sliced to the close-ref (plate wall, tip ~33 mm chord, `blade_hub_z`); not OEM CAD.
   **2026-09-15 evening:** hub 16.5 / PCHIP / cambered plate / sharp TE / boxy tip notches (§2.7–2.8).
   Open: **2.3b** sickle UX review (keep for now; odd to edit).
4. **Validation P–Q (Phase 3 remainder)** — close-ref STL free-air **−17%**. Screening levers exhausted. See `a12x25_pq_report.md`.
5. **Print + measure (Phase 5)** — `docs/validation/north-star-staged.md`; **do not** check §5.1 until hardware data exists. Primary path to close absolute free-air.
6. ~~**§14 Archetype Design Parity (stage 1)**~~ — Prop/Mixed/Volute/CROR Design depth landed 2026-09-15.
   Leftovers: none for stage-1 Design UI (~~14.4b~~ 2026-09-16).
7. **§15 adversarial leftovers** — ~~15.1–15.6~~ all done 2026-09-16 (incl. 15.5 binder split).
8. **Only then** surrogate depth (§7.4 NN/FNO), absolute noise (§1.4), archetype CFD depth (§4.x).

§8 / §9 / §10 / §12 / §13 stage-1 are **closed in code**. Absolute CFM honesty waits on hardware (§5) or a new fidelity lever beyond screening.
Phases 4.1 / 4.2 / 6.1 landed (dependency audit, perf baseline, keep/cut board).
**Do NOT** re-optimize tip-round or bio-features — tested null on flow AND noise.
**Do NOT** datasheet-tune Stock from BEM (stagger candidate CFD +0.6 CFM only).

---

## 1. Simulation fidelity — are the numbers real?

- [x] **1.1 Tip clearance + frame struts in the optimizer CFD (stage 1). DONE 2026-09-01**
  Optimizer uses **0.5 mm** min leftover (`--tip-gap`) and a four-bar stationary `frame.stl`
  downstream of the MRF zone. Spec-backed CFD pins the square duct to the frame ID
  (leftover = frame/2 − built r). Remaining: circular AMCA rig.
- [x] **1.2 Realistic operating point / system curve (stage 1). DONE 2026-09-02**
  Presets / `--load-pa` are **Pa at 50 CFM** on ΔP = k Q². Two CFD solves stay
  (free + that Pa); `cfm_load` / efficiency are the 2-point fan line ∩ parabola.
  Remaining: third CFD at the predicted op (cockpit refine-op exists).
  **2026-09-15:** axial affinity `P∝RPM²` under derate + BEM hose-op prescreen landed
  (`objectives.py`, matches mixed/CROR/volute).
- [x] **1.3 FDM anisotropy in the structural gate (stage 1). DONE 2026-09-14** **[impact: med]** **[effort: low]**
  `LAYER_ADHESION_K=0.60` on centrifugal yield (`structural/stress.py`) + `FDM_E_K=0.70` on tip
  deflection / flutter modulus (`structural/deflection.py`, §10.11). Tests: `tests/test_stress.py`,
  `tests/test_deflection.py`. Remaining: full orthotropic FEA / first-mode flutter depth.
- [ ] **1.4 Absolute noise (FW-H), fan + prop.** **[impact: med]** **[effort: high]**
  Fan noise is a band-limited *relative* proxy (Curle/loading); prop noise is a *relative* analytic
  proxy (`propeller/noise.py`). Both lack calibrated dB(A). A porous FW-H surface (GPU LBM) or a bench
  mic would give absolute numbers. Tonal (BPF) is validated via uneven spacing; broadband is
  coarse-grid-limited (~0.5 mm cells needed, >12 GB VRAM).
- [ ] **1.5 Full P–Q curve + shut-off pressure + grid convergence** for the buildable a12x25 designs.
  **[impact: med]** **[effort: med]** **Partial (2026-09-14; free-air corrected 2026-09-18):** free-air mesh ladder + GCI at tip_gap 0.5 mm. The 2026-09-14 ladder read ~44.7 CFM but varied `base_cell` only and left the ~1.5 mm blade wall under-resolved; resolving it (surf3 + tail-mean) gives grid-converged **~48–51 CFM (Richardson ≈50.8, −15…−20% vs 60.1)**. tip/frame/wall_ks/stagger A/Bs documented. Stock multi-back P–Q at **0.5 mm** tip: shut-off **proxy ~24.0 Pa** (interim ±5 Pa **pass**; 18 Pa mildly unconverged). Free-air interim ±10% **still fail** (even corrected). Absolute shut-off still needs a converged Q→0 (or agreed) solve before datasheet claims. See `docs/validation/a12x25_pq_report.md` (correction banner) §9.
- [x] **1.6 Low-Reynolds-number airfoils (stage 1). DONE 2026-09-13**
  UIUC/Selig CSVs in `fansim/data/polars/` + `cl_cd_table` wired into `_cl_cd`
  (`tests/test_uiuc_polars.py`). Remaining: broader family coverage / cockpit airfoil picker.

## 2. Missing geometry / features fans need

- [x] **2.1 Tip shroud / ring (stage 1). DONE 2026-09-01** (`BladeParams.shroud_thick_mm`,
  cockpit slider, `--shroud`). Printable full-span ring on the built tip envelope;
  BEM drops tip-loss when the ring is on. Remaining: partial-height ring (cockpit
  `shroud_height_frac`, TE-anchored) done 2026-09-02; ring-to-frame CFD gap
  (pinned frame ID + leftover ≥ 0.5 mm) done 2026-09-02; winglet interaction
  (§7.5) done 2026-09-03 — full ring disables the winglet.
- [x] **2.2 Stator / outlet guide vanes (stage 1). DONE 2026-09-13** **[impact: high]** **[effort: high]**
  Plate OGV row in `fansim/cfd/stator.py`, `--stator` / `--stator-stack`, OpenFOAM `stator.stl`
  (`tests/test_stator.py`). Remaining: cambered OGVs, searched vane count, measured η gain.
- [x] **2.3 Sickle / forward-swept planform (stage 1). DONE 2026-09-13** **[impact: med]** **[effort: med]**
  `apply_sickle` + Optuna `--sickle` (`tests/test_sickle.py`). Cockpit Design LE sickle mid/tip
  sliders (`e_le_skew_*`) landed 2026-09-15. Remaining: Optuna mid-band search (independent mid
  vs tip) beyond tip-only `--sickle`.
  - [x] **2.3b Sickle UX / semantics review. REVIEWED 2026-09-18 → keep.** **[impact: low]**
    The "odd to edit" concern is already mitigated: the `slider()` widget surfaces the detailed
    `CONTROL_DESC` tooltips for `e_le_skew_mid`/`e_le_skew_tip`, which explain the LE-only tangential
    skew and both caveats (not live — press Preview; a timed-out tip-notch build keeps the old mesh
    so sickle can look like a no-op). Keeping independent **mid + tip** sliders gives more planform
    control than the tip-only Optimize `--sickle` at no cost, so **not** collapsed/parked. Labels
    ("Sickle" vs the separate "Skew") stay — distinct words, and the tooltips disambiguate.
- [x] **2.4 Infill-aware weight (stage 1). DONE 2026-09-14** **[impact: low]** **[effort: low]**
  `estimate_weight_g(..., infill_frac=)` defaults to ``DEFAULT_PRINT_INFILL=0.20`` for FDM filaments
  (resin stays solid). Build gate no longer assumes 100% fill. Override with ``infill_frac=1.0`` for
  solid-mass checks. Tests: `tests/test_fan_spec.py`.
- [x] **2.5 RPM as a lever / real motor torque–speed curve (stage 1). DONE 2026-09-13**
  `fansim/optimize/motor_curve.py` stamps + operating RPM on mixed/volute/CROR evaluate
  (`tests/test_search_rpm.py` — CLI + `run_study` → `evaluate_candidate(rpm=…)`). Remaining: full PWM search in all archetypes.
- [x] **2.6 Stepped inlet / notched tips (stage 1). DONE 2026-09-13** **[impact: low]** **[effort: med]**
  `apply_notched_tips` + `--notched` / cockpit flags (`tests/test_notched_tips.py`).
  **2026-09-15:** boxy/skewed rectangular tip TE bites (not sine lobes); Design Tip panel switch +
  depth; Stock reference enables them; control images `e_tip_notched` / `e_tip_notch_depth`.
- [x] **2.7 Cambered plate face curve / scoop (hub→tip). DONE 2026-09-15** **[impact: med]** **[effort: low]**
  Rounded plate previously ignored camber (flat paddle). `rounded_plate` now bows with NACA
  meanline (`max_camber` / `camber_pos`) so Camber root/mid/tip create the tip-on **scoop**
  (LE↔TE face curve) along the span — matches the white close-ref overlay vs a flat black
  paddle. UI copy says “scoop”; technical name remains camber. Slider max raised to **0.15**;
  Stock tip camber **0.12**. Wrap/lean still owns spanwise planform twist. Tests:
  `tests/test_rounded_plate.py`.
- [x] **2.8 Plate sharp TE + Stock close-ref defaults. DONE 2026-09-15** **[impact: med]** **[effort: low]**
  Plate TE roundness via `te_thick_scale` (1 = bullnose, ~0.2 = sharp); Stock
  `a12x25_reference.yaml`: hub **16.5**, `span_interp=pchip`, `te_thick_scale=0.2`, tip notches **off**,
  tip chord **36**, tip stagger **15°**, `blade_hub_z` **5**, skew mid/tip **6/13** (mid raised
  from 3 to ease mid-span LE bump under PCHIP; tip wrap kept).

## 3. Objectives, constraints & settings to revisit

- [x] **3.1 Application presets (case / heatsink / radiator). DONE 2026-09-01**
  (`fansim/optimize/presets.py`, `--preset` on `scripts/run_optimization.py`). **[impact: high]**
  **[effort: low]** ★ Each preset sets the application impedance: **case = 8 Pa**, **heatsink = 20 Pa**,
  **radiator = 35 Pa** are **Pa at 50 CFM** on ΔP = k Q². The CFD probe is still that Pa; scored
  `cfm_load` / efficiency are the 2-point fan line ∩ system curve operating point. NSGA-II still
  maximizes (free CFM, load CFM, efficiency); the impedance is what changes which designs win.
  `--load-pa` still overrides. Historical default remains 1 Pa when neither flag is set.
- [x] **3.2 Re-open `max_camber` + blade count in GUIDED search. DONE 2026-09-13** **[impact: med]** **[effort: low]**
  `GUIDED` / `GUIDED_LC` match OPEN hose bounds (`n_blades` 5–11, `max_camber` 0–0.06;
  `tests/test_search_space.py`).
- [x] **3.3 Smarter frame tip cap. DONE 2026-09-13** **[impact: low]** **[effort: low]**
  `TIP_CAP_CLEARANCE_MM` + per-candidate `frame_half_mm` on `suggest_params` (not flat 4 mm).
- [x] **3.4 Auto-fit on export. DONE 2026-09-15** **[impact: low]** **[effort: low]**
  Cockpit Design defaults: **Fit hub to motor on export** + **Fit tip/depth to frame on export**
  (`export_fit_hub` / `export_fit_frame` → `prepare_export_flat`). Aero-cost caveat stays in the UI copy.

## 4. New archetypes (design classes the axial fan can't cover)

- [x] **4.1 Centrifugal / mixed-flow impeller (stage 1 scaffold). DONE 2026-09-13** **[impact: high]** **[effort: high]**
  `MixedFlowArchetype`, geometry + evaluate + cockpit tab (`tests/test_mixed_flow*.py`). Remaining: high-Pa hose wins vs axial.
- [x] **4.2 Counter-rotating stacked rotors (stage 1 scaffold). DONE 2026-09-13** **[impact: med]** **[effort: high]**
  `CrorArchetype` + dual-MRF evaluate (`tests/test_cror.py`). Remaining: noise + measured static gain.
- [ ] **4.3 Prop compressible open-air CFD tier.** **[impact: med]** **[effort: high]** BEMT screens
  props; a real CFD pass refines finalists (tips run Mach 0.4–0.58, where BEMT/incompressible is weak).

## 5. Physical validation loop — the north star (needs hardware; owner: **user**)

- [ ] **5.1 Print a real-frame design + measure** CFM / static / noise / weight. Recorder is built
  (cockpit → `validation/measurements/` with material/print-type/weight fields). **Nothing is
  measured yet** — one real point changes hypothesis → result. **Print-fit kit ready**
  (`scripts/export_a12x25_print_ready.py` + mount gauge vs measured MotorMount / frame); still
  **blocked on commercial hub**. See `docs/validation/north-star-staged.md`. Do **not** check
  done until hardware data exists.
- [ ] **5.2 Calibrate the sim** from the measurement (the store's sim-vs-real + calibration hooks exist).

## 6. Research / papers to fold into `docs/bibliography.md`

All folded into `docs/bibliography.md` (2026-09-18): §7 "Fan & propeller aerodynamics" (BEM, tip
leakage, low-Re polars, shroud/winglet, sim→print, prop BEMT) + §1 (Sharland fan-noise sources).

- [x] Tip leakage physics — **Storer & Cumpsty (1991)**, **Denton (1993)** loss mechanisms (→ bib §7; §1.1, §2.1).
- [x] Low-Re airfoils — **UIUC/Selig low-Reynolds-number database**, **Lissaman (1983)** review (→ bib §7; §1.6).
- [x] Shrouded/ducted fans; casing treatments / recirculation for stall margin (→ bib §7; §2.1).
- [x] Fan broadband noise — **Sharland (1964)** (complements Curle/FW-H) (→ bib §1).
- [x] Swept/sickle automotive cooling-fan noise studies (→ bib §7; §2.3 — specific DOIs to re-verify).
- [x] 3D-printed impeller performance — FDM surface-roughness & anisotropy (→ §1.3, sim→print penalty §7.6).
  Structural anisotropy + sim→print knockdown landed; absolute printed CFM still waits on §5 measure.
- [x] Props — **Hanson (1985)** open-rotor/CROR noise; **QProp**/**JavaProp** Re + compressibility BEMT corrections (→ bib §7).

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
  Stage 2 (2026-09-13): tabulated UIUC/Selig CSVs per family (§1.6 stage 1). Ranking still needs §7.3.
  15 BEM/prop tests pass. → implements §1.6 stage 1; ranking still needs §7.3.
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
- [x] **7.4 ML / kriging surrogate tier (stage 1). DONE 2026-09-13** **[impact: high]** **[effort: med-high]**
  `--surrogate-prescreen` / GP on catalog DB wired in `study.py` (`tests/test_surrogate_catalog.py`).
  Remaining: CNN/FNO field predictor (§7.4 depth) — **after** Phase 1–5 sequence above. Refs:
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
- [x] **7.6 Sim→print penalty calibration from published printed-impeller studies. DONE 2026-09-15.** **[impact: med]**
  **[effort: low]** `print_penalty.py` knockdown (CFM×0.95, η×0.92–0.96 by tip thickness, optional FSI
  tip-deflection×gap) wired into axial `evaluate_candidate` + mixed/CROR/volute. Smooth-wall stamps stay in
  `raw` (`cfm_*_cfd`); reported objectives are *printed*. Still provisional until §5 hardware
  recalibrates the factors. Refs:
  [tip-vortex manipulators, num vs experimental on printed condenser fan](https://arxiv.org/pdf/2309.13195),
  [blade-thickness effects on axial-fan performance](https://www.academia.edu/70824092/Experimental_study_of_blade_thickness_effects_on_the_global_and_the_local_performances_of_axial_flow_fans). → feeds §1.3, §5.

---

## 8. Cockpit — surface CLI scoring

Wire existing `evaluate_candidate` / preset plumbing into Assess and Fan Optimize (no new physics).

- [x] **8.1 Assess: hose picker + provenance. DONE 2026-09-03.** `assess_preset` + `score_caption`.
- [x] **8.2 Assess: opt-in refine-op. DONE 2026-09-03.** `assess_refine_op` → third CFD at op.
- [x] **8.3 Fan Optimize panel. DONE 2026-09-11 / wiring closed 2026-09-15.** BEM/GP/shroud/stator/sickle +
  `--search-rpm` cockpit → `optimization_argv` → `run_study` → `evaluate_candidate(rpm=…)`
  (`tests/test_search_rpm.py`, `tests/test_optimization_argv.py`).

## 9. Recovery hardening (2026-09-11)

Crash-safe evaluates, registry wiring, and cockpit hygiene after the drive-death rebuild.

- [x] **9.4 Split `app.py` by tab. DONE 2026-09-11.** Thin shell + `*_tab.py` modules.
- [x] **9.5 Wire propeller into Archetype registry. DONE 2026-09-11.** `PropellerArchetype`; wind stub stays loud.
- [x] **9.6 BEM/surrogate prescreen crashes → infeasible, not CFD.** Mixed + surrogate tests.
- [x] **9.7 Archetype Optimize: BEM exception → trial FAIL, not `(0,0)`.** `tests/test_mixed_optimize.py`.
- [x] **9.8 Volute motor derate under torque budget.** `tests/test_volute.py`.
- [x] **9.9 Corrupt pareto/design JSON skipped with warning.** Mixed/prop persist tests.
- [x] **9.10 Validate fan-model ranges on save. DONE 2026-09-11.** `FanSpec.__post_init__`.
- [x] **9.11 Lock cockpit `user_designs` mutations.** `designs_lock` + upsert helpers.

## 10. Math / simulator accuracy (2026-09-11)

Accepted spec: `docs/superpowers/specs/2026-09-11-math-accuracy-fixes-design.md`. All IDs **fixed or stamped** in tree.

- [x] **10.1–10.2 FWH/Curle kernels + fan BEM shaft power (no double Cd term).**
- [x] **10.3 Fan BEM tip loss: gap leakage only (no Prandtl on ducted fan).**
- [x] **10.4 Prop BEMT swirl:** `Vt = Ω r (1−a′)` (propeller sign).
- [x] **10.5 Analytic polar:** `cd = cd0` only (no extra induced term).
- [x] **10.6 UIUC table fallback** when Re below tabulated range.
- [x] **10.7 BEM shutoff** aligned with curve report interp.
- [x] **10.8 Screening honesty:** `SCREENING_GRID_STAMP` on axial/mixed/CROR/volute evaluate.
- [x] **10.9** Single `CFM_PER_M3S` / default ρ on acoustics proxies.
- [x] **10.10 Circular inlet area check** after snappy (`require_circular_inlet_area`).
- [x] **10.11 FDM `E` knockdown** on δ and f1 (documented stamp).

## 11. Re-review leftovers (2026-09-11)

Fresh pass after §9/§10. Post-recovery fast suite: **602 passed / 6 failed** (2026-09-14 baseline).
Windows OCCT shutdown may exit `0xC0000374` after a green pytest summary — not an assertion failure.

- [x] **11.7 Math/science re-review. DONE 2026-09-11.** No new must-fix equations; keep MRF RANS tier.
- [x] **11.1 Volute screening honesty parity.** `SCREENING_GRID_STAMP`; no circular inlet on sealed scroll.
- [x] **11.2 Propeller registry** (same as §9.5).
- [x] **11.3 Cockpit starts with empty Optuna** (`load_study_designs` → `[]`).
- [x] **11.4 Hide parked LE/TE thickness sliders** (Rounded plate for bullnose).
- [x] **11.5 CROR/prop Optimize: no `(0,0)` gated trials** — `TrialPruned` + `feasible=False`.
- [x] **11.6 Roadmap encoding repair** (UTF-8 §8–§11 restored 2026-09-14).
- Hardware print + measure: **§5** — staged; see `docs/validation/north-star-staged.md`.
- [ ] **11.7 claim superseded:** “no new must-fix equations” was wrong — see **§12** (2026-09-15 audit).

---

## 12. Math-application fidelity (2026-09-15 audit) — CLOSED

Evidence board: Cursor canvas `math-application-audit.canvas.tsx`. Prior “math is good / §10–11 closed”
assurance was wrong for cockpit thickness, Fit envelopes, and axial scoring. Items below are what
still needs to happen before Stock / Fit / Assess / BEM can be trusted together.

### 12.0 Landed this session (do not re-add)

- [x] **12.0a** Uniform thickness = wall **mm** (not equal t/c).
- [x] **12.0b** TE thick scale >1 multiplies aft section (not near-invisible blunt only).
- [x] **12.0c** Stock fingerprint includes LE/TE / section_family / span_interp / le_skew.
- [x] **12.0d** `le_skew_mid/tip` round-trip through `blade_from_flat`.
- [x] **12.0e** Assess preflight gates on **live** dia/depth (not stale Preview STL).
- [x] **12.0f** Axial affinity `derated_probe_pa` + BEM prescreen on **hose op CFM**.
- [x] **12.0g** Grip-aware `mount_min_hub_radius` (~20.725 mm) + shared pad layout.
- [x] **12.0h** `tip_le_te_z` / `_root_axial_span` honor LE/TE thick scales.

### 12.1 Cockpit / Stock fidelity — HIGH **[impact: high]** **[effort: med]**

- [x] **12.1 Stock camber fidelity.** YAML root/mid/tip camber preserved as `camber_root/mid/tip`
  (+ `max_camber` mid alias). Cockpit has three camber sliders; `tests/test_camber_thick_mode.py`.
- [x] **12.2 Persist thickness mode.** Store `thick_mode` (+ `thick_mm`) in flat/Assess JSON; reload
  uses stored mode instead of re-inferring from wall mm.
- [x] **12.3 Deduplicate `CONTROL_DESC`.** Single source: `fansim/cockpit/fan_copy.py`
  (imported by `fan_tab` + `fan_widgets`).

### 12.2 Fit / envelope coherence — HIGH **[impact: high]** **[effort: med]**

- [x] **12.4 One depth measure.** `impeller_z_extent` = blades + hub (+ nose) + shroud — Fit UI,
  `measure_flat`, Assess gate, `fit_envelope`.
- [x] **12.5 One tip gate.** `remaining_tip_gap_mm` / 0.5 mm leftover in tip UI, Fit status
  (`frame_gap_note` + tip readout).
- [x] **12.6 `scale_to_hub` tip leftover.** Uses Fit/CFD gap (`OPTIMIZER_TIP_GAP_MM`), not hardcoded −2.
- [x] **12.7 Mount gauge false FAIL.** Wider cavity wall sampling (grip-aware) + tip mesh FP
  tolerance (0.20 mm) so export sidecars match Fit/CFD leftover without loosening design gates.
- [x] **12.8 Export order.** Grow grip-aware hub first (`prepare_export_flat(..., fit_hub=)`), then
  `fit_envelope`, then editor re-apply.

### 12.3 Scoring / BEM honesty — HIGH **[impact: high]** **[effort: med–high]**

- [x] **12.9 Free-delivery ΔP convention.** Fan line accepts measured CFD free static (`p_free_pa`,
  affinity λ²); BEM still uses P=0 by construction. Axial/mixed/CROR/volute wired.
- [x] **12.10 Label BEM ranking-only.** UI switch + `--bem-prescreen` help + `fan_bem` module
  docstring: never present BEM CFM beside CFD as equivalent; notes ignored geometry levers.
- [x] **12.11 CFD kinematic-pressure contract.** Fixture: FO averages field `p`; parse ×ρ once
  (`tests/test_cfd.py::test_kinematic_pressure_contract_once_times_rho`).

### 12.4 Geometry honesty — MEDIUM **[impact: med]** **[effort: med–high]**

- [x] **12.12 Cylinder wrap.** Documented as planar tangent sections + ``cylindrical_tip`` trim
  (not θ = t/r stream-surface); `_section_points_3d` / `_section_loop` comments corrected.
- [x] **12.13 LE/TE parametric `x`.** Scales/weights use generator chord parameter (not cambered
  surface X); `naca4(..., return_chord_param=True)`.
- [x] **12.14 TE blunt under stagger.** Documented experimental (chord-normal pre-pitch); UI
  tooltip + stagger≠0 regression in `tests/test_le_te_thick.py`.
- [x] **12.15 Solidity radius + analytic test.** Hub σ at `hub_radius` (not `hub−embed`);
  `tests/test_solidity.py`.

---

## 13. Production readiness / engineering hygiene (2026-09-15 review) — CLOSED (stage 1)

Full-repo pass after the memory-rebuild. **Verdict: not production-ready** (research prototype with a working design loop). Rubric **53/100**. Physics/fidelity items stay in **§12**; this section is ship/maintainability. Evidence canvas: `production-readiness-review.canvas.tsx`.

Do **not** treat a green pytest summary as “the app works.” Fast suite ~654 tests (`not docker and not slow`). Ship blockers + CI/mypy/ruff-critical landed; full-style ruff debt and absolute CFM (P–Q / §5) remain.

### 13.0 Ship blockers — CRITICAL **[impact: high]** **[effort: low]**

- [x] **13.1 Restore `fan_tab.py` parse.** Assess-gate nested `try:` fixed. Prove: `tests/test_fan_tab_parse.py`.
- [x] **13.2 Cockpit import/compile smoke.** `tests/test_cockpit_compile_smoke.py` parses every `*_tab.py` + `app.py`.
- [x] **13.3 Front-door honesty.** `README.md` Status matches P–Q report (−17% / −26%); old +2% claim retired.
- [x] **13.4 Kill stale trackers.** `docs/known-issues.md` archived → points at this roadmap.

### 13.1 Tests that lie — HIGH **[impact: high]** **[effort: low–med]**

- [x] **13.5 Deduplicate F811 tests.** Removed first duplicate defs in `test_placement` / `test_shroud` / `test_cockpit_view` / `test_prop_cfd`; `ruff --select F811,F821` clean on those files.
- [x] **13.6 Stop source-string CLI tests.** Scripts expose `build_parser()`; tests load via `tests/_cli_parsers.py` and `parse_args`. Help-text ★ checks use `format_help()`. `--search-rpm` study wiring closed (`tests/test_search_rpm.py::test_run_study_passes_sampled_rpm_to_evaluate`).
- [x] **13.7 `test_catalog.py` type hint.** `from pathlib import Path` + `_make_run(runs: Path, ...)`.
- [x] **13.8 Coverage gate on critical paths.** `pytest-cov` in `dev`; `tests/test_evaluate_candidate_feasible.py` asserts numeric CFM on a stubbed feasible path; `tests/test_camber_thick_mode.py` covers `blade_from_flat` camber/thick_mode. Raise `fail_under` once a baseline is green.

### 13.2 Code quality / maintainability — HIGH **[impact: med]** **[effort: med–high]**

- [x] **13.9 Split `fan_tab.py`.** Stage 1: UI → `fan_tab_ui.py` (~1030 lines); widgets from `fan_widgets.py`; copy from `fan_copy.py` (§12.3). Stage 2 (§15.5, 2026-09-16): `setup_fan_tab` → 68-line coordinator + nine `FanSession` binders (core/models/editor/viz/library/export/assess/optimize/trials, 117–545 lines each) + `fan_runtime`.
- [x] **13.10 Ruff as a gate (critical rules).** `F811`/`F821` cleared across `fansim tests scripts`. Full style debt (~hundreds of I001/F401/S110/...) still open -- do **not** mass-rewrite BLE001 on isolated eval workers (sec 9.6). CI selects F811,F821 until the autofix pass lands.
- [x] **13.11 CI on push.** `.github/workflows/ci.yml`: `uv sync` + ruff F811/F821 + `pytest -m "not docker and not slow"`. Document Windows OCCT teardown `0xC0000374` after a **green** summary (`docs/validation/suite_baseline_2026-09-14.md`) so operators do not treat heap-corruption-on-exit as a failed assertion.
- [x] **13.12 Recovery archaeology out of the product tree.** `.gitignore` now drops `CHAT_RECOVERY/`, `.superpowers/sdd/`, and one-shot `scripts/_patch_roadmap_*.py` / `_fix_roadmap_*.py` / `_smoke_ui_review_after.py` (files may still sit on disk; they are not ship surface).

### 13.3 Performance — MEDIUM **[impact: med]** **[effort: med]**

Already measured (`docs/validation/perf_baseline.md`); not re-litigated:

- [x] **13.13 Screening-resolution geometry policy.** `with_screen_loft` / `build_impeller_screen` (`SCREEN_N_SPAN=10`, `SCREEN_N_CHORD=36`) for watertight+envelope screens; `build_impeller_preview` uses screen loft. CFD `evaluate_candidate` keeps default `n_span`/`n_chord` (`tests/test_screen_loft.py`).
- [x] **13.14 Drop debug `print` on design select.** Results click now `_log.debug("select(%r)", trial)`.
- [x] **13.15 Stock / polar cache completeness.** `stock_fingerprint` covers §12.0c knobs (LE/TE / section_family / span_interp / le_skew / camber / thick_mode); `tests/test_stock_cache.py`. Polar families are `lru_cache`d by **name** (`tests/test_polar_cache.py`) — no cross-family object reuse.

### 13.4 Production hygiene — MEDIUM **[impact: low–med]** **[effort: low]**

- [x] **13.16 License + version.** MIT `LICENSE`; `pyproject.toml` → `0.1.0`.
- [x] **13.17 Cockpit bind address.** `scripts/cockpit.py` defaults `--host 127.0.0.1` (passed through `--reload` child). Use `--host 0.0.0.0` only for intentional LAN access.
- [x] **13.18 Control images in repo or generated.** `docs/control_images/*.png` tracked in git
  (**50** files — covers every `CONTROL_DESC` key including camber stations, wall/section family,
  LE/TE scales, cylindrical tip, smooth span, blade-on-hub); cockpit data-URIs from disk.
  Regenerate: `uv run python scripts/generate_control_images.py`.
- [x] **13.19 Type-check the public surface.** `mypy` in `dev`; `[tool.mypy]` scoped to `fan_spec.py` / `search_space.py` / `metrics.py`; CI runs `mypy`.
- [x] **13.20 VTK/NumPy 2.5 warning.** Pytest `filterwarnings` ignores VTK/PyVista `result.shape` DeprecationWarnings. Viz stays pinned `<0.49` until Trame 4 migration (`dependency_peer_audit.md`).
- [x] **13.21 Dirty-tree discipline.** Working tree landed through §13 hygiene commits; leave untracked recovery STLs / scratch scripts out of product commits.

### 13.5 Geometry perf leftovers (recheck 2026-09-15 evening) — OPEN

F811 name-collision duplicates are **gone**. Axial Fan preview already skips the boolean fuse and uses `SCREEN_N_SPAN=10`. Timed on current stock (`a12x25_reference.yaml`, 9 blades, cylindrical tip):

| Path | Wall | Notes |
|------|------|-------|
| `build_impeller_preview` stock | **2.3 s** | screen loft + mesh copies, no fuse |
| same, second call | **2.3 s** | no in-process cache beyond OCCT warmup |
| `build_impeller_screen` (fused, coarse) | **8.5 s** | watertight, not for CFD |
| `build_impeller` (fused, CFD/print) | **31.6 s** | was 13.1 s on the old recipe (Task 4.1) |
| preview with tip-round (6 stations) | **7.8 s** | screen `n_span=10` then forced to 30 |

- [x] **13.22 Preview must not bump loft to 30. DONE 2026-09-16.** `build_blade_solid` skips the
  `len(stations)>3 → max(n_span,30)` bump when `n_span <= SCREEN_N_SPAN` (screen/preview). Tip-notch
  preview floor stays at `NOTCH_SPAN_SECTIONS_PREVIEW`. Tests: `tests/test_screen_loft.py`.
- [x] **13.23 Mixed / Prop cockpit Preview non-fused. DONE 2026-09-16.** Mixed Preview uses
  `build_mixed_flow_preview` via `build_mixed_stl_isolated(..., preview=True)` (rotate-copy;
  Export still fused + cup). Prop Analyze 3-D uses `build_prop_preview` (axial
  `build_impeller_preview`; Export still `build_prop` + bore). CROR Preview still fused (ok for now).
  Tests: `tests/test_mixed_flow.py`, `tests/test_propeller.py`, `tests/test_mixed_flow_cockpit.py`.
- [x] **13.24 Do not coarsen CFD STL — measured. DONE 2026-09-16 (§15.6).** Fused CFD path stays
  full-resolution. One-`.clean()` micro only saves **~4 s (~8%)** — fuse dominates, leave the
  double-clean. Real regression was tip-notch `n_span` floor 48 (see §15.6 / `perf_baseline.md` §5);
  floor lowered to **28**. Motor-cup Preview still uses the slow fused path — leave it.

BEM is ~14 ms after polar cache — **leave it**. OpenFOAM `base_cell` is a validation honesty choice, not a speed knob.

### 13.0 Landed / do not re-add

§13.1–13.20 closed (13.9: UI extract + FanSession binder split both done 2026-09-16). Do not copy §12.0 items here. Do not re-open parked wind / absolute FW-H / mixed-flow expansion — those are `docs/validation/keep_cut_board.md`.

---

## 14. Archetype Design Parity (2026-09-15) — cockpit Design + Optimize depth

Bring Prop / Mixed / Volute / CROR editors up toward Fan blade vocabulary. Spec:
`docs/superpowers/specs/2026-09-15-archetype-design-parity-design.md`.
**Override keep/cut “no expansion” for Design UI only** — not for archetype CFD campaigns.

- [x] **14.1 Prop BladeParams Design + Optimize. DONE 2026-09-15.** Thickness/camber R-M-T, sweep, LE curve/sickle,
  wrap, tip round/cylindrical, uniform wall; `suggest_prop` searches the same keys.
- [x] **14.2 Shared BladeParams editor kit. DONE 2026-09-15.** `blade_editor.py` + `blade_copy.py`; Prop on kit;
  CROR mounts two prefixes.
- [x] **14.3 Mixed Design + Optimize (stage a). DONE 2026-09-15.** Expose `thickness` / `max_camber` / `camber_pos`
  in UI + `suggest_mixed`.
- [x] **14.3b Mixed span-varying chord/stagger. DONE 2026-09-16.** Diagonal loft interpolates
  root/mid/tip chord + stagger (`MixedFlowParams.chord_*` / `stagger_*`; mid aliases
  `chord_mm` / `stagger_deg`). Legacy single-value flats broadcast. Cockpit R/M/T sliders +
  `suggest_mixed` Optuna keys. BEM adapter maps the triplet. Tests: `test_mixed_flow`,
  `test_mixed_flow_bem`, `test_mixed_optimize`, `test_mixed_flow_cockpit`.
- [x] **14.4 Volute Design depth. DONE 2026-09-15.** Expose dormant `VoluteParams` (blade/backplate/tongue/outlet/wall).
- [x] **14.4b Volute cheap Optimize. DONE 2026-09-16.** NSGA over Design flats via a
  geometry proxy (`capacity_proxy`, `head_proxy`; stamp `volute_proxy=geometry`) —
  ranking only, not CFM. `fansim/volute/optimize.py` + `persist.py`; cockpit Optimize /
  scatter / click-to-load. CFD Assess remains the honest score (no top-N refine yet).
  Tests: `tests/test_volute_optimize.py`.
- [x] **14.5 CROR dual BladeParams Design + expanded `suggest_cror`. DONE 2026-09-15.** Front/rear editors,
  thin/export on edited flats; Optimize searches prefixed chords/stagger/thickness/camber/sickle.
- [x] **14.6 CROR 3-D Preview. DONE 2026-09-16.** Preview button builds thinned stack STL via
  `export_cror_stl` into a lazy CROR plotter (Prop/Mixed pattern). Placeholder card removed;
  CROR tab UI deferred until first visit like Prop.

---

## 15. Adversarial review — new findings (2026-09-15 evening)

Second, hostile pass **after** §12 (math fidelity) and §13 (hygiene, rubric 53/100). Those were
thorough; this only lists what they **missed or under-weighted**, with evidence. Fair note first —
the small stuff is clean: **0** mutable-default args, **0** `== None`, **0** `shell=True`/`eval`/`exec`,
**0** `time.sleep` in `fansim/`; the FNO/archetype `NotImplementedError`s are *honest* fail-loud stubs;
archetype `evaluate_*` are real (not placeholders). The problems are provenance, one embarrassing
visual, and error-handling that hides failure.

- [x] **15.1 Strip recovery-apology headers from shipped modules. DONE 2026-09-16.**
  Stripped leading `# RECOVERED-FROM-CHAT` / `# RECONSTRUCTED` / `# EXTRACTED-FROM-CURSOR*` from
  **64** `fansim/*.py` files (`scripts/_strip_recovery_headers.py`). Single provenance note:
  `RECOVERY_TODO.md` (blade.py golden signed off in §15.2).
- [x] **15.2 `blade.py` geometry-golden sign-off. DONE 2026-09-16.** Committed
  `validation/reference/a12x25_blade_golden.json` (parametric stock volume / bounds /
  tip-section sample) + soft tip/axial envelope vs close-ref STL.
  Helpers: `fansim/validation/blade_golden.py`. Tests: `tests/test_blade_golden.py`.
  Note: stock volume is ~1.4× close-ref (approximate recipe, not OEM CAD) — golden
  guards **regression**, not absolute mesh match.
- [x] **15.3 Flagship 3-D view looks broken — clamp velocity glyphs. DONE 2026-09-16.**
  `make_glyph_arrows` caps length scale at **p95** `|U|` (`GLYPH_MAG_PERCENTILE`); orientation
  still uses true ``U``. Tests: `tests/test_glyphs.py`.
- [x] **15.4 Cockpit swallows failures silently — stage a. DONE 2026-09-16.**
  Added `fansim/cockpit/errors.py` (`log_caught` / `set_state_error`). Eliminated bare
  `except Exception: pass` in `fan_tab.py` + `app.py` — every catch logs (DEBUG for optional
  view_update / captions; WARNING+ for action-adjacent). Soft fallbacks that return defaults
  (depth fit, thickness average, …) remain intentional; action handlers already surface
  Preview/Assess/Export/Optimize errors. Tests: `tests/test_cockpit_errors.py`.
  Further: push the same helper into Mixed/Prop/Volute/CROR binders when touching those files.
- [x] **15.5 `setup_fan_tab` binder split. DONE 2026-09-16.**
  Split the single 2717-line `setup_fan_tab` into a 68-line coordinator plus nine per-domain binders
  (`fan_core` / `fan_models` / `fan_editor` / `fan_viz` / `fan_library` / `fan_export` / `fan_assess`
  / `fan_optimize` / `fan_trials`, each 117–545 lines) sharing the `FanSession` bag; `pv`/`asynchronous`
  moved to `fan_runtime`. Cross-domain calls route through `session.*`. Behavior-preserving. New nets:
  `test_fan_tab_setup_smoke` (runs `setup_fan_tab` on a headless Trame server, invokes the sync
  handlers, and drives the async handler bodies — Preview/Assess/Sweep/Optimize/Export/Stock — with the
  heavy I/O boundaries, i.e. `run_in_executor` targets and `subprocess.Popen`, stubbed by name) and
  `test_fan_binders_wiring` (AST: every `session.x` read is provided — the F821-equivalent for the bag;
  bare-name typos are already caught by ruff F821). While mapping, found+fixed a recovery-induced render
  bug (`_apply_render` merged into `_add_envelope` → recursion + NameError). The four other `*_tab.py`
  can now share this scaffold.
- [x] **15.6 Root-cause the `build_impeller` 13→31.6 s regression. DONE 2026-09-16.**
  Profiled (`scripts/_profile_build_impeller.py`). Stock with tip notches was **~153–168 s**
  (floor 48), not ~32 s — fuse of notched blades dominates. Ablation: no notches ~61 s;
  default ~19 s; 2026-09-14 baseline 13.1 s was pre-notch recipe. Cylindrical tip is secondary
  (~4–5 s loft). One-`.clean()` ~4 s only. **Fix:** `NOTCH_SPAN_SECTIONS` 48→28 (~87 s, ~2×).
  Write-up: `docs/validation/perf_baseline.md` §5.

**Rollup:** §15.1–15.6 all closed 2026-09-16 (15.5 binder split done). Geometry-perf:
~~13.22~~ / ~~13.23~~ / ~~13.24~~ done.

## 16. Real-fan orientation + fan-model prune (2026-09-17)

- [x] **16.1 Fix the upside-down a12x25 (motor on the intake). DONE 2026-09-17.**
  Measurement (blade LE at z=−4.66, TE at +4.66; `spin=-1` = CCW from the −Z intake) showed the
  blades, rotation, and +Z airflow were already correct — the only bug was that the motor boss +
  carved cup sat on the **−Z intake** face. Fix relocates just the motor to the **+Z exhaust**
  face (confirmed against a real Noctua via mockups): flipped the `blade_hub_z_mm` bias sign in
  `_hub_axial_range` so a positive bias grows the hub on +Z; moved the `build_hub` nose/dome to the
  −Z intake end; carved the cup from the +Z face and gauged it there (`carve_motor_mount` /
  `mount_gauge._estimate_cavity`, incl. a bore-detection fix for the sparse cylinder-wall middle).
  Blades, `spin`, and +Z flow untouched, so this is **not** a mirror/turn-over — catalog CFD scores
  shift only by the small hub-boss relocation. Reconciled `domain.py` + `openfoam_case.py` convention
  docstrings (intake −Z / exhaust +Z / motor +Z). Regenerated `a12x25_blade_golden.json`.
- [x] **16.2 Prune mis-calibrated axial fan model. DONE 2026-09-17.** Removed `generic_120` (the
  deprecated loose 120 mm envelope predating the real-frame measurement; no code/test depended on
  it). Kept `a12x25` and `delta_afc1212de` (the latter is the CROR envelope — a real datasheet fan,
  not bad data). No `config/fan_models/*.yaml` user models existed.

## 17. Archetype tab parity — Results / Assess / airflow (2026-09-18)

§14 brought Prop/Mixed/Volute/CROR **Design** depth to parity; the **Results / Assess / viz** side
still lags the Fan tab (feature counts: fan ~25 vs mixed/prop ~6, volute ~5, cror ~3). Bring each
archetype tab up to the Fan tab's post-run workflow **where the physics makes sense**.

Update 2026-09-19/20: on audit, Prop/Mixed/Volute/CROR **already** have a results scatter,
Optimize, Assess/Analyze, reload-prior-runs, and click-to-load — so 17.1/17.2 were largely
present. The real Fan-only gap was the **airflow viz**, now the focus of 17.3.

- [x] **17.1 Results scatter + previous-runs dropdown.** DONE 2026-09-20. Scatter + reload were
  already present; added a shared `data.design_dropdown_items` + a "Previous runs" VSelect to all
  four archetype tabs (Mixed/Volute by trial, CROR/Prop by click index). gold-✕ reference is
  fan-only (no published archetype reference), so N/A.
- [~] **17.2 Assess / run a single design from the tab.** Already present (Mixed/Volute Assess,
  Prop Analyze, CROR Optimize+CFD-refine).
- [~] **17.3 Airflow viz where applicable.** **[impact: med]** **[effort: med]**
  - [x] **Mixed** (2026-09-19) — full |U|/p + axial-Uz + streamlines, verified on a real MRF case.
  - [x] **CROR** (2026-09-20) — rendered for the best CFD-refined design (dual AXIAL rotors).
  - [ ] **Volute** — radial scroll: the fan slices don't fit; needs |U|/p + a scroll/meridional
    view (not the axial-Uz cut-plane). Its z=0 Z-normal slice + downstream-wake seed assume an
    axial machine, so the renderers need geometry-aware slice/seed before reuse.
  - [ ] **Prop** — open-air (no duct): streamlines only; the midplane/cut-plane assume a duct.
- [x] **17.4 Shared binder.** **[impact: med]** **[effort: med]** DONE 2026-09-19/20:
  `fansim/cockpit/airflow_panel.py` (render_airflow_pack / pick_airflow_uri / png_data_uri);
  Fan tab deduped onto it (ae00cd2); Mixed + CROR wire it. Fuller results/binder unification
  (`fan_trials`) still optional.

## 18. Catalog data hygiene — stale CFD results (2026-09-18)

- [ ] **18.1 Stamp + quarantine stale CFD scores.** **[impact: high]** **[effort: med]** The tail-mean
  metrics + adaptive-mesh fixes (bf3fd6a) and the a12x25 recipe refit (5caa070) changed the CFD numbers;
  trials already in `runs/*/study.db` were scored with the **old under-resolved / final-sample** solver,
  so their stored CFM / efficiency are systematically wrong (free-air under-read ~30 vs ~45+ CFM). There
  is **no solver-version stamp** to tell old from new.
  - Add a `cfd_version` `user_attr` when a trial is scored (`optimize/study.py` + the cockpit Assess
    path) so future results are distinguishable.
  - A cleanup/migration script (`scripts/`) scans a study.db, marks pre-stamp trials **stale**, and
    reports them — **do not** silently delete the user's optimization history.
  - Cockpit Results **flags / filters** stale designs (don't present wrong numbers as truth) and offers
    re-Assess. Same treatment for the archetype catalogs once §17 lands.

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
