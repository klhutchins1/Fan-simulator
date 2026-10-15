# QA round 12 pre-registration (Tasks A, B, C, D, E), written before any round-12 data

Code under test: master @ 143d5a8 (contains 3b30b9e print-id, cec573a brief, 27.1 fuse guard). Runs use a
separate local clone `/workspace/fansim/qa/run_r12` of `/workspace/fansim/repo-r13` at 143d5a8, so exports/
and validation/prints/index.jsonl are written there, never into repo-r13. Nothing committed to repo-r13; no
fansim source edited. Python: repo-r9 .venv with PYTHONPATH=<run clone> (import path asserted). QA hooks are
sitecustomize monkeypatches in QA processes, disclosed. Timing: time.monotonic(). No CFD/Docker/OpenFOAM,
no loft/glyph work, no outside STLs. Round 11 is skipped (superseded); 27.1.patch is NOT applied.
FANSIM_MEMORY_TIER=8gb for builds; FANSIM_FUSE_GUARD is never set. One heavy build at a time.

## Task A: QA-34 strip check
Control: S5_0184 from repo-r10 handoff/2026-10-13_from-qa-10/data/b_sample.jsonl (flat + features as stored).
New: from repo-r7 stress/inputs.jsonl.gz (sample_error rows dropped, file order), pool = stratum S5,
shroud_thick_mm == 0, any feature value > 0, excluding S5_0184, S5_0228, S5_0112; draw
random.Random(11013).sample(pool, 2). No top-up.
Each: section_wrap forced "cylinder", build_stl_isolated(preview=False, timeout=900), 8gb tier, serial.
Error text containing "hang" -> "refused (hang)" (not FAIL, not replaced). B-rep: r10 hook_b QA_FUSE_LOG wraps
fuse_many and logs len(Solids()); the last logged call's solid count is "B-rep solids".
Measured on the file the builder wrote (trimesh): watertight, n_bodies = len(split(only_watertight=False)),
degenerate = count(area_faces < 1e-9).
- F0 PASS iff S5_0184: watertight and n_bodies == 1 and degenerate == 0 and B-rep solids == 1.
  If F0 FAIL: stop A, keep the STL gz.
- F1 PASS iff every new build that is OK (not hang-refused) meets the same STL criteria (watertight, 1 body,
  0 degenerate). If both new builds are hang-refused, F1 = INCONCLUSIVE (0 OK).
- F2 report only (faces, volume, build time, B-rep solids, features).

## Task B: 27.1 remaining growth
Sample: reuse round-9 Task E IDs exactly (same selection code as repo-r9 docs/qa/shroud_memory/run_e.py:
12 shrouded S7 in height bins [0.3,.55),[.55,.8),[.8,1.01) x 4 by n_blades, each + unshrouded twin
(shroud_thick_mm=0), + 4 unshrouded controls seed 9012) = 28 builds. Serial P builds, build_stl_isolated
(preview=False, timeout 900), hook handoff/2026-10-13_to-qa-11/hook_c11 (FUSE_CALL_LOG). Gate as r9:
MemAvailable >= 1.1*(3.0 shrouded / 2.5 else)+0.5 GB, wait <= 600 s monotonic; if unmet build anyway and flag.
Per OK build: take the first "call" event and the "exit" event of the same pid.
remaining_bytes = (VmHWM_exit - VmRSS_call) * 1024.
ask_bytes = 1.15 * fuse_remaining_estimate_gb(n_faces, shrouded=, n_blade_faces=) * 1024**3 using the logged
n_faces/shrouded/n_blade_faces (resources.GB = 1024**3).
- B PASS iff remaining <= ask on all OK builds (twins kept). Builds without a call+exit pair are reported as
  "no pair" and excluded from the ratio but listed; non-OK builds listed with error.
- Report remaining/ask per build, and whether n_blade_faces == n_faces - 4 on shrouded calls.

## Task C: 28.2 print-id on Stock Export
Path: headless cockpit (CockpitCtx + fan_tab.setup_fan_tab as tests/test_fan_tab_setup_smoke.py / r7 harness)
on a real asyncio loop; Stock v3 (A12x25, cup) selected as at cold open; assess_material left at PETG;
the real export_stl_current handler and the real isolated export worker (no fakes). No recess, no glyphs.
- P0 PASS iff STL name matches ^{pid}_{name}_{YYYYmmdd-HHMMSS}.stl$ with pid 5 chars, first 4 in
  0123456789ABCDEFGHJKMNPQRSTVWXYZ, 5th in that set + *~$=U, and print_id.verify_print_id(pid) is True.
- P1 PASS iff README (.md sidecar) first non-empty line contains pid and README contains "Sharpie".
- P2 PASS iff *_print_fit.json has keys print_id (== pid), section_wrap, recipe_hash, git, material (non-empty).
- P3 PASS iff validation/prints/index.jsonl line count increased by exactly 1 and that line has print_id == pid
  and stl == the exported path (string equal, or same resolved path).
- P4 PASS iff STL watertight and n_bodies == 1, and K7 (r10 cup_measure, hub face from
  mount_hub_params(a12x25_reference.yaml) as r10 a_mark.py) gives grip_count == 20,
  |floor_above_hub_face - 12.985| <= 0.05 mm and |grip_protrude_mm - 0.696| <= 0.05 mm (r10 Task A base).

## Task D: PLA+ material picker (report, no PASS needed)
Same headless cockpit, new session: note the default chip value, set state.assess_material = "PLA+" (what the
v_model writes), then without switching back record:
M0 state.assess_material after each action; M1 real Preview (preview handler, real build) fit-line grams,
compared to vol*density for PETG and PLA+ (materials.py densities); M2 one real Stock Export with PLA+ selected:
README material + nozzle/bed lines, print_fit.json material, index line material; M3 Assess handler with
evaluate_candidate_isolated faked (r7 harness pattern, no CFD): material kwarg the run received and saved
extra["material"]; M4 code read of fan_optimize.py --material. Also record active_spec().material.
Verdict per surface: "follows PLA+" or "says PETG".

## Task E: UI regression tests (proposal, run only if A-D done)
2-4 pytest files under handoff/2026-10-14_from-qa-12/tests/, headless, no CFD, no 3-D. One must assert Export
README material follows assess_material. Reported: pass/fail of each on 143d5a8; the material test is
expected to FAIL on HEAD if D shows the README says PETG (that FAIL is the intended finding, not a test bug).
