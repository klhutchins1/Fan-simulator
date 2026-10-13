# QA round 9 pre-registration (Tasks A, B, C, D), written before any round-9 data

Code under test: repo-r9 clean clone, branch `cylinder-sections` @ 7b02bed (origin/cylinder-sections;
master 2ce35b6). Task E runs on master 2ce35b6 (a detached worktree, no commits). No fansim source is
edited; any monkeypatch is QA-side, in QA processes, and disclosed. All time limits use time.monotonic().
Box note (known before data): MemAvailable is ~3.3 GB of 16 GB at the start (host-side usage), so the
round-7 memory gates will bind; B/C/D/E processes wait for MemAvailable >= 2.5 GB before each build.

## Task A: robustness of the wrapped builder
Population: round-7 `stress/inputs.jsonl.gz` (2341 rows), rows with `sample_error` excluded.
Sample, seed 9009 (`random.Random(9009)`), 150 designs, disjoint groups, drawn in this order:
- CTL: all 5.
- S8 (near bounds): 10 random.
- shrouded: 15 random among shroud_thick_mm > 0 (not S8/CTL).
- featured: 15 random among non-zero bio-features, unshrouded (not S8/CTL).
- From the remaining unshrouded, unfeatured S1-S6 rows: 15 notched, 15 winglet, 15 tip-round,
  10 uneven spacing, then 50 plain, all random. The population has NO notched / winglet / tip-round /
  uneven rows, so those options are SET on random base designs (disclosed):
  notched: `notched_tips=True` (fixed recipe); winglet: winglet_sweep U(0,10) mm, winglet_lean U(0,18) deg,
  winglet_span 0.85 (search-space ranges, at least one of the two >= 2); tip round: tip_round U(0.3,1.0),
  tip_round_start 0.80; uneven: spacing_spread U(0.15,0.6), spacing_seed randint(1,999).
- Strata S1-S7 must each appear; if one is missing, the plain group replaces its first draws to cover it.
Per design: P build with flat `section_wrap="planar"` and P build with `"cylinder"`, order alternating by
sample index (even: planar first). C (cup) build with cylinder for 30 designs: the 5 CTL + 25 random
(seed 9009) whose hub_radius >= mount_min_hub_radius; if fewer are eligible, as many as there are.
Runner: round-7 design_job logic (build_stl_isolated, 8gb tier, P timeout 300 s, C 600 s), one build at a
time, round-7 K12 faces hook, memory gate (P waits up to 300 s for 3.0 GB then builds; C needs 6.0 GB
waited 600 s, else SKIPPED_MEM and reported), started with setsid nohup, resumable.
Rules (cylinder builds; planar is the control):
- W1 PASS iff every design whose planar P build is OK (or REJECTED identically) has a cylinder P build that
  is OK and: watertight, 1 body, volume > 0, 0 degenerate faces; zmin >= hub_face - 0.05 mm; rmax <=
  tip + TIP_TRIM_TOL_MM (unshrouded) or |rmax - (open_tip_rmax + ring)| <= 0.1 mm (shrouded).
  A cylinder build that fails/rejects where planar succeeds is a W1 FAIL. Planar-side failures are
  reported, not scored.
- W2 PASS iff |V_cyl / V_planar - 1| <= 5 % on every design with both OK.
- W3 PASS iff mono_cyl <= 2 x mono_planar on every design with both OK, with an absolute allowance:
  a design also passes if mono_cyl - mono_planar <= 5 s (worker start-up noise dominates sub-10 s builds).
  Builds flagged suspect_suspend (wall - mono > 60 s) are excluded and counted. Also reported: the
  strict ratio-only count.
- W4 PASS iff every completed C build passes round-7 K7 (floor 13.0 +/- 0.2 mm above the mount hub face,
  20 grips, protrusion 0.70 +/- 0.15 mm). SKIPPED_MEM / N/A are counted, not scored.
- W5 PASS iff 0 cylinder P builds are CONCLUSIVE-wrong (prove_direction CONCLUSIVE and
  builder_direction_refusal(pr, design camber) not None, i.e. round-7 K5 FAIL). INCONCLUSIVE counts and
  median camber of their sections, cylinder vs planar, are logged (no rule).

