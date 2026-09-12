<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

---
name: fan-sim-overnight-jobs
description: "Overnight CFD jobs launched 2026-08-30 night — review results next session"
metadata:
  type: project
---

**FOCUSED REAL-FRAME FAN RUN #2 LAUNCHED 2026-09-01 ~14:30 -> runs/opt_realframe2/ (log opt_realframe2_
0901_1430.log). run_optimization --fan-model a12x25 --space guided --mountable --trials 60. Same proven
frame-aware guided+mountable space as opt_realframe but 60 trials to FILL the buildable Pareto (the first
run found only 3). ~5h. REVIEW: compare its front vs opt_realframe (t22 53.9 CFM) — does more sampling
find better buildable designs? Fold winners into catalog.**

**PROP NOISE MODEL DONE + COMMITTED 2026-09-01 (clears the prop-graph backlog). fansim/propeller/noise.py
estimate_prop_noise(params,rpm,perf) = RELATIVE proxy (NOT calibrated dBA): tip-speed self-noise
(30*log10 tipspeed) + compressible rise past M0.4 + thrust-per-blade loading. Wired: prop optimizer
records rel_dba+tip_mach per design; cockpit prop tab GRAPH is now THRUST vs NOISE (color=eff g/W, click
to load); Analyze readout shows noise/tip-Mach/BPF; front list shows 🔉noise. 3 noise tests + 3 optimize
tests pass. commit 6-files-after-978156e. Absolute dBA would need CAA/FW-H or a bench mic (future).**

**PROP OPTIMA (all 4 sizes) DONE 2026-08-31 (inline, BEMT-instant, 2.5s) -> runs/prop_optima/prop_optima
.json. run_prop_study 400 trials each, power-capped (5in 700W, 3in 250W, 7in 500W, 2in 120W). Per size
the punchy (max-thrust) + efficient (max-g/W) ends: 5in 2136g@3.07 / 704g@5.00; 3in 758g@3.04 / 167g@5.77;
7in 2142g@4.32 / 906g@6.03; 2in 287g@3.21 / 48g@7.06. All want 4 blades + low pitch (hover-optimal, the
BEMT rediscovery). BACKLOG (user deferred, low tokens): PROP TAB still has NO scatter graph (only the
optimizer VList table) — add thrust-vs-eff scatter (colored by power); thrust-vs-NOISE needs a prop-noise
model first (BEMT has none). See [[fan-sim-status]] todos.**

**FEATURE MIN/MAX SWEEP LAUNCHED 2026-08-31 ~22:49 (CHAINED after opt_realframe -> no CPU contention).
scripts/run_feature_minmax.py (NEW) reads opt_realframe/pareto.json best design as base, OAT-sweeps each
lever (n_blades, stagger_mid/tip, chord_mid/tip, sweep_tip, lean_tip, camber, hub_radius) at its MIN and
MAX on the REAL a12x25 frame -> runs/feature_minmax/minmax.json + minmax_tornado.png (ranked CFM span per
lever). ~16 CFD evals @ base_cell 0.006/800it ~1h AFTER opt_realframe. log: feature_minmax_0831_2249.log
(waits on opt_realframe_0831_1504.log 'DONE'). Answers 'how big is each feature's effect' within the
buildable envelope. REVIEW: the tornado shows which levers move CFM most; fold into design-rules.**

**REAL-FRAME a12x25 OPTIMIZATION LAUNCHED 2026-08-31 ~15:05 -> runs/opt_realframe/ (log runs/opt_
realframe_0831_1504.log). run_optimization.py --fan-model a12x25 --space guided --mountable --trials 40.
First designs optimized WITH the REAL corrected a12x25 envelope (110mm tip / 25mm depth / 37.25mm hub) so
they fit the actual fan natively — vs all prior runs (opt_*, opt_overnight) built for the loose 119mm/
no-real-frame envelope (now generic_120). CONFIRMED running (docker CFD up, trials passing the gate).
~3h, 40 trials. CRITICAL FIX FIRST: the search space wasn't frame-aware — tip_radius defaulted to 56.5mm
(built dia ~116mm) so the FIRST attempt GATED 100% on 'tip dia > 110'. FIX: search_space.suggest_params
gained max_tip_radius= (ALWAYS samples tip_radius within [48, max] when given); study.run_study passes
max_tip_radius = spec.tip_dia_mm[1]/2 - 4.0 (the built dia bulges ~4mm past 2*tip_radius). Yield smoke:
guided+mountable+framecap 40 samples -> dia<=110 40/40 (was 0), depth<=25 25/40, BOTH 25/40 (~63% feasible,
depth gate filters the deepest). REVIEW next: pareto.json + pareto.png; compare best real-frame CFM/eff vs
the force-fitted old designs; fold into catalog + scorecard. This is THE clean answer to the 'old designs
don't fit the real frame' problem (vs hand-fitting with the 3 frame fitters, which costs aero).

Launched a detached overnight chain 2026-08-30 ~21:43 (user asleep, low on weekly tokens, asked to
'launch a few long jobs to graph interesting improvements'). Log: runs/overnight_0830_2142.log.
Two sequential CPU/Docker CFD jobs (sequential to avoid contention). CONFIRMED running (container up,
runs/tip_study/control created). REVIEW WHEN USER RETURNS — read the outputs, report the graphs.

**JOB 1: TIP-ROUND CFD STUDY (scripts/run_tip_study.py, NEW) -> runs/tip_study/**
Isolates the brand-new tip_round lever (added earlier 2026-08-30) on base opt_extended2_t36 (86 CFM,
nB7). 8 configs: control, round 0.2/0.4/0.6/0.8 (@start 0.80), round 0.5 early (start 0.65), round 0.6
cap (start 0.88), round 0.5 + winglet sweep 6. Depth leeway 20mm (measure aero not fit). ~40 min.
Outputs: tip_verdict.json + tip_study.png (tip_round vs CFM/eff curve). THE QUESTION: does rounding the
tip help airflow/eff (cut tip-vortex/leakage loss) or just cost blade area? First CFD test of the
feature. NOTE: RANS won't capture tip-vortex NOISE — a GPU/FluidX3D noise pass on the tip STLs is the
natural follow-up (GPU was idle; not launched to keep the overnight run robust).

**JOB 2: MOUNTABLE + WINGLET OPTIMIZATION (run_optimization.py --space guided --winglet --mountable
--trials 30) -> runs/opt_overnight/**
Fresh NSGA-II Pareto of BUILDABLE designs (hub>=27.2mm fits the 50mm Noctua motor) exploring the
winglet DOFs, on the guided (design-rules) space. ~2.5-3h. Outputs: pareto.json + scatter PNG + trial
STLs. Interest: a new mountable frontier that could beat the current mountable best (opt_mountable_t1
~85 CFM) now that winglets (~+4% flow) are in the search. Also benefits from the relaxed printability
gate (thin tips now allowed) so the optimizer has more room.

WHEN REVIEWING: read runs/overnight_0830_2142.log for the plain-English verdicts (both scripts print a
'best/direction' summary), then the two graphs. Fold winners into the catalog (build_catalog) + the
[[fan-sim-status]] scorecard. See [[fan-sim-cockpit-issues]] for the tip_round + printability context.
