<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Fan-simulator — Engineering Roadmap & TODO

**Master plan of open work.** Combines the 2026-09-01 engineering review (major sim-fidelity and
feature gaps) with the standing backlog. Check items off as they land; keep the "why" so we don't
re-litigate decisions. **This is the source of truth for what's left — read it at the start of a work
session.**

- Last reviewed: **2026-09-15** (full production-readiness pass: **not shippable**. Physics honesty
  stays **§12**; engineering hygiene is **§13**. Validation P–Q still open — see `a12x25_pq_report.md`)
- Tags: **[impact]** how much it changes results · **[effort]** rough build cost · owner *me* unless noted.
- Related: `docs/known-issues.md` (historical cockpit fixes — **stale**, see §13.4), `docs/high-accuracy-plan.md` (fidelity
  ladder), `docs/design-rules.md` (extracted levers), the memory index.
  Canvases: `math-application-audit.canvas.tsx` (fidelity) · `production-readiness-review.canvas.tsx` (hygiene).

---

## ★ Recommended sequence

1. ~~**§13.0 parse**~~ — dirty-tree `fan_tab.py` Assess splice fixed; `tests/test_fan_tab_parse.py`
   smoke. Rest of **§13** still open (docs honesty, CI, duplicate tests) — parallel with §12.
2. ~~Math audit (Phase 1)~~ — recovered-tree pass 2026-09-11 (§10). **Re-opened 2026-09-15** after thickness/LE-TE/Fit/scoring bugs; remaining work is **§12** (do this before trusting Stock/Fit/Assess numbers).
3. ~~Noctua reference geometry (Phase 2)~~ — envelope + Stock yaml; close-reference STL under `validation/reference/` (not OEM CAD).
4. **§12 math-application fidelity (cockpit + Fit + scoring honesty)** — stock camber, depth/tip gates, free-ΔP convention, BEM labeling. Canvas: `math-application-audit`.
5. **Validation P–Q (Phase 3 remainder)** — close-ref STL free-air **−17%** (49.8 CFM; layers +0.6 → 50.4). Shut-off proxy **fails** on STL (~14.6 Pa) while parametric Stock still ~24 Pa (interim pass). Screening levers (mesh/tip/frame/ks/stagger/layers) exhausted for free-air. See `docs/validation/a12x25_pq_report.md`.
6. **Print + measure (Phase 5)** — staged runbook `docs/validation/north-star-staged.md`; **do not** check §5.1 until hardware data exists. This is now the primary path to close absolute free-air.
7. **Only then** surrogate depth (§7.4 NN/FNO), absolute noise (§1.4), and archetype CFD depth (§4.x).

§8 cockpit scoring and §9 recovery hardening are **closed in code** (2026-09-11–13) but **§13 reopened hygiene**: the Fan tab is a 3600-line recovery splice, tests do not import it, and front-door docs still claim CFD accuracy the P–Q campaign disproved.
§10 equation stamps remain; **§12 is the live “don’t trust the UI math yet” list**; **§13 is “don’t ship this as a product yet.”**
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
  **[impact: med]** **[effort: med]** **Partial (2026-09-14):** free-air mesh ladder + GCI asymptotic at tip_gap 0.5 mm (~44.7 CFM, −26% vs 60.1); tip/frame/wall_ks/stagger A/Bs documented. Stock multi-back P–Q at **0.5 mm** tip: shut-off **proxy ~24.0 Pa** (interim ±5 Pa **pass**; 18 Pa mildly unconverged). Free-air interim ±10% **still fail**. Absolute shut-off still needs a converged Q→0 (or agreed) solve before datasheet claims. See `docs/validation/a12x25_pq_report.md` §9.
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
  `apply_sickle` + Optuna `--sickle` (`tests/test_sickle.py`). Remaining: cockpit LE editor / mid-band search.
- [x] **2.4 Infill-aware weight (stage 1). DONE 2026-09-14** **[impact: low]** **[effort: low]**
  `estimate_weight_g(..., infill_frac=)` defaults to ``DEFAULT_PRINT_INFILL=0.20`` for FDM filaments
  (resin stays solid). Build gate no longer assumes 100% fill. Override with ``infill_frac=1.0`` for
  solid-mass checks. Tests: `tests/test_fan_spec.py`.
- [x] **2.5 RPM as a lever / real motor torque–speed curve (stage 1). DONE 2026-09-13**
  `fansim/optimize/motor_curve.py` stamps + operating RPM on mixed/volute/CROR evaluate
  (`tests/test_search_rpm.py` — CLI wiring still a known gap). Remaining: full PWM search in all archetypes.