## Task B: built vs sliders on wrapped builds
Designs (cylinder wrap, chord_basis as stored / shipped default "measured" where absent): Stock v3
(`config/problems/a12x25_reference.yaml`), lt120 (`docs/qa/benchmarks/lt120/fansim_params.json`, wrap set
to cylinder), t9000, t9002, t9003, t9005 (flats from `handoff/2026-10-09_to-qa-2/cfd_designs.csv`, no wrap
key => cylinder), and 20 stress designs: random (seed 9010) from unshrouded, sample_error-free rows.
Method: round-8 run_d (2-blade full build_impeller, measure_sections at each station radius capped 0.99,
analytic NACA bias for camber). In addition each design's lone chord-realised blade is built twice:
unclipped and clipped at the hub face (clip_blade_below), both untrimmed; a station is "clip-reached" iff
the unclipped minus clipped chord at that radius exceeds 0.1 mm (or the clipped section is missing).
Rule (as round 8): a station is MATERIAL if |chord_m/chord_p - 1| > 3 % or |camber_m - camber_p - bias| >
0.005; reported at chord/r >= 0.4 (the round-8 rule) and at all stations.
Prediction to test (Claude's V1): at non-clip-reached stations 0 material. Verdict "V1 confirmed" iff 0
material at non-clip-reached stations with chord/r >= 0.4 across all 26 designs.
Population (B.3, no rule): over 200 random unshrouded stress designs (seed 9011), lone blade unclipped
(chord-realised, cylinder), hang depth = hub_face_z - zmin (mm), fraction with hang > 0.05 mm, and count
of clip-reached stations by the chord-difference criterion (on the first 60 of those 200 if time-bound;
disclosed).

## Task C: Stock surface fit (prototype; shipped recipe untouched)
Start: v3 wrapped recipe. Variables: per-station stagger, chord, camber, and LE/TE position terms
(sweep, skew, lean_deg) always on; up to 2 extra interior stations. Objective: mean |signed distance|
from the build to `validation/reference/a12x25_impeller.stl` with `scripts/stock_surface_distance.py`'s
alignment (rotation over one pitch + axial shift), 6000 points, seed 1, blade surface only.
Targets (all three needed for PASS), evaluated by the unchanged surface-distance method on the final
proposal: (T1) mean <= 0.41 mm; (T2) mean over r/R 0.8-1.0 <= 0.26 mm; (T3) V2's section tolerances
via `scripts/fit_recipe_to_stl.py`'s measurement (stagger 1.5 deg, chord 3 %, camber 0.005, t/c 10 %
at r/R 0.50-0.99). Planar v2 and wrapped v3 are re-measured on this box as the baseline.
Output: proposal YAML in docs/qa/stock_fit/; no CFD.

## Task D: external STLs, radial-led rule (27.2b)
Readers: cylinder = `fansim.audit.direction.prove_direction`; radial = round-8 `stacking_cut.
prove_direction_stacking(mode="radial")`, unchanged. Rule: ACCEPT the radial reading iff radial is
CONCLUSIVE and the cylinder is INCONCLUSIVE or agrees (same omega, pump, chirality); otherwise ASK.
Sample: >= 8 axial impellers/fans from Printables/Thingiverse (or similar) whose licence is CC-BY or CC0
(any version), mesh loadable as STL, plus both repo references (a12x25_impeller.stl, fan01_rotor.stl),
and the y-mirror of every part. Outside files stay in /tmp/qa9_ext (never in a repo); URL + licence noted.
Ground truth is recorded per part BEFORE the readers run, from the page's stated spin/airflow, else from
blade shape (tip-lead sign as round 8 `tip_lead_sign`, and visual LE/pressure side); parts with no
determinable truth are reported as coverage-only. Mirror truth = (-omega, pump, -chi).
Rule: PASS iff 0 ACCEPTED readings are wrong (originals + mirrors). Coverage = accepted / total
(reported, no threshold). Parts whose mesh the readers can't process count as ASK.
