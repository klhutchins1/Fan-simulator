# QA round 8 pre-registration: Tasks B, C, D (one commit, before any B/C/D data)

Tested code: master `f86df9a` (clean clone `/workspace/fansim/repo-r8`). Written 2026-10-12 before any
B/C/D build, measurement or reading. Task A (harness re-run) needs no prereg and was run first.
Thresholds are the brief's; only wording is adjusted, with reasons in brackets.

## Task B: radial-plane direction cut, confirmation

### Readers (frozen)
- cylinder = `fansim.audit.direction.prove_direction` at `f86df9a`, unchanged.
- radial = `prove_direction_stacking(mesh, mode="radial")` from round 7
  (`handoff/2026-10-11_from-qa-7/scripts/stacking_cut.py`), byte-for-byte unchanged. No tuning.

### Sample (fixed seed 20261012, `random.Random(20261012)`)
Source: round-7 stress `inputs.jsonl` (2341 rows). Excluded: every id among round 7's 67 Task-F parts,
every one of the 65 designs built in the round-7 stress run, screen_r3 9601-9630, rows with sample_error.
Cell from the flat dict (|camber| = max |camber_root/mid/tip/max_camber|, lean = |lean_tip|):
- S3cell: 0.02 <= |camber| < 0.04 and lean >= 30 -> draw 22 (of which >= 2 featured);
- flatlean: |camber| < 0.02 and lean >= 20 -> draw 16 (>= 1 featured);
- ordinary: |camber| >= 0.04 -> draw 26, round-robin over strata S1..S8 (>= 2 featured).
Featured = any tubercle/serration/dimple amplitude > 0; >= 5 featured in total.
Draw: shuffle each cell with the seed, take featured quota first, then fill in order.
After the build each part is scored in the cell given by its **built** design camber
(max |station max_camber| from `blade_from_flat`, as in round 7); cell moves are reported.
Named extras (reported, not counted in R1/R2/R5 sample sizes but counted in R3/R6): S3_0014 (the
round-7 failure).
Flipped parts: 5 parts drawn (seed) from the ordinary draw, rebuilt with camber_root/mid/tip and
max_camber = -0.03, bypassing `validate_blade_params` in a QA-side wrapper only (no source edit).
References: `validation/reference/a12x25_impeller.stl`, `validation/reference/fan01/fan01_rotor.stl`.
Every part (incl. references and flipped) is also read mirrored (y -> -y, faces inverted).
Builds: 2 blades (`n_blades=2, blade_angles_deg=None`), as round 7. Disclosed in the report.

### Expected answers
- builder part, design camber c >= 0: (omega +1, pump -1, chi -1); c < 0 (flipped): (-1, +1, -1);
- mirror of any part: (-omega, pump, -chi);
- a12x25 reference: chi -1, omega = `tip_lead_sign`, pump = -omega; FAN-01: (+1, +1, +1).
A reading is OK (CONCLUSIVE and equal), WRONG (CONCLUSIVE, not equal), or INC.

### Rules
- R1: radial gives 0 WRONG over all originals and mirrors (incl. references, flipped, extras).
- R2: radial is OK on >= 95 % of originals with |design camber| >= 0.02 (incl. flipped, excl. references).
- R3: for every part whose radial reading is CONCLUSIVE, its mirror's radial reading is CONCLUSIVE with
  opposite chirality. [wording: "flips" = CONCLUSIVE and opposite sign]
- R4: both references radial OK.
- R5 (external rule): CONCLUSIVE iff cylinder and radial are both CONCLUSIVE and give the same
  (omega, pump, chi); else "ask for the spin". Pass iff 0 WRONG (originals+mirrors) and OK on >= 90 %
  of originals with |design camber| >= 0.02.
- R6 (builder rule): refuse iff (a) cylinder or radial is CONCLUSIVE with chi != -1, or (b) both are
  CONCLUSIVE and both (omega, pump) differ from the split implied by sign(design camber). Pass iff
  it refuses none of the S3cell parts (built cell) nor S3_0014, refuses every mirror of a builder part,
  and refuses all 5 flipped parts.
  R6b (secondary, reported only): the same with the existing |camber| >= 0.02 trust gate on (b).

## Task C: fuse memory at the call (QA-27)
- Population: 22 designs from the round-7 stress population whose round-7 fuse face counts span
  9.9k-71k: S1_0018 S7_0015 S2_0014 S7_0017 S8_0002 S2_0016 S6_0018 S1_0020 S7_0013 S6_0015 CTL_0001
  S6_0019 S1_0016 S6_0017 S6_0016 S5_0016 S5_0017 S5_0007 S5_0014 S5_0019 S5_0015 S3_0019 (6 featured:
  S5_*). Full blade count, P build (`build_stl_isolated`, preview=False, no mount),
  FANSIM_MEMORY_TIER=8gb, one at a time.
- Hook (sitecustomize, QA-side only): at each `check_fuse_memory(n_faces)` call record n_faces, the
  worker's VmRSS, VmHWM and MemAvailable and time.monotonic(); before the worker exits (wrapping os._exit
  and atexit) record its VmHWM.
- Safety (not a result rule): a build starts only if MemAvailable >= 1.1 x (round-7 peak_mb for that
  design) + 0.5 GB, waiting at most 600 s monotonic; otherwise it is SKIPPED and reported. Timeout 900 s
  monotonic per build. All limits time.monotonic().
- increment = VmHWM_exit - VmRSS_at_call. est = fuse_peak_estimate_gb(n_faces).
- Comparison (the only rule): the guard is safe for a build iff increment <= 1.15 x est - RSS_at_call.
  "Guard safe" overall iff it holds for every built design. Also reported: least-squares fits of
  increment vs faces and VmHWM vs faces, and per build whether MemAvailable_at_call >= increment.

## Task D: built blade vs its numbers
- Designs: Stock (`stock_a12x25_params()`), lt120 (`docs/qa/benchmarks/lt120/fansim_params.json`),
  the first 5 non-stock rows of `handoff/2026-10-09_to-qa-2/cfd_designs.csv` in file order.
- Each built with chord_basis "measured" and "loft" (everything else equal).
- At every station radius of the design: param vs cylinder-cut chord, stagger, max camber, t/c, using
  `fansim.validation.section_compare.measure_sections` (or its cylinder-cut primitive) on the built
  mesh, same blade count as the design (2-blade allowed if memory requires; disclosed).
- Estimator bias for camber: measured once by running the same estimator on an analytic NACA 44xx
  cylinder-wrapped section (expected 0.034-0.038 read for 0.04); bias(c) applied as the measured offset.
- Rule: the gap is MATERIAL if, at any station with chord/r >= 0.4, |chord_meas/chord_param - 1| > 3 %
  or |camber_meas - camber_param - bias| > 0.005.
- Also reported (no rule): gap vs chord/r table, and whether "measured" differs from "loft".

## Task E: not done this round unless time remains; if done, a separate later prereg commit.
