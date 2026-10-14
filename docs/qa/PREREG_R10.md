# QA round 10 + 10b pre-registration (Tasks A, B, C), written before any round-10 data

Code under test: clean clone `/workspace/fansim/repo-r10`, master @ a09905a (contains the wrap merge ae3f1c4).
Nothing is committed to repo-r10; no fansim source is edited. QA hooks/monkeypatches are QA-side, in QA
processes, disclosed. All time limits use time.monotonic(). No CFD, Docker, OpenFOAM or outside STLs.
Task D (fuse guard after 27.1) is NOT run: the 27.1 patch is not in this bundle. Task E (near-stall) is optional,
unregistered, descriptive only if done.
Box note (known before data): MemAvailable ~3.1 GB of 16 GB (host-side), so memory gates will bind as in round 9.
Python: repo-r9 .venv (identical uv.lock) with PYTHONPATH=/workspace/fansim/repo-r10 (import path verified).

## Task A (Cursor round 10): print-part ID mark-spec on wrapped Stock v3
Geometry: `config/problems/a12x25_reference.yaml` (section_wrap cylinder), print-ready with the A12x25
MotorMount via `build_impeller_with_mount` (same as `export_print_ready`), exported at tol 0.02 / ang 0.1.
Hub-down: rear (motor) face on bed, +Z inlet up.
Measurement: the hub top plane z_top = max z of the hub (from `_hub_axial_range`, cross-checked with the mesh).
A polar grid (r 0..hub_radius+2 mm step 0.05 mm, theta step 0.25 deg) is ray-cast downward from above the part;
a cell is "flat face" iff the first hit is within 0.02 mm of z_top with face normal z > 0.999. Same on −Z: rays
upward from below, first hit within 0.02 mm of the bed face z_bed (mesh zmin of the hub face) with normal z < −0.999.
Reported: the flat annulus [r_in, r_out] per theta, min blade-root r at z_top (blade material in the hub top
plane), bore/fillet radius, and cup cavity radius/floor on −Z.
- M1 PASS iff on +Z there is an annulus of radial width >= 6 mm over a contiguous arc >= 25 deg in which every
  grid cell is flat face.
- M2 PASS iff cutting a dummy box recess 8 x 3.2 x 0.5 mm (length tangential, width radial, depth 0.5 mm into the
  face), centred in the preferred ring region, into the print-ready B-rep (QA script, CadQuery cut) gives:
  one solid (len(Solids()) == 1), STL watertight, 1 mesh body, volume change within 0.5 % of 8*3.2*0.5 mm3 of the
  expected removed volume (|dV - 12.8| <= 1.5 mm3), and the round-9 cup gauge (K7: floor 13.0 +/- 0.2 mm above
  the mount hub face, 20 grips, protrusion 0.70 +/- 0.15 mm) unchanged from the un-pocketed build.
- M3 PASS iff the recess footprint dilated by 1.0 mm lies entirely in flat-face cells (so >= 1 mm from blades,
  bore, fillet, edge) and its floor is >= 1.0 mm from the cup cavity (axially, where the footprint radius overlaps
  the cavity+grip radius; radially otherwise) and >= 1.0 mm from any grip pad.
- M4 (report, rule-checked): at 0.12 mm layers / 0.4 mm nozzle: min stroke >= 0.45 mm, min depth 0.36 mm
  (3 layers; 0.5 mm passes), 5 Crockford glyphs at 3.2 mm cap height (advance 0.75 x cap = 2.4 mm, so ~12 mm arc
  at the ring mid-radius), and whether a 12x12 Data Matrix at 0.5 mm/module (6 mm + 1-module quiet zone = 7 mm
  square) also fits on the same ring next to the text. Text is required; matrix optional.
- Fallback: if M1 fails, M2-M4 on the −Z annulus outside the cup cavity. If both fail: report and stop.
- Aero: pocket face area / inlet hub-disk area (pi * hub_radius^2); < 0.5 % => no CFD.