- [x] **2.6 Stepped inlet / notched tips (stage 1). DONE 2026-09-13** **[impact: low]** **[effort: med]**
  `apply_notched_tips` + `--notched` / cockpit flags (`tests/test_notched_tips.py`).

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
- [ ] **3.4 Auto-fit on export (optional).** **[impact: low]** **[effort: low]** The cockpit has manual
  hub/tip/depth fitters; consider an opt-in "fit to frame on export" (like the hub-grow toggle), with the
  aero-cost caveat.

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
- [ ] **7.6 Sim→print penalty calibration from published printed-impeller studies.** **[impact: med]**
  **[effort: low]** Studies comparing metal vs FDM-plastic impellers quantify the roughness + deflection
  penalty — use them to set a knockdown so the tool predicts *printed* performance, not idealized. Bonus
  finding: **thick blades give a flatter efficiency curve + more stable operation across impedance** (a
  robustness lever). Refs:
  [tip-vortex manipulators, num vs experimental on printed condenser fan](https://arxiv.org/pdf/2309.13195),
  [blade-thickness effects on axial-fan performance](https://www.academia.edu/70824092/Experimental_study_of_blade_thickness_effects_on_the_global_and_the_local_performances_of_axial_flow_fans). → feeds §1.3, §5.

---

## 8. Cockpit — surface CLI scoring

Wire existing `evaluate_candidate` / preset plumbing into Assess and Fan Optimize (no new physics).

- [x] **8.1 Assess: hose picker + provenance. DONE 2026-09-03.** `assess_preset` + `score_caption`.
- [x] **8.2 Assess: opt-in refine-op. DONE 2026-09-03.** `assess_refine_op` → third CFD at op.
- [x] **8.3 Fan Optimize panel (stage 1). DONE 2026-09-11.** BEM/GP/shroud/stator/sickle flags in `fan_tab.py`.
  Remaining: `--search-rpm` declared on CLI (`tests/test_search_rpm.py` gap).

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

## 12. Math-application fidelity (2026-09-15 audit) — OPEN

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

## 13. Production readiness / engineering hygiene (2026-09-15 review) — OPEN

Full-repo pass after the memory-rebuild. **Verdict: not production-ready** (research prototype with a working design loop). Rubric **53/100**. Physics/fidelity items stay in **§12**; this section is ship/maintainability. Evidence canvas: `production-readiness-review.canvas.tsx`.

Do **not** treat a green pytest summary as “the app works.” Fast suite collected **654** tests (`not docker and not slow`). **§13.1–13.4** ship blockers addressed in-tree (parse smoke, README honesty, archived known-issues). Ruff/CI still open.

### 13.0 Ship blockers — CRITICAL **[impact: high]** **[effort: low]**

- [x] **13.1 Restore `fan_tab.py` parse.** Assess-gate nested `try:` fixed. Prove: `tests/test_fan_tab_parse.py`.
- [x] **13.2 Cockpit import/compile smoke.** `tests/test_cockpit_compile_smoke.py` parses every `*_tab.py` + `app.py`.
- [x] **13.3 Front-door honesty.** `README.md` Status matches P–Q report (−17% / −26%); old +2% claim retired.
- [x] **13.4 Kill stale trackers.** `docs/known-issues.md` archived → points at this roadmap.

### 13.1 Tests that lie — HIGH **[impact: high]** **[effort: low–med]**

- [ ] **13.5 Deduplicate F811 tests.** Recovery splices redefined the same names; pytest keeps the **last** copy only. Files: `tests/test_placement.py` (3), `tests/test_shroud.py` (2), `tests/test_cockpit_view.py` (2), `tests/test_prop_cfd.py` (1). Delete the duplicates; if the copies drifted, keep the stricter one.
- [ ] **13.6 Stop source-string CLI tests.** `tests/test_search_rpm.py::test_cli_declares_search_rpm_and_bounds` (and peers in `test_surrogate_catalog.py`, `test_stator.py`, `test_boost_ensemble.py`, `test_prop_cfd.py`, …) assert `"--flag" in Path(...).read_text()`. Parse `argparse` or invoke `main` with `SystemExit`. The `--search-rpm` wiring gap in §8.3 is still a real gap — the string test does not close it.
- [ ] **13.7 `test_catalog.py` type hint.** `_make_run(runs: "pathlib.Path", ...)` — `pathlib` is never imported (`F821`). Use `from pathlib import Path`.
- [ ] **13.8 Coverage gate on critical paths.** No `pytest-cov`, no threshold. Provenance already flags `objectives.py` / `study.py` as having **no numeric CFM assertion** in the fast suite (`docs/validation/provenance_risks.md`). Add coverage for `evaluate_candidate` feasible path + `blade_from_flat` round-trip of camber/thick_mode (feeds §12.1–12.2).

### 13.2 Code quality / maintainability — HIGH **[impact: med]** **[effort: med–high]**

- [ ] **13.9 Split `fan_tab.py`.** **3633 lines** (next cockpit file is ~780). Assess / Optimize / Preview / Results / export are one module with duplicated `CONTROL_DESC` / `OPT_SEARCH_HELP` vs `fan_copy.py` (stale TE-thick tooltip in `fan_copy`; widgets still import it). Fold into §12.3: **one** `CONTROL_DESC` source, tab modules < ~400 lines.
- [ ] **13.10 Ruff as a gate.** `ruff check fansim tests scripts` → **551** issues. Highest-signal first: **10 invalid-syntax** (the 13.1 splice), **8 F811**, **2 F821**, **24 S110** try/except/pass, **179 unused `# noqa`**. Then autofix I001/F401. Do **not** mass-rewrite BLE001 on isolated eval workers — those swallows are load-bearing (§9.6).
- [ ] **13.11 CI on push.** No `.github/workflows` (and no in-repo Gitea workflow). Fast job: `uv run --extra dev --extra optim python -m pytest -m "not docker and not slow" -q` + `ruff check`. Document Windows OCCT teardown `0xC0000374` after a **green** summary (`docs/validation/suite_baseline_2026-09-14.md`) so CI does not treat heap-corruption-on-exit as a failed assertion.
- [ ] **13.12 Recovery archaeology out of the product tree.** `CHAT_RECOVERY/` is untracked and **not** in `.gitignore` (keep/cut: **DON’T SHIP**). Ignore it. Move one-shot `scripts/_patch_roadmap_11.py`, `scripts/_fix_roadmap_encoding.py`, `scripts/_smoke_ui_review_after.py` out of `scripts/` (or a `scripts/_recovery/` that is gitignored).

### 13.3 Performance — MEDIUM **[impact: med]** **[effort: med]**

Already measured (`docs/validation/perf_baseline.md`); not re-litigated:

- [ ] **13.13 Screening-resolution geometry policy.** Fused `build_impeller` **~13 s** dominates every Optuna trial that passes BEM (~16 ms). Preview **~5 s**. Polar cache bought **~14%** on BEM only. Need an explicit coarser `n_span`/`n_chord` for screen-only STL (acceptance: watertight + envelope, not CFD-identical). Do not silently drop loft resolution on the CFD path.
- [ ] **13.14 Drop debug `print` on design select.** `fansim/cockpit/fan_tab.py` ~2499 `print(f"[cockpit] select({trial!r})", flush=True)` on every Results click. Use `_log.debug`.
- [ ] **13.15 Stock / polar cache completeness.** `stock_cache.py` exists (uncommitted). Confirm Preview gold-STL cache invalidates on every fingerprint field in §12.0c, and that BEM polar-family cache does not leak across airfoil family changes.

### 13.4 Production hygiene — MEDIUM **[impact: low–med]** **[effort: low]**

- [ ] **13.16 License + version.** No `LICENSE`. `pyproject.toml` is `0.0.1`. Decide license (personal tool vs publish) before any “product” language.
- [ ] **13.17 Cockpit bind address.** `scripts/cockpit.py` `server.start(port=args.port)` with no `--host`. Trame/uvicorn default is often **0.0.0.0**. Bind `127.0.0.1` unless `--host` is set (local CFD UI is not meant to be a LAN service).
- [ ] **13.18 Control images in repo or generated.** `.gitignore` drops `docs/control_images/*.png`; cockpit encodes them as data-URIs if present, else empty tooltips. Either generate in `uv sync` / a makefile target, or stop advertising hover min/max images.
- [ ] **13.19 Type-check the public surface.** No mypy. Start with `fansim/fan_spec.py`, `optimize/search_space.py`, `cfd/metrics.py` — the modules provenance ranks for absolute CFM.
- [ ] **13.20 VTK/NumPy 2.5 warning.** Fast suite emits 52 `DeprecationWarning`s from VTK `result.shape = shape`. Track PyVista 0.49 / VTK pin (`docs/validation/dependency_peer_audit.md` already capped viz for API churn).
- [ ] **13.21 Dirty-tree discipline.** This review ran against a large uncommitted mix (geometry, Fit, glyphs, Stock STL, SDD packets). Do not treat the working copy as HEAD. Land or revert before the next fidelity campaign.

### 13.0 Landed / do not re-add

Nothing in §13 is done. Do not copy §12.0 items here. Do not re-open parked wind / absolute FW-H / mixed-flow expansion — those are `docs/validation/keep_cut_board.md`.

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
