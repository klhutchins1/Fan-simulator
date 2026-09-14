<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# Fan-simulator — Engineering Roadmap & TODO

**Master plan of open work.** Combines the 2026-09-01 engineering review (major sim-fidelity and
feature gaps) with the standing backlog. Check items off as they land; keep the "why" so we don't
re-litigate decisions. **This is the source of truth for what's left — read it at the start of a work
session.**

- Last reviewed: **2026-09-14** (reconciled to post-recovery tree; fast suite **602 passed / 6 failed** — see `docs/validation/suite_baseline_2026-09-14.md`)
- Tags: **[impact]** how much it changes results · **[effort]** rough build cost · owner *me* unless noted.
- Related: `docs/known-issues.md` (historical cockpit fixes), `docs/high-accuracy-plan.md` (fidelity
  ladder), `docs/design-rules.md` (extracted levers), the memory index.

---

## ★ Recommended sequence

1. ~~Math audit (Phase 1)~~ — done on recovered tree.
2. ~~Noctua reference geometry (Phase 2)~~ — envelope + `a12x25_reference.yaml` Stock (not OEM STL).
3. **Validation P–Q (Phase 3 remainder)** — free-air mesh/tip/physics/recipe checks recorded (~−26% vs 60.1); **near–shut-off P–Q at tip_gap 0.5 mm** still open (§1.5). See `docs/validation/a12x25_pq_report.md`.
4. **Print + measure (Phase 5)** — staged runbook `docs/validation/north-star-staged.md`; **do not** check §5.1 until hardware data exists.
5. **Only then** surrogate depth (§7.4 NN/FNO), absolute noise (§1.4), and archetype CFD depth (§4.x).

§8 cockpit scoring, §9 recovery hardening, §10 math fixes, and §11 re-review are **closed in code** (2026-09-11–13).
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
  **[impact: med]** **[effort: med]** **Partial (2026-09-14):** free-air mesh ladder + GCI asymptotic at tip_gap 0.5 mm (~44.7 CFM, −26% vs published 60.1); tip/frame/wall_ks/stagger A/Bs in `docs/validation/a12x25_pq_report.md`. Historical P–Q at ~1.0 mm tip had shut-off **proxy ~20.1 Pa** (20 Pa unconverged). **Remaining:** Stock multi-back P–Q at **published 0.5 mm** tip with finer near-stall backs; do not claim absolute shut-off until converged near Q→0. See `docs/high-accuracy-plan.md`.
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
- [ ] **2.4 Infill-aware weight.** **[impact: low]** **[effort: low]** Weight uses solid volume; real
  prints use infill, so the 65 g cap is pessimistic (rejects buildable designs). Make it infill-%-aware.
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
  (material/print-type/weight fields). **Nothing is measured yet** — the whole design layer is unvalidated
  (only the CFD *engine* is, on the real STL). One measurement changes "hypothesis" → "result."
  **Staged 2026-09-11** (no commercial hub on hand): `docs/validation/north-star-staged.md`.
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
