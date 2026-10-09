---
name: fan-sim-status
description: "Fan-simulator build progress and what's next"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9facc2be-ff12-44e2-9ede-0cced25b4756
  modified: 2026-08-30T04:23:12.748Z
---

**BACKLOG ITEMS DONE 2026-08-31 (both verified: build_server constructs, store round-trips):**
1. PROP GRAPH: added prop_scatter_figure (thrust vs efficiency, colored by power, customdata=row idx)
   as a trame-plotly Figure in the Propeller tab (always-mounted card so prop_fig_update lands); optimize_
   prop pushes it via ctrl.prop_fig_update; click a point -> load_prop_row (same customdata-only binding as
   the fan plot). Thrust-vs-NOISE still needs a prop-noise model (BEMT has none) — remains backlog.
2. RECORD ACTUAL PRINT: validation/store.DesignMeasurement + record_measurement gained print_type:str +
   weight_g:float|None (material already existed but was auto-filled from spec — now user-entered, falls
   back to spec.material). Cockpit Record-measurement panel: Material (text) / Print type (VSelect FDM/SLA-
   resin/SLS/other) / Weight g (number) row; save_measurement passes them. Old JSON records still load
   (defaults). Ties the real printed part (material+process+weight) to its sim for the scorecard.

**OPEN TODOS (were user-requested 2026-08-31; both DONE above):**
1. PROPELLER TAB needs a GRAPH (right now the prop optimizer shows only a Pareto TEXT list / VList).
   Add a scatter plot. User asked "thrust vs NOISE? maybe another factor?" — but props have NO noise
   model yet (BEMT gives thrust/eff/power/FM only). So: plot THRUST vs EFFICIENCY (the two objectives we
   have), colored by power or FM, for now; a prop-NOISE model (BPF tone from n_blades×rpm, tip-speed
   broadband, or a CV-force analog) is the prerequisite for a real thrust-vs-noise graph — flag that.
