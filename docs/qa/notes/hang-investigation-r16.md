# Blade hang below the hub: causes, predictor, hub skirt (QA round 16, hang)

Master 9562574, read-only. Prereg `52eca5f39cfa21beccc202ecd19cb2d70cd71929` (`qa/prereg_r6`, branch
`prereg/round16-hang`, `qa_r16_hang/PREREG_R16_HANG.md`, sha256 `6ee13807…b4af7b3`), committed 16:52 MDT before
any data. Runs used `qa/run_r16` (a clone of the same commit with its own venv) on the box, with a fresh loft cache.
No CFD, Docker, OpenFOAM or outside STLs, and no fansim edits. Every code idea here is a proposal. Scripts and data:
`handoff/2026-10-17_from-qa-16-hang/`.

## Plain-language answer
- **What hang is.** Each blade section is a tilted airfoil. The tilt (stagger) puts the trailing edge (c/2)·sin(stagger)
  below mid-chord. Sweep lifts the whole section. The hub's bottom face sits 1.5 mm below the **root's** trailing edge.
  So a section hangs whenever its own trailing-edge drop, minus its sweep, beats the root's drop by more than 1.5 mm:
  `hang = max over span[(c/2)·sin(stagger) − sweep] − (c_root/2)·sin(stagger_root) − 1.5`.
  The decomposition is exact on all 432 hanging designs (residual 9e-16 mm). Median terms: TE drop 9.08, sweep −0.36,
  root drop −5.23, margin −1.5. In 324/432 designs the low point is next to the mid station (r_frac 0.47/0.53); in 81 it
  is at the tip. Refused designs hang at r 32–57 mm, which matches r10.
- **Sliders that EXTEND hang.** Only 8 matter: chord and stagger at root, mid and tip, plus sweep at mid and tip. A wide
  or steep mid or tip section deepens the hang. A wide or steep root makes the hub taller and hides it. Sweep lifts the
  section. Lean, skew, hub radius, tip radius, thickness, camber and blade count have **exactly zero** effect: Sobol
  ST = 0.000 on the guided box. Lean and skew only move sections around the circle, and NACA thickness is zero at the
  trailing edge.
- **How they combine.** Strongly non-additive. 53 % of the variance in the guided space comes from interactions (Sobol
  ΣS1 = 0.47). This happens because chord × sin(stagger) is a product, and only the worst section counts (a max over the
  span), measured against the root. For example, chord_mid has S1 ≈ 0 but ST 0.22: it matters only when the mid section
  is the lowest one.
- **What AMPLIFIES hang: a code loop, not a slider.** The chord-realisation fixed point (`loft_chords_for_measured_targets`)
  measures chord on the **clipped** blade. It sees the chord the hub-face cut removed, lengthens the loft chord to put it
  back, and that pushes the trailing edge lower still. The clip removes h/sin β of chord, and half of the re-added chord
  drops the TE by h/2, so stagger cancels out. Two iterations give 1 + ½ + ¼ = **1.75×**. Measured: median built/designed
  = **1.77** (h_d ≥ 1 mm, n = 140). The chord-only stage gives 1.65× and the clip camber/stagger correction adds a median
  0.21 mm. With designed hang held fixed, no slider moves the amplification by more than about 0.015 mm per unit
  (stagger_mid +0.015 mm/°, sweep_mid −0.025 mm/mm).
- **Hub extension.** It works mechanically: 29/30 sound meshes, the cup fits, no BEM change, median +0.98 g. But under
  the registered rule it is **not worth it on its own**: only 12/30 designs are rescued, because the extra depth pushes
  designs out of the 25 mm frame. It **is** worth doing up to the 15 mm motor-cup hub that A12x25 export already builds
  (see QA-44 below), with the growth placed below the blades.
- **Recommendation: A + C now, B only as "use the hub you already have".** Gate the validator and the optimizer on
  predicted **built** hang (1.75 × designed, or the A-3 line). That is the coupled slider limit C, and it costs 2.2 % more
  of the guided space. Then evaluate hang against the mount-grown hub, with the growth placed below the blades.
  Separately, decide whether the chord loop should keep compensating for chord the clip removes on purpose (QA-43).