## Task B (10b): wrap confirmation on merged master, n = 40
Population: round-7 `stress/inputs.jsonl.gz`, sample_error rows excluded. Seed 10010 (`random.Random(10010)`),
disjoint groups drawn in this order: CTL all 5; featured 5 (S5_0167 forced in, 4 random; unshrouded, non-zero
bio-features, not S8/CTL); near-bounds S8 5; shrouded 5 (not S8/CTL); then from unshrouded unfeatured S1-S6:
notched 4, winglet 4, tip-round 4, uneven 4, plain 4. The population has no notched/winglet/tip-round/uneven rows,
so those options are SET on random bases with the round-9 recipe (disclosed): notched_tips=True; winglet_sweep
U(0,10), winglet_lean U(0,18) (one >= 2), winglet_span 0.85; tip_round U(0.3,1.0), tip_round_start 0.80;
spacing_spread U(0.15,0.6), spacing_seed randint(1,999).
Per design: P planar and P cylinder (order alternating by index), round-9 job_a logic (build_stl_isolated, 8gb tier,
P timeout 300 s, gate 3.0 GB waited 300 s); C (cup, cylinder) on the 5 CTL + 5 random eligible (seed 10010,
hub_radius >= mount_min_hub_radius), gate 3.5 GB waited 900 s else SKIPPED_MEM. One build at a time, setsid nohup,
resumable. Hooks: round-7 K12 faces hook plus a fuse_many hook logging every call (n tools, tier one-by-one flag,
mono s, len(Solids()) of the result).
Refused (hang): a cylinder design that `validate_blade_params` refuses with the hang message is "refused (hang)",
counted, not a W1 failure (checked up-front with blade_hang_below_hub_mm and again from the build error).
- W1 as round 9 (cylinder P OK, watertight, 1 body, V > 0, 0 degenerate, zmin >= hub_face - 0.05, rmax rule),
  excluding refused (hang). S5_0167 OOM, if it recurs, is logged as the known W1 miss (counted as a FAIL, flagged).
- W2 |V_cyl/V_planar - 1| <= 5 %.  W3 mono_cyl <= 2 x mono_planar or delta <= 5 s; suspect_suspend excluded.
- W4 every completed C build passes K7.  W5 0 CONCLUSIVE-wrong cylinder P builds.
- W6 PASS iff every non-refused cylinder P build that completes is one solid (last hub+blades fuse_many result and
  the ring fuse result, if any, have len(Solids()) == 1) and its STL is watertight with 1 body, AND no non-refused
  cylinder build fails with "did not join into one solid". Fallback rate = builds whose hub+blades fuse ran twice
  (all-at-once then one-by-one) / builds; reported, no threshold.

## Task C (10b): hang limit and correction
C.1 Designed hang `blade_hang_below_hub_mm` (section_wrap forced "cylinder", clip_below_hub as stored) on the round-9
B.3 population (200, seed 9011, same filter) plus 200 fresh: seed 10012 from the remaining sample_error-free rows
(shrouded allowed). Reported: distribution, share > 0, share > 2.0 mm (refused), and on the round-9 200 the ratio to
my round-9 realised-loft hang. Also: `validate_blade_params` refuses iff designed hang > 2.0 (must agree 400/400).
C.2 Every allowed (validate passes) design with designed hang > 0: 2-blade build_impeller (shipped path, so the
correction applies), measure_sections at each station radius (capped 0.99). Readable station = station frac not None
in `_station_measure_fracs` and n_blades > 0. Reference ("analytic", independent of the correction): slider chord;
slider stagger; slider camber + bias, where bias = `_measure_loop` camber of the design's OWN family 2D section
(`section_loop_2d(family, ...)` with its le/te radius as the builder passes them) wrapped on R = 1e4 mm minus the
slider camber (round-9 method, family-aware).
- C2 PASS iff at every readable station of every such design: |chord_m/chord_p - 1| <= 3 %, |camber gap net| <= 0.005,
  |stagger_m - stagger_p| <= 1.5 deg. Reported also split by clip-reached (unclipped vs clipped lone blade, round-9
  criterion) and the count of stations the correction touched.
C.3 `objectives.evaluate_candidate` on two refused designs, CFD stubbed as in tests/test_objectives_orientation.py:
PASS iff result.feasible is False, the reason carries the hang message, and no mesh/CFD stub is called. Message
judged plain (says mm, the limit, and what to change) by reading.
C.4 Misjudgements (descriptive): refused designs whose lowest designed point is at r < hub_radius (hub-embedded
root) — checked by recording the r of the min-z section point; allowed designs with any C2 failure.