2. MEASUREMENT RECORDER should capture the ACTUAL PRINT: user-entered MATERIAL (may differ from the
   spec's), PRINT TYPE (FDM / SLA-resin / etc.), and measured WEIGHT (g). Today cockpit save_measurement
   pulls material from active_spec() and records cfm/static/noise/rpm/instrument/notes only. Add
   material + print_type + weight_g fields to validation/store.DesignMeasurement + record_measurement
   + the cockpit Record-measurement panel (VTextField/VSelect). Ties the real printed part to its sim.
Also available (not done, user's call): RETAG old run/catalog designs fan_model 'a12x25'->'generic_120'
(they were built for the loose 119mm envelope, not the real 110mm Noctua frame; generic_120 added
2026-08-31). Left old data untouched per user ("don't remove old tests"). See [[fan-sim-a12x25-specs]].

**COCKPIT FAN|PROPELLER TABS DONE 2026-08-30 (propeller archetype STAGE 4 — the explicit UI reorg).
VERIFIED LIVE IN BROWSER (port 8092, runs/opt_guided). fansim/cockpit/app.py restructured:
(1) TAB BAR (v3.VTabs v_model=active_tab: '🌀 Fan — CFD design' | '🚁 Propeller — instant BEMT
design'). Used v_show (NOT VWindow) to gate each tab's content — the fan VRow just gained
v_show="active_tab === 'fan'" (a ONE-LINE change, no mass re-indent of the 200-line fan block =
low-risk); prop content is a sibling html.Div v_show="active_tab === 'propeller'". (2) FAN EDITOR
REGROUPED: the one giant 'Geometry' accordion panel -> 8 logical panels (Planform / Pitch·twist /
Airfoil / 3-D shape / Winglet / Hub / Spacing / Features); Randomize-geometry btn moved above the
accordion (always visible). (3) PROPELLER TAB (self-contained, no CFD/catalog): prop-size VSelect
(prop_spec_names) + live spec readout (dia×pitch, blades, shaft, tip Mach); blade sliders p_n_blades/
p_pitch/p_chord_root·mid·tip/p_camber; ANALYZE btn = instant BEMT readout (thrust g / g-W / W / FM /
15 m-s forward prop-eff) + async build_prop 3-D preview on a SECOND pv.Plotter (prop_plotter, wired
ctrl.prop_view_update); OPTIMIZE btn (trials/max-power fields) = run_prop_study async ~1s -> VList
front (click a row -> load_prop_row fills sliders + re-analyzes + rebuilds geometry); EXPORT STL btn
-> build_prop to exports/prop_<model>.stl. ALL FLOWS BROWSER-VERIFIED: fan regroup renders; prop
Analyze -> 2190g/2.92gW/FM0.75 + 3-blade twisted prop rendered; Optimize -> 59-design front (matches
CLI); row-click -> 4-blade 3.9" loaded, readout+sliders+3-D all updated to 4-blade geom; tab toggle
back to Fan -> scatter still interactive, plot-click still selects #9015+syncs dropdown (no regression).
23 prop+acoustics tests pass. Robustness: optimize_prop treats blank/0 max-power as 'any', guards
trials parse. THE PROPELLER ARCHETYPE IS NOW COMPLETE end-to-end WITH A UI: pick size -> tune/optimize
blade -> analyze thrust/eff -> export, all CFD-free. Stages 1-4 (spec+registry / geometry pitch-twist /
BEMT / optimizer / cockpit tabs) all done. FUTURE (not built): prop compressible open-air CFD tier to
refine finalists (tip Mach 0.4-0.58); forward-flight objective in the optimizer (currently static hover
only); tooltip images for the prop sliders (fan sliders have them via docs/control_images/e_*.png).**

**COCKPIT FAN|PROPELLER TABS DONE 2026-08-30 (propeller archetype STAGE 4 — the explicit UI reorg).
VERIFIED LIVE IN BROWSER (port 8092, runs/opt_guided). fansim/cockpit/app.py restructured:
(1) TAB BAR (v3.VTabs v_model=active_tab: '🌀 Fan — CFD design' | '🚁 Propeller — instant BEMT
design'). Used v_show (NOT VWindow) to gate each tab's content — the fan VRow just gained
v_show="active_tab === 'fan'" (a ONE-LINE change, no mass re-indent of the 200-line fan block =
low-risk); prop content is a sibling html.Div v_show="active_tab === 'propeller'". (2) FAN EDITOR
REGROUPED: the one giant 'Geometry' accordion panel -> 8 logical panels (Planform / Pitch·twist /
Airfoil / 3-D shape / Winglet / Hub / Spacing / Features); Randomize-geometry btn moved above the
accordion (always visible). (3) PROPELLER TAB (self-contained, no CFD/catalog): prop-size VSelect
(prop_spec_names) + live spec readout (dia×pitch, blades, shaft, tip Mach); blade sliders p_n_blades/
p_pitch/p_chord_root·mid·tip/p_camber; ANALYZE btn = instant BEMT readout (thrust g / g-W / W / FM /
15 m-s forward prop-eff) + async build_prop 3-D preview on a SECOND pv.Plotter (prop_plotter, wired
ctrl.prop_view_update); OPTIMIZE btn (trials/max-power fields) = run_prop_study async ~1s -> VList
front (click a row -> load_prop_row fills sliders + re-analyzes + rebuilds geometry); EXPORT STL btn
-> build_prop to exports/prop_<model>.stl. ALL FLOWS BROWSER-VERIFIED: fan regroup renders; prop
Analyze -> 2190g/2.92gW/FM0.75 + 3-blade twisted prop rendered; Optimize -> 59-design front (matches
CLI); row-click -> 4-blade 3.9" loaded, readout+sliders+3-D all updated to 4-blade geom; tab toggle
back to Fan -> scatter still interactive, plot-click still selects #9015+syncs dropdown (no regression).
23 prop+acoustics tests pass. Robustness: optimize_prop treats blank/0 max-power as 'any', guards
trials parse. THE PROPELLER ARCHETYPE IS NOW COMPLETE end-to-end WITH A UI: pick size -> tune/optimize
blade -> analyze thrust/eff -> export, all CFD-free. Stages 1-4 (spec+registry / geometry pitch-twist /
BEMT / optimizer / cockpit tabs) all done. FUTURE (not built): prop compressible open-air CFD tier to
refine finalists (tip Mach 0.4-0.58); forward-flight objective in the optimizer (currently static hover
only); tooltip images for the prop sliders (fan sliders have them via docs/control_images/e_*.png).**

**PROP OPTIMIZER DONE 2026-08-30 (propeller archetype STAGE 3.5). fansim/propeller/optimize.py:
run_prop_study(spec, n_trials, max_power_w=) — NSGA-II over the prop BLADE within a fixed size/RPM
envelope (n_blades 2-4, pitch 0.6-1.4x nominal, chord root/mid/tip, camber), objectives = MAXIMIZE
(thrust_g, efficiency_g_per_w) via BEMT. BEMT is instant -> 400 trials in ~0.6s (vs hours for CFD).
max_power_w gates over-budget designs (return 0,0) so the front is realistic to a real motor. Result
(fpv_5inch, 700W cap): at the ~650W stock draws, optimizer finds ~2090g @ 3.19 g/W vs stock ~1850g @
2.85 = +13% thrust AND +12% eff at same power, FM 0.80. PHYSICS IT REDISCOVERED ON ITS OWN: for STATIC
hover thrust it prefers MORE blades + LOWER pitch (4-blade ~2.8-3.1" over stock 2-blade 4.3") — the
well-known hover-vs-speed prop tradeoff. HONEST: compares vs my ROUGH stock ref, not bench data; '4
blades always wins' partly because BEMT's solidity term doesn't fully penalize blade-wake interference;
DIRECTION (low pitch + more blades for hover) is real+textbook, MAGNITUDE needs bench validation.
Objective is STATIC only (biases low pitch); forward-flight would want more pitch. scripts/run_prop_
optimization.py (prints Pareto + --export builds the picked design's watertight STL via build_prop
chord_frac/camber kw; default pick = most efficient). tests/test_prop_optimize.py (3: front populated+
ordered, power cap respected, designs sane). exports/prop_5inch_optimized.stl. 17 prop tests pass.
FULL PROP LOOP NOW: spec+registry -> geometry(pitch-twist) -> BEMT(thrust/eff) -> OPTIMIZE -> export,
all CFD-free/instant. NEXT: stage 4 cockpit Fan|Propeller tabs + editor regroup (the explicit UI reorg).**

**PROP OPTIMIZER DONE 2026-08-30 (propeller archetype STAGE 3.5). fansim/propeller/optimize.py:
run_prop_study(spec, n_trials, max_power_w=) — NSGA-II over the prop BLADE within a fixed size/RPM
envelope (n_blades 2-4, pitch 0.6-1.4x nominal, chord root/mid/tip, camber), objectives = MAXIMIZE
(thrust_g, efficiency_g_per_w) via BEMT. BEMT is instant -> 400 trials in ~0.6s (vs hours for CFD).
max_power_w gates over-budget designs (return 0,0) so the front is realistic to a real motor. Result
(fpv_5inch, 700W cap): at the ~650W stock draws, optimizer finds ~2090g @ 3.19 g/W vs stock ~1850g @
2.85 = +13% thrust AND +12% eff at same power, FM 0.80. PHYSICS IT REDISCOVERED ON ITS OWN: for STATIC
hover thrust it prefers MORE blades + LOWER pitch (4-blade ~2.8-3.1" over stock 2-blade 4.3") — the
well-known hover-vs-speed prop tradeoff. HONEST: compares vs my ROUGH stock ref, not bench data; '4
blades always wins' partly because BEMT's solidity term doesn't fully penalize blade-wake interference;
DIRECTION (low pitch + more blades for hover) is real+textbook, MAGNITUDE needs bench validation.
Objective is STATIC only (biases low pitch); forward-flight would want more pitch. scripts/run_prop_
optimization.py (prints Pareto + --export builds the picked design's watertight STL via build_prop
chord_frac/camber kw; default pick = most efficient). tests/test_prop_optimize.py (3: front populated+
ordered, power cap respected, designs sane). exports/prop_5inch_optimized.stl. 17 prop tests pass.
FULL PROP LOOP NOW: spec+registry -> geometry(pitch-twist) -> BEMT(thrust/eff) -> OPTIMIZE -> export,
all CFD-free/instant. NEXT: stage 4 cockpit Fan|Propeller tabs + editor regroup (the explicit UI reorg).**

**UNEVEN-SPACING LBM STUDY LAUNCHED 2026-08-29 -> runs/spacing_study (scripts/run_spacing_study.py,
base opt_run1_t9006 nB9 from CATALOG via get_entry, spreads [0,0.4,0.6,0.8], seed 7, ~10-12min GPU).
Tests the ONE untested acoustic idea: does UNEVEN balanced blade spacing cut the BPF TONE (spread it
across 1xrev harmonics) vs even? Decoupled from solidity, so unlike the null bio-features it attacks tone
directly. KEY PRE-CHECK (compute-free): analytic peak_tone_reduction_db shows ODD blade counts matter —
6 blades ~-1.6dB (near-symmetric balanced patterns, weak), 7 ~-4.4, 9 ~-5.4, 11 ~-5.4 -> used a 9-blade
base for a real effect. Compares LBM-measured bpf_tone_db (even vs uneven) AND vs the analytic prediction;
control forced truly even (blade_angles_deg=None). -> spacing_verdict.json. **RESULT = POSITIVE (the first clearly-working design lever, vs the feature nulls). runs/spacing_study,
691s. Even 9-blade base vs uneven spreads. NAIVE bpf_tone_db (tone at the single 9xrev=300Hz) looked
MIXED (-3.0 at 0.4 but +4.7/+6.0 at 0.6/0.8) -- because uneven spacing SPREADS energy OFF the BPF, which a
single-frequency measure can't see (measurement artifact, script's auto 'lever works' was luck). FIX
(compute-free, re-analyzed the SAVED CV-force CSVs, no new GPU): new farfield.peak_tone_over_harmonics(p,
dt,f_rev) = loudest tone across ALL k*f_rev shaft-order harmonics = the HONEST tonality metric. With it:
EVEN peak tone 34.9 dB; spread 0.4 -> 29.5 (-5.4), spread 0.6 -> 29.1 (-5.8), spread 0.8 -> 34.2 (-0.7).
=> uneven spacing at spread ~0.4-0.6 CUTS the peak tone ~5-6 dB, MATCHING the analytic prediction (-5.4),
with FLAT broadband (~50 dBA) + FLAT thrust (~-0.08) = a pure, COST-FREE acoustic lever. Optimum ~0.4-0.6
(0.8 over-spreads). BONUS: the compute-free analytic tonal proxy (acoustics/tonal.peak_tone_reduction_db)
is now LBM-VALIDATED -> cheap tonal scoring for future designs. WIRED: peak_tone_db added to noise_from_cv_
force output; run_spacing_study.py uses it; 2 farfield tests (peak-tone finds loudest harmonic / catches
spread energy a BPF measure misses). LESSON: measure the RIGHT thing -- for tone-spreading designs use
peak-over-harmonics, NOT single-BPF. ODD blade counts needed (6~1.6dB, 9~5.4dB analytic potential).
MADE USABLE 2026-08-29: cockpit do_preview now shows a live '🔉 Uneven spacing: predicted peak tone −X dB,
free of any flow cost' readout (from the LBM-validated peak_tone_reduction_db on the current blade-angle
pattern, no GPU) whenever the previewed design has uneven spacing, + an 'even blade count' nudge. Turns
the validated lever into a live design guide. Cockpit builds, sign verified (+drop). USER RESTART.**

**README REWRITTEN (2026-08-29) — the old one was STALE (claimed 'noise unbuilt, GPU unused', no catalog/
store/print/mount/mountable). New README reflects the finished tool: built+working list, VALIDATED (+2%
free-air on real STL, 21Pa shut-off), honest caveats (optimizer CFM optimistic=relative rankings trusted;
feature benefit NULL at achievable fidelity; nothing physically measured yet=the one real gap), the full
WORKFLOW (optimize->cockpit->export->print+mount->measure->catalog), quickstart w/ --reload, key commands
(run_optimization --mountable, export_finalists, catalog build/list/show, prune_runs, score_feature_noise),
and the data layout. Front door now matches reality.**

**SHOWDOWN SCORECARD ARTIFACT (2026-08-29, the project's capstone deliverable). Honest head-to-head
HTML artifact (Archivo/IBM Plex, blue=buildable/green=real/rust=unbuildable): Noctua (60 CFM real,
23 dBA, the benchmark) vs opt_mountable_t1 (85/80 CFM sim, mountable YES, print 41/100) vs
opt_extended2_t36 (86/81 sim, 40% eff, mountable NO). Comparison table across airflow/eff/noise/fits-
motor/printable/MEASURED. Deliberately NO false 'beats Noctua' claim — the 85 is a sim ideal, real print
expected LOWER; the 'Measured for real?' cell is an emphasized EMPTY dashed box (Noctua ✓, design blank)
= the emotional/honest center. Verdict: print opt_mountable_t1 + measure to fill the box. URL in the
2026-08-29 session. Ties together optimizer+mountable-constraint+print-export+measurement-store honestly.**

**WALKING SKELETON COMPLETE (Phase 1 done).** One command runs the full loop:
`uv run python scripts/run_baseline.py` → geometry → STL → OpenFOAM MRF case → mesh → solve
→ `runs/<out>/metrics.json`, ~5 min (40s mesh + 250s serial solve).

- `fansim/geometry/`: airfoil.py (NACA4), blade.py (BladeParams/RadialStation, loft+pattern+
  fuse hub), export.py (STL + trimesh watertight), config.py (YAML). Watertight 7-blade
  impeller, 113mm dia x 24mm deep.
- `fansim/cfd/`: domain.py (TestRig — SQUARE box duct for skeleton, MRF zone), templates.py
  (all v2406 dicts, `@placeholder@` subst), openfoam_case.py (build_case + MESH_PIPELINE),
  runner.py (docker subprocess, mounts case at /case), metrics.py (parse forces/moment +
  surfaceFieldValue → CFM/static-P/torque/power/efficiency).
- Image: `opencfd/openfoam-default:2406`. MRF via constant/MRFProperties, omega rad/s.
  Feature-extract binary = `surfaceFeatureExtract`; cylinderToCell uses point1/point2.
  FoamFile header must NOT open an unclosed `/*` banner (drop the ASCII banner).
- Baseline numbers (inlet 2 m/s, over-driven): 56 CFM, static -48 Pa, torque 10 mN.m,
  2.1 W, thrust 0.28 N. NEGATIVE static/efficiency = fixed-velocity inlet past free
  delivery, NOT a bug — Phase 2 P-Q sweep fixes it.
- Tests: 9 passing (`tests/test_geometry.py`, `tests/test_cfd.py`). `docker` marker registered.
  Scripts end with `os._exit(0)` to skip a harmless OCP/VTK teardown segfault.

**Phase 2 in progress — parallel solve + P-Q fan curve.**
- Parallel MPI solve (`run_solve(n_procs=8)`): decomposePar + mpirun; 251s→81s serial→8-core.
  `scripts/run_fan_curve.py` sweeps inlet velocity → CSV + PNG plot + free-delivery estimate.
- TWO non-obvious bugs fixed (both cost real debugging time):
  1. On restart, OpenFOAM ROTATES function-object files: old `surfaceFieldValue.dat` ->
     `surfaceFieldValue_0.dat`, new run writes the suffixed name. Parser globbed `.dat` and
     read STALE data → every sweep point returned point-1's value. FIX: `run_solve` now
     `rm -rf processor* postProcessing` before every solve.
  2. Rotation direction: +omega about +z made THIS blade handedness pump -z (acted as a
     resistance → negative static pressure everywhere). FIX: `TestRig.spin=-1` →
     `omega_signed`; MRF uses signed omega, power uses unsigned. Now static pressure positive.
- Baseline P-Q curve (spin fixed, 7 pts): free delivery ~123 CFM, shutoff dP ~4 Pa. Shape
  correct (static declines to 0 at free delivery). Pressure is LOW (~4 Pa vs Noctua ~23 Pa):
  the baseline is a high-flow/low-pressure under-cambered guess — optimizer's job to improve.
  Mid-curve is slightly non-monotonic (~10% noise) = under-convergence (600 iters) + coarse
  box duct. For the optimizer, tighten convergence OR use 1-2 fixed operating points/candidate
  (a 7-pt curve is ~8 min/candidate — too slow for search).

**Pressure-driven BCs added (for optimization — makes CFM blade-dependent):**
- `build_case(back_pressure_pa=...)` switches to total-pressure inlet + fixed static
  back-pressure outlet (templates `*_PDRIVEN`). `scripts/run_baseline.py --back-pressure P`.
- Added potentialFoam init in `run_solve`; switched SIMPLE to `consistent no` + under-relax
  (p 0.3, U/k/omega 0.7) — the old SIMPLEC/0.9 DIVERGED (FP exception) under pressure BCs.
- Baseline free-delivery (back_pressure=0): 66.9 CFM, 3.42 Pa, eff 14.3%, stable/converged.
- OPEN METRIC-DEFINITION ISSUE: pressure-driven free delivery (67 CFM) != velocity-driven
  zero-crossing (123 CFM) because `static_pressure_rise = (p_out - p_in)*rho` mixes kinetic
  terms differently across BC modes (totalPressure inlet vs zeroGradient). BEFORE optimizing,
  define clean objectives: use TOTAL-pressure rise (p0_out - p0_in) for fan pressure, and CFM
  at a fixed back-pressure load for flow. Add total(p) surfaceFieldValue FOs.

**Phase 3 optimizer BUILT (objectives = CFM_free + CFM_load + efficiency, all maximized).**
- `fansim/manufacturability/` (materials PLA/PLA+/PETG/ABS/TPU + printability min-wall gate),
  `fansim/structural/stress.py` (centrifugal gate — negligible at 2000 RPM, SF~658),
  `fansim/optimize/` (objectives.evaluate_candidate = gates + mesh once + solve at
  back_pressure 0 and load; search_space.suggest_params ~10 dims; study.py Optuna NSGA-II
  + SQLite, resumable), `scripts/run_optimization.py` (Pareto JSON + scatter PNG + STLs).
- Objective def: cfm_free = flow at back_pressure 0; cfm_load = SIGNED flow at load_pa
  (default 5 Pa) — reversal (fan can't sustain load) scores 0; efficiency at load.
- FIXED metrics.py: flow now SIGNED (was abs()) so flow reversal under load reads as failure.
- Search space tightened: THICKNESS (0.10,0.08,0.06) + chord>=14mm so tip section stays
  >0.8mm printable (trial 0 of validation got gated at 0.65mm before this).
- 20 tests pass (14 non-docker: search space, gates, infeasible path). Validation run
  `runs/opt_val` (3 trials) in progress to confirm full CFD loop + plot.
- Per-candidate cost ~4-5 min (mesh once + 2 solves @ base_cell 0.005/0.006, 500-800 iters).

**FIRST REAL OPTIMIZATION DONE (runs/opt_run1, 24 NSGA-II trials, 56 min, all feasible).**
Optimizer WORKS and found big gains over the hand-guessed baseline:
- Winner trial 2 (nB=9): cfm_free 75.9, cfm_load 65.9, eff 20.5% (baseline reversed/~0 at 2Pa load).
- trial 15 (nB=11): 76.0 / 63.8 / 18.0%. Pareto front = {2, 15}. Params in runs/opt_run1/pareto.json.
- Clear trend: high-solidity (9-11 blade) designs sustain load flow + higher efficiency.

**FEATURE LIBRARY BUILT (`fansim/geometry/features.py`): tubercles (LE undulation),
serrations (TE sawtooth), dimples (surface thinning) as smooth section perturbations (stay
watertight, no booleans). `Features` dataclass on BladeParams; resolution auto-bumped
(6/wave, cap 72 sections) so featured blades stay light. Wired into search via
`suggest_params(trial, with_features=True)` + `run_optimization.py --features`. Verified
tubercles watertight (104k faces at old res; reduced now). 18 fast tests pass; slow featured
watertight tests + config roundtrip added.**
CAVEAT: feature wavelength must be resolvable by the CFD mesh (base_cell 6mm vs ~4mm tubercle
spacing) — needs surface refinement / finer mesh to see feature effects reliably.

**TWO FEATURE FOLLOW-UPS LAUNCHED 2026-08-28 (concurrent: GPU + CPU, no competition):
1. LBM NOISE PASS (GPU) — scripts/score_feature_noise.py --run runs/feat_study2: runs FluidX3D CV-force
   noise (evaluate_noise) on the smooth control + all 20 featured trial STLs -> band-limited dB(A) + BPF
   delta vs control -> runs/feat_study2/feature_noise.json. THE acoustic test the flow/eff study couldn't
   do. ~50-60 min. CAVEAT: LBM ~1mm/cell under-resolves the ~2mm blade AND ~1-4mm features -> may be
   resolution-limited/inconclusive; relative delta at consistent band-limit is the signal.
2. NEAR-STALL / STALL-DELAY (CPU) — scripts/run_stall_study.py --base-json runs/opt_extended2/pareto.json
   --base-trial 36 -> runs/stall_study: sweeps back-pressure [2,3,4,5]Pa on base t36 for 3 variants
   {smooth, tubercles(0.08/6), tub+serr}, compares cfm_load-vs-back-pressure (does tubercled sustain flow
   to higher bp = stall delay?). -> runs/stall_study/stall_verdict.json. ~60-70 min. CAVEAT: steady RANS
   does NOT converge near stall (unsteady) -> points flagged UNCONVERGED, limit-cycle averages; rigorous
   stall test needs transient URANS/LBM. Read as suggestive relative comparison under a consistent method.
Both new scripts. Report both verdicts when done.**

**NEAR-STALL / STALL-DELAY RESULT = NO SIGNAL (inconclusive-leaning-negative) (runs/stall_study, 4175s).
cfm_load vs back-pressure (smooth / tubercles / tub+serr): 2Pa 76.8/75.5/76.3, 3Pa 68.8/67.6/68.6, 4Pa
58.9/58.5/59.5, 5Pa 51.1/51.0/52.5. All 3 variants track within ~1-2 CFM the whole way; flow declines
SMOOTHLY for all (none stalls while another holds); smooth is even HIGHEST at 2-3Pa. tub+serr edges +0.6
to +1.4 CFM at 4-5Pa but within noise + those points UNCONVERGED. NO stall-delay effect detected. BUT the
CAVEAT outweighs the result: tubercles work via streamwise vortices / unsteady 3-D attached flow that
STEADY RANS on a ~5mm mesh (vs ~5mm tubercle wavelength) arguably CANNOT resolve -> weak evidence, method
likely blind to the mechanism. Not a falsification. Real answer needs TRANSIENT (URANS/LBM) + a feature-
resolving mesh. Combined w/ the flat-study null: at achievable RANS fidelity, features show NO flow/eff/
stall benefit — consistent w/ theory (features are noise/vortex devices RANS can't see). Noise (LBM) pass
still the decisive test.**

**LBM FEATURE-NOISE RESULT + COMBINED FEATURE VERDICT (runs/feat_study2/feature_noise.json, 5006s).
Control 50.0 dBA_band / 24.3 BPF. BROADBAND: ~neutral — most trials ±0.5dB, only 2/20 quieter by >0.3dB
(-0.4/-0.6 = negligible), several LOUDER (+1.2..+1.8). No broadband benefit (script's '2/20 quieter =
features CUT noise' is MISLEADING). TONE (BPF): LARGE swings -4.8..+6.8dB (features clearly perturb the
tone) BUT INCOHERENT — heavy serrations cut tone on trial6 (-4.8) yet RAISED it on trial7 (+5.4); no
feature type reliably reduces it. => COMBINED VERDICT across all 3 follow-ups: features show NO RELIABLE
benefit on flow/eff (null), stall (null, method-blind), broadband noise (null-to-worse), or tone (big but
incoherent swings). NEGATIVE for the bio-feature thesis AS TESTABLE IN THIS SIM. THE decisive caveat:
every test fights the SAME wall — the sim CANNOT resolve the features (CFD ~5mm mesh vs ~1-5mm feature
wavelength; LBM ~1mm under-resolves blade+features). These features work via fine-scale unsteady vortex
physics neither RANS nor feasible-VRAM LBM captures (~90M cells > 12GB). So it's 'NOT DEMONSTRATED IN SIM',
NOT 'proven useless'. STRONGEST ARGUMENT YET for the PHYSICAL-VALIDATION loop (print smooth vs featured +
measure) = the RECORD REAL DATA todo. The feature question is now compute/physical-gated, not a sim TODO.**

**FEATURE-ISOLATION STUDY DONE (runs/feat_study2, 7537s/2.1h, 20 trials all feasible). HONEST VERDICT
= NULL/MARGINAL on FLOW/EFF (the script's auto 'features HELPED' is TOO GENEROUS — its +0.5 threshold is
below the CFD noise floor). Control (smooth opt_extended2 t36): 86.3 free / 81.4 load / 40.7% eff. ALL 20
feature combos: free 86.1-87.6, load 81.1-82.7, eff 39.8-41.8 -> total spread ~1.5-2% = AT the screening
noise floor (~1-2% @ base_cell 0.005). NO COHERENT TREND: trial7 (heavy ser 0.05/12) +1.3 == trial17
(ZERO ser) +1.3 == trial10 (~no tubercle) +1.3; aggressive-feature trials 15/18 at-or-BELOW control. If
serrations/tubercles helped flow you'd see high-ser trials cluster high — they don't. => NO detectable
flow/eff benefit at this fidelity; the variation is noise. This is the EXPECTED honest result: features
are STALL-DELAY + NOISE devices, not bulk-flow devices, and this ran on the STABLE curve (1 Pa, far from
stall) on an already-optimized blade = least room to help flow. THE THESIS IS ABOUT NOISE, which this
study did NOT measure. REAL TEST STILL PENDING = LBM acoustic pass scoring the 20 featured trials vs the
smooth control (evaluate_noise/score) — the only way to test the acoustic claim. Also worth: a study near
STALL (higher back-pressure) where tubercles' stall-delay could actually show on flow. Data:
runs/feat_study2/feature_verdict.json + trials.**

**FEATURE-ISOLATION STUDY (proper) LAUNCHED 2026-08-28 -> runs/feat_study2. base=opt_extended2 t36
(nB7, smooth, 86/81 CFM 40% eff = the OPTIMIZER'S BEST geometry -> tests 'can features improve even
the optimized design?'). 20 trials + smooth control, iters 1000, base_cell 0.005, load_pa 1.0, ~2-2.5h.
FIXED STALE SCRIPT DEFAULTS FIRST (critical): run_feature_study.py defaulted load_pa=2.0 (BROKEN
near-stall objective that voided earlier rankings) + iters=800 -> corrected to 1.0/1000 to match the
fixed pipeline. Smoke-tested (1 trial coarse) OK: control 90/84/39%, works w/ current code (RPM-derate/
fan_spec/isolated-eval all compatible). CAVEAT: this study measures FLOW/EFF only; the bio-feature
thesis is largely about NOISE, and the cheap proxies (loading/Proudman) poorly capture surface-feature
noise -> the acoustic claim needs a SEPARATE LBM pass (score the featured finalists vs the smooth control
w/ evaluate_noise) AFTER this run. Old prelim (runs/feat_study, 2 trials) suggested features +CFM/+eff
but was noisy/load_pa-broken; this is the real 20-trial test. Output: runs/feat_study2/feature_verdict.json.**

**Feature-isolation study running (runs/feat_study, `scripts/run_feature_study.py` fixes
base=trial2 geometry, varies ONLY features). EARLY signal (2 trials): smooth control (finer
base_cell 0.005) = 69.9/49.3/10.8%; trial 0 tubercles(0.04,8)+serrations(0.04,7) =
68.4/60.5/19.0% -> +11 CFM load, +8% eff. PRELIMINARY (screening noise ~10%) but features
look like they HELP. Needs full 20-trial study + high-accuracy confirmation.**
Note: control 69.9 vs screening 76 for same design = fidelity shift (base_cell 0.006->0.005)
-> exactly why the high-accuracy tier matters.

**HIGH-ACCURACY PLAN written: `docs/high-accuracy-plan.md`. Fidelity ladder: screening ->
confidence-gate finalists -> Tier-2 (circular duct, prism layers, grid-independence/GCI, full
P-Q, UQ, OpenFOAM<->FluidX3D cross-check, transient LES/LBM + FW-H for real dB(A)) -> extract
transferable design rules (Sobol/surrogate -> docs/design-rules.md) -> Tier-3 print+measure.
Modules to build: cfd/testrig_cylinder, gridindep, hifi, lbm_fluidx3d; acoustics/fwh;
optimize/ladder; analyze/sensitivity. Sequencing: circular-duct+GCI FIRST (credibility keystone).**

**COCKPIT V1 BUILT + VERIFIED LIVE (Phase 1b). `fansim/cockpit/` (data.py loads designs from
Optuna study.db + trial STLs; app.py Trame+PyVista+Plotly). `scripts/cockpit.py --run <dir>
--port N`. Interactive design-space Plotly scatter (Pareto ★, eff colorbar) | live PyVista 3D
model + metrics panel. BOTH selection paths verified in-browser: click a plot point -> loads
that design's 3D model+metrics; dropdown too. 3D rotate/zoom via PyVista toolbar.**
Cockpit gotchas fixed: trame-plotly Figure takes a real go.Figure (not a state tuple);
pyvista view update = `ctrl.view_update = plotter_ui(plotter).update`; VSelect needs
`update_modelValue=(fn,"[$event]")`; plotly click event kwarg is `click=(fn,"[$event]")`.
Screenshots need the browser pane displayed (worked after interaction).

**COCKPIT V2 DONE + VERIFIED: parameter-editor panel (Geometry + Features expansion panels,
~17 sliders via `_slider` helper), "Preview geometry" button -> `do_preview()` builds
BladeParams from sliders (blade_from_flat + Features), printability-gates, regenerates
impeller STL, shows it ORANGE in the 3D viewer. "Reset" reloads the selected design. Verified
live: edited a design -> Preview -> orange model rendered. No CFD needed (geometry only).**

**COCKPIT V3 BUILT — FULL LOOP COMPLETE. "Assess this design" + "Sweep" (regression over one
param: camber/blades/stagger tip/sweep tip/tubercle amp/serration amp/dimple depth x N steps).
Async via `asynchronous.create_task` + `loop.run_in_executor(_blocking_eval)` (evaluate_candidate
base_cell 0.006/iters 500/8 procs); state.flush() pushes status; reactive plotly via
`ctrl.figure_update = fig_widget.update` + refresh_figure() (user runs = crimson ◆ 2nd trace,
ids 9000+). Verified live: click Assess -> status "Running CFD…", docker container spins up,
`runs/opt_run1/cockpit_assess/design_9000/` created + meshing. On completion _assess() appends
a Design to user_designs, refresh_items+refresh_figure, selects it (◆ on plot + 3D model).
(Completion/◆-point confirmation was pending the running eval when last checked.)**

USER'S FULL VISION DELIVERED + VERIFIED: click graph->fan+metrics; edit sliders->preview;
Assess->CFD->◆ on plot; Sweep->regression. Launch: `uv run --extra viz --extra optim python
scripts/cockpit.py --run runs/opt_run1`. Assess VERIFIED end-to-end: design_9000 ran CFD,
◆ landed on plot (free 66.7/load 48.7/eff 11.5%), 3D+metrics updated. Cockpit gotcha: the
in-app browser websocket drops during long runs (my automation nav resets it) — refresh_figure
writes to server state so a RECONNECT shows the ◆; a real user who waits sees it live. Made
click bindings canonical tuples.

**TIER-2 DIAGNOSIS (CRITICAL, per adversarial review). The 2 Pa LOAD OBJECTIVE IS BROKEN — the
steady solve does NOT converge there (near a stall bifurcation). Trial 2 cfm_load across runs:
65.9(600it) / 48(700it) / 71.1(1000it load-only) / 41.6(1500it) — MORE ITERS MADE IT WORSE.
NOT init-velocity bistability (probe: 3 inits @1000it all→71.1, 0.9%). NOT random (repro @700
= 47.7-49.4). It's non-convergent wandering near stall. BUT cfm_FREE (back_p=0) stayed ~70 every
run — free delivery is on the STABLE curve. So ALL prior rankings (76-CFM winner, Pareto, "features
help") are unreliable — dominated by the broken load objective.

Scripts: `test_bistability.py` (init sweep), `test_reproducibility.py` (repeat evals),
`capture_convergence.py` (flow-vs-iteration trajectory plot at multiple back-pressures).

CONVERGENCE TRAJECTORY PLOT (runs/convergence/convergence.png, trial 2, 2000 iters): 0 Pa and
1 Pa settle to FLAT plateaus by iter ~500 (81.5, 77 CFM); 2 Pa OSCILLATES forever (~70±1.5 limit
cycle, near-stall). Decisive: 0-1 Pa are usable operating points, 2 Pa is not.

FIX IMPLEMENTED: (1) `metrics.convergence()` reads outletFlow trajectory -> `converged` +
`flow_drift_pct`; FO sampling every iters/40 (`@FOINT@`); evaluate_candidate flags UNCONVERGED.
(2) OBJECTIVES MOVED TO STABLE CURVE: load_pa default 2.0->1.0, iters default 1000 (plateau by
~500), across objectives.py/study.py/run_optimization.py. cfm_load now = flow @ 1 Pa (stable).
Validating: repro 3x @ new settings (load 1Pa, iters 1000) on trial 2.

CARRYOVER BUG FOUND + FIXED: standalone 1 Pa solve = 77 CFM (init-independent: 76.4/76.8/77.5
for guesses 0.5/2.0/4.5) but evaluate_candidate's free->load-in-SAME-DIR gave 66. Reusing one
case dir across back-pressures contaminated the 2nd solve (mechanism unknown; case states looked
identical). FIX: `evaluate_candidate` now solves each operating point in its OWN case dir
(workdir/free, workdir/load) — each independent mesh+solve. Costs +1 mesh/candidate. Affected
EVERY optimizer eval. Trustworthy trial-2 values (isolated, 1000it, 0.005): free ~81, 1Pa load
~77, eff ~27% — reproducible + plausible. Validating repro_isolated (2x).

SCREENING FIXED + VALIDATED. Root causes were (1) near-stall 2 Pa objective -> 1 Pa; (2)
TRUNCATED DOMAIN (short ducts 1.0/1.5) -> long ducts 2.0/4.0 in evaluate_candidate; (3)
under-iteration -> 1000 it. NOT init-bistability, NOT carryover (both mis-diagnosed then
disproven). Trial 2 now: cfm_free 81.5, cfm_load 76.7-76.8 (0.1% spread!), eff 27%, converged=True,
reproducible. Convergence gating (`metrics.convergence`) is the safeguard. objectives.py: long
ducts 2.0/4.0, mesh-once, load_pa 1.0, iters 1000. 18 fast tests pass.

STILL OPEN: ABSOLUTE accuracy needs GRID CONVERGENCE (81.5 is @ base_cell 0.005; finer mesh may
shift it). Per-candidate now ~5-6 min (long ducts).

RE-OPTIMIZATION running (runs/opt_v2, 24 trials, fixed pipeline — prior opt_run1 rankings VOID).
Trial 2 re-evaluated to exactly 81.5/77.0/27.2% (matches validation). Numbers now cohesive.

VALIDATION INFRA BUILT this session (all ready to run once cores free):
- Cockpit ConnectionResetError spam FIXED (asyncio exception handler in app.py `_quiet_connection_reset`); verified 0 tracebacks after reconnects.
- `scripts/run_grid_convergence.py` — solve @ 3 base_cells, report GCI/drift (free delivery).
- `config/problems/a12x25.yaml` — 7-blade A12x25 approximation, 113.7mm dia x 20.4mm (fits 25mm), watertight.
- `scripts/validate_a12x25.py` — P-Q sweep vs published (60.1 CFM free-air, 22.9 Pa shut-off), over-prediction ratio + plot.
- README updated (honest status). See [[fan-sim-a12x25-specs]].
NEXT: when opt_v2 done -> show Pareto; run grid convergence + A12x25 validation.**

**GEOMETRY REWRITE (user: 'that fan looks nothing like the real noctua fan' — correct). Old
generator stacked airfoils STRAIGHT RADIALLY -> thin paddles, can't overlap. FIX: `RadialStation`
now has `lean_deg` (circumferential wrap); `_section_points_3d` rotates each PLANAR section about
Z by lean (planar = watertight; non-planar cylindrical wrap gave 826 open edges — reverted).
Varying lean 0->tip wraps blades -> realistic swept overlapping fan (build/wrap_fixed.png,
new_a12x25.png). lean=0 exactly reproduces old geometry. Added `networkx` dep (trimesh split
needed it). Search space: added lean_mid(0-25)/lean_tip(0-45), MAX_CHORD 28->40 (solidity),
envelope GATE in evaluate_candidate (reject dia>119 or depth>25mm). Default BladeParams +
config/problems/a12x25.yaml updated to wrapped realistic geometry. opt_v2 STOPPED (paddle space).
18 tests pass.

**SOLIDITY / OVERLAP (user: real fan's blade ROOTS overlap, mine had a gap — correct). Added
`blade_solidity(params)` -> {hub,mid,tip} = chord*cos(stagger)/pitch (>1 = blades overlap, no
see-through gap; drives static pressure). Verified root section angular span 76deg > 51.4deg
pitch = real overlap (formula matches geometry). Default + a12x25.yaml now HIGH-SOLIDITY: hub
1.75 / mid 1.16 (overlap) / tip 0.69 (~matches real A12x25 tip ~0.77 — tip gap is physically
normal). Wide chords (34/44/38) + low stagger (26/26/22) + wrap. Wrapped geometry CONFIRMED
through CFD: default = 65.3/59.2 CFM, 20.8% eff, converged=True (~320s/candidate). Search space
MAX_CHORD 40 lets optimizer tune solidity. build/final_default.png.

NEXT: re-run optimization on realistic wrapped high-solidity space; import real A12x25 STL for
exact validation (Thingiverse 403s scraping — need user to supply the STL file, e.g. into build/).**

**GPU TIER STOOD UP (2026-08-27): FluidX3D compiled + running on RTX 4070 Ti at 4657 MLUPs/s,
99% GPU util. Built with msys2 ucrt64 g++ (links C:/Windows/System32/OpenCL.dll directly; no SDK).
Repo at E:\Projects\programming_2\FluidX3D (sibling). Headless BENCHMARK default. Build/run cmds +
next steps in docs/fluidx3d-setup.md. NEXT: custom setup.cpp (import fan STL as rotating boundary,
transient) -> FW-H for noise dB(A) + shut-off pressure. This is THE remaining frontier (noise +
near-stall). The idle GPU is now usable.**

**ROTATING-FAN LBM WORKS (2026-08-27). Custom `FluidX3D/src/setup.cpp` (backup setup.cpp.orig)
imports build/a12x25_real_capped.stl as a ROTATING solid boundary in a duct + runs it on the GPU.
defines.hpp: MOVING_BOUNDARIES/EQUILIBRIUM_BOUNDARIES/SUBGRID/FP16S on, BENCHMARK off. Moving-
boundary recipe that works: each block rotate(Rz(omega*dt)) -> voxelize_mesh_on_device(fan,TYPE_S,
center,0,(0,0,omega)) -> run(dt), dt=4 (tip<1cell/block). Domain 120x120x300 (4.3M), duct wall +
axial-inflow inlet + fixed-rho outlet. Perf: ~6300 MLUPs/s, ~1460 steps/s, GPU 99%, 2.5GB VRAM,
12000 steps in ~15s, STABLE (no divergence). FIRST RESULT: ~27 CFM, flat steps 2k-12k (<2% drift)
— but this is a LOADED, OVER-VISCOUS point (Re=8000 for LBM stability; confined duct w/ back-
pressure), NOT free-delivery, so NOT yet comparable to validated ~60 CFM. Proves the transient GPU
tier runs+pumps+is stable; quantitative match is next. VTK exported (bin/export/u-*.vtk, 51MB).
NEXT TUNING: raise Re toward ~1e5 (finer grid/lower nu) + free-air BCs (open plenum both ends, no
back-pressure) to match free-delivery 60 CFM; then closed-outlet shut-off (~22.9 Pa); then blade-
surface pressure history -> FW-H for dB(A); then wire noise as 3rd optimizer objective.**

**FREE-DELIVERY CROSS-CHECK + KEY RESOLUTION FINDING (2026-08-27). Free-air BCs (fan+short shroud
mid-domain, all 6 faces open equilibrium@ambient, no back-pressure, omega flipped so fan pumps +z,
180x180x360=11.6M cells). Result settles ~35-37 CFM (+/-10% unsteady, positive, stable) = ~40%
UNDER the OpenFOAM/published 60.1. BRACKET TEST FALSIFIED tip-clearance hypothesis: 1-cell
clearance (r_in=56) and SEALED tip (r_in=55, 0 clearance) BOTH give ~35-36 CFM -> shortfall is
NOT leakage. Cause = COARSE BLADE RESOLUTION: at 1 cell~1mm the ~2mm blade is only ~2 cells thick,
does less aero work than the 0.25mm OpenFOAM mesh. Fixing needs ~0.5mm cells (~90M cells, ~50GB
VRAM) > 4070 Ti's 12GB. CONCLUSION: LBM at feasible resolution is NOT the tool for absolute FLOW
(OpenFOAM nails that, +2%); its unique value is TRANSIENT physics RANS can't do — shut-off
pressure + NOISE (FW-H). Pivot the GPU tier there. setup.cpp = working free-air rotating-fan
harness (backup setup.cpp.orig). NEXT: closed-outlet shut-off run (target ~22.9 Pa) + FW-H noise.**

**SHUT-OFF PRESSURE VALIDATED (2026-08-27). Fan in duct, intake open, discharge into SEALED capped
chamber. Chamber pressurizes until fan stalls (residual flow ~0.0 CFM = true dead-head); Δρ across
fan -> si_p((rho_disch-rho_intake)/3). 48000 steps: EARLY TRANSIENT OVERSHOOT ~29-32 Pa (chamber
filling) SETTLES by step ~28k to ~20-23 Pa (mean ~21). vs published 22.9 Pa = -8%; steady RANS was
~13 Pa = -43%. The transient GPU tier NAILS the near-stall pressure RANS can't (must read the
SETTLED value, not the fill transient). Lesson: don't quote early transient — I first mis-reported
~29 (+27%); the equilibrated value is ~21 (-8%).**

**NOISE TIER (in progress 2026-08-27). Plan: Curle COMPACT-DIPOLE proxy — rigorous here (BPF=7
blades x 33.3rev/s=233Hz; wavelength 1.47m >> 0.11m fan => acoustically compact, dipole valid, not
just 'cheap'). FluidX3D has FORCE_FIELD ext -> lbm.object_force(TYPE_S)=net force vector on solid.
Recipe: enable FORCE_FIELD; run fan in OPEN plenum (only TYPE_S = fan, no shroud) so object_force
isolates fan; log F(t) each sample over ~10 revs (~46000 steps, BPF period 660 steps); Python
post: Curle p'(x,t)=(x_i/(4*pi*c0*r^2))*dF_i/dt at 1m -> FFT -> 1/3-octave -> A-weight -> dB(A) +
BPF tone. Then wire dB(A) as 3rd optimizer objective. Full retarded-time surface FW-H = later
finalist upgrade (compact dipole is appropriate for this small fan).**

**NOISE PIPELINE BUILT — tonal+relative WORK, absolute far-field BLOCKED (2026-08-27).
(a) Curle force-dipole BLOCKED: object_force(TYPE_S)/update_force_field() return NaN on the
re-voxelized MOVING fan (flow fine, only the force kernel NaNs). FluidX3D has NO example of force
on a rotating/revoxelized object (all force examples static: sphere/Ahmed, TYPE_S|TYPE_X). Real
FluidX3D limitation. Reverted FORCE_FIELD/VOLUME_FORCE in defines.hpp.
(b) FIXED PRESSURE PROBES work (scripts/fan_noise_probes.py + setup.cpp probe version): 6 numerical
mics sample p=(rho-1)*cs^2 -> si_p over ~12 revs -> build/fan_probe_history.csv. Welch PSD + A-wt +
BPF detection -> build/fan_noise_probe_spectrum.png. BPF 233Hz + harmonics CLEANLY resolved,
loudest at tip-radius probe (physical). BUT domain ~0.12m < acoustic near-field lambda/2pi~0.23m =>
NO probe in acoustic far field; near-field = hydrodynamic pseudo-sound (SPL 112-120dB near-field);
1/r extrap over-reads ~70dB. ABSOLUTE far-field dB(A) NOT recoverable this way (published 22.6).
TRUSTWORTHY: BPF tone + RELATIVE noise deltas between designs = what optimizer needs (north star =
relative gains). Sufficient to wire noise as a RELATIVE 3rd objective.
ABSOLUTE far-field (future): control-volume force (momentum flux+pressure over FIXED surface around
fan -> net F(t), no moving-boundary kernel -> analytic dipole to 1m) OR porous FW-H surface.
setup.cpp currently = CV-force noise version (backup setup.cpp.orig = benchmark).

**CONTROL-VOLUME FORCE NOISE — BUILT, far-field SOLVED, absolute broadband coarse-grid-limited
(2026-08-27). setup.cpp CV version: net fan force on fluid via momentum balance over a FIXED box
surface (x,y +/-70, z +/-45 cells from fan), F=-(d/dt INT_V rho*u dV + OINT_S(rho*u*u_n+p'*n)dA),
pure fluid rho,u -> NO moving-boundary NaN. build/fan_cv_force.csv (SI vol-momentum P + surface-flux
Fs); scripts/fan_noise_cv.py -> F(t)=-(dP/dt+Fs) -> Curle dipole to 1m (compact). RESULTS: mean
thrust Fz=-0.076 N (PHYSICALLY SANE -> validates momentum balance!); on-axis BPF tone ~20 dB @1m
(close to published 22.6 dBA!); directivity front>45>side (correct). BUT overall ~60 dB(A),
CUTOFF-SENSITIVE (62->32 dBA as LP 4kHz->700Hz) -> absolute broadband NOT trustworthy at 1mm (grid
can't separate real vs numerical broadband; surface term carries it, not volume jitter; dF/dt x
A-weight peak 2.5kHz over-weights). TRUSTWORTHY: thrust, BPF tone, directivity, + RELATIVE ranking
with a CONSISTENT band-limit (cutoff cancels). Absolute broadband needs ~0.5mm (~90M cells)>12GB.
NOISE OBJECTIVE for optimizer = band-limited (<=~2-3kHz) A-wtd on-axis dB(A) @1m applied identically
to all designs = valid RELATIVE metric. build/fan_noise_cv_spectrum.png.

**FINALIST NOISE EVALUATOR BUILT + WIRED (2026-08-27). GPU LBM noise now scores optimizer finalists
(noise = expensive objective, finalists only, per plan; cheap RANS proxy still screens every
candidate). Pieces:
- setup.cpp GENERALIZED: reads build/noise_job.cfg (stl=, dia_mm=, out=); scales any impeller STL to
  1mm/cell, axis-Z, CV box auto-sized to R+12. Falls back to A12x25 if no cfg. (backup setup.cpp.orig)
- scripts/evaluate_noise.py: evaluate_noise(stl, dia_mm=auto-from-bounds, cutoff_hz=2500) -> writes
  cfg, runs FluidX3D.exe (env PATH += C:\msys64\ucrt64\bin), analyze_cv_force() -> dict{noise_dba_band,
  noise_dba_full, bpf_tone_db, thrust_n}. ~1-2 min/design on 4070 Ti. Also a CLI.
- scripts/score_finalists_noise.py <run_dir>: runs evaluate_noise on every pareto.json finalist's STL
  (runs/<dir>/pareto/trial_XXXX_*.stl), tabulates cfm/eff + noise, ranks quietest-first, writes
  runs/<dir>/finalist_noise.json. TESTED: trial22 -> thrust -0.066N, BPF 26.1dB, dBA_band 46.6.
- noise_dba_band = A-wtd on-axis dB(A)@1m low-passed @2500Hz, SAME band for all -> valid RELATIVE
  rank (absolute offset cancels). This completes CFM + pressure + NOISE multi-objective (relative).
- Speed fix: surface-only force (vol term dropped, 61.5 vs 62.0 dBA negligible) + sample/16 -> ~2.5
  min/design. subprocess MUST NOT capture FluidX3D stdout (DEVNULL; capturing deadlocks pipe).

opt_v3 FINALIST NOISE RANKING (runs/opt_v3/finalist_noise.json, quietest first, band@2500Hz):
  trial18 nB5: 70.2/64.7 CFM, eff38.3%, thrust-0.036N, BPF18.7dB, dBA_band47.2 (+0.0) QUIETEST
  trial14 nB5: 71.3/63.9 CFM, eff38.5%, thrust-0.038N, BPF13.7dB, dBA_band47.5 (+0.4) BEST EFF
  trial5  nB7: 73.5/69.1 CFM, eff36.2%, thrust-0.065N, BPF30.5dB, dBA_band47.7 (+0.5)
  trial22 nB7: 78.3/73.1 CFM, eff33.4%, thrust-0.062N, BPF26.7dB, dBA_band48.7 (+1.6) MOST FLOW/LOUDEST
COHERENT PHYSICS: 5-blade (low loading, thrust~-0.037) = quiet + efficient; 7-blade (thrust~-0.063)
= more flow but louder (BPF tone tracks blade loading 14->30dB). Flow-vs-noise tradeoff is real +
rankable (1.6dB spread). Pareto now has a NOISE axis. Showdown pick = priorities: flow(22)/eff(14)/
quiet(18). Absolute dBA_band~47 not meaningful (coarse grid); ranking + tradeoff structure ARE.**

**DESIGN RULES EXTRACTED (2026-08-27). scripts/score_all_noise.py -> noise on ALL 14 feasible opt_v3
trials (runs/opt_v3/all_noise.json, incremental/resumable). scripts/extract_design_rules.py ->
Spearman rank corr of every param + derived solidity(hub/mid/tip) vs every objective -> docs/
design-rules.md + docs/design-rules-heatmap.png. KEY FINDINGS (rho, n=14):
- **stagger_mid = WIN-WIN-WIN**: cfm +0.65, eff +0.44, noise -0.79 (quieter). Strongest noise corr;
  raising mid-span blade angle helps flow+eff+noise simultaneously = the free-lunch lever.
- **SOLIDITY/overlap = dominant NOISE driver**: sol_tip +0.70, sol_mid +0.67 (louder); sol_mid also
  -0.57 eff. The overlap that buys static pressure is what makes it loud = core flow-vs-noise tradeoff.
- **fewer blades = quieter(+0.64 noise) + more efficient(-0.61)**, modest flow cost(-0.35).
- **max_camber -0.78 on BOTH cfm and eff** (narrow range) -> keep camber low.
- **tip chord**: eff +0.60, tone -0.50 (wider tip chord = efficient + quieter tone). lean_mid +0.50 tone.
RECIPE: high mid-stagger + wide tip chord + low camber + fewest blades/lowest solidity meeting the
flow+pressure target; add solidity only to buy pressure, knowing it costs noise. Caveats: n=14,
screening CFD, relative noise, correlational. This is the transferable design-rule deliverable.**

**RULES-GUIDED OPTIMIZATION = BIG WIN (2026-08-27, runs/opt_guided, 18 trials, 3431s). Added
`guided` flag through search_space.suggest_params (GUIDED bounds dict) -> study.run_study ->
run_optimization.py --guided. GUIDED bounds: stagger_mid 32-48 (high), chord_tip 26-40 (wide),
max_camber 0-0.02 (low), n_blades 5-8 (fewer), chord_mid<=32 + lean_mid<=12 -> sol_mid ~0.34-0.64
(vs open ~0.8-1.4). RESULT: guided t5 (nB6: 86.6/80.9 CFM, 36.7% eff) PARETO-DOMINATES the ENTIRE
opt_v3 front — more flow than opt_v3's best-flow t22(78.3) AND higher eff (33.4). Guided front:
t5(86.6/80.9/36.7), t17(nB7,77.7/72.8/37.9), t12(nB6,69.5/63.4/38.9=best eff, beats opt_v3 38.5).
+10.6% peak airflow, whole front pushed out, with FEWER trials. Rules GENERALIZED. NOISE-scoring
guided finalists next (score_finalists_noise runs/opt_guided) to confirm quieter-at-matched-flow
(guided sol_mid is lower -> rules predict quieter). NOTE: absolute CFM optimistic (idealized
parametric geom in slip-ish sim; real printed part lower — see north star relative-gains framing).

GUIDED NOISE = MIXED/HONEST (runs/opt_guided/finalist_noise.json). Guided finalists: t17(77.7CFM,
37.9%,BPF25.6,dBA49.3), t5(86.6,36.7%,BPF22.4,dBA50.6), t12(69.5,38.9%,BPF18.7,dBA50.8). vs opt_v3
quietest t18(70.2,dBA47.2,thrust-0.036)/t14(dBA47.5). MATCHED-FLOW: guided t17(77.7) vs opt_v3
t22(78.3): guided +4.5% eff, LOWER BPF tone (25.6<26.7), but dBA_band +0.6 (49.3 vs 48.7) ~ a WASH
on total noise. Guided is ~1-2dB LOUDER on band-limited broadband overall. WHY: guided hits high
flow by LOADING each blade harder (high stagger+wide chord+fewer blades -> thrust -0.058..-0.067)
even though SOLIDITY is lower. Two competing noise mechanisms: solidity/overlap (guided lowered ->
tone dropped, rule HELD) vs per-blade loading (guided raised -> broadband up). The single-var rules
captured solidity but the flow-driven search re-loaded the blades. opt_v3's quiet corner (t14/t18)
was LOW-loading 5-blade (thrust -0.037) = quiet but low-flow; guided has no such corner b/c it
optimized flow+eff only (noise is finalist-only, not an objective). VERDICT: rules-guided = decisive
FLOW+EFF win (Pareto-dominates, +10.6% flow); NOISE ~wash at matched flow (tone better, broadband
worse). RULE REFINEMENT: quiet-at-fixed-flow needs BOTH low solidity AND spread loading (more
blades, lower per-blade load) — a 3-way tension the guided bounds didn't encode. NEXT (future):
noise as explicit objective (expensive) or a per-blade-loading cap in guided bounds.

**PER-BLADE-LOADING CAP BUILT + RUNNING (2026-08-27, runs/opt_loadcap). Closed the noise loop:
low solidity = each blade overloaded (high diffusion factor -> broadband noise), so cap loading via
a SOLIDITY FLOOR. Implementation: objectives.evaluate_candidate(min_sol_mid, min_sol_tip) gates
(pre-CFD, ~13s reject) designs below the floor via blade_solidity(). search_space now has a `space`
selector (open|guided|guided_lc) replacing the `guided` bool; GUIDED_LC = load-spreading bounds
(n_blades 7-11 MORE blades to spread load, chord_mid 22-40 wider, stagger_mid 28-44, chord_tip
26-40, camber 0-0.02). run_study(space=, min_sol_mid=, min_sol_tip=); run_optimization.py --space
guided_lc --loadcap (or --min-sol-mid/--min-sol-tip). RUNNING: --space guided_lc --min-sol-mid 0.85
--min-sol-tip 0.55, 24 trials (guided_lc sol_mid 0.65-1.33 mean0.90 vs guided 0.34-0.64 = load
spread). Verified gate fires. When done: compare opt_loadcap vs opt_guided at matched flow + noise-
score finalists -> did capping loading give QUIETER-at-high-flow? That's the closed-loop test.

LOADCAP RESULT = HONEST NEGATIVE / hypothesis FALSIFIED (runs/opt_loadcap, 2241s). Solidity floor
0.85/0.55 pushed NSGA-II to the HIGH-solidity extreme: both finalists nB=11, sol_mid 1.17-1.24.
NOISE: t1(72.8CFM,31.4%,dBA53.7), t16(62.4,37.4%,dBA53.6) = LOUDEST of all 3 runs AND lower flow +
eff. THREE-WAY dBA_band: open/optv3 MID-solidity(~0.8-1.4)=47.2-48.7 QUIETEST; guided LOW-solidity
(0.34-0.64)=49.3-50.8; loadcap HIGH-solidity(1.2)=53.6-53.7 LOUDEST. => SOLIDITY vs NOISE is
U-SHAPED/NON-MONOTONIC: moderate solidity is the quiet sweet spot; BOTH too-sparse (overloaded
blades->broadband) and too-dense (tonal+blockage) are louder. A solidity FLOOR alone overshoots to
the loud high-solidity extreme (a BAND floor+ceiling would be needed to target the sweet spot). ROOT
CAUSE: noise isn't an OPTIMIZER OBJECTIVE (finalist-only), so the search maximizes flow/eff within
the constraint and lands wherever that pushes (here: loud 11-blade). VERDICT: per-blade-loading cap
via solidity floor did NOT close the noise loop (falsified). REAL fixes: (1) make NOISE an explicit
finalist-gated objective so the search targets the quiet+high-flow corner directly; (2) the user's
[[fan-sim-uneven-spacing]] idea - attacks the TONAL term directly, decoupling it from solidity.
The open-search t14/t18 (mid-solidity, 5-blade, low-loading, ~47dBA, ~70CFM) remain the quietest
found - moderate everything. This is the loop doing its job: a clean falsification + U-shape insight.**
GPU TIER SCORECARD: free-delivery ~36 CFM (blade under-resolved at 1mm, vs OF 60); shut-off ~21 Pa
(-8%, vs published 22.9, RANS -43%); noise tonal+relative done, absolute pending CV-force/FW-H.**

**opt_v3 DONE (realistic geometry, validated pipeline): Pareto = trial22(nB7,78.3/73.1/33.4%),
trial5(73.5/69.1/36.2%), trial14(nB5,71.3/63.9/38.5%), trial18(70.2/64.7/38.3%). 14 feasible/10
gated. EFFICIENCY 33-38% = PHYSICALLY REALISTIC (first trustworthy optimization; earlier buggy