## 1. Attribution (P1: 2141 R7 stress inputs, unshrouded, forced cylinder wrap, plus 600 guided samples)
- Hanging: 432/2741, and 141 are over 2 mm (guided: 74/600 hanging, 13 over 2 mm).
- A2, grouped permutation importance on M2 (5-CV R² 0.773, against 0.433 linear; interactions add **+0.34**). Results:
  sweep_mid 0.88, chord_mid 0.47, chord_root 0.45, stagger_mid 0.28, stagger_root 0.26, sweep_tip 0.08 (drivers), then
  stagger_tip 0.027, chord_tip 0.023, lean_mid 0.003, tip_radius 0.003. On the guided-only set: chord_root 0.48,
  sweep_tip 0.39, sweep_mid 0.32, stagger_root 0.25, chord_mid 0.24, stagger_tip 0.16. sweep_mid ranks first on R7
  because the open space allows sweep_mid down to −3 mm.
- Largest single pairwise gains: sweep_mid×chord_mid +0.060, sweep_mid×chord_root +0.041, sweep_mid×stagger_root
  +0.028, chord_mid×chord_root +0.020.
- Report-only Sobol on the guided+extended box (N = 512, exact validator geometry): ST chord_root 0.39, sweep_tip 0.36,
  sweep_mid 0.32, chord_mid 0.22, stagger_root 0.15, stagger_tip 0.15, stagger_mid 0.085, chord_tip 0.085. Every other
  slider is 0.000.
- Predictions: **P-a PASS** (lean ≤ 0.003), **P-b PASS** (top 5 drawn from the set, interactions material),
  **P-c PASS** (hub_radius < 0.003), **P-d PASS** (median ratio 1.77 in [1.6, 1.9]; 1.75 predicted).
- Deviation: the 5 CTL recipes (full 7-station payload) were dropped from A2. With them included, ridge M2 extrapolated
  to R² −1645. A1 includes them.
- P2 (300 CAD designs, seeded): built hang equals the STL zmin on 25/25 (max diff 0.21 mm, within 5 %). Of these,
  73 are over 2 mm as designed and **123 over 2 mm as built** (1.68×; r14 found 1.85×). 50 designs that the validator
  passes are cut deeper than 2 mm. No design hangs as built without also hanging as designed.

## 2. Option A: cheap predictor of built hang (hold-out n = 150, 63 over 2 mm)
| predictor | MAE | p95 abs | sens @2 | false refusal @2 |
|---|---|---|---|---|
| A-0 designed (today) | 0.97 | 3.66 | 56 % | 0 % |
| A-1 1.75 × designed (no fit) | 0.18 | 0.73 | 100 % | 2.3 % |
| A-2b no-CAD loop emulator + affine | 0.19 | 0.71 | 100 % | 3.4 % |
| A-3 linear (≈ 1.86·h_d − 0.15 when hanging) | **0.17** | 0.67 | 100 % | 1.1 % |
- **FAIL as registered**: every candidate misses the p95 ≤ 0.5 mm target. MAE, sensitivity, false-refusal rate and
  runtime (6 ms, no CAD) all pass.
- Report-only: the tail is the S5 designs with LE/TE features (tubercles, serrations). On feature-free designs (n = 132,
  the default optimizer) A-3 scores MAE 0.12 / p95 0.35 and A-1 scores 0.13 / 0.47, so all targets pass. Feature
  designs: p95 1.3–1.8 mm.
- **Proposal:** validate on `1.75 × blade_hang_below_hub_mm` (or the A-3 line), or measure the realised loft directly.
  `prepare_loft_chords` already runs before every build and its result is cached, so reading section points on it is free.

## 3. Option B: hub skirt (30 refused-as-built designs, fansim's own hub_height_mm + blade_hub_z_mm, top face fixed)
- Skirt e = h_d + 0.5 mm (median 2.55, max 5.5). One pass was always enough: with the face below the blade, the clip
  does nothing, so the 1.75× loop never starts. The skirt only has to cover the **designed** hang, not the built hang.
  Blade volume falls by a median 7.5 % because the loop stops inflating the chords.
- G1 mesh 29/30 watertight with one body. The one failure (S8_0056, "3 separate pieces") fails the same way with no skirt
  (control), and its hub (r 19.4) is below the 20.7 mm mount minimum. Zero failures are caused by the extension.
- G2 bed 29/30. Nothing sits below the new face, so the part prints flat hub-face-down; without the skirt the TE would
  poke below the bed.
- G3 cup 25/30. All 5 failures already exist in the base design (hub radius < 20.7 mm). The skirt leaves the cup and
  grips untouched.
