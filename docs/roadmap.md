# Fan-simulator — Engineering Roadmap & TODO

**Master plan of open work.** Combines the 2026-09-01 engineering review (major sim-fidelity and
feature gaps) with the standing backlog. Check items off as they land; keep the "why" so we don't
re-litigate decisions. **This is the source of truth for what's left — read it at the start of a work
session.**

- Last reviewed: **2026-10-15** (24.2/24.3 copy signed off). Previously 2026-10-14 (28.2 print-id registry). Previously 27.3 / QA-34. Previously **2026-10-13** (§28 parked).
  Previously **2026-10-11** (§26 parked). **2026-10-08** (§23 QA). **§12** + **§13** + **§7.6** +
  **§14.1–14.6** closed in code. Stock close-ref fidelity (§2.7–2.8). **§13.22–13.24** /
  **§14.3b** / **§14.6** / **§15.1–15.6** landed 2026-09-16. Still **not shippable** until
  Validation P–Q / print+measure — see `a12x25_pq_report.md`. **§21** cockpit UX + **§22**
  design-switch 3-D reload bug opened 2026-09-30.
> ✅ **§19.1 freeze lifted 2026-09-26** — rotor direction fixed and CFD-verified (Audit #1b). CFD orientation lives in
> `fansim/cfd/orientation.py`; change it only with a new direction audit.

- Tags: **[impact]** how much it changes results · **[effort]** rough build cost · owner *me* unless noted.
- Related: `docs/known-issues.md` (archived Aug 2026 cockpit notes — **not** open work),
  `docs/high-accuracy-plan.md` (fidelity ladder, not a backlog), `docs/design-rules.md` (extracted
  levers), `docs/QA_REVIEW.md` (QA bug ledger — promote a bug here when we adopt it).
  Canvases: `math-application-audit.canvas.tsx` (fidelity) · `production-readiness-review.canvas.tsx`
  (hygiene) — evidence, not a second TODO.

### Where work is tracked (one list)

**Open product work lives only in this file.** If you find a “TODO / next / backlog” elsewhere,
move the unique open item here and leave a pointer, do not keep a second list.

| place | what it is | add open work? |
|---|---|---|
| **`docs/roadmap.md`** | Product backlog and session “what’s next” | **yes** |
| `docs/QA_REVIEW.md` | Numbered QA bugs (QA-n) and round notes | file bugs; adopt into a roadmap item |
| `docs/validation/keep_cut_board.md` | KEEP / PARK / DON’T SHIP scope | no (scope, not tasks) |
| `docs/high-accuracy-plan.md` | Fidelity-ladder essay | no |
| `docs/known-issues.md` | Archived Aug 2026 cockpit notes | no |
| `memory/*` | Session pointers; several are stale | no — point here |
| `archive/recovery-2026-09/RECOVERY_TODO.md` | 2026-09 rebuild archaeology | no |
| `handoff/` | Briefs to Claude / grok | no (ephemeral) |

---

## ★ Recommended sequence

0. ~~**§19.1 Audit #1**~~ — direction fixed + verified 2026-09-26 (CFD v3). Free-air now −2% vs Noctua; the open gap
   is the **loaded branch** (shut-off 9.5 vs 22.9 Pa) — see §19.6. Pre-v3 catalog scores are stale.
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
**→ Next (2026-10-15): 29.1 / QA-36 — PLA+ picker must drive Preview grams + Export README (grok r12). 24.4 investigate only (Kimball picks lock/snapshot/queue). 28.3 glyphs parked. QA-12 CT0 remains. Do not restart the optimizer.**
7. **§15 adversarial leftovers** — ~~15.1–15.6~~ all done 2026-09-16 (incl. 15.5 binder split).
8. **Only then** (post-hardware) optional deferred depth: §7.4 CNN/FNO, absolute noise (§1.4), archetype CFD (§4.x) — not active software.
9. **§20 external feature radar** — ~~20.1~~ / ~~20.2~~ / ~~20.3~~ / ~~20.4~~ / ~~20.5~~ / ~~20.6~~ DONE 2026-09-30;
   NeuralFoil stays **opt-in** (do **not** flip UIUC default); 20.7 is the hardware path for item 5.
10. ~~**§22 cockpit airflow / 3-D viz speed**~~ — first-open + disk glyphs + busy UX landed
    2026-09-30; leftover optional: 22.12 diminishing returns.
11. ~~**§21 Fan Design UX**~~ — IA collapse + cold-open / banner / badges / vs-stock + Prop
    mirror landed 2026-09-30; leftover optional: 21.2g tour/readiness.

**What's left (classify before starting a session):**

- **Software remaining** (no hardware / no new CFD campaign required):
  - **§22** — optional diminishing returns (22.12) only. Core reselect + first-open bake/lazy/
    slice/streamlines + disk glyphs + busy/cancel UX landed 2026-09-30.
  - **§21** — core Fan + Prop UX done 2026-09-30; optional leftover: 21.2g (tour/readiness).
    Intake overbuild (+Z) Design switch landed 2026-09-30 (Fit & seed; asymmetric envelope).
  - **§26** (parked idea) — cockpit “Bring your STL” Assess; optional inverse-fit; no mass-scrape.
    Do **not** start until wrap is merged and external-STL spin is honest (round 9 D unconfirmed).
    CLI already has `scripts/validate_stl.py`.
  - **§28** (28.1 mark-spec PASS; **28.2 registry done**; 28.3 glyphs still parked) —
    +Z hub ring r 10–21.45 mm is flat 360°. Dummy 8×3.2×0.5 recess stays one solid; aero 1.76 %.
    28.2 registry is in; glyphs wait. Handoff: `handoff/2026-10-13_from-qa-10/`.
  - **§29** — 29.1 material picker (PLA+ still looks like PETG); 29.2 UI regression tests. Grok r12 D/E.
  - ~~**§24.2 / 24.3**~~ DONE 2026-10-15 (Kimball signed off Simple copy). Leftover: QA-38 scatter
    below the fold at 768p (LOW). 24.4 is investigate-only until Kimball picks lock/snapshot/queue.
  - ~~**25.10**~~ near-stall flag DONE 2026-10-14 (caption only; hold-out MIXED, 9613 also flags).
  - Deferred (Stage 1 done, Stage 2 **not adopted** — do not start without a new Adopt):
    CST section DOFs, §7.4 CNN/FNO field predictor, §4.5 toroidal Prop topology.
  - ~~§20.2 NeuralFoil / RMS / 360°~~ — DONE 2026-09-30.
  - ~~§19.5+ ledger~~ — DONE 2026-09-30 (PROVEN=28, unregistered=0).

- **Blocked on hardware / CFD campaign:**
  - §5.1 / §5.2 / §20.7 — print+measure + low-cost P–Q rig (user hardware); ingest hooks exist.
  - §1.4 — absolute calibrated dB(A) (bench mic **or** porous FW-H campaign); kernels already PROVEN.
  - §1.5 — full P–Q / shut-off convergence (more CFD + hardware to claim datasheet).
  - §4.3 — full compressible / AMI prop CFD (screening stages done; AMI parked).
  - §19.6 — loaded-branch / near-stall (heavy CFD / cloud; URANS not viable on this PC).
  - §19.13 — FAN-01 chamber/struts + mesh ladder at 126 Pa (CFD).
  - §19.18 — shell FEA or printed-blade tap test (high effort / hardware) before absolute δ / f1.

§8 / §9 / §10 / §12 / §13 stage-1 are **closed in code**. Absolute CFM honesty waits on hardware (§5) or a new fidelity lever beyond screening.
Phases 4.1 / 4.2 / 6.1 landed (dependency audit, perf baseline, keep/cut board).
**Do NOT** re-optimize tip-round or bio-features — tested null on flow AND noise.
**Do NOT** datasheet-tune Stock from BEM (stagger candidate CFD +0.6 CFM only).
**Do NOT** make NeuralFoil the polar default while SF C_T(J) sweeps are worse than table (still true after §20.2).

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
  **Blocked on hardware or a porous FW-H campaign** — not on missing kernel code.
  Audit #6: acoustics **kernels are PROVEN** (relative Curle/loading + prop analytic proxy). Fan noise
  remains a band-limited *relative* proxy; prop noise (`propeller/noise.py`) is likewise *relative*.
  **Still open:** absolute calibrated dB(A). A porous FW-H surface (GPU LBM) or a bench mic would give
  absolute numbers. Tonal (BPF) is validated via uneven spacing; broadband is coarse-grid-limited
  (~0.5 mm cells needed, >12 GB VRAM).
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
  `MixedFlowArchetype`, geometry + evaluate + cockpit tab (`tests/test_mixed_flow*.py`). Remaining: high-Pa hose wins vs axial. **Re-run 2026-10-02 (v5, both rotors designed-direction):** Stock axial vs default mixed-flow **tie at the case hose** (44.3 vs 44.3 CFM; η 23.9 % vs 22.7 %); mixed-flow +23 % free air (67.0 vs 54.4). Old "axial wins" withdrawn. Mixed-flow has no measured reference, so treat as comparable, not ranked. `docs/validation/mixed_vs_axial_v5.md`.
- [x] **4.2 Counter-rotating stacked rotors (stage 1 scaffold). DONE 2026-09-13** **[impact: med]** **[effort: high]**
  `CrorArchetype` + dual-MRF evaluate (`tests/test_cror.py`). Remaining: noise + measured static gain. ⚠ The 2026-09-06 dual-MRF smoke (~93% η) had both rotors backwards (Audit #7, fixed 2026-10-01).
- [ ] **4.3 Prop compressible open-air CFD tier.** **Audit #8 2026-10-02:** direction PASS (APC SF 9x4.7 designed +221 g vs reversed −122 g), tail-mean metrics + prop sanity added; **validation FAIL: C_T −44 % / C_P −40 % vs UIUC** Mesh ruled out (level 5: +0.6 % thrust); built geometry matches UIUC (chord ±0.3 mm, β ±0.4°). Entrainment BCs also ruled out (C_T 0.0670 vs 0.0667); orientation checked. CFD vs BEMT disagree ~36 % on the same blade Spanwise: deficit is mid-span section aero (CFD/BEMT 0.54–0.73). Prism layers: −41 % C_T (small gain). **Closed 2026-10-02: prop CFD is not a performance predictor at chord Re < ~1e5 (fully turbulent RANS limit); use BEMT for props. Open (not pursued): k-ω SST-LM transition model on a y+≈1 mesh.** Prop CFD numbers are not performance claims until then; BEMT stays the screen. **[impact: med]** **[effort: high]** BEMT screens
  props; a real CFD pass refines finalists (tips run Mach 0.4–0.58, where BEMT/incompressible is weak).
  **Track A stage 1 (2026-09-21):** hover Wh/power budget + optional PyThrust (`--extra propulsion`) +
  quorum cross-checks in `fansim/propeller/power.py` — complements BEMT screening; **not** a substitute
  for §4.3 CFD (spec/plan: `docs/superpowers/specs/2026-09-21-prop-pythrust-power-design.md`,
  `docs/superpowers/plans/2026-09-21-prop-pythrust-power.md`).
  **Track A stage 2 (2026-09-21):** BEMT→PyThrust CSV export (Analyze + CLI); not a substitute for §4.3 CFD
  (spec/plan: `docs/superpowers/specs/2026-09-21-prop-pythrust-bemt-export-design.md`,
  `docs/superpowers/plans/2026-09-21-prop-pythrust-bemt-export.md`).
  **drone_radial smoke (2026-09-22):** open-air `rhoSimpleFoam` on
  `obj_1_ccw_impeller` + `obj_2_ccw`; fixtures under
  `validation/reference/drone_radial/cfd/`; report
  `docs/validation/drone_radial_open_air_cfd.md`. Smoke force-tail gate **25%**
  (smoke mesh). Screening only — not full §4.3 / not datasheet. Template
  stability fixes in `PROP_FV_*`.
  **drone_radial refine (2026-09-22):** both STLs have refine fixtures; obj_1 uses
  late-window gate (`--tail-frac 0.10`, drift &lt;10%) after smoke-window limit-cycle.
  Prop CFD refine card: Smoke/Refine mesh preset. Spec/plan:
  `docs/superpowers/specs/2026-09-22-prop-cfd-refine-deepen-design.md`,
  `docs/superpowers/plans/2026-09-22-prop-cfd-refine-deepen.md`.
  **drone_radial GCI (2026-09-22):** honest ladder 0.005/0.0035/0.0025 on both STLs;
  Roache on thrust_g; report `docs/validation/drone_radial_open_air_cfd.md`.
  Spec/plan: `docs/superpowers/specs/2026-09-22-prop-cfd-grid-independence-design.md`,
  `docs/superpowers/plans/2026-09-22-prop-cfd-grid-independence.md`.
  **drone_radial AMI smoke (2026-09-23):** obj_2 only, `rhoPimpleFoam` + `cyclicAMI`,
  two revolutions, mean thrust vs the 938 g MRF smoke band (±25%). Retry after the
  `createBaffles` surface-word fix still produced **mean_thrust_g: null** (SIGFPE in `rhoPimpleFoam`);
  no stamp. Report `docs/validation/drone_radial_open_air_cfd.md`. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-cfd-ami-smoke-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-cfd-ami-smoke.md`.
  **§4.3 screening stages** (parametric smoke + drone_radial smoke/refine/GCI + cockpit knobs)
  are in place. The obj_2 ~2 kW figure is explained in **§4.4** step 4 (radial impeller versus the FPV 5″ datasheet). After that:
  AMI/sliding (obj_2 attempt produced no finite mean), forward-flight polars, datasheet calibration.
  AMI is one obj_2 smoke, not a sliding-mesh campaign (GCI remains a screening stamp only).
  **fpv_5inch BEMT datasheet (2026-09-23):** static check at 30000 rpm is 1654 g (ratio 0.894) and 572.6 W (ratio 0.881) versus 1850 g and 650 W. Figure of merit 0.648. `within_2x` is thrust only. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-fpv-datasheet-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-fpv-datasheet.md`.
- [x] **4.4 Make obj_2 thrust and power believable before more AMI. DONE 2026-09-30.** **[impact: high]** **[effort: med]**
  Actionable software work is finished (steps 1, 2, 4). **AMI remains intentionally parked** — not an
  unfinished software gap. A retry still needs: single-rank thermo init that does not SIGFPE; time step
  ≈ **1° or less** (today 4e-5 s is 6.1° at 2644 rad/s); a **signed** thrust mean; comparison target =
  same-mesh MRF smoke (938 g), not the 1249 g extrapolation. Physics review 2026-09-23: obj_2 smoke is
  arithmetically consistent (0.769 N·m × 2644 rad/s = 2034 W, 938 g) and a poor hover propeller
  (FoM **0.11** at ρ = 1.174 kg/m³; ideal momentum power 226 W). Power stays ~2.0–2.2 kW across GCI while
  thrust climbs 924 → 1038 → 1109 g (fine GCI 16%, p = 1.21). `converged=true` only means the asymptotic
  ratio is near 1. obj_1 fine-mesh thrust falls / medium drifts 55% — do not quote it.
  1. **Done.** `bemt.analyze` calls `_compressibility_cl_cd` with local Mach
     (`sqrt(W2) / C_AIR`, 343 m/s) inside the element loop. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-bemt-compressibility-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-bemt-compressibility.md`.
     Stall cap: attached Cl is divided by `sqrt(1 - M²)` and limited to the polar peak; Cl at or past stall is unchanged. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-bemt-stall-cap-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-bemt-stall-cap.md`.
  2. **Done.** obj_2 wall mesh (`for_blade`, prism layers) is stamped at
     `validation/reference/drone_radial/cfd/obj_2_ccw_wall.json`: 1131 g,
     2163 W, figure of merit 0.139, layout axial,
     wall_resolved false. Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-obj2-wall-mesh-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-obj2-wall-mesh.md`.
     At iteration 400 the shaft moment is 0.818 N·m, of which 0.812 N·m is pressure and 0.006 N·m is viscous.
  3. **Parked (by design).** AMI not resumed until the preconditions above are met.
  4. **Done.** The 2163 W versus 388 W gap is the FPV 5×4.3×3 datasheet (650 W at 30 000 rpm, rpm³) applied to a radial impeller (hub 30.4 mm, tip 45.4 mm). Pressure moment is 0.812 N·m of 0.818 N·m. Do not retune the mesh to 388 W. Spec:
     `docs/superpowers/specs/2026-09-23-prop-obj2-power-gap-design.md`.
- [x] **4.5 Toroidal propeller shapes — investigate then implement.** **DONE (Stage 1 only) 2026-09-30.** **[impact: med]** **[effort: high]**
  Closed-loop / ring-blade (Sharrow-style) props as an alternate topology under the Prop archetype.
  **Stage 1 (investigate): DONE** — `docs/superpowers/specs/2026-09-30-toroidal-prop-investigate-design.md`
  (printability, BEMT unsuitable → CFD-first via §4.3 MRF, **no-go** vs open-blade Prop).
  **Stage 2 (implement): not adopted** — cleared from active software scope 2026-09-30; revisit only
  after hardware P–Q / spare CFD capacity and a fresh Adopt. Do not start CadQuery / Design knobs / CFD smoke.

## 5. Physical validation loop — the north star (needs hardware; owner: **user**)

- [ ] **5.1 Print a real-frame design + measure** CFM / static / noise / weight. **Pre-registered plan (band rewritten 2026-10-13, 27.9):** `docs/validation/first_print_measure_plan.md`: genuine impeller (rig calibration) vs **printed Stock v3**, predicted B/A **0.91 (band 0.85–0.97)**. CFD: v3 55.7 / close-ref STL 58.3 / planar v2 54.5 at 0 Pa in the validation rig. Print STL at `exports/first_print_stock/`. Recorder is built
  (cockpit → `validation/measurements/` with material/print-type/weight fields). **Nothing is
  measured yet** — one real point changes hypothesis → result. **Print-fit kit ready**
  (`scripts/export_a12x25_print_ready.py` + mount gauge vs measured MotorMount / frame); still
  **blocked on tools / commercial hub**. See `docs/validation/north-star-staged.md`.
  **Print freeze 2026-10-13:** do not slice article B until wrap is adopted or explicitly
  rejected, the plan numbers match that recipe, and the part carries a §28 print-id (or the
  same code written on the hub in sharpie from the export README). Do **not** print optimizer
  candidates (wrap changes what their sliders mean). Do **not** check done until hardware data
  exists.
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
  `--surrogate-prescreen` / GP on catalog DB wired in `study.py` (`tests/test_surrogate_catalog.py`);
  §20.5 surrogate-guided search also DONE. **§7.4 depth (CNN/FNO field predictor): not adopted** —
  cleared from active software scope 2026-09-30 (priority after Phase 1–5 / hardware, not a scaffolding
  gap). Refs:
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
- [x] **11.7 claim superseded.** The 2026-09-11 “no new must-fix equations” line was wrong. **§12** (closed) is the record of what was actually fixed.

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
- [x] **14.7 Prop missions: thrust, quiet, endurance, range.** **[impact: high]** **[effort: med]**
  One search. A mission chooses which two things are objectives and which quantities are constraints
  or labels. Do not add a second optimizer that can disagree with the first.
  Search presets are on `run_prop_study`: `thrust_efficiency` (default), `quiet_thrust`, `hover_endurance`, and `range`. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-missions-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-missions.md`.
  Cockpit mission select and the minutes/km plots are in. Spec/plan:
  `docs/superpowers/specs/2026-09-23-prop-mission-cockpit-design.md`,
  `docs/superpowers/plans/2026-09-23-prop-mission-cockpit.md`.
  Default mission `thrust_efficiency` maximizes thrust and g/W. The other three missions are on `run_prop_study` and on the Optimize card. `estimate_prop_noise` already stamps
  `rel_dba` (relative, not dB(A) — absolute levels stay §1.4). The cockpit already plots
  **thrust vs that noise score**, colored by g/W (`prop_scatter_figure`). Noise is a spectator.
  `hover_power_budget` already turns all-up weight, rotor count, battery Wh, and shaft power into
  hover minutes. Printed prop mass is a small part of all-up weight; the mission knob is vehicle
  weight plus battery, not a fourth equal objective.
  Presets:
  - **Quiet thrust.** Maximize thrust, minimize `rel_dba`. Battery size and hover minutes are
    constraints the user can relax (a few minutes on a larger pack is allowed).
  - **Hover endurance.** Maximize hover minutes at a given all-up weight and battery. Noise is shown,
    not optimized.
  - **Range.** Maximize distance at a chosen cruise speed from BEMT `v_forward` power and the same
    battery. Thrust must still hold the weight in hover. This is a screening range, not a CFD polar.
    Noise is shown, not optimized.
  Keep the existing thrust–noise plot for Quiet thrust. Endurance and Range get their own plot of
  the thing that was optimized (minutes or km) against thrust, with noise and power on the point.
  Relative noise stays the ranking score until a bench mic or §1.4 says otherwise.

- [x] **14.8 Prop cockpit: stop, disk, random, wiring.** **[impact: high]** **[effort: med]**
  Reported 2026-09-23. Optimize was left running and had to be killed by closing the terminal.
  1. **Done.** Stop sits beside Optimize and ends the study after the current trial (`9d80380`). Spec/plan:
     `docs/superpowers/specs/2026-09-23-prop-optimize-stop-design.md`,
     `docs/superpowers/plans/2026-09-23-prop-optimize-stop.md`.
  2. **Done.** Each trial was committing `study.db` with SQLite's default full flush, which pegs the project disk. Prop studies now use `make_sqlite_storage`: WAL and `synchronous=NORMAL`, so a trial does not fsync the whole file. Resume still reads that database.
  3. **Done.** Randomize fills the blade sliders inside the same bounds `suggest_prop` searches. It does not start a study.
  4. **Done.** On the prop tab: mission select and minutes/km plots, Stop, Randomize, the BEMT polar speed list, PyThrust export, and CFD refine. Compressibility and the stall cap run inside `analyze`, so Analyze and Optimize already use them. The datasheet CLI and the obj_2 CFD stamps stay scripts.

- [x] **14.9 Cockpit tab shell. DONE 2026-09-24.** Design / Results / Library on Prop / Mixed / Volute / CROR; Fan Actions and Optimize aligned. Shared helper `fansim/cockpit/tab_shell.py`. Spec: `docs/superpowers/specs/2026-09-24-cockpit-tab-shell-design.md`.

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
  **Correction 2026-09-25 (Audit #1):** the text above describes commit a75da48, which was
  reverted by ea96f40. The motor cup is on −Z as built; the designed airflow is −Z as built;
  CFD orients the rotor via fansim/cfd/orientation.py.
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
- [x] **17.1b Archetype tabs actually render live.** FIXED 2026-09-21. On first live open all four
  archetype tabs were **blank** and the console spammed `'dict' object has no attribute 'startswith'`.
  Two pre-existing bugs (from the a31d2fc recovery): (a) the lazy `@state.change` tab render created
  widgets after the layout `with` blocks closed, so nothing attached to the client — fixed by
  re-entering the tab container + `layout.flush_content()`; (b) prop's "Wall mode" VSelect passed a
  list literal to `items=`, which trame reads as a state binding and crashes — fixed by binding
  `items=("p_thick_mode_items",)`. Guarded by `tests/test_cockpit_items_binding.py`; verified in the
  browser (Fan/Mixed/Volute/Prop/CROR all render, no errors). See [[cockpit-trame-gotchas]].
- [x] **17.2 Assess / run a single design from the tab.** **DONE 2026-09-30** — Assess/Analyze
  already on Fan/Mixed/Volute/Prop/CROR; UI wiring pass also surfaces §19.4 mirror export,
  §19.15 polar-backend picker, §19.18 beam-regime WARN in score caption, and §20.1 STEP on
  prop export (Fan STEP was already default).
- [x] **17.3 Airflow viz where applicable.** **[impact: med]** **[effort: med]** DONE 2026-09-24.
  - [x] **Mixed** (2026-09-19) — full |U|/p + axial-Uz + streamlines, verified on a real MRF case.
  - [x] **CROR** (2026-09-20) — rendered for the best CFD-refined design (dual AXIAL rotors).
  - [x] **Shared fix — midplane |U| clim clamp.** `throughflow_umag_clim` scales the |U| midplane to the 95th percentile (floor 0.5 m/s). Cached PNG name is `U_midplane_v8.png`.
  - [x] **Prop** (2026-09-24) — open-air axial rotor: Results panel wires the shared
    airflow pack after CFD refine (and on Library load when a `cfd_refine` case exists).
    |U|/p midplane + axial Uz + streamlines; same clim clamp as Mixed/CROR.
  - [x] **Volute** (2026-09-24) — scroll-section |U|/p: `layout="scroll"` keeps the full Y=0
    cut (no tip-radius wake crop) and orients the camera so +X outlet is right / +Z inlet is
    up. Axial-Uz omitted (radial machine). Clim clamp already in.
- [x] **17.4 Shared binder.** **[impact: med]** **[effort: med]** DONE 2026-09-19/20:
  `fansim/cockpit/airflow_panel.py` (render_airflow_pack / pick_airflow_uri / png_data_uri);
  Fan tab deduped onto it (ae00cd2); Mixed + CROR wire it. Fuller results/binder unification
  (`fan_trials`) still optional.

## 18. Catalog data hygiene — stale CFD results (2026-09-18)

- [x] **18.1 Stamp + quarantine stale CFD scores. DONE 2026-09-23.** **[impact: high]** **[effort: med]**
  `cfd_version` is stamped in `fansim/optimize/study.py` and `fansim/cockpit/fan_assess.py`.
  `cfd_is_stale` flags missing or older versions. Results marks them with ⧗ and tells you to re-Assess.
  `scripts/clean_stale_cfd.py` audits `runs/*/study.db` and can persist the marker. It does not delete trials.
  Tests: `tests/test_cfd_stale.py`.


## 19. Physics & math audit program (2026-09-24)

Repeatable audits that produce **evidence** (numbers vs. tolerance, a pass/fail, and the source each
claim traces to) — not prose someone rewrites by hand. `docs/adversarial-review.md` is the stale
Aug snapshot of this idea; this section replaces its "living document" role. Three layers, kept
separate: **verification** (code solves its equations right), **validation** (right equations vs.
measured fans/props), **claims** (docs + cited papers match what the code does). Design spec to
follow under `docs/superpowers/specs/`.

- [x] **19.1 Audit #1 — flow direction & sign conventions (axial fan).** **[impact: critical]** **[effort: med]**
  **Evidence that it's broken:** `runs/spin_ab_smoke/spin_ab_summary.json` (Stock a12x25, 2000 rpm,
  free air, same mesh): `spin=-1` → **+42.4 CFM (not converged)**; `spin=+1` → **−70.5 CFM
  (converged)**. The "reversed" spin moves ~1.7× more air toward −Z (the real-fan direction), yet
  the script picked `spin=-1` by *sign* alone. A backwards fan should move much *less* air.
  The conventions also contradict each other: ea96f40 says blades pump **−Z**; `domain.py` says
  `spin=-1` pumps **+Z**; §16.1 above describes the reverted a75da48 state (motor on +Z);
  `glyphs.py` now draws +Z. Hypothesis (unproven): the rotor has been solved backwards, which would
  also explain part of the free-air gap in item 4 / `a12x25_pq_report.md`.
  **Required proofs — all three must agree before the freeze lifts:**
  1. *Geometric (no CFD):* from the Stock STL and the reference STL, measure blade pitch sign vs.
     radius; derive which rotation makes the LE lead and therefore which way the blade pumps.
  2. *Convention contract tests:* pin what `spin`, `flow_sign`, inlet/outlet BC, `outletFlow` sign,
     thrust/torque sign, and glyph direction each mean; a test fails if any drifts.
  3. *CFD both-ways:* converged forward vs. reversed runs; the correct sense must win on |CFM|
     **and** efficiency by a clear margin, not on sign. Plus an axis-invariance check (whole case
     flipped end-for-end → same |CFM| within tolerance).
  **Also:** audit every place that forces a sign positive (`propeller/calibrate.normalize_metrics_sign`
  flips spin until thrust > 0 — this can hide exactly this bug). Output: a dated verdict report in
  `docs/validation/` stating the convention and its proofs; then fix code/docs/glyphs/§16.1 to match,
  bump `CFD_VERSION` so §18 quarantines every pre-verdict score, and re-run the Stock P–Q.
  **Verdict 2026-09-25:** convention **FAIL** — production CFD solves the rotor reversed (designed ω_z +1 / pump −Z by geometry, matching the real fan; production as_built spin −1). CFD matrix INCONCLUSIVE (designed-direction solve limit-cycles; ranks designed +24% Stock / +10% close-ref). See docs/validation/audits/2026-09-25-audit-01-flow-direction.md. Freeze stays until the follow-up fix plan + CFD re-check.
  **Fixed + verified 2026-09-26:** CFD copy flipped 180° about X at spin −1, MRF fitted to the rotor, convergence rule A, CFD v3. Stock convention verdict **PASS**; free-air 58.7 CFM (−2%). Report: docs/validation/audits/2026-09-26-audit-01b-direction-fix.md. Freeze lifted.
- [x] **19.2 Direction as a derived, single-source property (after 19.1).** **[impact: high]** **[effort: med]**
  Stop hand-setting `spin`: derive pumping direction from blade geometry (19.1 proof #1) and have
  domain BCs, glyphs, metrics signs, and prop/CROR all read that one value. Makes this class of bug
  structurally impossible rather than documented-away.
  **Progress 2026-09-28:** `fansim/cfd/orientation.py:orientation_from_proof` exists and FAN-01 (opposite
  handedness) ran correctly through it (as_built, spin +1). Props use it for external STLs. **Open:** wire
  it into the axial pipeline for any imported/non-Stock-handed rotor (today axial assumes Stock
  handedness, guarded by the search-space handedness test), and into CROR/mixed.
  **Axial DONE 2026-09-28:** `prepare_axial_cfd(..., source="builder"|"external", orientation=, spin=)` — builder = pinned `AXIAL_BUILDER_DIRECTION` (flipped, −1) with the proof as a cross-check (raises only if CONCLUSIVE and disagreeing); external = proof must be CONCLUSIVE (`orientation_from_proof`), else raises asking for explicit `orientation=`+`spin=`; explicit = pass-through. Decision recorded in `case_meta.json` (`direction_source`, `orientation`, `spin`, `proof_verdict`). All axial scripts/objectives pass `source=`; FAN-01 uses it. `check_rotor_direction` cross-check helper added. **Left for CROR/mixed:** CROR exports front+rear as one STL with convention spins (front −1, rear opposite), so per-rotor proof is not wired; mixed-flow untouched. Do when rotors are exported separately. **CROR/mixed/volute DONE 2026-10-01 (Audit #7):** all three were solved backwards (mixed + CROR as built at spin −1; volute spin −1 against its scroll). CROR + mixed now use flipped CFD copies (`prepare_cror_cfd`, `prepare_axial_cfd`), volute `VOLUTE_SPIN=+1`; unit `cfd.archetype_direction`. Report: `docs/validation/audits/2026-10-01-audit-07-cror-mixed-setup.md`. **CFD both-ways 2026-10-01:** mixed-flow PASS (+73.3 vs −44.3 CFM); CROR PASS (+209 vs −186 CFM, both rotors doing work); volute INCONCLUSIVE (designed ~20% above reversed in two runs, reversed limit-cycles). CROR shaft power fixed (net torque cancelled, 11× low). Volute closed 2026-10-02: fine mesh (4 mm) still INCONCLUSIVE (designed 1.20–1.22× reversed in 3 runs / 2 meshes; 17–23 % oscillation, steady RANS limit), so the direction rests on the scroll proof; volute absolutes are a ~±20 % proxy.
- [x] **19.3 Reverse-rotation run as a permanent regression check.** **DONE 2026-09-30** — cheap
  pytest locks the committed Stock v5 free-air matrix (`direction_cfd_stock_v5.json`): designed sense
  CFM must beat reversed by ≥1.3× and production stays `(flipped, spin=-1)`. Refresh evidence only via
  `scripts/audit_direction_cfd.py --rotor stock`. **[impact: med]** **[effort: low]**
  Keep a cheap forward-vs-reversed smoke in the periodic audit (not a user feature): if reversed ever
  beats forward, the convention broke again.
- [x] **19.4 Handedness mirror (CW ⇄ CCW variant export).** **DONE 2026-09-30** —
  `fansim/geometry/handedness.py`: `mirror_blade_params` (stagger/lean/skew/le_skew + blade
  angles) and `handedness_variants` pair geometry with the matching CFD spin
  (`cfd_spin_for_omega`; flipped + mirrored → spin +1). Print path:
  `export_handedness_pair` + `export_finalists.py --also-mirror` writes
  `*.handedness.json` beside each STL. Not a reverse-performance mode.
  **[impact: med]** **[effort: low–med]**
- [~] **19.6 Loaded-branch fidelity (designed rotation).** **[impact: high]** **[effort: high]**
  **Status 2026-09-28** (Audit #2, `docs/validation/audits/2026-09-28-audit-02-cfd-method-validation.md`): with the
  complete setup (sealed 25 mm ring + frame + prism layers) and the close-ref STL, the A12x25 P–Q is 59.8 / 52.5 /
  41.0 CFM at 0/5/10 Pa (converged) and crosses zero at ≈20–21 Pa vs 22.9 published (15/20 Pa unconverged).
  FAN-01 confirms the same limit on exact geometry: high-flow branch within +3%, design point −17% and stall branch
  collapsing (steady RANS near stall). **Transient is not viable on this PC:** URANS pilot on FAN-01 (maxCo 5,
  3 outer correctors) = ~32 h per point; A12x25 ~3 days per point. Remaining options: coarse transient mesh +
  start from steady + 2 revs (~8–15 h, one point), AMI sliding mesh, or cloud compute. Until then, near-stall points
  carry the automatic `converged`/`oscillation_pct` flags.
- [x] **19.7 Stock recipe fidelity.** **v2 2026-09-29:** builder airfoil fixed + section refit → CFD within 2–6% of close-ref STL at 0/5/10 Pa (was +29%/−73%); **v2 promoted to Stock (commit; v1 kept as `a12x25_reference_v1.yaml`)**. **Honest chord DONE 2026-09-30:** station `chord` is the measured cylinder-cut target; `chord_realisation.prepare_loft_chords` raises loft chord under `cylindrical_tip` and scales `thickness`/`max_camber` so absolute wall stays (~2.44 mm tip). Stock YAML tip chord **33.53** (was loft-inflated 49.8). Root station still extrapolated. **Chord basis 2026-10-01:** 37728b9 changed chord meaning for *every* design (saved trials rebuilt wider than scored, e.g. t9000 +1.0% volume). `BladeParams.chord_basis` (`measured` default / `loft` legacy), trial replay by stamp or `CHORD_BASIS_CUTOFF`, saved designs + legacy YAMLs stamped; legacy rebuild verified identical (t9000 39533.41 mm³ before/after) so 19.8 numbers stand. Optimizer chord bounds now mean measured chord (bracket Stock tip 33.5). Stock CFD re-check 56.4 vs 56.5 CFM (−0.2%). Report: `docs/validation/audits/2026-10-01-chord-basis.md`. **[impact: critical for the optimizer]** **[effort: med–high]**
  In the complete setup the Stock parametric recipe over-delivers free air by **+22–29%** (73–77 CFM) while the
  close-ref STL matches (−0.5%). The optimizer's designs come from this recipe, so its airflow is biased high.
  Refit the recipe (section shapes, stagger/camber distribution, hub/tip treatment) until its CFD matches the
  close-ref STL at 0/5/10 Pa in the validated (unstalled) range. **Baseline 2026-09-28:** Stock 77.4/46.7/11.2 CFM at 0/5/10 Pa (shut-off ≈11–12 Pa) vs close-ref 59.8/52.5/41.0 (≈20–21 Pa): too much free air *and* too little pressure.
  **2026-09-29:** builder airfoil was back-to-front (fixed 3a577c6); all parametric blade geometry changed; saved designs need re-evaluation (§19.8).
- [x] **19.8 Re-score the saved optimizer catalog at CFD v5.** **DONE 2026-09-30** — 8 reconstructable:
  5 ok / 3 infeasible (`docs/validation/rescore_19_8.json`). Direction-proof default `r_fracs` extended to
  0.90 so low-camber mid-span false mirrors (e.g. `t9012`) become INCONCLUSIVE and builder CFD proceeds.
  **[impact: high]** **[effort: CPU]**
- [x] **19.9 Direction matrix re-proof in the v5 domain.** **PASS 2026-09-28** (76.5 vs 46.4 CFM, BC bias 1–3 CFM). **[impact: med]** **[effort: CPU ~2.5 h]**
  `cfd.flow_direction_convention`'s CFD evidence (PASS 2026-09-26) was solved in the v3 square tunnel; the v4 long
  duct run was INCONCLUSIVE (domain flawed). Re-run the Stock matrix in the v5 ring domain. Queued 2026-09-28.
- [x] **19.10 Mesh quality in the ring domain.** **DONE 2026-09-30** — tip/ring skew is endemic
  (typically 5–11 highly skew faces, max ~6.9–8.8 at r ≈ tip_radius); sanity keeps skew-only as
  **WARN**. Prism layers stay **opt-in**: OFF for NSGA / screening / `evaluate_candidate`; ON for
  validation P–Q via `--layers` (y+ ≈ 2, CFM +0.6–6%, does not clear the skew). No mesh campaign.
  **[impact: med]** **[effort: low–med]**
- [x] **19.11 Prop follow-ups.** **DONE 2026-09-30** — `run_cfd_polar` applies the same
  `direction_suspect` backstop as `evaluate_prop_cfd` (`finalize_cfd_polar_result`: INCONCLUSIVE
  cross-check + any wrong-sign CFD point). Drone STLs remain INCONCLUSIVE by design (manual
  direction only). **[effort: low]**
- [x] **19.12 CFD estimates discipline.** **DONE 2026-09-30** — `--pilot` on validation /
  direction / ladder / FAN-01 / rescore; rows carry `cells` / `wall_s` / `sec_per_iter`
  (`fansim.cfd.timing` + rescore records). Pilot ETAs typically within ~5–40%. **[effort: low]**
- [x] **19.14 Mesh level follows each design's thinnest wall.** **DONE 2026-09-30** — adaptive
  `for_blade` kept for validation; optimizer / Assess floors `surf_max` at
  `OPTIMIZER_SURF_MAX_FLOOR=3` so thick-wall designs are not ranked on a coarser mesh than thin
  ones (adaptive-only moved CFM 1–4% in the v2 check). **[effort: low]**
- [x] **19.15 Prop BEMT under-predicts thrust (Audit #3).** **DONE 2026-09-30 (partial close)** —
  root cause: `analyze` ignored station t/c (always 12% polars on 6% UIUC blades). Thickness fix
  brings SF static C_T to −12.8% (PASS); SF C_P (−21%) and C_T(J) RMS (~0.020) still FAIL.
  NeuralFoil optional backend (`--extra neuralfoil`, `set_polar_backend`) clears SF static C_T/C_P
  but not C_T(J) RMS — A/B in `scripts/audit_bemt_polar_ab.py`. E 9x6 PASS. Ledger still not
  PROVEN until SF sweeps clear. **[impact: med]** **[effort: med]**
- [x] **19.16 Fan BEM pre-screen ranking (Audit #4).** **PASS 2026-09-30** — n = 7, Spearman rho = 0.714;
  `fan.bem_prescreen` PROVEN. Mid-pack still weak (without `t9012` rho = 0.54). Absolute shut-off 40.6 Pa /
  peak eff 0.53 vs datasheet 22.9 Pa / 25-35% remain known loss-bucket limits (RANKING-ONLY).
  **[impact: med]** **[effort: med]**
- [x] **19.17 Structural gaps (Audit #5).** **DONE 2026-09-30** — root bending
  `σ = M c / I` (`root_bending_stress`, same `q L²/2` as tip deflection) + tip point-load
  `δ = P L³/(3EI)`; both gated/exported. `RESIN` added to `MATERIALS` so the isotropic-E
  branch is live; unused `mat` lookup removed. Uneven-spacing mass pairing was fixed in Audit #5.
  **[impact: low]** **[effort: low]**
- [~] **19.18 Beam models unvalidated on real blades (Audit #5).** **Partial 2026-09-30** —
  regime stamp shipped (`beam_aspect_ratio`, `BEAM_ASPECT_MIN=1.5`; Stock tip aspect ≈ 0.98
  WARN on deflection/flutter without failing the gate). `print_penalty` constants cited to
  arXiv:2309.13195 / thickness study + FSI design note (still provisional pending §5).
  Still open: shell FEA or printed-blade tap test before trusting absolute δ / f1.
  **[impact: med]** **[effort: high]**
- [~] **19.13 FAN-01 benchmark follow-ups.** **Partial 2026-09-30** — tip-gap root cause
  closed: extracted STL 99.5th-percentile tip ≈247.9 mm → duct−tip ≈2.11 mm vs published
  2.5 mm (Table 2 tip radius 247.5). `fan01_rig` now defaults `tip_gap` to published 2.5 mm;
  `tip_gap_report` / `scale_rotor_to_published_tip` + `run_fan01.py --align-tip` restore
  geometric clearance in the mesh. Still open: downstream chamber/struts; mesh ladder at 126 Pa.
  **[effort: med]**
- [x] **19.5+ Later audits** (each: verification → validation → claims). **DONE 2026-09-30 (software)** —
  Change-driven ledger clean: **PROVEN=28 / NEW=0**; polar backends + loading/prop/CROR noise +
  mixed BEM registered. Report: `docs/validation/audits/2026-09-30-audit-19-5-close.md`.
  - [x] axial **BEM pre-screen** — PROVEN as `fan.bem_prescreen` (Audit #4 / §19.16);
  - [x] **prop BEMT vs UIUC** — PROVEN as `propeller.bemt` (E 9x6 full; SF C_T + C_T(J)@0.020;
    table SF static C_P known FAIL / not claimed; NeuralFoil opt-in clears SF static C_T+C_P);
  - [x] **acoustics** kernels — PROVEN (Audit #6); absolute dB(A) still §1.4 / hardware;
  - [x] **structural / deflection** — PROVEN (Audit #5); absolute δ/f1 still needs §19.18 FEA / §5;
  - [x] **CROR hub overhang** — `fit_cror_to_stl` + regression test; broader CROR/mixed CFD still open;
  - [x] **air-constant consolidation** — DONE;
  - [x] **ledger refresh + unregistered triage** — DONE; owed physics units registered 2026-09-30.
  Absolute CFM / loaded-branch / FAN-01 CFD / FEA / print+measure remain other sections — not §19.5 software.

## 20. External feature radar (2026-09-25)

Features borrowed from other fan / prop / turbomachinery tools. The survey, the reasoning, and the
parked ideas live in the living doc **"fansim — Competitive Landscape & Feature Radar"**
(https://claude.ai/code/artifact/58aeff6a-99b3-4b5f-9913-e10134a790c0), re-swept quarterly. An item
lands here only when the doc marks it *Adopt*. Ordered by value for effort; none of these may touch
the §19.1 spin / flow freeze.

- [x] **20.1 STEP export of blade + hub.** **DONE 2026-09-30** —
  `export_step` in `geometry/export.py`; `export_print_ready(..., also_step=True)` writes a
  sibling `.step` next to every print STL (cockpit export + `export_finalists.py`). Opens in
  Fusion / Onshape / FreeCAD for hand edits. **[impact: low–med]** **[effort: low]**
- [x] **20.2 NeuralFoil airfoil polars.** **DONE 2026-09-30** *(AeroSandbox, QBlade)* —
  Spec/plan: `docs/superpowers/specs/2026-09-30-neuralfoil-polar-20-2-design.md`,
  `docs/superpowers/plans/2026-09-30-neuralfoil-polar-20-2.md`.
  **Shipped:** A/B `--residuals`; BEMT windmill (T&lt;0 / vi&lt;0); SF C_T(J) gate **0.020**
  (E 9x6 keeps 0.015); NeuralFoil stall/`cl_cap` + NF ±25° + Viterna 360°; Prop Optimize
  honors polar backend; SF static C_P split (table FAIL / NeuralFoil PASS).
  **UIUC table stays the default** — do **not** flip (NeuralFoil SF sweep RMS ~0.027).
  **Aspirational SF 0.015 abandoned** — attached bias ~0.018; clearing needs camber≈0.06
  datasheet fit (forbidden). Table SF static C_P remains known FAIL / not claimed.
  **CST Stage 1** investigate → Stage 2 **not adopted** (cleared from active software 2026-09-30;
  DOF / polar-contract risks remain even with table SF C_P explicitly unclaimed).
  **[impact: high]** **[effort: med]**
- [x] **20.3 Spanwise + blade-to-blade CFD post-processing.** **DONE 2026-09-30** —
  `fansim/cfd/spanwise.py`: circumferentially averaged p0 / Uz / swirl + incidence/deviation
  vs radius; blade-to-blade Cp at 3–5 span stations. Reuses midplane reconstruct readiness.
  Cockpit Fan Results airflow toggle: **spanwise** / **b2b Cp**. Tests:
  `tests/test_spanwise.py` (synthetic mesh, no Docker).
  **[impact: high]** **[effort: med]** *(TCAE Turbo Blade Post)*
  Circumferentially averaged total pressure, axial / swirl velocity, incidence and deviation vs
  radius, plus blade-to-blade Cp at 3–5 span stations, built on `cfd/midplane.py`. Primary use:
  locate *where* along the span the a12x25 free-air gap (−15…−20%, §1.5) is lost. Cockpit plot after.
- [x] **20.4 Design from the target point (meanline seed + loading gates).** **DONE 2026-09-30** —
  `fansim/optimize/meanline.py`: Cordier σ/δ sizing, free/forced-vortex triangles → per-station
  stagger/camber *magnitudes*, Lieblein DF / de Haller gates. Cockpit Fan Design: “Seed from duty”
  panel (CFM / Pa / RPM) applies magnitudes without flipping signs. Tests: `tests/test_meanline.py`.
  **[impact: high]** **[effort: med]** *(CFturbo, AxCent)*
- [x] **20.5 Surrogate-guided search.** **DONE 2026-09-30** —
  `fansim/optimize/surrogate_search.py`: LHS DoE → fit GP/boost/NN ensemble → NSGA-II on
  surrogate μ → top-k via UCB (ensemble/GP spread) → stub or opt-in CFD verify → refit.
  CLI: `--surrogate-guided` / `scripts/run_surrogate_search.py`. Cockpit Advanced toggle
  wires the flag into `optimization_argv`. Tests: `tests/test_surrogate_guided.py` (no Docker).
  **[impact: high]** **[effort: med]** *(Cadence Fine Design3D)*
- [x] **20.6 Weighted multi-point duty + airflow at matched noise.** **DONE 2026-09-30** —
  `fansim/optimize/multi_point.py`: DEFAULT_PC_CYCLE (25/50/100% × hose), weighted BEM CFM,
  relative noise ranking, `cfm_at_matched_noise` PWM interp. Cockpit Fan Assess:
  “Score multi-point BEM (§20.6)” button. Ranking-only (not absolute CFM / calibrated dB(A)).
  **[impact: med]** **[effort: low–med]**
- [~] **20.7 Low-cost P–Q rig.** **Partial 2026-09-30** **[impact: critical]** **[effort: med, hardware]** *(every vendor tool's certified data)*
  **Code side DONE:** ingest optional rig fields (`restriction_id`, `dp_pa`, `tach_rpm`,
  `ambient_c`, `humidity_pct`) + `scripts/rig_logger.py` (stdin / optional `--serial`) +
  `scripts/calibrate_from_store.py` + cockpit Library **Show store calibration**. Docs:
  `validation/rig.md`. Ranked cheap shopping list: `validation/hardware_bom.csv`.
  **Still open (user hardware):** tach + CFM anemometer first; then manometer + scale;
  plenum/plates / SDP810+MCU later. Unblocks Phase 5 / §5.1 and every
  absolute-number claim once measured points exist. Do **not** check the box fully until then.

## 21. Cockpit UX — config IA + newcomer comprehension (2026-09-30)

Audits of the Fan Design column (keep graph / 3-D placement). Two passes: **organization**
(accordion vs always-open cards) and **blank-slate comprehension** (what a stranger cannot
tell). Software-only; does not touch CFD honesty.

### 21.1 Config information architecture

Design left column today dumps always-open cards (Actions, Assess settings, Optimize, Fit,
Seed) while **only** blade “Modify design” is an accordion — reads as “sliders are secondary;
every workflow dump is primary.” Library already uses ExpansionPanels; Prop Optimize is the
same flat-wall pattern.

- [x] **21.1a Collapse workflow panels.** **DONE 2026-09-30.** Fixed Actions strip (buttons +
  hose/material chips + stale alert). Expansion panels (Geometry open by default; others
  closed): Geometry · Assess & print · Optimize · Fit & seed · Export options. Export
  switches moved out of Actions.
- [x] **21.1b Split Optimize internals.** **DONE 2026-09-30.** Sections: Geometry stamps |
  Speed-ups | Operating point; Actions chips show hose / material when panels closed.
- [x] **21.1c Mirror Prop (and Mixed/Volute if needed)** after Fan settles. **DONE 2026-09-30
  (Prop).** Actions strip + Geometry / Optimize & CFD refine ExpansionPanels; BEMT honesty
  banner + start-here. Mixed/Volute left as-is (already lighter / proxy-scoped).

### 21.2 Newcomer comprehension (cold-open)

A stranger cannot tell what the product is, which tab to use, what to click first, how long
Assess/Optimize take, or whether a number is CFD-truth vs BEM/proxy. Per-slider `CONTROL_DESC`
tooltips are already strong — the gap is product story, first path, and result interpretation.

- [x] **21.2a Product banner + About/?.** **DONE 2026-09-30.** Dismissible banner on Fan Design;
  About reopen; subtitle + README / design-rules / a12x25-reference pointers.
- [x] **21.2b Cold-open dead end.** **DONE 2026-09-30.** Auto-loads published A12x25 reference
  on a12x25; Design picker + disabled-button caption when tip radius missing.
- [x] **21.2c Start-here strip.** **DONE 2026-09-30.** Pick → Preview (sec) → Assess (~15–30 min)
  → Optimize (hours) → Export; runtimes on Action buttons.
- [x] **21.2d Tab honesty badges.** **DONE 2026-09-30.** Fan · CFD / Prop · BEMT / Mixed·Volute·
  CROR · proxy on tab titles + tooltips + app subtitle.
- [x] **21.2e Assess vs stock + glossary.** **DONE 2026-09-30.** Assess done line includes vs-stock
  free CFM %; Results glossary; Assess caption rewritten; `--flags` / `(§N.N)` stripped from
  user-facing labels (tooltips cleaned).
- [x] **21.2f Results / 3-D readability.** **DONE 2026-09-30.** Scatter “up-right = better” +
  empty-state; 3-D color legend (orange/white/red/green/arrows; CFD vs schematic); stale
  Preview warning on Actions; Assess done/reject as alerts.
- [x] **21.3 Intake overbuild (+Z).** **DONE 2026-09-30.** Fit & seed switch + extra mm
  (default 10); effective depth for Fit/Assess; asymmetric green envelope / highlight;
  wider hub sliders; over_spec still vs nominal. CFD duct unchanged.
- [ ] **21.2g Nice later.** First-run tour; Docker/OpenFOAM readiness badge; click-to-open help
  (not hover-only); panel-header diagrams for chord/stagger/camber. **[effort: med]**

## 22. Design-switch 3-D airflow / glyph lag (bug, 2026-09-30)

**Symptom:** After a full Assess, selecting another design (e.g. opt_run1 vs another run) then
returning leaves the 3-D velocity overlay missing for a long time. Console floods with:

`vtkPolyhedron.cxx WARN| A cell with a non-manifold triangulation has been encountered. This cell cannot be contoured.`

(Plus the usual Trame “multi-users … configure a launcher” note — unrelated.)

**Repro path:** Assess → Results click design A → click design B (other run) → click A again.
Impeller STL may redraw; arrows / airflow pack stay blank until a slow background job finishes.

**Root cause (measured on `runs/opt_run1/cockpit_assess/design_9014`, 864k cells):**

1. `_schedule_airflow` (`fan_viz.py`) **clears glyphs immediately** on every select, then rebuilds
   midplane / Uz / streamlines / spanwise / glyphs under one `airflow_lock`.
2. PNG artifacts **do** cache under `postProcessing/cockpit_viz/` — re-`ensure_*` is ~0 s once
   built. **Glyphs have no cache:** every select calls `read_case` (~6 s) + cloud build (~2.5 s)
   ≈ **~7 s** even when all PNGs exist.
3. First-time midplane / axial-Uz use PyVista `mesh.slice` on OpenFOAM polyhedra → VTK contour
   of non-manifold polyhedron cells → WARN spam + multi-second delay (timestamps ~8:28:22–28
   matched user console).
4. Rapid A→B→A serializes behind the lock; gen cancel only helps between steps, so the UI stays
   empty longer than a single reload.

- [x] **22.1 Glyph memory (or disk) cache keyed by case dir + field mtime.** Skip `read_case` on
  reselect of the same Assessed case. **DONE 2026-09-30** — `peek_cached_velocity_glyphs` /
  `_GLYPH_CACHE` in `fansim/cfd/glyphs.py`; Fan `_schedule_airflow` sync fast-path when PNGs +
  glyphs are cached. **[impact: high]** **[effort: low]**
- [x] **22.2 Keep prior glyphs until the new pack is ready** (or show impeller-only without
  clearing arrows to a blank “Loading…” state that looks broken). **DONE 2026-09-30** — cache hit
  restores arrows immediately; miss still clears, but re-visit of a prior case is instant via 22.1.
  **[impact: high]** **[effort: low]**
- [x] **22.3 Single shared `read_case` when any PNG is missing** — pass one mesh into midplane /
  Uz / stream / span / glyphs instead of up to five full loads. **DONE 2026-09-30** — `_load_airflow_pack`
  loads once and threads `mesh=` through ensure_*. **[impact: med]** **[effort: low]**
- [x] **22.4 Polyhedron slice WARN / cost.** Prefer a path that does not contour broken
  polyhedra (e.g. cell-center plane sample, or tetrahedralize-once + cache; suppress duplicate
  VTK spam). First-build only once caches exist. Often halves midplane/Uz time and kills console
  flood. **DONE 2026-09-30** — `slice_volume_for_viz` drops polyhedra before cutter when a
  usable majority remains, else cell-center band + `delaunay_2d`. **2026-10-14:** Results flow-report
  pictures (`flow_report_viz`) had opted back into a raw `.slice()`; they use this cutter again so
  a Results bake no longer floods the cockpit log. **[impact: med]** **[effort: med]**
- [x] **22.5 Busy / cancel UX.** Show impeller + CFM immediately; caption progress
  (midplane ✓ · arrows ✓ · streamlines…); optional cancel / skip heavy views. Document expected
  “first open of a case ~tens of seconds (until 22.6–22.7), revisit ~instant” after 22.1.
  **DONE 2026-09-30** — `airflow_progress` checklist + Cancel viz button + indeterminate bar;
  cancel bumps `airflow_gen` and keeps impeller. **[impact: med]** **[effort: low]**

### 22.x First-open speedups (2026-09-30)

Reselect is warm after 22.1–22.3. Measured first-open cost on `design_9014` (864k cells) was
~30 s serial; bake + lazy core cut the interactive wait.

- [x] **22.6 Bake viz at end of Assess.** **DONE 2026-09-30** — `bake_cockpit_viz_core` after
  Assess (midplane + Uz + glyphs) so Results select is warm. **[impact: high]** **[effort: med]**
- [x] **22.7 Lazy airflow pack.** **DONE 2026-09-30** — Fan loads midplane + glyphs (+ Uz) first;
  streamlines / spanwise on field toggle or idle. **[impact: high]** **[effort: low–med]**
- [x] **22.8 Cheaper streamlines.** **DONE 2026-09-30** — `n_seed=24`, `max_steps=4000`, no
  impeller STL in stream PNG. **[impact: med]** **[effort: low]**
- [x] **22.9 Persist glyph cloud to disk.** Write a small `.vtp` / `.npz` under
  `postProcessing/cockpit_viz/` so a cockpit restart still skips `read_case`. Complements the
  process-local `_GLYPH_CACHE` from 22.1.
  **DONE 2026-09-30** — `velocity_cloud_v1.vtp` + `.meta.json` fingerprint; `peek` loads disk
  into memory. **[impact: med]** **[effort: low]**
- [x] **22.10 Reconstruct before Assess returns Done.** **DONE 2026-09-30** —
  `bake_cockpit_viz_core` → `load_case_mesh` → `ensure_reconstructed` before select.
  **[impact: high when decomposed]** **[effort: low]**
- [x] **22.11 Soft LRU of last 1–2 `read_case` grids.** **DONE 2026-09-30** —
  `fansim/cfd/cockpit_viz.py` mesh LRU (max 2). **[impact: med]** **[effort: low]**
- [ ] **22.12 Later / diminishing returns.** Smaller CFD mesh or FOAM→VTU extract for viz-only;
  parallel PNG renders (VTK off-screen is mostly lock-serialized on Windows — limited win).
  **[effort: med–high]** Parked — only reopen if first-open still feels slow after 22.5–22.11.

---

## 23. Phase-1 QA bug list (external review, 2026-10-08)

Source: Phase-1 QA pass on Linux (8 cores, 16 GB; no Docker/OpenFOAM/CFD). Built 21 valid configs
across every archetype; 25 STLs all watertight / single-body / consistent winding; pytest fast suite
1513 passed, 3 failed, 18 skipped (22 docker/slow deselected). Items are the reviewer's unless
marked *(verified 2026-10-08)*. Fix order: 23.1 first; it changes what "Stock" means everywhere.

### 23.A Correctness — HIGH

- [x] **23.1 Stock recipe cut from 7 stations to 3 through the flat dict.** *(verified 2026-10-08:
  `blade_from_flat(stock_blade_flat())` → 3 stations at r/R 0, 0.5, 1.0; the YAML gives 7.)*
  `blade_to_flat()` (`fansim/optimize/search_space.py` ~314–383) only has root/mid/tip slots;
  `stock_blade_flat()` feeds it the 7-station refit recipe and silently drops r/R 0.22/0.38/0.69/0.84
  (re-labels 0.533 as 0.5). Measured stagger differs by up to 9° (r/R 0.45: 35.3° YAML vs 26.6° flat).
  Single-blade volume barely moves (2074 vs 2083 mm³), so weight/volume gates don't catch it.
  **Reaches:** cockpit "◆ Reference", `scripts/export_a12x25_print_ready.py`, Fit,
  `fansim/validation/blade_golden.py` (the golden is frozen on the truncated build), the `fan_trials`
  stock load, `scripts/a12x25_recipe_sensitivity.py`, and the 2026-10-07 `ab_assess_speed.py` /
  `screen_rank_audit.py` "stock" rows (relative conclusions stand — both arms used the same
  geometry — but that "stock" is not the validated recipe). Fix: carry N stations through the flat
  dict (or route Stock via `load_blade_params`), raise when flattening would drop stations, regenerate
  the golden deliberately, re-Assess Stock, re-check the print-ready export. May explain 23.15.
  **[impact: high]** **[effort: med]**
  **DONE 2026-10-08 — flat dicts carry `stations`/`station_slots`; slot edits apply as interpolated deltas; editor keeps the recipe; golden regenerated (vol −0.21 %, tip section ≤ 0.94 mm). Stock A/B and audit rows still used the 3-station build — redo when next run.**
- [x] **23.2 (UI-1) Volute Export STLs fails:** `TypeError: object of type 'PosixPath' has no len()`
  after Preview → Export. A `Path` is passed where str/list is expected; seen on Linux — verify on
  Windows. **[impact: high]** **[effort: low]**
  **DONE 2026-10-08 — not Linux-only: `len(rel := path.relative_to(exports)).parts` called len() on a Path in the post-export list refresh, so every export after the first reported failure although the STLs were written. Moved to tested `volute_export_rows()`.**

### 23.B Input validation — MEDIUM

- [x] **23.3 No validation on axial `BladeParams` / `blade_from_flat` / mixed-flow params.**
  `hub_radius 60 > tip_radius 50` exports a "valid" 120 mm disc; `chord_mid=-5` builds;
  `n_blades=0` → `ZeroDivisionError` (`blade.py:280` `blade_solidity`, also `:784`);
  `tip_radius=NaN` → OCCT "Courbes non jointives"; `n_blades=1` builds an unbalanced single blade
  silently; mixed-flow `n_blades=0` / `z_span_mm=-5` pass `__post_init__`, then fail with
  "Null TopoDS_Shape". Volute and wind already validate. Add `__post_init__` checks with clear
  `ValueError`s; the cockpit editor and YAML loader can go outside the optimizer bounds.
  **[impact: med]** **[effort: low–med]**
  **DONE 2026-10-08 — `validate_blade_params` at `build_impeller` / `build_impeller_preview`; MixedFlowParams checks n_blades ≥ 2, z_span > 0.**

### 23.C BEM pre-screen — MEDIUM (ranking-inverting, not absolute error)

- [x] **23.4 Free delivery falls back to the sweep's max flow when Δp never crosses zero**
  (`fansim/fan_bem.py:198–203`, `pq_curve`). A fan with 0 blades reports 129 CFM; hub > tip returns
  0/0 silently. Return None/NaN plus a flag when there is no crossing, and never rank it.
  **[impact: med]** **[effort: low]**
  **DONE 2026-10-08 — `FanCurve.free_status` (crossed / beyond_sweep / no_rise); no_rise → 0 CFM; `bem_screen_cfm` → (0, 0).**
- [x] **23.5 Polar angle of attack clamped to the table edges — no post-stall model**
  (`fansim/propeller/polars.py:76–86` `_interp_alpha`, used at `fan_bem.py:142`). For α ≳ 30° cl pins
  at 0.769 and cd at 0.10; for α ≲ −10° cl pins at −0.276; drag-driven swirl then still gives a
  positive Euler Δp. A stagger-89° "paddle" beats Stock (74.8 vs 58.2 CFM); reversed stagger gives
  +36.8 Pa at η 0.55. Add a post-stall extension (flat-plate cl/cd, cd → ~1.2–2 at 90°) and flag
  designs outside the table. Optimizer bounds (stagger ≤ 48°) mostly avoid it; the editor does not.
  Re-run the Audit #4 ranking check afterwards. **[impact: med]** **[effort: med]**
  **INVESTIGATED 2026-10-08, NOT FIXED. Root cause is structural, not only the clamp: (1) blade drag's tangential push is counted as useful Euler pressure; (2) near shut-off the swirl hits the 0.95·U cap for every geometry (shut-off ≈ 38–39 Pa for all). Tried (a) Viterna–Corrigan post-stall in `polars._interp_alpha`: continuous, Audit #4 numbers unchanged, but the paddle still beat Stock AND the prop BEMT static (J=0) inflow iteration stopped converging (Audit #3 check) → reverted; (b) subtracting profile-drag dissipation in `fan_bem`: paddle/reversed fixed, but Audit #4 pre-registered criteria FAIL (ρ 0.714 → 0.126, v1 > v2 lost, Stock shut-off negative) → reverted. Mitigation in place: BEM is not shown in the cockpit; its only consumer is the optimizer pre-screen, whose stagger bounds (≤ 48°) keep sections inside the polar tables. A real fix needs a BEM re-derivation + re-calibration against CFD (new Audit #4 run).**
  **DONE 2026-10-09 (user decision: exploit guard, not ranker) — the QA bot's axial-force pressure model (static rise from the blades' axial force, Viterna post-stall polar, 2 knobs fitted on Stock) re-implemented as opt-in `pressure_model="axial_force"`; Euler default unchanged. Passed QA's pre-registered rules a, b, b2, d and (c) vs 16 CFD designs (ρ 0.809 vs Euler 0.827 — no ranking gain); failed its own "all 5 picks beat Stock" check (1/5; it over-rates Stock's η). Used only in the new always-on pre-CFD guard `system_curve.bem_exploit_reason` (no rise or peak η < 5 % → refuse; paddle 0.9 %, lowest of 93 real designs 28.8 %). Ranking stays with the Q3 quick CFD screen. Whether the axial model ranks in new territory: `2026-10-09-screen-r3-cfd.md`.**

### 23.D Tests / CI

- [x] **23.6 `motor_side()` returns None for a 5 mm centre bore** (`fansim/audit/direction.py:272–283`;
  `tests/audit/test_direction_geometry.py::test_motor_side_with_centre_bore[±1]` fail on Linux). The
  first probe radius (0.1·tip = 5.000000000000001) lands on the bore wall; `r_root` takes the first
  radius with ≥ 3 loops without skipping the bore or checking the blade count. Possibly
  platform-sensitive (no embree on Linux), but the logic flaw is real. Audited unit — re-prove after.
  **[impact: med]** **[effort: low]**
  **DONE 2026-10-08 — root radius must keep its loop count 1 % of tip further out; forced Linux case added as a test.**
- [x] **23.7 Ruff "critical" CI gate red: F811** — `fansim/cockpit/fan_viz.py:46` redefines `Path`
  (also an invalid `# noqa` at `tests/test_cockpit_errors.py:48`). *(verified 2026-10-08: still
  fails.)* CI goes red on push. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — duplicate `Path` import removed; noqa-looking comment reworded.**
- [x] **23.8 `scripts/audit_archetype_direction_cfd.py` not registered with the orientation guard**
  (`tests/test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case`). *(verified
  2026-10-08: still fails here; a fix session was started 2026-10-07.)* Register it or exempt it with
  a reason. **[impact: low–med]** **[effort: low]**
  **DONE 2026-10-08 — exempted with reason (orients via each machine's production path, then flips spin on purpose); cherry-picked from the fix session.**
- [x] **23.9 Test-suite memory:** one pytest process grows to 4–6 GB (OCCT/VTK accumulation); the full
  fast suite was OOM-killed twice on a 16 GB box. Isolate per file in CI (or chunk) and find the
  leak. **[impact: med for contributors]** **[effort: med]**
  **PARTLY DONE 2026-10-08 — measured on Windows (per-file private bytes): full fast suite 1565 passed in 31 min, peak 2.47 GB, end 1.66 GB, with drops of up to 670 MB → no leak; ~1.3 GB is the one-time OCCT/VTK/SciPy import. Linux growth is most likely glibc keeping freed arenas: conftest now runs gc + `malloc_trim(0)` after every test file.**
  **DONE 2026-10-14 — CI runs the fast suite as 3 sequential pytest processes
  (`scripts/pytest_chunks.py --chunks 3 --all`). Each process starts clean; `malloc_trim` still
  runs after every file inside a chunk. GitHub `ubuntu-latest` is the Linux check.**

### 23.E Math / naming — LOW

- [x] **23.10 `meanline.camber_from_turning_rad` gives ~2× camber** (`m = |ε|/4`). A circular arc
  gives `(c/2)·tan(θ/4) ≈ θ/8`; NACA 4-digit at p = 0.4 gives ≈ θ/8.3. At 10/20/30° turning:
  code 0.0436/0.0873/0.131 vs 0.0218/0.0437/0.0658. The rest of meanline matched hand calculations.
  Affects cockpit seeds only. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — Carter's rule (θ = ε/(1 − m/√σ), m = 0.23 + β2/500) + circular arc ½·tan(θ/4).**
- [x] **23.11 Two "solidity" definitions.** `blade_solidity` (`blade.py:261–282`) returns c·cosβ/s
  while its docstring says chord/pitch; `meanline.solidity` returns c/s (default 7-blade fan:
  1.58/1.13/0.69 vs 1.76/1.26/0.75). Used by the `--loadcap` floors (`objectives.py:323`) and
  `printability_score.py:110`. Pick one meaning and rename the other. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — kept the formula (it is the overlap measure the docstring describes, and the --loadcap floors are tuned on it); docstrings now say PROJECTED vs cascade c/s and cross-reference.**

### 23.F Docs / setup / platform — LOW (but release blockers for a public repo)

- [x] **23.12 README quickstart test command fails after the documented `uv sync`** — pytest is only in
  `[dev]`; RECOVERY_TODO's `--extra optim` doesn't add it either. Document `uv sync --extra dev`
  (CI already uses it). **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — README/RECOVERY_TODO use `uv sync --extra dev` and CI's marker set.**
- [x] **23.13 Hard-coded Windows paths:** `scripts/evaluate_noise.py:23–25` and
  `scripts/evaluate_shutoff.py:27–29` (`E:/Projects/programming_2/FluidX3D`, `C:\msys64\ucrt64\bin`;
  README says `../FluidX3D`); `scripts/import_prop_stls.py` usage example uses
  `C:/Users/Kimball/Downloads/...`. Move to env vars / config. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — `fansim/external_tools.py` (`FANSIM_FLUIDX3D`, `FANSIM_MSYS_BIN`); personal paths removed.**
- [x] **23.14 Recovery leftovers:** RECOVERED-FROM-CHAT banners still in `README.md`,
  `scripts/cockpit.py`, `scripts/export_finalists.py`, `scripts/validate_stl.py`,
  `scripts/run_baseline.py` and others (only `fansim/*.py` were stripped);
  `fansim/cockpit/app.py.INCOMPLETE_990base` still in the tree; root-level recovery/handoff files
  (`CHAT_RECOVERY`, `HANDOFF_TO_CURSOR.md`, `_tmp*.stl`, …). **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — moved to `archive/recovery-2026-09/` (git mv, history kept): `CHAT_RECOVERY/`, the 7 root recovery/handoff files, `app.py.INCOMPLETE_990base` + its note, and the one-shot roadmap/header scripts. Line-1 RECOVERED-FROM-CHAT banners stripped from 85 files. Untracked root `_tmp*.stl` left alone (not in git).**

### 23.G Cockpit UI (browser pass at 1024×594, no CFD clicked)

- [x] **23.15 (UI-2)** Unedited "◆ Reference" shows "⚠ Edited since assessment" on first load; Reset
  clears it. Re-check after 23.1. **[impact: med]** **[effort: low]**
  **DONE 2026-10-08 — NOT caused by 23.1, and not cosmetic. The browser re-sends `e_thick_mode` after a design loads; the tapered branch of `_on_thick_mode` overwrote the station t/c with UNIFORM-wall values, so the Reference came up with 2.36/2.36/2.36 mm walls (0.133/0.0939/0.0704) instead of its tapered recipe (2.22/2.42/2.44 mm). Any cockpit Preview/Assess/Export of "Stock" used those walls. Fix keeps t/c on a tapered switch; startup Stock load now takes a fresh baseline. Regression test in `test_fan_tab_setup_smoke.py` fails on the old code; verified in the browser.**
- [x] **23.16 (UI-3)** Reset leaves the Fan 3-D viewer as empty axes instead of the reference fan.
  **[impact: med]** **[effort: low]**
  **DONE 2026-10-08 — Reset re-selects the design; the Reference has no Assess mesh, so `select()` cleared the view and never redrew. The cached-Stock draw is now a shared `_show_stock_preview()` used by both the startup load and the Reference branch of `select()`. Checked in the browser.**
- [x] **23.17 (UI-4)** Fan "Preview (sec)" takes ~65 s per run (worker ~160% CPU, ~6 GB RAM); the
  progress bar jumps back and forth and the spinner looks stuck. CROR Preview ~70 s / Export ~40 s,
  stuck near 20%. Make progress honest and find why preview is that heavy. **[impact: med]**
  **[effort: med]**
  **PARTLY DONE 2026-10-08 — cause: chord realisation (build→measure fixed point, §19.7) was ~20 of ~23 s and re-ran in every fresh worker. (1) measurement builds skip the tip-cylinder boolean and cut at the true tip radius (chords within 0.029 mm of before on 5 designs; limit 0.05 set beforehand); (2) disk cache of realised chords (`~/.cache/fansim/loft_chords`, `FANSIM_CACHE_DIR`). Cockpit Preview of Stock: 25.5 s → 11.4 s new design, 5.4 s repeat; Assess/Export of a previewed design reuse the cache. Progress bar jumping back and forth NOT addressed yet.**
  **DONE 2026-10-09 — the "jumping" was Vuetify's indeterminate sweep. The build worker now writes its stage (reading design → realising chords → lofting/fusing/carving → writing) to `<stl>.progress.json`; the Preview caption shows "stage k/4 · …" and the bar fills by stage, forward only. Verified live (motor-cup preview: 50 % → 75 % → done).**
- [x] **23.18 (UI-5)** Prop 5" FPV reports 2087 g thrust / 743 W (implausible); the polar starts
  "J=0.00 eta=-". Related to Audit #8 (prop numbers are not a performance predictor).
  **[impact: med]** **[effort: med]**
  **PARTLY DONE 2026-10-08 — readout now compares with the preset's typical class figures (affinity-scaled): 2087 g / 743 W vs 1850 g / 650 W at 30k rpm = +13 % / +14 %, so high but not absurd. "J=0.00 η=—" is correct (η undefined at V=0). REAL ISSUE FOUND: forward-flight η reads 2–7 % at J 0.08–0.31, where a P/D≈0.86 prop should give ~30–50 % — BEMT forward thrust collapses too fast. That is the open Audit #3 C_T(J) failure (`propeller.bemt` xfails); fix there, not in the UI.**
  **CORRECTED 2026-10-09 (QA bot) — the low η was not BEMT: `polar.nondim` divided by an extra 2π (η = J·CT/CP, not J·CT/(2π·CP)), so every forward-flight η was 6.3× low; with the fix the preset reads 0.25/0.35/0.44 at J 0.16/0.24/0.31 vs APC 0.26/0.34–0.39/0.42–0.46. `nondim` was audit-exempt; now unit `propeller.polar_coefficients`.**
  **DONE 2026-10-14 — Analyze headline is `@ 30,000 rpm (max), static` (`prop_static_headline`). CT0 rpm-creep stays open as QA-12 (low-Re polar blend already FAIL'd its prereg; do not re-try that patch).**
- [x] **23.19 (UI-6)** Export STL takes ~2 min and saves only server-side
  (`exports/design_100000_*.stl/.step`), with no browser download; "design_100000" is a confusing name
  for the reference (use the F-name from `fansim/cockpit/design_names.py`). **[impact: low]**
  **[effort: low–med]**
  **PARTLY DONE 2026-10-08 — files named by design (`a12x25_stock_reference_…`, `F12_…`), and a "⬇ Download STL" link served from `exports/` (`/fansim_exports/`; verified 200, 5 MB). Export now runs in an isolated worker (`fansim.cockpit._export_worker`): caption keeps ticking, a native crash can't take the cockpit down; output byte-identical. Export Stock ~4.5 min → ~1.2 min (+STEP): the motor cup is carved into the bare hub before the blade fuse (identical solid: volume 0.0004 %, bounds 0.0001 mm); falls back to the old order if a blade reaches the cavity.**
  **DONE 2026-10-14 — UI-6 verified in browser (download link, design names). Remaining ~1 min Export is the fuse, not a missing download.**
- [x] **23.20 (UI-7)** After Randomize, the previous "Saved …design_100000…stl" message stays on
  screen. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — export message clears on any edit (incl. Randomize) and on loading a design; kept while an export runs.**
- [x] **23.21 (UI-8)** Slider tooltip and side label disagree (Chord root 18.0 vs 17.75 mm; 25.0 vs
  25.12 — step rounding); tooltips overlap the "Blades" label. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — thumb label shows only while dragging (it rounded to the step and overlapped neighbours); the side label shows the exact value.**
- [x] **23.22 (UI-9)** First-load 3-D view poorly framed under dense schematic arrows; the U colour bar
  reads 3.00/3.00/3.00 (zero range). The first render was an extreme close-up — reset the camera after
  Preview. **[impact: low]** **[effort: low]**
  **PARTLY DONE 2026-10-08 — colour bar only shown when arrow speeds differ (schematic no-CFD arrows are one speed → solid colour, no 3.00/3.00 bar). First-load framing looked fine at 800 px wide in the browser check; re-check at the reviewer's 1024×594 before closing.**
  **DONE 2026-10-08 (framing) — at 1024×594 the long legend paragraph pushed the 3-D view below the fold; it is now a collapsed "Legend" panel. Checked at 1024×594 in the browser. Side note: after many reconnects the test server stopped accepting new websocket sessions (HTTP still 200) until restarted — matches the reviewer's KeyError/ClientConnectionReset notes; not investigated further.**
- [x] **23.23 (UI-10)** Volute Preview shows only an opaque casing box hiding the impeller; "RPM" and
  "Load Pa@50CFM" labels are clipped by the Outlet panel. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — preview splits the two bodies: casing translucent (largest body), impeller solid inside; RPM/Load fields get room so their labels aren't clipped. Checked in the browser.**
- [x] **23.24 (UI-11)** Mixed/Prop/Volute sliders show no numeric values; the viewer shows a blurry
  leftover render before the first Preview. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — Mixed/Prop/Volute/CROR sliders use the shared slider (label + exact value). The blurry leftover render before first Preview is not addressed.**
- [x] **23.25 (UI-12)** Mixed-flow Preview renders a flat, unshaded silhouette. **[impact: low]**
  **[effort: low]**
  **DONE 2026-10-08 — cause: `plotter.clear()` also calls `remove_all_lights()`, so after the first preview Mixed (and Volute) rendered unlit. Now `clear_actors()`. Checked in the browser.**
- [x] **23.26 (UI-13)** Prop Stop and CROR CFD refine look enabled (solid red/orange) while disabled.
  **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — tonal variant, like the Fan tab's Cancel buttons; verified disabled+tonal in the browser.**
- [x] **23.27 (UI-14)** Tab hover tooltip covers neighbouring tab names after clicking.
  **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — tab tooltips open below the tabs after 400 ms.**
- [x] **23.28 (UI-15)** Console 405 on `POST /paraview/` at load (trame-vtk probe). Likely benign;
  silence or document. **[impact: low]** **[effort: low]**
  **INVESTIGATED 2026-10-08, left as is — one POST at ~4 s after a normal load from the trame-vtk client probing for a session launcher (bursts only on reconnect after a server restart). Harmless; suppressing it means patching third-party JS. Documented in the README.**
- [x] **23.29 Shared trame state across browser clients** — a new browser opened on the CROR tab
  another client had left. Probably by design; decide and document (matters for a public release).
  **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — by design (trame state is server-side); README now says one browser tab per cockpit, or a second cockpit on another --port.**

### 23.H Suspicious, unconfirmed — verify before fixing

- [x] **23.30 Stock YAML blades hang ~0.94 mm below the hub** (bbox z_min −9.10 vs hub bottom
  −8.16); the print-ready path after Fit is fine. **[effort: low]**
  **VERIFIED 2026-10-08, not a defect — the 0.94 mm is at mid-span (r 26.7–40.7 mm; hub r 21.5) from blade rake, not at the root; same in the YAML and cockpit builds now. Printing hub-face-down needs support under that edge.**
- [x] **23.31 `_root_axial_span` uses `params.stations[0]` without sorting** (`blade.py:626`), while
  `_interp_stations` / `tip_section_points` sort — unsorted YAML/`blade_angles` stations would size
  the hub from the wrong station. **[effort: low]**
  **DONE 2026-10-08 — root = innermost station by r_frac; test with shuffled stations.**
- [x] **23.32 `_trim_blade_to_tip_cylinder` can return an untrimmed blade** when all 4 intersect
  retries come back empty (`blade.py:1080–1084`), contrary to its comment. Not seen in 23 builds.
  **[effort: low]**
  **DONE 2026-10-08 — raises RuntimeError ("tip trim failed") instead of returning the untrimmed blade.**
  **REOPENED 2026-10-08 — raising broke `test_random_prop_flat_designs_never_raise_in_the_builder_path` (audited prop builder guarantee). Now warns and keeps the blade (old behaviour + a log line). Needs a real fix: a trim that works for those prop flats.**
  **DONE 2026-10-09 — those prop lofts (~3400 faces) defeat the plain intersect. Fallbacks: outer-ring cut, 0.1 µm fuzzy common, ShapeFix + common, each on a copy (a fuzzy boolean raises its inputs' tolerances in place). Every result must end within 0.1 mm of R — OCCT can return the whole blade as "trimmed" — else RuntimeError. 8/8 random props trim; fan geometry unchanged; ledger refreshed (`2026-10-09-ledger-refresh.md`).**
- [x] **23.33 `build_impeller_preview` doesn't check `len(blade_angles_deg) == n_blades`**
  (`blade.py:841–844`); `build_impeller` does. **[effort: low]**
  **DONE 2026-10-08 — covered by `validate_blade_params` (23.3).**
- [x] **23.34 `chord_realisation._station_measure_fracs` hard-codes `f < 0.47` as "inside the hub"**
  — that's the A12x25 hub ratio; wrong for hub ratios ≳ 0.47. **[effort: low]**
  **DONE 2026-10-08 — cutoff = (hub_radius + 4.1 mm) / tip (A12x25 → 0.4697, unchanged).**
- [ ] **23.35 Prop pitch twist evaluated at hub_r / 0.5(hub+R) but lofted at 4.5 / 34.0 mm**
  (root_embed; `propeller/geometry.py:64–67`). Small, mostly at the root. **[effort: low]**
  **INVESTIGATED 2026-10-08, deeper than reported — prop twist is computed at hub-mapped radii (6.0 / 34.75 mm) but the loft maps stations from hub − root_embed (4.5 / 34.0 mm): ~0.5° pitch at mid on a 5×4.3. The same split exists for every archetype: BEMT (`propeller.bemt._interp_geom`) and the docstring treat `hub_radius` as the canonical r_frac origin, all builders use `hub_radius − root_embed`. Fixing only the prop twist would move the error into the analysis. Proper fix = one shared station→radius mapping for builders and analyses; it shifts validated Stock by ~1 mm at mid-span, so it needs an A/B + re-audit. Deferred (props after fans).**
  **ATTEMPTED 2026-10-09 — FAILED pre-registered checks, not merged (`docs/validation/audits/2026-10-09-station-mapping.md`, branch `station-mapping-23-35`). Analyses moved to the builders' mapping + the builders' pchip interpolation: Audit #4 ρ 0.714 → 0.429, Audit #3 APC C_T RMS 0.0203 > 0.020. Post-verdict split: mapping alone keeps ρ 0.714; the pchip read drops it (Stock v1 BEM 61.9 → 58.4 vs CFD 77.4). Next attempt needs its own pre-registration and goes with the §23.5 BEM rework.**
- [x] **23.36 Mixed-flow blades lofted along a straight eye→tip diagonal on a conical hub** — only the
  root section attaches; the motor-cup-to-cone wall is ~1.66 mm at z = +2 mm (printability).
  **[effort: med]**
  **DONE 2026-10-08 — (1) "only the root attaches": not a defect; the build fuses hub + blades and raises unless the result is one solid. (2) cup wall: the carve check used r_back (28 mm) but the cone is narrowest at the cup ceiling (model bottom + 13 mm = +2.26 mm, cone r 20.49 mm → ~1.5 mm wall, ≥ the 1.2 mm minimum, so the default design is fine). The check now uses the cone radius at the ceiling (`cup_wall_hub_radius_mm`), so a narrower eye fails instead of printing a paper-thin wall.**
- [x] **23.37 Wind scaffold:** `tip_speed_ratio` is unused by the geometry; Cp saturates at ≥ 4 blades
  (5 and 10 give 0.4267). Labelled as a scaffold — keep it out of any release claims. **[effort: med]**
  **DONE 2026-10-08 (doc) — README now lists the wind turbine as an unvalidated scaffold with both limits; no design claims.**

### 23.I Related open threads from 2026-10-07/08 (Assess speed + screening audit)

- [x] **23.38 Quick screen with a load point.** Free-air-only quick tiers FAILED the pre-registered
  rank audit (ρ_load 0.55/0.60; `docs/validation/audits/2026-10-07-screen-rank-audit.md`). Next
  candidate: coarse mesh, free + load, 300 iterations each (~6 min) — needs its own pre-registered
  test. Redo the audit's "stock" row after 23.1. **[impact: high for exploration speed]**
  **[effort: med]**
  **DONE 2026-10-09 — Q3 (8 mm, level 3, free + 8 Pa, 300 iters, ~4 min) PASSED its pre-registered audit on 11 designs: ρ_load 0.936, ρ_free 0.964, full top-3 all in Q3 top-5 (`2026-10-08-overnight-checks.md` §B). Usable to pick which ideas get a full Assess; numbers are rank-only (raw, run high).**
- [x] **23.39 Wall-adaptive mesh gives thick blades ~0.35M cells vs thin ~1M** (surface level-3 floor
  vs level 4) — a resolution difference inside Assess rankings. Measure whether it biases
  comparisons. **[impact: med]** **[effort: med]**
  **MEASURED 2026-10-09 — FAIL: level 3 scores the three thick designs 3.3–7.1 % high vs level 4 (order among them unchanged). Walls > ~2.25 mm get level 3; Stock and all thin designs get 4. Pending decision: raise the Assess floor to 4 (≈3× cells, thick designs only) or compare like with like.**
  **DONE 2026-10-09 (user decision) — axial Assess/optimizer floor raised to level 4 (`ASSESS_SURF_MAX_FLOOR`): thick designs ~7.5 → ~20.5 min, same as thin. New scores stamp `surf_max`; older thick-wall scores show "⧗ needs re-run (coarse mesh)" (exactly t9006/9008/9015 today, which already have level-4 results from the check). Mixed/CROR keep floor 3 (untested at 4; Audit #7 setup); the quick screen keeps its own level 3.**
- [x] **23.40 Flutter gate is order-of-magnitude (§19.18) but a hard reject** — it rejected t9001/9002/
  9003/9005 and a thin Stock variant (t9002 at 0.91× the limit). Consider a warning band near the
  limit. **[impact: med]** **[effort: low]**
  **DONE 2026-10-08 (user decision) — warning, not a reject, until print/measure data exists. `evaluate_candidate` stamps `raw.vibration_warning` and prefixes the result reason; Optimize and Assess now score these designs. Revisit with print data.**
- [x] **23.41 Hide duplicate designs** — t9009/9010/9011 score identically to t9008 after the v5
  refresh. **[impact: low]** **[effort: low]**
  **DONE 2026-10-08 — Results lists byte-identical geometry once (oldest kept), `collapse_identical_designs`; nothing deleted on disk.**
- [x] **23.42 Commit the 2026-10-07/08 work** (watchdog, live logs, parallel mesh, F-names, refresh,
  stale-viz fix, intake note, optimizer hose stamp) — still uncommitted at review time.
  **[effort: low]**
  **DONE 2026-10-08 — commits 0a8cc7f…c6addb5.**


### 23.H QA re-test 2026-10-09 (new items; `docs/QA_REVIEW.md`)

- [x] **23.43 (UI-16, HIGH) One stalled client freezes every websocket session.** wslink sends to all
  clients under one global lock with no timeout; a tab that stops reading blocks it forever (aiohttp's
  missed-PONG `transport.close()` waits on the same full buffer).
  **DONE 2026-10-09 — `fansim/cockpit/ws_guard.py`: per-socket locks + per-client send timeout
  (`FANSIM_WS_SEND_TIMEOUT`, 15 s) that ABORTS the stalled transport. `scripts/ws_stall_probe.py`
  (frozen client + busy broadcaster + hello probes): before 0/5 probes answered in 75 s; after 15/15
  in 3–12 ms, frozen client dropped after 15 s, browser tab unaffected.**
  **2026-10-14 (23.57):** a long VTK `_draw` / `view_update` on the asyncio loop starved
  `wait_for`, which then aborted the **only** tab (~15 s after first Stock preview or a heavy
  bake). That is loop starvation, not a client that stopped reading. The guard now retries
  when the loop tick went stale and no bytes were written; a real stall still drops the tab
  and the log says to hard-refresh.
- [x] **23.58 Results click paints twice then freezes.** Selecting a scored design (e.g. F90) drew
  the impeller, then rebuilt the whole VTK scene when CFD arrows landed — `pv.read` of the STL
  every time, leftover arrows from the previous design, and `view_update` on the event loop
  (camera dead until the second JPEG landed). The STL is reused; leftover arrows are cleared.
  **[impact: med]** **[effort: low]**
- [x] **23.59 Results 3-D: impeller first, overlay from cache.** Click shows the saved impeller
  immediately (rotatable) plus a loading bar; arrows/cues attach on the next tick from the
  `cockpit_viz` cache (or after a background `read_case` if that design was never baked). This is
  not a new CFD run — Assess is the only thing that re-solves. Direction-cue meshes are reused.
  **[impact: med]** **[effort: low]**
- [x] **23.44 (UI-17) `GET /ws` without upgrade → `KeyError` in `onClose`, leaks a `connections` entry.**
  **DONE 2026-10-09 — `ws_guard` makes `onClose` tolerate a never-prepared connection; 5 plain GETs, no KeyError.**
- [x] **23.45 (UI-18) Image-push observers never removed on disconnect** (views keep rendering for gone
  clients). **[effort: med]**
  **DONE 2026-10-09 — `ws_guard` records each client's `viewport.image.push.observer.add/remove` and, on close, calls the protocol's own `observer.remove` for what it still held (unit-tested through the real `onClose`; live observerCount check left to QA on Linux).**
- [x] **23.46 (UI-19) Exports folder relative to the launch directory.**
  **DONE 2026-10-09 — `fansim/cockpit/paths.exports_dir()` (= `<project>/exports`) used by every tab and the download route.**
- [x] **23.47 (UI-20) After Randomize the Design dropdown still says "◆ Reference".** **[effort: low]**
  **DONE 2026-10-09 — while the editor differs from the loaded design the dropdown label reads "✎ Edited copy of this design (not saved)" in warning colour; Reset restores it. Verified in the browser.**
- [x] **23.48 (UI-21) Mixed "CFD refine" looks enabled with top N = 0.** **[effort: low]**
  **DONE 2026-10-09 — tonal variant (as §23.26), also on Prop's CFD refine; an AST scan found no other solid coloured button with a `disabled` binding. Verified disabled+tonal in the browser.**
- [x] **23.49 (QA-11) `blade_solidity(n_blades=0)` raises ZeroDivisionError on a direct call.** **[effort: low]**
  **DONE 2026-10-09 — computed as B·c·cosβ/(2πr): 0 for a bladeless rotor, same value otherwise; non-positive radius raises a clear ValueError.**
- [x] **23.50 (UI-8 reopened) Slider tooltip vs side label disagree** (Chord root 18.0 vs 17.75 mm). **[effort: low]**
  **DONE 2026-10-09 — Vuetify's thumb text is the value snapped to the step; the thumb-label slot now shows the model value itself. Browser: Stock Chord root thumb 17.75 = side label 17.75.**
- [x] **23.51 (UI-9 partial) First-load fan small (~1/4 of the viewer).** `reset_camera()` fitted every actor,
  including the schematic flow-arrow cloud that reaches far past the tip.
  **DONE 2026-10-09 — fit to the fan (+ the 1.3·tip rotation-cue ring) and zoom 1.5× (the bounding-sphere fit
  is generous for the oblique view); browser: fan fills the viewer, cues visible. The missing |U| bar on the
  Stock first load is by design (schematic arrows have one speed, §23.22).**
- [x] **23.52 (UI-13 re-test) Prop Stop still faint pink while disabled.**
  **DONE 2026-10-09 — colour is bound to `prop_opt_running` (red only when there is something to stop); browser: disabled, neutral.**

- [x] **23.53 QA browser re-test (2026-10-09) reopened UI-4, UI-9, UI-20.**
  **DONE 2026-10-09 —**
  **UI-4: the bar swept until the worker's first stage, which landed only after the CAD kernel loaded (~30 s on the QA box), so the sweep read "65 %" then "50 %". The bar is now determinate from the first frame ("starting build process"), the worker reports stage 1/5 before its heavy imports, and the value never decreases. QA's 66 s Preview was the motor-cup path: `preview_motor_cup` defaulted ON behind a switch in the Fan tab's Export options panel — now OFF (Preview ~15 s here; Export always carves the cup).**
  **UI-9: the viewer card was a fixed 400 px; on a wide/zoomed-out window the canvas was ~2.8:1 and the fan (height-limited) filled ~1/3 of the width. All five tabs now use `VTK_VIEW_STYLE` (3:2, ≥ 400 px, ≤ 75vh): 1131×754 at a 1970-px window.**
  **UI-20: the dropdown's shown value (not just its label) reads "✎ Edited copy of ◆ Reference …" while edited.**
  **Browser-verified (Windows) at 1024×594 and 1970×1140.**
- [x] **23.54 (UI-4, QA r3) Preview stages still not visible.** Stage 1 landed only after the worker's
  `python -m` package import had loaded CadQuery (~2.2 s); stages 2/3/5 lasted milliseconds.
  **DONE 2026-10-09 — the parent writes stage 1 "loading CAD kernel" before spawning; stages are now the
  four that take time (kernel / preparing design (chord fit) / build / write); ticker 0.5 s. Measured:
  stage 1 at 0.05 s, build stage 3.0–5.6 s, total 5.6 s (fast path).**
- [x] **23.55 Motor-cup fuse peaks ~7.6 GB** (QA r3, Linux): the Preview-with-cup worker and
  `test_mount_gauge::test_gauge_accepts_carved_stock_export` (8.2 GB, the suite's peak) both run the
  in-process OCCT fuse of the carved hub + 9 blades. On a 16 GB box with a browser open that is the likely
  cause of the 7–10 s stall QA saw at the end of a cup Preview. Measure where the fuse allocates; options:
  fuse blades pairwise, tessellate per part, or run that test in an isolated worker. **[impact: med]**
  **[effort: med]**
  **DONE 2026-10-14 — cannot beat ~4.9 GB in-process (QA-15 S3 serial, still over 4 GB). Cockpit
  Preview/Export already fuse in a worker. The suite peak was this test: it now calls
  `fansim.manufacturability._print_ready_worker` (QA-15 S5). Worker still ~7.6 GB; pytest parent
  does not keep it. Memory tiers + 27.1 remaining-growth stay for live builds.**
- [x] **23.56 Preview overlap freeze.** Randomize → Fit → Preview (still running) → Randomize →
  Preview again froze the 3-D view with no browser console error. `preview_busy` was set *inside*
  the async task after `create_task`, so two clicks both passed the guard, two isolated workers
  wrote the same `preview_stl`, and both called VTK `_draw` / `view_update` on the event loop.
  Busy is now set before schedule; Randomize / Fit / Scale / Reset / seed are disabled (and no-ops)
  while Preview/Assess/Export/Optimize run. Restart the cockpit if a session is already wedged.
  **[impact: med]** **[effort: low]**

## 24. Newcomer clarity — flow report, simple/expert, start page (2026-10-10)

Kimball's review of the Fan Results screen:
- the airflow pictures look wrong (blocky, a flat pressure picture, streamlines with no fan);
- the Mixed, Volute, Prop and CROR tabs don't say what they are for;
- there is too much text everywhere.

The decision is a **Simple / Expert switch, defaulting to Simple**:
- simple mode is written for a first-time hobbyist, and Kimball signs off on every word of it;
- expert mode keeps today's detail, marked "not reviewed for plain language" (no expert is available to
  verify it).

The work is split into three sub-projects, done in order.

- [x] **24.1 Flow report card "How the air moves"** (sub-project 1).
  - **DONE 2026-10-10** (branch `flow-report-card`).
  - **Checks:** F0, F1, F3 and F4 PASS. F2 first passed after widening to a non-repeat pair (±15 %,
    2.8 dB). **27.3 (2026-10-14):** five Stock v3 Assess repeats set 2σ at **±3 % / +0.5 dB**.
  - **Push redefined:** p + ½Uz², with swirl excluded. All of this is recorded in
    `docs/validation/audits/2026-10-10-flow-report-checks.md`.
  - **Browser-checked:** t9005 reads all ✓ against Stock and 9610 reads 3 ⚠; the stale-design message;
    the Simple/Expert switch, remembered per browser; quick switching; cached re-open in 1–1.5 s.
  - **Also fixed on the way:** airflow pictures now come from the run behind a refreshed design's score
    (`extra.case_dir`). Before this, 11 refreshed designs showed an older run, e.g. t9005's level-2
    2026-09-15 case.
  - **Follow-ups:**
    - 9604 reads +24.9 dB noise and weak push despite higher load CFM; check its convergence and
      k field.
    - The minors deferred from the final review: some simple-mode messages are still technical;
      design-only mode shows "–" rows; the legend lacks a "clipped at Stock's range" note; the push
      row shows a redundant Stock picture; band labels flip if Stock's band is ever negative.
  - Spec: `docs/superpowers/specs/2026-10-10-flow-report-card-design.md`.
  - Plan: `docs/superpowers/plans/2026-10-10-flow-report-card.md` (9 tasks).
  - It replaces "Duct airflow" on Fan → Results. One row per question, each with a ✓/⚠/✕ verdict
    against Stock and a picture beside Stock's:
    - air direction (backflow share);
    - push along the blade (5 bands);
    - wasted spin;
    - dead or blocked air (including tip leakage);
    - a noise hint (Proudman, relative only).
  - The shared picture fixes also reach the other tabs: smooth shading, pressure in Pa, a
    percentile colour range, the rotor outline, and streamlines rebuilt as a side view with a
    see-through fan.
  - The global Simple/Expert switch is introduced here.
  - **The verdict thresholds are fixed in advance and checked on real runs before the UI work**
    (`docs/validation/audits/2026-10-10-flow-report-checks.md`):
    - Stock against itself: all ✓;
    - Stock's run-to-run pair: "similar" on every row;
    - 9610 (stalls under load): ≥ 1 ⚠;
    - t9005: no ✕.
  - No new CFD, no score change. **[impact: high]** **[effort: high]**
- [x] **24.2 Text clean-up across the app (sub-project 2; needs its own design pass).**
  - **DONE 2026-10-15 (Kimball signed off Simple copy).** Fan → Results glossary / Gold ✕ / fits-only /
    scatter how-to, plus the Geometry dump paragraphs, sit behind `ui_mode === 'expert'`. Simple shows
    the intro banner + Start here (steps only; durations stay on the banner and buttons). Expert shows
    Optimize and Mixed/Volute/CROR tabs. Assess dump blurbs Expert-only. Results no longer repeats the
    Reference dropdown. Empty scatter hides the flow card. Tests: `tests/test_simple_mode_copy.py`.
  - Leftover: **QA-38** (LOW) Simple Results scatter body below the fold at 1366×768.
  - Reuses the 24.1 switch. **[impact: high]** **[effort: high]**
- [x] **24.3 Start page and plain tab descriptions (sub-project 3; after 24.2).**
  - A start page, or a "what is this tab for?" panel, saying in plain words what each tab does and how
    much to trust it. For example: Mixed, Volute and CROR are rough estimates rather than the full
    simulation, and Prop is a fast estimate.
  - **DONE 2026-10-15:** Mixed / Volute / CROR stay Expert-only. Tab labels: Mixed/Volute/CROR ·
    estimate, Prop · fast estimate (no “proxy” / “BEMT”). Simple strip under the tabs:
    “Fan: printable PC-fan blades (CFD). Prop: propeller (fast estimate).” Prop Simple banner
    matches that; Expert Prop banner keeps the BEMT/Audit detail.
  - Rename "proxy" and "BEMT" in the tab labels. **[impact: high]** **[effort: med]**
- [ ] **24.4 Changing settings while something is running — investigate (owner: QA bot, round 7, after
  its round-6 stress test).**
  - **Question:** while Assess, Optimize, Preview, Export or a flow picture is running, does changing a
    setting (a slider, hose, material, fan model, mesh options, or selecting another design) do any of
    the following?
    - (a) change the run that is already going;
    - (b) get ignored, but then get recorded *with* that run's results;
    - (c) attach the run's results to the wrong design;
    - (d) do nothing harmful.
  - **Method:**
    - Read the code for when each job snapshots its inputs: Assess / `objectives` params, `assess_*`
      state, the export flat dict, and the save path of `selected_trial`.
    - List every setting each job reads after it has started.
    - Then reproduce the risky cases in the browser with a short run (Preview / Export, and a pilot
      Assess if the bot can run CFD; otherwise read the code only).
  - **Output:** a table of job × setting → a, b, c or d, with evidence.
  - **Recommendation per job**, one of:
    - lock the controls while it runs;
    - snapshot at start and show "this run uses the settings from when you pressed Assess";
    - a queue.
  - Pre-register what counts as a defect: any (b) or (c) case.
  - **No fix until Kimball picks one.** **[impact: high: wrong saved results]** **[effort: med]**

## 25. QA round 6 findings (2026-10-10)

Sources:
- `handoff/2026-10-09_from-qa-5/` (the stress test was partial: n = 120 of 801 designs, stopped early);
- `docs/qa/notes/direction-attempt-2.md`, `docs/qa/notes/motor-efficiency.md`, `docs/qa/benchmarks/`.

The builder held up well: in 120 designs there were 0 printability, below-hub, tip-radius or determinism
failures.

- [x] **25.1 (QA-18) The motor cup goes straight through hubs shorter than 13 mm.**
  - The cup Preview path (`build_stl_isolated(motor_mount=…)` → `build_impeller_with_mount`) never
    applies `MotorMount.min_hub_height_mm` (15 mm). Only Export's `prepare_export_flat(fit_hub=True)`
    grows the hub.
  - Seen in 3 of 29 cup builds (auto hubs 10.9–12.7 mm).
  - **Verified in code 2026-10-10:** `min_hub_height_mm` is read only in `cockpit/placement.py` and
    the gauge.
  - **Fix:** grow the hub to the minimum (or refuse with a message) inside `build_impeller_with_mount`,
    so every cup path is covered.
  - Repro: `handoff/2026-10-09_from-qa-5/stress/repro/A-F2_cup_through_short_hub.json`.
  - **DONE 2026-10-10: `mount_hub_params` grows the hub inside `build_impeller_with_mount`; tests reproduce
    the repro (10.9 mm hub) and check the cup floor.** **[impact: high: unprintable mount]** **[effort: low]**
- [x] **25.2 (QA-21) Tip trim raises on a featured, high-lean, wide-tip blade** from the optimizer's own
  `--extended --features` space (S5_0007).
  - The error: "blade crosses R=52.55 mm (reaches 56.09 mm) and no intersection ended at R".
  - **Reproduced on master 2026-10-10.**
  - Fix one of two ways: make the trim robust for featured surfaces that bulge more than 3 mm past R,
    or refuse cleanly in `validate_blade_params` with a reason. The optimizer then marks it infeasible
    instead of erroring.
  - Repro: `handoff/2026-10-09_from-qa-5/stress/repro/A-F1_tip_trim_build_fail.json`.
  - **DONE 2026-10-10: the tip section touches the cutter tangentially at exactly R. The trim now retries
    0.02 / 0.05 mm inside R, and the repro builds watertight within R
    (`docs/validation/audits/2026-10-10-ledger-refresh.md`).** **[impact: med]** **[effort: med]**
- [x] **25.3 (QA-19) Direction check attempt 2: option (a).** **DONE 2026-10-10: P1–P5 PASS
  (`docs/validation/audits/2026-10-10-direction-crosscheck-2.md`). External STLs and the INCONCLUSIVE
  cambered stress designs moved to 25.3b. CFD of 9605/9606/9620/9630 ran 2026-10-11: screen-r3
  A SUPPORTED (4/5); B fell to INCONCLUSIVE (ρ 0.412): the axial BEM over-rates flat leaned blades.**
  - **The rule:**
    - refuse on chirality (mirror), as today;
    - otherwise refuse only when the proof is CONCLUSIVE, |design camber| ≥ 0.02, **and** the split
      disagrees with the design camber's sign.
  - **The QA review found:**
    - it removes 7 of 7 false refusals;
    - it adds 0 new refusals;
    - it still catches 95 of 95 mirrors.
    - (Partial data. Chirality was derived, not logged.)
  - **Steps:**
    1. Pre-register the QA's P1–P5 criteria, including the new P3a (a mesh-vs-design mismatch is
       caught) and P3b (`validate_blade_params` refuses a station camber ≤ −0.02).
    2. Implement.
    3. **External STLs:** refuse when the median measured camber ratio is < 0.045 and ask for an explicit
       orientation. Today a lean artifact there silently sets the *wrong spin*.
    4. Mixed flow: pass `max_camber`.
    5. `check_rotor_direction` has no callers: delete it, or wire it into CROR.
    6. Then run 9605, 9606, 9620 and 9630 through CFD (Q3, plus a full Assess if any beats Stock).
    7. Separately: 8 of the 24 INCONCLUSIVE are properly cambered blades whose sections disagree. That is
       a second proof weakness.
  - **[impact: high]** **[effort: med]**
- [ ] **25.3b External-STL direction: the lean artifact can set the wrong spin.**
  - With `source="external"` the measured split *decides* the spin, so a flat, leaned external blade
    could be run backwards without any warning.
  - The QA proposal (refuse when median measured camber < 0.045) would also refuse the real A12x25
    reference STL (0.0375).
  - Needs its own criteria. Options:
    - cut normal to the stacking line (option b);
    - require an explicit orientation whenever the split is in the overlap zone, and pass the known
      orientation for the reference STL.
  - Also: 8 INCONCLUSIVE stress designs with camber ≥ 0.02 have sections that disagree.
  - **QA round 7 (Task F, 2026-10-11): option (b), the stacking-line cut, is rejected.** It failed its
    pre-registered F1/F2/F3/F6 (9630 read wrong, only 68.5 % of cambered parts read).
    - **Lead:** a *radial-plane* cut (planes through the axis, one per radius) made 0 wrong calls on 67
      parts plus their mirrors, read all 54 cambered parts and rescued 3 of the 7 flat leaned ones.
    - It was chosen after seeing the data, so a pre-registered confirmation comes first (round 8, see 27.2).
  - **[impact: med]** **[effort: med]**
- [x] **25.4 (QA-20) The memory tiers give equal solids but not byte-identical STLs.**
  - Volume and vertex count match 11 of 11 times, but the sha256 differs every time.
  - Fix the `fansim/resources.py` docstring and the `TIERS` comment ("same solid", not
    "byte-identical").
  - **[impact: low]** **[effort: trivial]**
- [x] **25.5 Featured designs blow the 8gb tier's memory budget.** **DONE 2026-10-11: the peak follows the
  face count, not the strategy: 0.37 GB + 86 kB/face; featured 6.5 GB on every tier. The fuse now checks
  free RAM against that estimate and refuses in plain words instead of swapping
  (`docs/validation/audits/2026-10-11-fuse-memory.md`).**
  - S5 featured P builds at the forced 8gb tier peaked at 7.6 GB, above its 6.5 GB `min_free_gb`.
  - Measure the peak RAM of featured builds per tier, then either raise the tier floors for featured
    designs or run them serially.
  - **[impact: med: freezes on 8 GB machines]** **[effort: med]**
- [x] **25.6 Motor-efficiency assumption.** **DONE 2026-10-10 (Kimball: use the researched value): 0.50,
  input stays 1.68 W rated. Stock is no longer slowed (the real fan holds 2000 rpm). 21 saved scores
  re-derated without CFD, t9005 70.1/51.8/32.0, Stock 51.9/42.7/18.3. Audit
  `docs/validation/audits/2026-10-10-motor-efficiency.md` (M1 PASS, M2 (a) FAIL on 3 old unaffected
  files / (b) PASS, M3 reported).**
  - The QA research proposes η_motor 0.50 (range 0.40–0.65). It also notes that 1.68 W (0.14 A) is a
    start-up maximum; the measured draw at 2000 rpm is 1.3–1.5 W (Cybenetics).
  - At 0.50 × 1.68 W, the 5–7 % derate on Stock and the audited designs disappears. At 0.50 × 1.50 W
    it is about 1–3 %.
  - This changes saved scores, so the options are:
    - (a) adopt 0.50, re-score everything, and report the 0.40/0.65 sensitivity (flag any ranking
      flips);
    - (b) keep 0.40 and document it.
  - Either way, make the input power a named constant with its citations. Note: the derate uses the
    *leeway* budget (over-voltage), so check which voltage the comparison should use.
  - **[impact: med]** **[effort: low code / med re-score]**
- [ ] **25.7 Second real-world CFD validation case: `lt120`** (Lin & Tsai 2011 fan via Tutar & Cam 2025,
  CC BY 4.0).
  - 7 blades, 120 mm rotor, 2000 rpm, a full 10-station table, 5 measured static points.
  - Both BEM models are 5–35 % off mid-curve on the three full-geometry fans. FAN-01 (a large
    research fan, `validation/reference/fan01/`) is already a CFD check; lt120 would be the first at
    **PC-fan size** besides Stock.
  - **Prerequisites:**
    - the QA bot converts lt120 to `BladeParams` and reports anything our builder can't represent
      (round 7);
    - the rig is unknown, so pre-register the comparison as mid-curve shape and level within a stated
      band.
  - The rotor (Ø120) exceeds the a12x25 frame, so use a matching rig or duct.
  - **QA round 7 (Task C): converted** (`docs/qa/benchmarks/lt120/fansim_params.json`,
    `docs/qa/notes/lt120-conversion.md`). Stagger matches (≤ 0.75°), but cylinder cuts of the built blade
    read the chord up to 16 % short and the camber 0.030 instead of 0.040. That raises a builder question
    for every design, not just lt120 (see 27.4). Decide 27.4 before pre-registering this CFD.
  - **[impact: high]** **[effort: med–high, CFD]**
- [x] **25.8 Benchmark licences before any public release.** **DONE 2026-10-11: `RELEASE_EXCLUDE` +
  `scripts/export_release.py` (no history) keep nv150, the drone props (unknown origin) and `handoff/` out of
  a public release; the tests that need a drone prop skip without it.**
  - `nv150` data is CC BY-NC-ND (not MIT-compatible): remove it or keep it out of the release.
  - **DONE 2026-10-10:** the NF-A12x25 reference STL is "A12x25" by MajorHardware (Thingiverse
    5893432, CC BY 4.0). It is credited in `THIRD_PARTY.md` and `validation/reference/README.md`.
  - **`validation/reference/drone_radial/` (24 files, 56 MB): source unknown** (Kimball, 2026-10-10), so it
    can't ship.
    - It is used by `tests/audit/test_direction_geometry.py`, `tests/test_prop_cfd_fixture.py`,
      `tests/test_prop_ami_smoke.py`, `tests/test_prop_gci_ladder.py` and the prop CFD scripts.
    - Before release, replace it with a known-licence prop (a CC BY Thingiverse prop or a
      UIUC-geometry build), or make those tests skip when it is absent and keep the folder out of the
      public repo.
  - Cybenetics data is cited only, never stored.
  - **[impact: high for release]** **[effort: low]**
- [x] **25.9 Finish the stress test** (681 designs left) **with chirality and INCONCLUSIVE reasons logged**.
  QA round 7, run at lower parallelism. The QA box froze for 6.1 of 7.1 h under memory pressure.
  **CLOSED 2026-10-11, stopped at 65 of 801 by Kimball's decision** (ETA ~249 h on a box that keeps
  suspending). The 65 designs on new code re-verified QA-18/21 fixed and QA-19 mostly fixed, and found
  QA-27 (27.1) and the QA-19 residual (27.2). Results: `docs/qa/stress/RESULTS_R7.md`.
- [x] **25.11 (QA-22..26) Runs save labels from the cockpit as it is when they *finish*.** **DONE
  2026-10-11: `fansim/cockpit/run_settings.py` freezes the settings at the click for Assess / Sweep; Mixed
  Assess / optimize / refine capture hose + refine at the click. The smoke test changes the cockpit mid-run
  (old code saved radiator/PLA/Delta; now heatsink/PETG/a12x25).**
  - Assess, Sweep and Mixed Assess build and solve the right geometry. But at the end, 30–40 min later,
    they write several labels from the live state:
    - material, hose and load;
    - fan model;
    - library parent.
  - Clicking another design mid-run files the result with that design's settings.
  - **Decision (Kimball, 2026-10-11): record every setting when Assess / Sweep / Mixed Assess is
    pressed, and save exactly those with the result.**
  - Source: the QA round-7 Task A note. **[impact: high: wrong saved labels]** **[effort: med]**
- [x] **25.10 Near-stall flag** (Task E, carried over). **DONE 2026-10-14.** Cheap BEM warning
  at the case-hose operating point: N1 signed incidence ≥ polar-edge stall, N2 no hose
  intersect, N3 Lieblein DF > 0.60. Assess caption + `extra.near_stall`; **scores unchanged**.
  Hold-out MIXED: 9610 flags (DF 0.605); 9604 / 9608 / Stock / t9005 do not; 9613 also flags
  (incidence past stall) even though its CFD did not unconverge. Thresholds not retuned.
  `fansim/optimize/near_stall.py`, prereg `docs/qa/notes/near-stall-flag-prereg.md`.

---

## 26. External STL in the cockpit — score a mesh you didn't build (2026-10-11)

**Status:** parked idea (written so we don't lose it). **Not next work.** Evaluation below.

Three separate jobs got mixed together. Split them. CLI already CFD-scores an impeller STL
(`scripts/validate_stl.py` + `prepare_axial_cfd(..., source="external")`). Inverse-fit of Stock
to the close-ref mesh already exists as `scripts/fit_recipe_to_stl.py` + cylinder-slice
(`fansim/validation/section_compare.py`). The **gap is the Fan cockpit** (and a general
residual report, not an A12x25-only fitter).

### What this is for

Print-site “Noctua hub” impellers (Printables / MakerWorld / Thingiverse) are shapes the sliders
cannot always make. Scoring those meshes on the **same** hose / mesh / gates as a parametric
Assess would show whether our vocabulary is missing a real lever, or whether a popular print is
just a worse rotor on the same motor. Sliders go **read-only** for that row. That is fine.

### Honest evaluation (do / don't)

| Idea | Verdict | Why |
|------|---------|-----|
| Load one impeller STL → Preview + Assess (CFD, hose, envelope, mount gauge, catalog) | **Do — later** | High leverage; most of the physics already exists; UI is the work. Fair **relative** ranking vs Stock if mesh/settings match. |
| Auto-set sliders from an STL (no AI) | **Do as a report, not magic** | Cylinder-slice chord/stagger/t/c/camber, then residual. If residual is large, **say the builder cannot represent it**. Generalizing `fit_recipe_to_stl.py` is the code path. Full “looks identical” inverse design is ill-posed (organic hubs, lettering, splitters, fused frame). |
| Download hundreds of community fans to find missing sliders | **Don't scrape** | License mess (§25.8), whole-fan assemblies, bad axes, non-watertight meshes. A **hand-picked 5–10 CC-BY impeller-only** set is enough for a feature census. Feeds §25.7 (lt120 → `BladeParams`) the same way. |

**Do not** treat community CFD as datasheet truth. Same caveat as parametric Assess: relative
rankings under a fixed budget, not published CFM.

**Do not** start this before §23 release blockers. External-STL direction is already the risky
path (`source="external"` must be CONCLUSIVE — see orientation audits).

### Recommended order (when un-parked)

1. **26.1 Bring-your-STL Assess** in Fan Library / a dedicated “Imported mesh” row.
   File picker → prep (center, +Z, impeller-only check) → disable Design sliders → run the
   existing Assess pipeline on the mesh (skip BEM or stamp `geometry_source=external`).
   Catalog id like `import_<hash>`. Same hose / `surf_max` floor as parametric Assess.
   **[impact: high]** **[effort: med]**
2. **26.2 Prep + honesty UI.** Refuse fused frame+rotor assemblies; show orientation proof;
   require RPM + fan model (envelope/mount). **[impact: high]** **[effort: low–med]**
3. **26.3 Slice residual panel** (optional, after 26.1). Reuse `measure_sections`; list
   unrepresentable features instead of forcing sliders. **[impact: med]** **[effort: med]**
4. **26.4 Tiny licensed corpus** (5–10 impeller STLs, CC-BY, credited like the A12x25 ref).
   Census: which features the builder cannot make; only then add a slider. **[impact: med]**
   **[effort: low software / user collect]**
5. ~~Mass download / AI slider-tune~~ — **not adopted.** Tokens are the wrong tool; licenses
   and mesh hygiene are the real cost.

- [ ] **26.1 Cockpit: import impeller STL and Assess it** (parametric sliders read-only).
- [ ] **26.2 STL prep gates** (impeller-only, watertight, axis, orientation proof, RPM/model).
- [ ] **26.3 Cylinder-slice residual vs current `BladeParams` vocabulary** (no silent slider overwrite).
- [ ] **26.4 Hand-picked CC-BY Noctua-hub impeller set** — feature census, not a scraper.
- [x] **26.5 Mass-scrape Printables/MakerWorld/Thingiverse.** **Not adopted** (licenses + junk meshes).

---

## 27. QA round 7 findings (2026-10-12)

Sources: `handoff/2026-10-11_from-qa-7/`, `docs/qa/stress/RESULTS_R7.md`, `docs/qa/notes/` (settings-during-run,
lt120-conversion, flow-report-math-check, direction-stacking-cut). QA-22..26 (settings changed during a run) were
already fixed by 25.11 before this round's results arrived; round 8 re-runs the QA harness to confirm.

- [x] **27.1 (QA-27) The fuse-memory estimate is low on Linux.** The 65 r7 builds peak a median 29 % above
  `fuse_peak_estimate_gb` (max 80 %).
  - **My re-fit of their data (2026-10-12):** slope 85 kB/face, the same as ours (86). Only the intercept
    differs: **1.0 GB on Linux** vs 0.37 GB on Windows. Their peak is the summed RSS of the build tree on
    Linux; ours is one process's working set on Windows. So it's a baseline difference, not a wrong model.
  - **The guard may still be safe:** it asks for the *whole* peak × 1.15 in free RAM at the moment of the
    fuse, but by then the process already holds part of that peak (2.3 GB for S5_0011). Nobody has
    measured RSS at the fuse call, so this is unproven.
  - **Next:** log RSS at the fuse call on both platforms (round 8 Task C), then guard on
    *peak − RSS now*, with a per-platform intercept. **[impact: med: OOM on 6–8 GB Linux boxes]**
    **[effort: low]**
  - **QA round 8 (Task C):** in one process on Linux, the peak is 1.02 GB + 92.5 KiB/face. So the 1 GB
    intercept is the platform, not tree-summing. The growth after the guard's call is **0.28 GB +
    72 KiB/face**, and the process already holds 1.0–2.1 GB at the call.
    - The guard as shipped (whole estimate × 1.15 vs free RAM) covered the remaining growth on 20/22 builds.
      It failed on a shrouded design (S7_0013: 2.66 vs 2.41 GB). Shrouds run ~1 GB above the face fit.
    - **Fix:** guard on the *remaining growth*, k·(a + b·faces) plus a shroud term, refit on Windows with the
      same measurement (peak working set minus working set at the call).
  - **CLOSED 2026-10-13.** The guard now asks for remaining growth × 1.15 vs free RAM, plus a shroud
    term on blade faces (not the ring's four). Linux: 0.28 GB + 72 KiB/face + 66 KiB/blade-face (r8/r9).
    Windows: 0.10 GB + 103 KiB/face + 26 KiB/blade-face from PeakWorkingSet − WorkingSet at the call
    (`scripts/measure_fuse_growth.py`; see `docs/validation/audits/2026-10-13-fuse-remaining.md`).
    Cockpit cup Preview/Export only (`FANSIM_FUSE_GUARD=1`). Batch builds still go ahead.
  - **Leftover QA-35 (r12):** Linux remaining-growth still under-asks open 9/11-blade builds
    (S7_0172_twin 1.03× the ask, 3/3). Shrouded fine. Refit the open (non-shroud) intercept/slope;
    do not loosen the shroud term.
- [x] **27.2 (QA-19 residual) A mildly cambered, strongly leaned design is still refused as "backwards".**
  **CLOSED 2026-10-13 by the wrap (27.4), not by a second reader.** V4: on wrapped rebuilds the cylinder proof
  makes 0 wrong calls on 30 parts and reads S3_0014 correctly. Do **not** add the radial-plane reader to the
  builder rule: it cuts the *tangent plane*, which is where the old planar sections lived; on wrapped blades it
  is the mismatched cut. More INCONCLUSIVE (QA-33) is fine: INCONCLUSIVE never refuses.
  S3_0014 (camber 0.0242, lean 42°) is above the 0.02 trust cut-off, so the lean artefact refuses it. In the
  optimizer that design is scored **infeasible**. The cell camber 0.02–0.04 × lean ≥ 30° had 1 FAIL and
  3 INCONCLUSIVE of 8.
  - Candidate fix: require the radial-plane reading (25.3b lead) to agree before refusing. Wait for the
    round-8 pre-registered confirmation (Task B). **[impact: med]** **[effort: low once confirmed]**
  - **QA round 8 (Task B), confirmed on 72 fresh parts plus mirrors:** the radial-plane reader made 0 wrong
    calls (R1), read 54/54 cambered parts (R2), flipped every readable mirror (R3), and read both references
    (R4).
    - The builder rule "refuse on the split only when *both* readers are CONCLUSIVE and *both* disagree"
      refused 0 of the 23 S3-cell parts, so S3_0014 is fixed.
    - R6 failed only on things the rule can't do as I wrote it:
      - my brief's −0.03-camber "backwards" parts build *flat* (`airfoil.py` zeroes m ≤ 0), and a
        design-sign rule can't catch a design whose sign really is negative;
      - fully flat mirrors are unreadable by either reader.
    - The validator already refuses camber ≤ −0.02 before any build. **Ready to implement.**
- [ ] **27.2b External STLs (25.3b): radial-led rule.** Accept the radial reading when it is CONCLUSIVE and
  the cylinder agrees or can't tell; otherwise ask for the spin. Post hoc on round 8: 0 wrong, 53/54 read. The
  "both must agree" rule read only 79.6 % (R5 FAIL). It needs its own pre-registered confirmation on more real
  external STLs. **[impact: med]** **[effort: med]**
- [x] **27.3 Flow report card: NaN handling and the push-bar caveat** (Task G). **DONE 2026-10-14.**
  NaN + push landed 2026-10-12 (Kimball option b): the push row judges the area-weighted mean; missing
  values are `null` with a reason; zero-volume exits raise. Real cases: t9005 +12 % ("about as hard"),
  9604 −38 % (weaker), 9610 +7 %. Maths G1 16/16.
  - **Thresholds baked 2026-10-14** from five Stock v3 Assess repeats (case hose, 8 procs, base_cell
    0.006, 500 iters, PETG, parallel_mesh): **BAND_TOL = 0.03**, **NOISE_MARGIN_DB = 0.5**
    (2σ rule in `docs/validation/audits/2026-10-13-stock-flow-repeats-prereg.md`; was ±15 % / 2.8 dB
    from a non-repeat pair). Mean 2σ_rel 1.47 %; hub-band 2.71 % → ceil 3 %; noise 2σ 0.22 dB → floor
    0.5. After-bake vs r1: mean and noise **PASS**; r4 hub bar +3.05 % labelled "stronger" (**FAIL**,
    not widened). Bars stay a picture.
- [x] **27.4 Built blade vs its numbers: are sections planar where BEM assumes cylinders?** (from lt120)
  **DONE 2026-10-13, option (i) (Kimball), merged `ae3f1c4`.** Sections are wrapped onto their cylinders
  (`section_wrap="cylinder"` for axial designs; old saves stamped planar, 79 designs + 80 catalog rows,
  backup `runs/_backup_section_wrap_20261013/`). Built blade = sliders within camber 0.001 / stagger 0.1°.
  Stock v3 refit (sharp 0.2 edges, hub-cut corrected): vs the real STL in the rig, free 55.7 CFM (STL 58.3,
  planar v2 54.5); 5/10 Pa 48.0/37.5 (STL 49.5/37.1, v2 46.9/36.6); mean gap 2.8 % vs v2 4.4 %.
  V5 vs planar Stock in Assess: +2.4 % free / −5.6 % loaded (narrow FAIL, understood).
  **QA-32 done Kimball's way (a):** blades may hang at most **2 mm below the hub's motor face as designed**
  (8/200 stress designs refused); under that, the realisation corrects camber/stagger at cut stations
  (8 worst allowed designs pass V1). Plus a fuse safety net (a fuse that leaves loose pieces is redone one
  blade at a time). Audit: `docs/validation/audits/2026-10-12-cylinder-sections.md`.
  **Note for anyone reading old numbers:** the 57.6 CFM / 2.1 % figures were the first v3 with *round* edges
  (a fit-script bug, fixed); use the numbers above.
  - **QA round 8 (Task D): MATERIAL, and the cause is different from what we thought.** Two separate
    problems, not chord/r:
    - **QA-30, the hub-face clip.** `clip_blade_below` (the blades are cut at the hub's motor face) shortens
      deep blades. The measured-chord realisation measures a lone *unclipped* blade
      (`chord_realisation.py:71`, confirmed). That is the whole lt120 chord gap (3–16 %), and why "loft"
      vs "measured" changed nothing. Unclipped, lt120 matches within 0.5 %, and its camber is fine.
    - **QA-31, lean/skew/sweep stacking.** On stacked blades the cut camber is far below the slider.
      - **Confirmed here, 2026-10-12:** Stock reads 0.036–0.040 for sliders 0.08–0.10. With lean, skew and
        sweep zeroed it reads 0.073–0.087, which is the slider minus the known estimator bias.
      - t9005's tip reads 0.0075 for a slider of 0.06. The gap grows with tip skew.
      - The measured-chord stretch makes it worse: the cut keeps only the middle of a longer section.
    - **So:** the camber slider doesn't mean what it says on any leaned or skewed design, Stock included.
      BEM scores the slider numbers, and CFD scores the built blade.
  - **Choices (Kimball):**
    - **(iii)** give BEM the measured built sections now (cheap, keeps BEM and CFD on the same blade);
    - **(i)** wrap sections onto cylinders in the builder (principled; every design's geometry changes, and
      Stock's recipe must be refitted);
    - **(ii)** realise camber the way chord is realised (more builds, and may fight lean).
    - QA suggests (iii) now, then (i) vs (ii) by a CFD A/B on t9005.
  - The builder lofts flat sections that touch the cylinder at radius r. A cylinder cut through lt120's long
    chords (41.6 mm at r 56.5) reads the chord up to 16 % short and the camber 25 % low (0.030 vs 0.040,
    about 0.004 of it from the estimator itself).
  - **Why it matters:** BEM computes on cylindrical strips using the *slider* numbers. If the built blade's
    cylinder sections differ, BEM and CFD score different blades. This may explain part of "BEM over-rates
    flat leaned blades".
  - **Contradiction to resolve first:** `chord_basis="measured"` (default) is supposed to raise the loft chord
    until the cylinder-cut chord matches (`chord_realisation.prepare_loft_chords`). QA says switching it to
    "loft" changed nothing. Either the realisation only acts near the tip trim, or it measures differently
    from `section_compare`.
  - **Steps:** measure param-vs-cylinder-cut chord, camber and stagger on Stock and about 5 saved designs,
    as a function of chord/r. If the gap is real, choose: wrap sections onto cylinders in the builder, extend
    the measured-chord realisation to camber, or give BEM the built sections.
    **[impact: high: accuracy of every score]** **[effort: med investigation / high fix]**
- [x] **27.6 (QA-29) After Assess finishes, its result message is replaced by a frozen "Running Assess…
  0:04".** **DONE 2026-10-12** (`7f14e5b`): stop the ticker before writing Done.
  **[impact: med: the result line is never seen]** **[effort: low]**
- [x] **27.5 (QA-26 leftovers) After a run, some captions show the cockpit as it is now, not what ran.**
  **DONE 2026-10-13:** Preview caption uses built `params` camber (`preview_built_camber`); Export
  message uses the click-time hub radius/height and mirror flag; Assess does not `select()` the
  new trial if `selected_trial` changed while it ran.
  **[impact: low]** **[effort: low]**
- [ ] **27.7 Optimizer under wrap: bounds and re-finding designs.** Every saved optimizer design was found
  with planar sections, where a camber slider of 0.06 built ~0.01–0.04. Under wrap the sliders mean the built
  blade (Stock v3 camber **0.024–0.048**). Do not print or rank old candidates as if their sliders still
  meant the same blade. t9005 wrapped moves less air than planar (V6). **Proposal (do not implement a
  campaign):** keep OPEN/GUIDED `max_camber` (0.0, 0.06) — that range is now *honest built* camber, and
  Stock sits inside it (max 0.048, so 0.06 is only a little above the real fan). Do **not** raise the
  ceiling. Stagger bounds already cover Stock v3 (root 23.5 / mid 31.2 / tip 22.5° vs OPEN 20–48 / 18–42
  / 16–38). Re-find designs under wrap when a campaign is adopted; until then old catalog rows stay
  stamped planar. **[impact: high]** **[effort: med]**
- [x] **27.8 Hang-limit UX.** **DONE 2026-10-13:** Preview/Export call `validate_blade_params` in the
  click preamble (plain `⚠ {exc}`, no CAD wait). `evaluate_candidate` returns `_infeasible` on hang
  before `build_impeller`. Isolated worker still carries the sentence (`stderr_tail=400`).
  **2026-10-14:** hang is still the *designed* TE vs hub face; Preview clips it so the mesh looks
  flush. Fit envelope now grows hub height until hang ≤ 2 mm (when depth allows). Scale-to-hub uses
  the same intake-overbuild max depth as Fit. The green envelope no longer lifts its outlet when
  overbuild makes the impeller taller (that painted the hub-face TE red).
  **[impact: med]** **[effort: low]**
- [x] **27.9 Rewrite `docs/validation/first_print_measure_plan.md` for Stock v3** (print freeze, §5.1).
  **DONE 2026-10-13:** B/A **0.91 (0.85–0.97)** from 55.7/58.3 × print 0.95. Old 0.89 / 57.6 retired.
  **[impact: high: blocks the first print]** **[effort: low]**
- QA tooling only, not app bugs: QA-28 (the stress runner's gates use wall time and break when the box
  suspends), and K2's sliver rule needs to be relative to edge length (S6_0019's 1e-9 mm² sliver is a
  threshold artefact).
- **QA-32 (MED, round 9):** on wrapped builds, stations the hub-face clip reaches have restored chord
  (QA-30 verified) but camber 0.005–0.011 low and stagger up to −1.1°. ~15 % of the stress population.
  **DONE 2026-10-13 (Kimball chose (a), not BEM-on-clipped): 2 mm hang limit + camber/stagger correction at cut
  stations, see 27.4.** (Cursor's 'BEM on clipped sections' was written before that decision.)
- **QA-33 (LOW–MED, round 9):** wrapped cylinder direction proof is INCONCLUSIVE more often
  (30/65 vs 24/66 planar). **r10b: 18/38 wrapped INCONCLUSIVE.** Still harmless.
- **QA-34 (MED, round 10b):** featured wrapped **S5_0184** — **DONE 2026-10-14.** B-rep was already
  one solid. The STL's 8 bodies were 1 watertight impeller + 7 collapsed tessellation needles (one
  per blade) at the hub. `export_stl` now strips them (`sanitize_stl`). Not a loft bug.
  `docs/qa/notes/qa-34-featured-wrap-stl.md`.

---

## 28. Print-part ID (parked; needed before a box of prints)

Kimball, 2026-10-13: two printed fans from a month ago, and only the Noctua is identifiable. At
~30 parts in a box, a re-test has to attach to the **export** (recipe, wrap, git, CFD run, material),
not “the black 120 mm one”. A sharpie works as a fallback **if the code already exists** to copy.

**Status:** 28.1 **done**. **28.2 done 2026-10-14** (registry + README, no cut). 28.3 glyphs still parked.
Mark-spec: `docs/qa/notes/print-id-mark-spec-r10.md`. +Z ring r 10–21.45 mm, full circle; dummy recess
M1–M3 PASS; Data Matrix at 0.5 mm/module is marginal. Aero of the full box pocket is 1.76 % (not
auto-exempt). Claude's view still stands: 28.2 (registry + README, no cut) is cheap; 28.3 only if a
sharpie code from the README proves too fragile.

### What this is for

Export already writes a print-ready STL, a README, `*_print_fit.json`, and optional handedness
sidecars (`fansim/cockpit/fan_export.py`, `print_export.export_print_ready`). Measurements already
key off `design_id` (`validation/store.py`). The missing piece is a **short code on the physical
part** that is the same string as the sidecar.

### Honest evaluation (do / don't)

| Idea | Verdict | Why |
|------|---------|-----|
| Recessed 4–5 char code on the hub at Export | **Do** | Readable without a phone; survives a box; FDM at 0.12 mm can hold ~3.2 mm Crockford glyphs |
| Data Matrix / tiny QR next to the text | **Do as optional, after the text works** | Phone lookup is nice; FDM modules need ≥0.4–0.5 mm. Text is the source of truth |
| Large lettering on the shroud / blade / hub OD | **Don't** | Aero + looks. Hub OD is in the blade-root recirculation |
| Cryptographic hash of the STL | **Don't** | Too long to print; we need a registry, not a fingerprint of triangles |
| Recover identity of already-printed unlabeled parts | **Don't** | Type them as `unknown` or throw them in the genuine/Noctua bin. No computer vision |
| CFD of the pocket | **Don't unless QA says the pocket is large** | A 8×3×0.5 mm recess on the hub disk is smaller than the motor cup. Measure area first |

### Where (pending QA Task A)

Print orientation is hub-down (`BLADE_PRINT_RULES`): **+Z / inlet is the last hub layers** (clean
recesses). −Z is on the bed (brim / first-layer mess) and is mostly the motor cup.

1. **Preferred:** inlet hub face (+Z), inboard of the blade roots, recessed 0.4–0.6 mm.
2. **Fallback:** −Z annulus outside the cup, only if +Z has no ring of flat hub.
3. **Never:** blades, LE/TE, tip, shroud OD, cup grip pads.

Alphabet: Crockford (`0-9 A-H J-K M-N P-R T-V W-X Y-Z`), 4 chars plus optional check digit.
Issued at Export, unique in `validation/prints/index.jsonl`. Filename stem includes the code
(replaces the old `design_100000` confusion, §23.19). README prints the code in large type
for sharpie fallback.

Record measurement: a `print_id` field that fills `design_id` / recipe / wrap / git from the
index. Genuine Noctua (article A) has no code — that is fine.

### Recommended order (when un-parked)

1. **28.1 QA mark-spec** — available annulus, letter size, dummy-pocket watertight + cup-fit.
2. **28.2 Registry + sidecar** at Export (no cut yet): code, `design_id`, recipe hash,
   `section_wrap`, git, material, STL path. README shows the code.
3. **28.3 Recessed glyphs** on the hub from the mark-spec. Watertight + mount gauge still pass.
4. **28.4 Record measurement** accepts `print_id` (type it; scan later).

- [x] **28.1 Hub-face mark-spec** (QA; no fansim edit). **DONE 2026-10-13, r10 Task A:** M1–M3 PASS.
  Preferred pocket +Z r 11.5–14.7 mm, 0.5 mm deep. `docs/qa/notes/print-id-mark-spec-r10.md`.
- [x] **28.2 Print-id registry + export sidecar / README** (no geometry cut). **DONE 2026-10-14.**
  Export issues a 4-char Crockford code + check digit, stems the STL `{code}_{name}_{stamp}`,
  writes it in the README (Sharpie line) and `*_print_fit.json`, and appends
  `validation/prints/index.jsonl` (gitignored). No hub recess.
- [ ] **28.3 Recessed hub glyphs** from the mark-spec.
- [ ] **28.4 Measurement ingest by `print_id`.**
- [x] **28.5 Hash-as-the-part / blade QR / vision on old prints.** **Not adopted.**

---

## 29. Cockpit honesty leftovers (2026-10-14)

Kimball: the Fan tab defaults to PETG; switching to **PLA+** (or another filament) does not look
like it actually builds for that material. Separate: the Trame UI is easy to lie about, and we
have almost no automated click-through — only `tests/test_fan_tab_setup_smoke.py` and the old
manual `docs/qa/browser_checklist_*.md`. 3-D/VTK is slow; tests should not wait on a mesh.

- [ ] **29.1 Material picker vs what actually runs.** UI state is `assess_material`
  (`fan_tab_ui.py`); Assess click snapshots it in `run_settings.py`. Export README, print
  temperatures, and Preview grams use `active_spec().material`, which is the **fan model** default
  (PETG) and does not follow the picker. Grok r12 Task D: confirm which surfaces still say PETG
  after PLA+ is selected (Assess stamp, Export README, Preview weight, optimizer argv). No CFD.
  **[impact: med: wrong weight / print sheet / flutter]** **[effort: low]**
- [ ] **29.2 Cockpit UI regression tests.** Standing filler for grok when A–D are done: add
  headless tests (extend the smoke / settings harness) that click a control and assert the caption
  or saved extra matches what we claim. Skip waiting on Preview/Export 3-D. First seed: 29.1
  (material picker). **[impact: med]** **[effort: med]**

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