- G4 depth (≤ 25 mm) 18/30. 8 failures already exist (the base design is already over 25 mm with a 15 mm hub) and 4 are
  caused by the skirt. The skirt adds 0.7–5.1 mm of depth over the 15 mm-hub baseline.
- G5 mass: median +0.98 g at 20 % infill, +4.9 g solid, against the auto hub. Against the 15 mm hub that A12x25 export
  builds anyway, it is +0.41 g / +2.1 g. 3 designs fail the gate (2.3 g, 2.2 g, 1.7 g / 8.6 g solid). Two of them add
  0 g against the 15 mm hub.
- G6 aero: BEM free-air change 0.0 % on all 30, and the annulus area is unchanged. BEM uses hub radius only and the skirt
  keeps the radius. It adds about 2πR·e of wetted area inside the hub wake (median about 190 mm² beyond the 15 mm hub), so I expect the
  effect to be negligible. That is an estimate, not CFD.
- **Verdict as registered: NOT WORTH IT.** 12/30 rescued (40 % < 70 %), and the failing gate is the rescue rate, driven
  by depth. Mass (median 0.98 ≤ 1.0 g) and mesh gates pass. Among the 19 designs that fitted A12x25 to begin with,
  12 are rescued (63 %).
- Collision: the skirt has the hub's radius, so it can't hit the struts sideways. It does need the impeller to sit
  e higher on the motor (cup measured from the new face), which is the G4 depth gate. If the impeller is not raised,
  the skirt uses up e of the hub-to-strut gap. I have no measured gap for that, so it is unknown.

## 4. Option C: coupled slider limits
Limit: `(c_k/2)·sin β_k − sweep_k − (c_root/2)·sin β_root − 1.5 ≤ 2/1.75 = 1.14 mm` for k = mid and tip (closed form).
Equivalently, designed hang ≤ 1.14 mm.
| rule | guided space removed | built>2 kept (misses /123) | built≤2 removed (/177) | stagger_mid ≥ 44 removed |
|---|---|---|---|---|
| today (designed ≤ 2) | 2.2 % | 50 | 0 | 3.2 % |
| C-closed (station formula) | 4.8 % | 1 | 13 | 8.8 % |
| C-exact (validator margin ≤ 1.14) | 4.3 % | 1 | 5 | 8.0 % |
The median stagger_mid barely moves (39.0 → 38.9°), so C does not remove the optimizer's favoured high-stagger region.

## 5. Comparison
| | A predictor | B skirt | C coupled limit |
|---|---|---|---|
| fidelity vs built hang | 100 % sens, 1–2 % false (no features) | n/a: removes the cut | 1/123 missed, 5/177 false |
| designs rescued or excluded | none rescued; correct refusals | 12/30 rescued | excludes +2.1 % of guided space |
| physical cost | none | +1 g, +0.7–5 mm depth | none |
| runtime / scope | 6 ms, validator one-liner | params only (Fit already grows the hub, but symmetrically) | optimizer bounds or a gate |
**Recommended:** A as the validator rule (built hang = 1.75 × designed), applied in the optimizer gate (that is C).
Plus B-lite: in the optimizer, evaluate hang against the hub that will actually be built (≥ 15 mm for A12x25), with the
growth placed below the blades. That alone rescues 54/141 refused designs at no extra depth (P1, `p1_mount15.json`).
The extra growth Fit envelope adds today is symmetric, so half of it is wasted above the blades. Pass
`blade_hub_z_mm = +Δh/2` to put all of it below.

## Bugs / findings → QA_REVIEW
- **QA-43 (MED):** the 2 mm limit is checked on designed hang, but the built cut is 1.75× deeper (chord loop refills
  the clipped chord). 50/123 designs built deeper than 2 mm pass the validator.
- **QA-44 (MED):** the optimizer and CFD validate and score with the auto hub, while A12x25 Export and cup Preview grow
  it to 15 mm symmetrically. That moves the clip plane by up to 3.3 mm. 54/141 designs refused at the auto hub pass at
  the export hub, and 171/291 allowed hanging designs are printed with a different trailing edge from the one scored
  (118 are not cut at all).
- **QA-45 (LOW):** with a hub below the mount minimum, the cup carve sometimes raises "did not join into one solid
  (3 separate pieces)" (S8_0056) instead of the plain "hub radius too small" message the other 4 such designs got.
