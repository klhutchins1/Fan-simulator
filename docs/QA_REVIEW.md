# QA Review — Fan Simulator

**Not the product backlog.** Live open work is [`docs/roadmap.md`](roadmap.md). This file is the
numbered QA bug ledger (QA-n / UI-n) and round notes. Adopt a bug into a roadmap item when we
take it; do not keep a second TODO list here.

Running QA list maintained by Fan Sim QA (Kimball's QA bot). The QA bot only edits this file; it never edits code.

**From round 28 (Kimball, 2026-11-09): the QA bot no longer edits this file or the board.** It writes its round as one new
file, `docs/qa/rounds/r<NN>.md` (results, plus any new or changed tracker rows written out in full), with notes and
patches under `docs/qa/` as before. The lead copies the rows into the tracker. Reason: the bot works on a delivered
copy, so its edits to shared files had to be hand-merged every round. Rounds are for independent re-derivations and
bug hunts; re-check a fix only when the bug was HIGH.

## How to use this file (for Claude / whoever fixes things)
- Each item has an ID (`QA-n` for code/math, `UI-n` for cockpit UI). Keep IDs stable; never renumber.
- When you fix something, change its **Status** to `fixed (pending QA)` and add the commit hash. The QA bot re-tests and marks it `verified` or `reopened`.
- Use `wontfix` or `by design` with a one-line reason if you disagree.
- Known recovery gaps from README_RECOVERY.md / RECOVERY_TODO.md are not counted as bugs.
- Paths like `/workspace/fansim/...` and `qa/...` are on the QA bot's machine (screenshots, scratch scripts); ask if you need one.

## ▶ Next round for the QA bot: round 27 (queued by Cursor 2026-11-09). Delivered as `handoff/2026-11-09_to-qa-27/`

Round 26 and the 2026-11-08/09 self-initiated packs (QA-68, G2, ui-hunt-1, G3, leads 23–30) are **DONE**; thank you. Build: master at the commit that added this folder. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize run. Pre-register A and B before data. Do not re-prove G2 or G3 claims C22/C24/C25.

| # | task | board |
|---|---|---|
| A | **QA-57 closeout.** On this master, Volute Assess copy (`volute_tab.py` Assess lines and result readout) must carry "ranking only, unvalidated (CFD not yet converged)", not only Optimize. If Cursor has applied `docs/qa/patches/g3-QA57-volute-assess-label.patch`, verify it (red check + tests). If not, confirm the gap is still there. Mixed side stays **verified / not re-tested**. | QA-57, R1.10 G3 |
| B | **UI-39 and UI-40.** Sweep steps must refuse empty / non-int / out of 2–12 with a visible message, never queue a huge CFD sweep. Optimize Trials must show "2–40" and refuse out-of-range instead of silent clamp. Apply/verify `docs/qa/patches/ui-hunt-1-UI39-UI40-steps-trials.patch` if landed; else re-probe. Do not click Run. | UI-39, UI-40 |
| C | **QA-70.** Expert noise-hint row must still show when a run has the tip-speed+CFM hint but no turbulence SWL. Patch `docs/qa/patches/ui-hunt-1-QA70-noise-hint-row.patch`. G2 claims stay **verified / not re-tested**. | QA-70, R1.10 G2 |
| D | **G4 if it is on this master.** Dropped ~2× / ~0.6× / ~3–5 %; Assess "two CFD solves … 20–40 min"; README Known limits list still has R1.4's "about 5 % less airflow than the real A12x25". If G4 is not merged, say so and skip. QA-69 (`design-rules.md` "Noise dB(A) (min)") is G4's. | R1.10 G4, QA-58, QA-69 |

Notes to `docs/qa/notes/r27-*.md`, plus a "Round 27" section below.

## Tested build
- Source: copy of `T:\Projects\Fan Simulator` working tree, 2026-10-08 (no `.git`, so no commit hash). Linux, Python 3.12, no Docker/OpenFOAM/CFD.
- **Re-test 2026-10-09:** `master` @ `961f9534674c375bbc0a730a34979d859a1be05d` (commit date 2026-10-08 21:56 MDT), cloned from `fansim_master.bundle`; `uv sync --extra dev`; Linux, no Docker/OpenFOAM/CFD. Code items re-run with the original repros (`qa/retest_code.py`); UI items checked headlessly (curl, wslink websocket client, code + regression tests). "needs browser pass" = fix claimed in a commit, not yet confirmed by clicking.
- **Re-test 2026-10-09 (2):** branch `qa-fixes-2026-10-09` @ `d781894` (from `fansim_2026-10-09.bundle`; forks from 961f953; `station-mapping-23-35` not tested). Bundle `master` is `6b7f3bf`, not the `6f31514` named in the brief: 6f31514 is an ancestor of master (6 docs-only commits on top, docs/handoff + one `.gitignore` line) and is NOT an ancestor of the branch. Fix tests: 59 passed, 1 skipped, 1 xfailed (`test_ws_guard`, `test_tip_trim`, `test_build_progress`, `test_prop_polar`, `test_blade_validation`, `audit/test_prop_bemt_audit`, `test_volute_export_rows`). The full fast suite was not re-run on the branch. Websocket checks: `handoff/2026-10-09_from-qa/ws/`, run on 961f953 and d781894 side by side. Browser steps still to do: `docs/qa/browser_checklist_2026-10-09.md`.

- **Re-test 2026-10-09 (3):** `master` @ `e48a32d` (merge of `qa-fixes-2026-10-09`; clone `/workspace/fansim/repo-r3`), Linux, no CFD. Full fast suite run in one process (see below). Browser rows for UI-4/9/20/23: `docs/qa/browser_checklist_2026-10-09_r3.md` (results pending).
- **Re-test 2026-10-09 (4):** `master` @ `f238f54` (clean clone `/workspace/fansim/repo-r4`, `uv sync --extra dev`), Linux, no CFD. Slow suite, cup-fuse memory, export/STL correctness, docs audit; browser rows in `docs/qa/browser_checklist_2026-10-09_r4.md`. Requests 1–3 (QA-4 cross-check) on `axial-force-bem` @ `5396796` in a separate worktree.

## Tracker
| ID | Sev | Area | Summary | Status |
|---|---|---|---|---|
| QA-1 | HIGH | Geometry/Stock | 7-station Stock A12x25 recipe cut to 3 stations by `blade_to_flat`/`stock_blade_flat` | verified `20aed3e` |
| QA-2 | MED | Geometry | No validation for axial/mixed-flow inputs (hub>tip, neg chord, 0 blades, NaN) | verified `e5ed908` (validation at build; `BladeParams` itself still accepts bad values) |
| QA-3 | MED | BEM | Free delivery falls back to sweep max when pressure never > 0 (0 blades = 129 CFM) | verified `e5ed908` |
| QA-4 | MED | BEM/polars | AoA clamped to table edges; paddles/reversed blades score as good fans | not yet fixed: patch not applied on d781894 (`fan_bem.py` unchanged). QA clone with `docs/qa/patches/axial-force-pressure.diff` passes pre-registered rules a, b, b2, d (Stock 59.8 CFM / 22.08 Pa; paddle 14.0 CFM, η 0.009; reversed −22.5 / −19.2 Pa; top-5 66.7–68.5 CFM; default `euler` byte-identical); rule c pending tonight's `cfd_designs.csv`. Criteria sha256 `17e1e9c4…f7e2`. **Round 3 (2026-10-09, master e48a32d):** the patch is still not on master. Rule (c) **PASSES** on 16 CFD designs: Spearman ρ axial 0.809 vs euler 0.827, each with 2/3 of the CFD top 3. The new pre-registered check (prereg commit `5913a74` on `prereg/round3`, criteria sha256 `66db0018…bdf75e`), "all 5 BEM-screen picks above Stock in axial mode", **FAILS**: only 1/5 is above Stock (9501, 1.056). Cause: the BEM over-rates Stock's efficiency (29.4 % vs CFD 17.9 %). Still open **Round 4 (2026-10-09, `axial-force-bem` @ `5396796`, not merged; prereg `docs/qa/notes/r4-prereg-axial-crosscheck-eff-audit.md`, sha256 `1252f73f…acaf`):** Claude's re-implementation matches the QA model exactly on 6,601 cases (0 differences, ρ 1.000, 0 guard/feasibility disagreements). The guard refuses nothing real and refuses every full paddle and wrong-hand blade; hand-edited partial paddles / wrong-hand spans get through (closest: 80° paddle at 8.9 % peak η). Candidate extra check: euler/axial free-CFM > 1.3 (not checked against CFD). Notes: `docs/qa/notes/r4-axial-crosscheck-and-guard.md`. Still open (guard gap; see also QA-13) |
| QA-5 | MED | Audit/tests | `motor_side()` returns None with 5 mm centre bore (2 failing tests) | verified `e5ed908` |
| QA-6 | LOW | CI | Ruff F811 in `fansim/cockpit/fan_viz.py:46` fails "Ruff critical" | verified `5f5b29b` |
| QA-7 | LOW/MED | Tests | `audit_archetype_direction_cfd.py` not registered with rotor-orientation guard | verified `97b9258` |
| QA-8 | LOW | Math | `camber_from_turning_rad` ~2x circular-arc camber | verified `e5ed908` |
| QA-9 | LOW | Math | Two different "solidity" definitions; docstring mismatch | verified `e5ed908`/`ca1f8c9` (by design, docstrings explain both) |
| QA-10 | LOW | Docs | README quickstart test command needs `--extra dev` | verified `5f5b29b` |
| UI-1 | HIGH | Volute | Export STLs fails: `TypeError: object of type 'PosixPath' has no len()` (verify on Windows) | verified in browser 2026-10-09 (Volute Export STLs succeeded, `ca1f8c9`) |
| UI-2 | MED | Fan | Unedited Reference shows "Edited since assessment" on load | verified in browser 2026-10-09 (`1e344ec`) |
| UI-3 | MED | Fan | Reset leaves 3-D viewer empty | verified in browser 2026-10-09 (`d4e9010`) |
| UI-4 | MED | Fan/CROR | Preview ~65-70 s, progress bar jumps/looks stuck | fixed (pending QA, r5) `1453c4f`: per-cockpit progress file cleared before each Preview (no 75 % pin); readouts off the loop (worst stall 0.82 s). Earlier: fixed (pending QA) `5b342ba` (r4): your diagnosis was right on all points. The parent writes stage 1 'loading CAD kernel' before spawning (the `python -m` package import loads CadQuery before the worker's own code). Stages are now the four that take time: kernel / preparing design (chord fit) / build / write. Ticker 0.5 s. Measured fast path: stage 1 at 0.05 s, build 3.0–5.6 s, done 5.6 s. The cup-path stall + lost bar value is tracked as roadmap 23.55 (7.6 GB fuse, memory pressure). Earlier: **reopened (browser r3, master e48a32d, 2026-10-09).** B1a (motor cup off): 'starting build process' 2 % for 0–2.2 s, then straight to 'stage 4/5 · lofting blades + hub' 60 % at 3.4 s, done ~6.8 s; stages 1, 2, 3 and 5 never shown; never backwards, no freeze. B1b (cup on): 2 % → 'stage 4/5 · building + carving motor cup' 60 % from 3.2 s to ~53 s → 'stage 5/5 · writing STL' 80 % → done ~65 s; stages 1–3 never shown; ~7–10 s freeze during 5/5 (timer stalled 0:53→0:56) and the bar lost its numeric value. B1c restarts at 2 % (OK) but repeats the B1b freeze (~7 s at 0:57). Screenshots `docs/qa/screenshots/2026-10-09-r3/B1b_bar_midrun.png`, `B1c_bar_midrun_0m06.png`. **Diagnosis:** see 'Round 3 browser results' below. Previous: fixed (pending QA) `0354b3c`: bar determinate from the first frame ('starting build process' → 'stage k/5'), never decreases, no sweep; worker reports stage 1 before loading the CAD kernel. The 66 s was the motor-cup path: `preview_motor_cup` defaulted ON (switch in the Assess & print panel) — now OFF, Preview ~15 s on Windows. **History — QA round 2 browser on d781894: reopened (browser, Linux, d781894): caption is 'Running Preview… m:ss', 'stage k/4' appears only late (3/4 ~0:32, 4/4 ~1:01); bar ~65% at 0:01 then drops to ~50% at 0:32 (still goes backwards); stock Preview ~66 s; stage 3/4 says 'carving motor cup' with motor cup off; UI unresponsive for seconds during Preview. docs/qa/screenshots/2026-10-09/B1_FAIL_*.png** **r4:** browser re-test rows B1a–c in `docs/qa/browser_checklist_2026-10-09_r4.md` (pending) **Browser r4 (2026-10-09, :8080 master f238f54): REOPENED (B1a/b/c all fail).** B1a: at ~0.26 s the caption showed a stale 'stage 5/5 · writing STL'; 'stage 1/4 · loading CAD kernel' only at ~0.59 s (over the 0.5 s rule), with the bar already ~80 %; then only 3/4 'lofting blades + hub' (3–6 s); stages 2 and 4 never seen; done ~6.7 s. B1b (cup on): 1/4 0–2 s, 3/4 'building + carving motor cup' 2–48 s, 4/4 'writing STL' 48–51 s, done ~54 s; stage 2 missing; elapsed counter froze at 0:51 for ~3.4 s before finishing. B1c: 'stage 4/4 writing STL' and a near-full bar from the previous run at 0.16 s, stage 1/4 at 0.6 s. Screenshots `docs/qa/screenshots/2026-10-09-r4/B1*.png`. **Diagnosis (code reading):** (1) *Stale caption/bar:* the progress file is never cleared after a run, and its path is the box-global `tempfile.gettempdir()/fansim_cockpit_preview.stl.progress.json` (`fan_session.py:75`, `fan_viz._preview_progress_path`). `do_preview` starts the ticker *before* the executor thread reaches `build_stl_isolated`, which is what overwrites the file with stage 1, so the first tick (t≈0) reads the previous run's 4/4 (or 5/5 left by older code / another cockpit). `progress_caption` then sets the bar to 75–80 %, and because it is `max(prev_pct, …)` the bar can't come back down for the rest of the run. The next tick is only after `interval` (0.5 s) plus the tick work, hence stage 1 at ~0.59 s. (2) *Stage 2 invisible:* `_build_worker` writes 2/4 'preparing design (chord fit)' right after its imports, then `prepare_loft_chords` returns from the disk cache in ms and 3/4 is written immediately, so stage 2 lasts milliseconds unless chords are uncached (a new design). Stage 4 on the fast (non-fused) path is also sub-0.5 s. A 0.5 s poll can't see them. (3) *3.4 s end stall:* after the executor returns, `task()` runs `_draw(preview_stl)` (pv read + VTK render), `session.spec_status` (trimesh load/volume/gauge), `grade_printability`, the tone line and `ctrl.view_update()` synchronously on the event loop. The ticker task can't run during this, so the elapsed counter freezes. r3 headless measured 1.6 s; in a real browser the remote render/image push is at the real viewport size, and the 4.7 MB cup mesh is bigger. **Suggested fixes:** clear/overwrite the progress file (stage 1) synchronously in `do_preview` before `spawn_busy_ticker`, or reset with no `max()` against a stale value; make the preview/progress paths per cockpit (run dir or pid); drop stage 2 as a separate stage when chords are cached, or have the caller latch every stage it has seen; move `spec_status`/`grade_printability` into the executor and keep the ticker alive until `_draw` finishes. See also UI-30. |
| UI-5 | MED | Prop | 5" FPV prop reports 2087 g / 743 W (implausible) | verified `ad1c716`, incl. browser B5: Prop tab shows η 25%/35%/44% at J 0.16/0.24/0.31; static 2087 g / 743 W (plausible vs APC). Follow-up CT0 creep → QA-12 |
| UI-6 | LOW | Fan | Export only saved server-side, ~2 min, `design_100000` name | verified in browser B6: download link works (5.0 MB STL downloaded), file in repo/exports; export still ~75 s. docs/qa/screenshots/2026-10-09/B6_PASS_export_link.png |
| UI-7 | LOW | Fan | Stale "Saved..." message after Randomize | verified in browser 2026-10-09 (`c6fb753`) |
| UI-8 | LOW | Fan | Slider tooltip vs side label disagree; tooltip overlaps label | verified in browser B2 `c4da19c`: Chord root tooltip 17.75 = label 17.75 mm (minor: aria value reports 18; tooltip slightly overlaps end of label text). docs/qa/screenshots/2026-10-09/B2_PASS_chord_root_tooltip.png |
| UI-9 | LOW | Fan | Poor first-load framing; colour bar zero range | **verified (browser r3, `0354b3c`)**: Fan tab 1102×735 = 3:2 at 100 %, fan fills ~2/3 of the width, centred (B3a); still fine at 75 % zoom (B3b). The other 4 tabs' frames are 3:2 and not clipped, but their model framing wasn't judged because nothing was previewed there. Screenshots `B3a_framing_zoom100.png`, `B3b_framing_*.png`. Previous: fixed (pending QA) `0354b3c`: viewer card was a fixed 400 px, so a wide (zoomed-out) column gave a ~2.8:1 canvas and a height-limited fan; all tabs now 3:2, ≥ 400 px, ≤ 75vh (1131×754 at a 1970-px window). **History — QA round 2 browser on d781894: reopened (browser B3): after reload the fan fills only ~1/3 of viewer width, centred, ringed by arrows (normal reload, not hard reload). docs/qa/screenshots/2026-10-09/B3_FAIL_fan_small_in_viewer_after_reload.png** |
| UI-10 | LOW | Volute | Casing hides impeller; clipped labels | verified in browser 2026-10-09 (`8e975bf`) |
| UI-11 | LOW | Mixed/Prop/Volute | No slider values; leftover blurry render | verified in browser 2026-10-09 (viewers clean before Preview) |
| UI-12 | LOW | Mixed | Flat unshaded preview | verified in browser 2026-10-09 (`8e975bf`) |
| UI-13 | LOW | Prop/CROR | Disabled buttons look enabled | verified in browser B4: Prop Stop grey/disabled when idle. docs/qa/screenshots/2026-10-09/B4_PASS_prop_stop_disabled.png |
| UI-14 | LOW | All | Tab tooltip covers neighbouring tabs | verified in browser 2026-10-09 (`b4524ab`) |
| UI-15 | LOW | All | Console 405 on POST /paraview/ | verified `ea418f3` (by design: documented benign; POST /paraview/ still 405) |
| QA-11 | LOW | Geometry | `blade_solidity(BladeParams(n_blades=0))` raises ZeroDivisionError (build-time validation now blocks it, direct API call doesn't) | verified `c4da19c`: `blade_solidity(BladeParams(n_blades=0))` → {hub, mid, tip} all 0.0 |
| UI-16 | HIGH | Server | One connected-but-stalled client (frozen/sleeping tab) freezes ALL websocket sessions; new sessions never get `wslink.hello` reply, HTTP stays 200 | verified `94a7365` (Linux): 1 SIGSTOPped client + 200 image pushes. Fresh sessions always connect (0.25–0.38 s during the pushes, was a 15 s timeout every time); 200/200 pushes complete (was stuck at 76); the stalled client is dropped about 15 s later with one warning; no restart needed |
| UI-17 | LOW | Server | A non-upgrade GET `/ws` logs `KeyError` in wslink `onClose` and leaks a `connections` entry; abrupt disconnects log `Cannot write to closing transport` tracebacks on Linux | verified `94a7365`: 20× `curl /ws` gives 0 KeyErrors and `connections` back to 0 (961f953: +20 KeyErrors, 20 leaked entries). The 'Cannot write to closing transport' log noise is also gone in this run (0 vs 15 on 961f953) |
| UI-18 | LOW | Server | Remote-view image-push observers are never removed when a client disconnects (observerCount only grows; views keep rendering/pushing with no clients) | verified `c4da19c`: `observerCount` stays at `{}` after 30 aborted observer sessions and after 506 stress cycles (961f953: 30, growing to 538) |
| UI-19 | LOW | Fan | Export download dir is `Path("exports").resolve()`, i.e. relative to the launch CWD, not the repo/run dir | verified `94a7365` + browser B6 (file lands in repo/exports) |
| UI-20 | LOW | Fan | After Randomize, Design dropdown still says '◆ Reference · Noctua A12x25 (published)' though geometry changed | **verified (browser r3, `0354b3c`)**: while edited, the shown value and label read as specified; Reset restores both (B7). Screenshots `B7_dropdown_edited.png`, `B7_dropdown_after_reset.png`. Previous: fixed (pending QA) `0354b3c`: the selected value itself now reads '✎ Edited copy of ◆ Reference …' (label: '✎ Edited copy (not saved) — based on:'). **History — QA round 2 browser on d781894: reopened (browser B7): only the small caption above the field reads '✎ Edited copy of this design (not saved)'; the selected dropdown value still shows '◆ Reference · Noctua A12x25 (published)'. docs/qa/screenshots/2026-10-09/B7_FAIL_dropdown_still_reference.png** |
| UI-21 | LOW | Mixed | CFD refine button solid orange with 'top N = 0', looks enabled (not clicked) | verified in browser B8: CFD refine on Mixed/Prop is pale tonal disabled (not clicked). docs/qa/screenshots/2026-10-09/B8_PASS_mixed_cfd_refine_tonal.png |
| UI-22 | LOW | Mixed | Preview timer may lag ('Running Preview… 0:01' ~6 s after click) | verified / not reproduced on Linux branch d781894 (B9): '0:00' 0.13 s after click, ticks ~1 s, done ~3.9 s |
| QA-12 | LOW | Prop/BEMT | Static CT0 creeps up ~60% from 4k to 30k rpm (measured: flat). Diagnosis `docs/qa/notes/prop-ct0-rpm-creep.md`: ~44% from the analytic fallback below Re 4e4 (`fansim/propeller/polars.py:151`), ~44% from real table Re effects, ~15% from Mach. No patch yet | open (new 2026-10-09). **Round 3:** the pre-registered low-Re polar blend (criteria sha256 `e91b2804…6844`) **FAILS**. It removes the 66 % jump at Re 4e4, but creep stays at +62 %, and GWS rules R3 (0.160→0.196) and R4 (0.0080→0.0100) get worse. Record-only patch: `docs/qa/patches/prop-lowre-polar-blend.diff`. The root cause is the analytic low-Re formula itself. GWS regression test `e7d8174` verified: its data files are byte-identical to the UIUC zip extract. Still open |
| UI-23 | LOW | All | Browser console `TypeError: n[i[e]] is not a function` in `assets/index-*.js` from `invokeConnectionClose`, twice, on page reload (B10) | open, needs one discriminating run (r4): please reload 3× on **961f953** (pre-guard) or with `FANSIM_WS_GUARD=0`. If it still fires, it's upstream trame-client; if not, it's ours. My Windows Chrome-pane runs (1 tab, guard on/off, master) never captured it. Earlier: **still open (browser r3, master e48a32d)**: the `TypeError: n[i[e]] is not a function` from `invokeConnectionClose` fired once per reload, 3/3, with **one** tab connected, at unload. That contradicts 'not reproduced with 1–2 tabs'. Screenshot `B10_console_after_3_reloads.png`. Previous: upstream / not ours (2026-10-09): an unhandled rejection in trame-client's close callbacks while the page unloads. Captured once on the branch (7 stale tabs connected, reload during start-up); not reproduced with 1 or 2 tabs with the guard on, with the guard off (`FANSIM_WS_GUARD=0`), or on master. Harmless (page is going away). Please note client count / timing if you see it again. **History — QA round 2: opened 2026-10-09 (seen twice on page reload during B10, Linux, d781894).** **r4:** discriminating run prepared (checklist r4 B10a–c: :8081 = 961f953 pre-guard, :8082 = master with `FANSIM_WS_GUARD=0`, :8080 = master control). Results pending **Browser r4 discriminating run: not reproduced anywhere.** 0 TypeErrors on :8081 (961f953, pre-guard), :8082 (guard off) and :8080 (master); 3 reloads each, Preserve log on, cross-checked by a script. r3 saw 3/3 on master, so it's **intermittent**; it doesn't discriminate guard vs upstream. Stays **LOW/open**. Side notes: on :8080 only, an `Uncaught (in promise) {code:-32099, viewport.image.push … connection not open}` sometimes appears at unload (the script saw similar unnamed rejections on all ports); one :8080 reload hung on a blank page for ~20 s. `docs/qa/screenshots/2026-10-09-r4/B10*.png` |
| QA-4b | MED | BEM/scoring | Stock efficiency BEM 29.4 % vs CFD 17.9 % | diagnosed (r4): same quantity (definitional difference −0.66 pp). ≈ 4 pp is the CFD scorer's straight-line η interpolation; ≈ 6.8 pp is real BEM pressure over-prediction (14.7 vs 8.0 Pa at 41.75 CFM). Note `docs/qa/notes/r4-efficiency-definition-audit.md`. Open (BEM pressure) |
| QA-13 | MED | BEM/axial | Axial-model efficiency unbounded: up to 115 % on 11-blade, high-solidity designs (6/1,752 > 100 %) | new (r4, on `5396796`): don't rank on axial η until an energy bound (static rise ≤ Euler work) is enforced. Note `docs/qa/notes/r4-axial-crosscheck-and-guard.md`. Open |
| QA-14 | LOW | Scoring/docs | Scored CFM / η can't be reproduced from `cfd_designs.csv` | fixed (pending QA, r5) `0a21dc6`: docs/how-scores-are-computed.md + CSV correction columns. Earlier: new (r4): needs derate, free-pressure and raw-η columns. Undocumented for users: print knockdown, 40 % motor-efficiency assumption (Stock derated to 1,907 rpm), measured free-delivery pressure, extrapolation past the test point, straight-line η estimate. Note `docs/qa/notes/r4-scored-vs-raw.md`. Open |
| QA-15 | MED | Geometry/memory | Stock cup fuse (`fuse_impeller`, one 10-arg parallel OCCT Boolean) peaks 7.66 GB and retains it; drives the test-suite and slow-suite peaks (8.0 GB) and the cup Preview worker | fixed (pending QA, r5) `e7d9a9e`: memory tiers from free RAM (fansim.resources); serial/per-blade fuse; same solid. Earlier: r4 request 5: 7 pre-registered strategies, **none passes** the ≤ 4.0 GB rule (all byte-identical geometry). Best: serial booleans (S3) 4.89 GB, +15 % time; S1+S3 4.46 GB but 2.7× time. No patch; note `docs/qa/notes/cup-fuse-memory.md`. Open **r6 stress (Task A, n=120):** the tier builds work (K8 volume/vertex-equal 11/11, K9 within budget 11/11), but see QA-20: the files are not byte-identical. Observation: featured (S5) P builds at the forced 8gb tier peaked at up to **7.6 GB** (S5_0011), above that tier's 6.5 GB `min_free_gb`. Open |
| DOC-1..5 | LOW–MED | Docs | README / a12x25-reference claims audit | new (r4 request 8): personal plan path (README:12); tip band 55–57 mm excludes Stock (54.5) and contradicts the 110 mm frame + 0.5 mm clearance (MED); stale 'reality check' / Task 3.1 / FW-H text; clean-clone gaps (runs/, catalog.db, config/fan_models, build/, propulsion extra; catalog/ and fan_models are CWD-relative); `config/design_space.yaml` still 7 blades / 56.5 mm / 120 mm frame. Note `docs/qa/notes/docs-claims-audit-2026-10-09.md`. Open |
| QA-16 | MED | Export/mount | Motor cup depth measured from the impeller's lowest blade point, not the hub face | fixed (pending QA, r5) `e7d9a9e`: fan blades cut at the hub face (user rule) + cup measured from the hub face. Earlier: new (r4 request 6): `carve_motor_mount(z_bounds=bb.zmin)` cuts 13.0 mm from the blade plane, but the blades hang 0.94 mm (Stock) / 2.42 mm (9504) below the hub face, so the motor hub is held by only **12.06 / 10.58 mm** of hub + grip pads. The gauge reports 13.0 and OK. Measured by ray casting (`handoff/2026-10-09_from-qa-3/export/`). Open (check intent with a print) **r6 stress:** the reference is fixed on master (cup cut from the hub face): all hubs ≥ 14.3 mm read a floor 12.98–12.99 mm above the hub face (26/29 C builds). The remaining failures are QA-18 (short hubs). **Verified for hubs ≥ 14.3 mm**. r8: side effect found, the clip shortens chord on deep blades and the chord realisation doesn't see it → QA-30 |
| QA-17 | LOW | Export | `also_mirror` builds the as-designed solid twice; gauge cavity Ø is vertex-noisy | fixed (pending QA, r5) `1453c4f`: mirror pair copies the as-designed STL/STEP. Earlier: new (r4): `<stem>.stl` and `<stem>_as_designed.stl` are identical (Hausdorff 5e-11), a third full build (Stock export 205 s). The gauge `cavity_dia_mm` reads 38.06 / 37.79 for an identical 37.94 mm cup; `mount_msg` rounds to '37 mm'. Open |
| UI-24 | HIGH | Fan | Motor-cup and fit switches ('Export options') sit at the bottom of the left column, ~2 screens below **Export STL**, so a user can't see what Export will do | fixed (pending QA, r5) `1453c4f`: Print / export card directly under the 3-D view (Export STL + switches + download + memory tier). Earlier: new (browser r4 B11, newcomer pass). `docs/qa/screenshots/2026-10-09-r4/B11_1366x768_export_options_far_below.png`. Open |
| UI-25 | MED | Fan | After a cup-on Preview, turning the cup off leaves the carved mesh in the viewer, even across reloads, with no stale marker | fixed (pending QA, r5) `1453c4f`: per-cockpit preview files; carved mesh no longer survives across cockpits. Earlier: new (browser r4). Likely related to the box-global `/tmp/fansim_cockpit_preview.stl` (UI-30). Open |
| UI-26 | MED | Fan | Jargon next to the action buttons: 'case hose · PETG — change under Assess & print below', 'camber 0.037/0.083/0.097', 'Difficulty 42/100 — FDM + supports', 'Gold = parametric Stock; published CFM is the ✕' | new (browser r4 B11/B12). Open r22 (b3d5543): **still open**: hose line now Expert-only and camber/Difficulty off the first view, but 'Gold = parametric Stock…' renders on first view in both modes and camber/Difficulty after Preview (`docs/qa/notes/r22-A-ui-bug-pass.md`). r24 (23831da): **still open**: 'Gold = parametric Stock…' still on first view, both modes (`docs/qa/notes/r24-A-ui-bug-pass.md`). r25: still open on master 9d0118f and on branch 237a094 (jargon in 3/4 viewports this run; 1366 Simple miss on both heads = render timing, no code change). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch); 1366 Simple miss again (render timing). |
| UI-27 | MED | Fan | At 1366×768 the 3-D viewer is cut off below the fold; a long intro banner pushes the picker and Actions down | new (browser r4 B11). `docs/qa/screenshots/2026-10-09-r4/B11_1366x768_first_view.png`. Open r22 (b3d5543): **still open**: picker and Preview now above the fold, but the viewer bottom is at 957 px of 768 (also 1172 of 1080 at 1920×1080). r24 (23831da): **still open**: viewer bottom 957 px of 768. r25: still open on master and branch (viewer bottom 957 px of 768). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-28 | LOW | All | Disabled Cancel buttons (pale pink) and Randomize (pale teal) are hard to read | new (browser r4, by eye; contrast not measured). Open |
| UI-29 | LOW | Fan | At 1920×1080: narrow controls column, tiny text, lots of empty space; 'Start here' is a tiny grey line | new (browser r4 B12). `docs/qa/screenshots/2026-10-09-r4/B12_1920x1080_first_view.png`. Open r22 (b3d5543): **still open**: column 41 % and body 16 px pass; 'Start here' still a 12 px grey caption. r24 (23831da): **still open**: 'Start here' still 12 px grey caption. r25: still open on master and branch (probe identical to r24). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-30 | MED | Cockpit | All cockpits on one box share `tempfile.gettempdir()/fansim_cockpit_preview.stl` (+ `.progress.json`, `.meta.json`; Volute: `fansim_volute_preview.stl`), so concurrent cockpits overwrite each other's preview/progress, and a stale progress file seeds the next Preview's caption and bar (UI-4) | fixed (pending QA, r5) `1453c4f`: `<temp>/fansim_<pid>/` for Fan/Mixed/Prop/Volute/CROR. Earlier: new (r4 code reading, `fan_session.py:75`, `volute_tab.py:121`). Contradicts README's 'start a second cockpit on another `--port`'. Open |
| UI-31 | HIGH | Fan/Optimize | Surrogate-guided Optimize from the cockpit never runs CFD. Training labels and 'verify' come from `synthetic_label()`, a test formula (`surrogate_search.py:309-326,458,477`), because the cockpit never passes `--verify-cfd` (no toggle exists). The path also silently ignores Trials, all Geometry stamps, Search RPM, Refine op and roughness (`run_optimization.py:160-192`). | new (tooltip audit 2026-10-31, code reading; not run). `docs/qa/notes/tooltip-audit-2026-10-31.md` §3/§5. Open r24 (23831da, this bundle, not `r111-hide-surrogate`): **still open**: switch renders in Expert; argv has no `--verify-cfd`; stub/`synthetic_label` defaults unchanged. r25: **fixed on branch (pending merge)** (verified on unmerged branch r111-hide-surrogate @237a094, not on master): 0 Surrogate-guided labels rendered, `cockpit_optimization_argv` omits `--surrogate-guided` with state forced on, CLI refuses without `--verify-cfd`/`--stub-labels`. **Master 9d0118f: still open** (switch renders; `fan_optimize.py:141` wires state). Not closable yet: CLI test guard-only; QA-66. `docs/qa/notes/r25-A-r111-branch-check.md`. r25b: **verified on master 0635a18**: 0 Surrogate-guided labels rendered, argv has no `--surrogate-guided` with state forced on, CLI guard refuses (`run_optimization.py:164-170`). R1.11 not closable (QA-66; CLI test guard-only). `docs/qa/notes/r25b-master-0635a18-recheck.md`. |
| UI-32 | MED | Fan/Optimize | No image tooltips for Optimize (16 controls) or the Assess honesty switches. `fan_copy.py:14` loads only `docs/control_images/e_*.png`, so `opt_*`/`assess_*` images could not show even if present. | new (tooltip audit 2026-10-31). 16 proposed PNGs in `handoff/2026-10-31_from-qa-tooltips/img/`. Open r24 (23831da): **still open**: loader returns 54 `e_*` keys, 0 `opt_*`/`assess_*`; Optimize hovers show 0 images. r25: still open on master and branch (54 `e_*` / 0 `opt_*`,`assess_*`). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-33 | MED | Fan/Optimize | The UI doesn't say Optimize ignores the current Design sliders. It searches the guided space for the fan model from scratch (`study.py:176`, no seed/enqueue); only fan model, stamps and Assess settings carry over. | new (tooltip audit 2026-10-31; Kimball's question). Open r24 (23831da): **still open**: rendered Optimize panel text does not say the Design sliders are unused. r25: still open on master and branch. r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-34 | MED | Fan/Optimize | 'Boost + GP mean' / 'NN + GP mean' do nothing unless Catalog GP skip or Surrogate-guided is on (`cli_argv.py:164-173`). Not disabled; the tooltip names only GP skip. | new (tooltip audit 2026-10-31). Open r24 (23831da): **still open**: Boost/NN enabled with both gates off; argv emits nothing for them. r25: still open on master and branch (Boost/NN enabled with GP skip off; on the branch GP skip is now their only gate). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch); Boost/NN tooltips now name only GP skip, switches still enabled with GP skip off. |
| UI-35 | MED | Fan/Geometry | 13 tooltip images label min/max values that differ from the slider range (`generate_control_images.py` CONTROLS drift), e.g. Skew ±6 shown for a ±20/±25 slider; camber 0.12 vs 0.15; hub radius 30 vs 35. | new (tooltip audit 2026-10-31). `range_check.json`; re-renders in `handoff/2026-10-31_from-qa-tooltips/img/range_fix/`. Open r24 (23831da): **still open, 13/13** (range_check: 20 mismatches incl. all 13). r25: still open on master and branch (range_check identical to r24). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch) (range_check 58 rows, 20 mismatches). |
| UI-36 | MED | Fan | 49 Fan-tab settings have no tooltip, including ones that change results: Fan model, Hub profile (no text or image), Application preset, Print material, Sweep, Intake overbuild, Seed-from-duty, Export fit switches, action row. | new (tooltip audit 2026-10-31, headless hover confirmed). Open r24 (23831da): **still open, 0/8** hovered controls show a tooltip; inventory unchanged (49). r25: still open on master and branch (0/8 hovers; inventory 293 / 292 = Surrogate row removed). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch) (0/8 hovers; inventory 292 rows, byte-identical to branch). |
| UI-37 | LOW | Prop/Mixed/Volute/CROR | 108 of 109 proxy-tab controls have no tooltip: shared `slider()` looks up `CONTROL_DESC` by prefixed model names (`p_`, `mf_`, `cror_f_`…), which never match; `BLADE_DESC` is used only for Cylindrical tip. | new (tooltip audit 2026-10-31). Open r24 (23831da): **still open**: proxy-tab inventory 1/100 with tooltip. r25: still open on master and branch. r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-38 | LOW | Fan/Assess+Optimize | Application/Print material don't say they also drive Optimize; picking a design silently resets preset/refine/roughness to its saved values (`fan_trials.py:103-105`). | new (tooltip audit 2026-10-31). Open r24 (23831da): **still open**: design pick still silently resets preset/refine/roughness. Correction: the Expert Print-material caption already says 'Used by Assess and Optimize' (`fan_tab_ui.py:926`, present at 3b92eea), so the first clause was overstated; Application's caption does not mention Optimize. r25: still open on master and branch. r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| UI-39 | MED | Fan/Sweep | Sweep "steps" accepts anything and has no cap; empty/"1e9" make Run fail silently; a large count queues that many CFD Assess runs (`fan_assess.py:448`) | new (ui-hunt-1, 2026-11-09). Patch `docs/qa/patches/ui-hunt-1-UI39-UI40-steps-trials.patch`. Open. |
| UI-40 | MED | Fan/Optimize | Optimize "Trials" accepts −5/100/1e9 then silently clamps to 2–40 (`fan_optimize.py:130-133`); label doesn't say so | new (ui-hunt-1, 2026-11-09). Same patch as UI-39. Open. |
| UI-41 | LOW | Fan | Seed CFM, ΔP, RPM and arrow Scale show no validation state; they store typed text | new (ui-hunt-1, 2026-11-09). Open. |
| UI-42 | LOW | Fan | Slider readouts print raw 4-decimal values with cryptic units (`fan_widgets.py:35`) | new (ui-hunt-1, 2026-11-09). Open. |
| QA-69 | LOW | Docs | `docs/design-rules.md:10` says "Noise dB(A) (min)" for the LBM model output (`scripts/extract_design_rules.py:106`) | new (r26 G2 follow-up, 2026-11-08). Address in G4. Open. |
| QA-70 | LOW | Fan/flow card | Expert G2 noise-hint row is dropped when a run has no turbulence SWL, though the hint only needs tip speed + CFM (`fan_flow_report.py:146`) | new (ui-hunt-1, 2026-11-09). Patch `docs/qa/patches/ui-hunt-1-QA70-noise-hint-row.patch`. Open. |
| QA-18 | MED | Geometry/cup Preview | Motor cup goes straight through a hub shorter than 13 mm (no cup floor) | new (r6 Task A, K7 3/29: S2_0000, S8 edge stagger_root min, S8 edge chord_root min; auto hubs 12.72 / 12.62 / 10.92 mm). `build_stl_isolated(motor_mount=…)` (the cockpit cup Preview path) doesn't enforce `MotorMount.min_hub_height_mm` (15) or refuse; only Export's `prepare_export_flat(fit_hub=True)` grows the hub. Grips/Ø are correct. Repro `stress/repro/A-F2_cup_through_short_hub.json`; `handoff/2026-10-09_from-qa-5/stress/summary.md`. Was open → **verified fixed `5980677`** (r7 stress: S2_0000, S8_0002, S8_0008 hubs grown to 15.0 mm, floor 12.985 mm, 20 grips; K7 0/14 FAIL over the 65-design run). |
| QA-19 | MED | Audit/direction | `prove_direction` falsely refuses builder designs with max_camber < 0.02 and lean_tip ≥ 20° | r6 Task A, K5: 7/119 CONCLUSIVE-wrong (9605, 9606, 9620, 9630 plus new S3_0002 guided_lc, S4_0005, S4_0012; 8–11 blades) and 24 INCONCLUSIVE. All 7 are in that cell (7 FAIL + 10 INCONCLUSIVE of 22). Not all 11-blade: S4_0005 has 8 blades and S4_0012 has 9; the shared factor is low camber with high tip lean. The mirror check K6 passes on all of them, so the checker misreads lean curvature as camber. Repro `stress/repro/A-F3_direction_false_refusal.json`. Input to Task B. Was open → **mostly fixed `5980677`**: all 7 r6 false refusals now pass the new K5 rule (K5_old FAIL 8 → K5 FAIL 1 over 65 designs). **Residual:** S3_0014 (9 blades, max_camber 0.0242, lean_tip 42°) is CONCLUSIVE omega −1/pump +1, mirror passes K6, and the new rule refuses it because its camber is just above the 0.02 cut-off. Same lean-as-camber misread, one camber bin higher. See `docs/qa/stress/RESULTS_R7.md`. Still open for camber 0.02–0.04 × lean ≥ 30°.. **r8 Task B (fresh sample, 2-blade rebuilds):** the cylinder proof is still CONCLUSIVE-wrong on 6/72 (5 flat-leaned plus S3_0014 again). The radial-plane cut had 0 wrong on 72 parts + mirrors and read 54/54 cambered parts. The combined (both-agree) rule had 0 wrong but read only 43/54 (R5 FAIL). The builder rule R6 FAILS as registered. `docs/qa/notes/direction-radial-confirmation.md` |
| QA-20 | LOW | Resources/docs | Memory tiers give equal solids but **not byte-identical STLs** | r6 Task A, K8: volume within 1e-6 and the same vertex count 11/11, but the sha256 differs between 16gb/8gb/6gb in **11/11**. The `fansim/resources.py` docstring's 'byte-identical solid' claim is false at the file level. Repro `stress/repro/A-F4_tiers_not_byte_identical.json`. Open |
| QA-21 | LOW–MED | Geometry | Tip trim raises on a featured, high-lean, wide-tip blade from the optimizer's own space | r6 Task A, K1 1/120 (S5_0007: 10 blades, tip R 52.55, chord_tip 36.4, lean_tip 42.8°, tubercles + serrations + dimples): `RuntimeError: tip trim failed: blade crosses R=52.55 mm (reaches 56.09 mm) and no intersection ended at R…` (worker exit 3). It passed `validate_blade_params`; it should build or be refused cleanly. A real builder robustness bug, not a sampler artefact. The runner labelled it CRASH because the 160-char stderr tail cut off the traceback; it's really a BUILD_FAIL. Repro `stress/repro/A-F1_tip_trim_build_fail.json`. Was open → **verified fixed `5980677`** (S5_0007 P OK, K1–K6 PASS; K1 0/65 over the r7 run). |
| QA-22 | MED | Cockpit/Assess provenance | Assess, Assess-existing, Sweep and Mixed Assess stamp material, hose/`load_pa`, refine-op and fan model from the **live** state at save time, not from what the run used (`fan_assess.py:171-177, 220-222, 297`; `mixed_tab.py:393-394`) | new (r7 Task A). Repro: `docs/qa/settings_during_run/harness.py`, scenarios A2/A3 (the run used PETG, case 8 Pa, refine off, a12x25; saved PLA, legacy 1 Pa, refine on, delta_afc1212de). Fix: snapshot at click. **r8 (`f86df9a`, fix `e5bdb81`): verified fixed.** Harness A2/A3 now save PETG / case 8 Pa / refine off / a12x25 (the click-time values); Mixed Assess takes hose+refine at the click (code, `mixed_tab.py:357-358`). `docs/qa/notes/settings-during-run-r8.md` |
| QA-23 | MED | Cockpit/Assess provenance | Clicking another design during Assess restamps the running job's result with **that design's** hose and refine-op: `fan_trials.select` writes `assess_preset`/`assess_refine_op`/`assess_wall_ks` (`fan_trials.py:95-97`) | new (r7 Task A). Repro: harness A4 (saved preset legacy, load_pa 1.0, refine_op True; the run used case/8 Pa/off). The most likely real-world trigger. **r8: verified fixed** (harness A4 saves case / 8 Pa / refine off) |
| QA-24 | MED | Cockpit/library lineage | `parent_id`/`place_op`/`placed_on` are read at save time (`fan_assess.py:225-228`): applying another library recipe during Assess saves the result under the **wrong parent**; selecting a trial or randomizing clears it | new (r7 Task A), class (c). Repro: harness A5 (started under LIB_X, saved parent_id LIB_Y). **r8: verified fixed** (harness A5 saves parent LIB_X) |
| QA-25 | LOW–MED | Cockpit/Sweep | A Sweep silently picks up material, hose, spec, refine and wall-ks changes **between steps** (each step re-reads state in `_blocking_eval`), and step 1 is stamped with the changed value | new (r7 Task A), class (a)+(b). Repro: harness A7 (steps 2–3 ran PLA, step 1 ran PETG; all three saved PLA). **r8: verified fixed** (harness A7: all 3 steps ran and were stamped PETG) |
| QA-26 | LOW | Cockpit/display | After the run, the Preview caption shows the live camber sliders (`fan_viz.py:420`) and the verdict uses the live fan model; the Export message shows the live hub radius/height (`fan_export.py:236,241`); Assess-existing never stamps `material`; after Assess the view jumps back to the assessed design (`fan_assess.py:410`) | new (r7 Task A), display only. Repro: harness P1 (built camber_mid 0.0834, caption 0.113). **r8: partly fixed.** Assess-existing now stamps `material` (harness A6: PETG). The Preview caption (P1: built 0.0834, caption 0.113), the Export message and the view jump are **unchanged**, as expected (roadmap 27.5). Still open |
| QA-27 | MED | Resources/memory | `fuse_peak_estimate_gb` (0.37 GB + 86 kB × faces) under-predicts the fuse peak RSS; the 15 % guard headroom is not enough | r7 stress K12 (`5980677`): 62/65 FAIL; peak/estimate median 1.29, IQR 1.25–1.36, range 1.04–1.80 (up to +1.57 GB), faces 9.9k–44k. Un-forced, the guard would admit builds that then need ~30 % more RAM than planned (OOM risk on 6–8 GB machines). Fix: refit intercept/slope on the 65 points in `handoff/2026-10-11_from-qa-7/stress/run_r7/designs.jsonl.gz` (`meas.K12`) or raise headroom to ≥ 1.5×. `docs/qa/stress/RESULTS_R7.md`. Open. **r8 Task C (single process, at the call):** VmHWM vs faces fits 1.02 GB + 92 kB/face (22 builds, 9.9k–71k faces), so the Linux intercept is the same in one process as round 7's tree sum; it is not a summing artefact. Increment after the call fits 0.28 GB + 72 kB/face. Prereg rule (increment ≤ 1.15·est − RSS_at_call) **FAILS on 21/22**. The guard's actual test (1.15·est ≤ MemAvailable) still covered the remaining growth on 20/22; it fails on shrouded S7_0013 (+2.66 GB vs 2.41 GB) and is marginal on S7_0017 (0.98). Shrouded designs run ~1 GB above the face-count fit. `docs/qa/notes/fuse-memory-at-call.md`. **27.1 CLOSED 2026-10-13:** guard is remaining growth × 1.15 vs free RAM, plus a shroud term on blade faces. Linux 0.28 GB + 72 KiB/face + 66 KiB/blade-face; Windows 0.10 GB + 103 KiB/face + 26 KiB/blade-face. `docs/validation/audits/2026-10-13-fuse-remaining.md`. |
| QA-28 | LOW | QA tooling (stress runner) | Memory-gate and build timeouts in the stress runner use `time.time()`, so a box suspend blows through them | `handoff/…qa-7/stress/design_job.py` `wait_mem()`/`build()`: S2_0020 T16gb waited 44 082 s on a 600 s gate; S1_0020 P build 9 377 s wall vs 35.8 s monotonic. Use `time.monotonic()` for limits (keep wall time for logging). Not an app bug. Open |
| QA-29 | LOW | Cockpit/display | After Assess finishes, the result message (`Done ◆#n: free … load … eff …`, the vs-stock line and the score caption) is replaced by the stale busy caption `Running Assess… m:ss`. The ticker (`fan_assess.py:154-167`) keeps rewriting `assess_msg` while `assess_busy`, and `on_assess` awaits the viz bake (`:389`) after writing Done but before `ticker.cancel()` (`:405`) | new (r8 Task A). Pre-existing (same in `5980677`; round 7 saw Done by timing luck). Repro: `docs/qa/settings_during_run/harness_bake_race.py 4 none|slow`: both end on "Running Assess…". Fix idea: cancel the ticker before writing Done. Open |
| QA-30 | MED | Geometry/scoring | The hub-face clip (`clip_blade_below`, `blade.py:845-870`, QA-16) cuts off the lower part of deep blades. The measured-chord realisation measures an **unclipped** single blade (`chord_realisation.py:71`), so it never sees that loss. lt120's built chord is 3–16 % short whatever the chord basis | new (r8 Task D). lt120 with `clip_below_hub=False`: chord within 0.5 % at every realised station (−3.2 % at the hub station, which isn't realised); clipped: −3.2…−15.6 %. The impeller zmin is −7.47 mm vs the blade's −12.63 mm. This, not planar sections, is why `chord_basis="loft"` and `cylindrical_tip` changed nothing in round 7. BEM scores the slider chord. Open |
| QA-31 | MED | Geometry/scoring | On leaned/skewed blades the built cylinder-cut camber is far below the slider camber. The measured-chord realisation keeps the chord right by stretching the loft chord (Stock tip 33.5 → 49.6 mm, t9005 tip 38 → 58 mm), and the cut keeps only the middle of the stretched section | new (r8 Task D). Net of estimator bias, at chord/r 0.6–1.2: Stock −0.015…−0.049; t9000/t9002/t9003/t9005 −0.006…−0.043 (t9005 tip reads 0.0075 for slider 0.06). With lean, skew and sweep zeroed (Stock, loft basis) the gaps are ≤ 2 % in chord and about +0.003 in camber. So the cause is the circumferential stacking, not chord/r. BEM and CFD score different blades. Prereg rule: MATERIAL. **Closed by wrap (27.4):** built = sliders where the hang limit allows. |
| QA-32 | MED | Geometry | Wrapped hub-clip stations: camber 0.005–0.011 low, stagger up to 1.1° | r9. **r10b Task C: verified closed.** 49 hanging designs / 105 stations, 0 outside 3 % / 0.005 / 1.5° (max 2.9 % / 0.0048 / 1.46°). Hang limit refuses designed > 2 mm on 400/400. |
| QA-33 | LOW–MED | Geometry/direction | Wrapped cylinder proof INCONCLUSIVE more often | r9 30/65 vs 24/66 planar. **r10b B: 18/38 wrapped INCONCLUSIVE.** Harmless: INCONCLUSIVE never refuses. Open. |
| QA-34 | MED | Geometry/export | Featured wrapped S5_0184: B-rep fuse is 1 solid, STL is not watertight (8 bodies, 7 degenerate faces). Planar twin is clean. `fuse_impeller` does not flag it. | r10b Task B W1/W6. **CLOSED 2026-10-14:** 7 collapsed tessellation needles (one per blade); impeller mesh was already watertight. `export_stl` → `sanitize_stl`. `docs/qa/notes/qa-34-featured-wrap-stl.md`. |
| QA-35 | MED | Memory/27.1 | Linux remaining-growth guard under-asks open builds: S7_0172_twin (11 blades, 22.7 k faces) 2.19 GiB vs ask 2.12 GiB (1.03×, 3/3 repeats); open 9/11-blade twins at 0.91–1.03× | r12 Task B. Shrouded fine (≤ 0.80×). **fixed (pending QA)** `049b705` (Linux open refit 0.515 GiB + 82.3 KiB/face). **VERIFIED r14 A1** (9562574): 26/26 OK, worst open 0.85, S7_0172_twin 0.826. |
| QA-36 | MED | UI/material | Material picker PLA+ not followed by Preview grams or the Export README/nozzle/bed/print_fit/registry (all read `active_spec().material` = PETG); Assess stamp + optimizer do follow | r12 Task D; tests in from-qa-12/tests fail on HEAD. **fixed (pending QA)** `d7a23d6` (`active_spec()` carries the picked material). **VERIFIED r14 A2** for Export (README PLA+ 215/60 °C, print_fit, index) + 6/6 tests; the Preview line can't show the material (→ QA-42), and the busy-switch check (24.4) is INCONCLUSIVE. |
| QA-37 | LOW | Export/28.2 | Killing the cockpit process mid-Export does not stop the isolated export worker (it keeps fusing, ~6 GB); if it dies after writing the STL, `{id}_….stl` is left with no README/sidecars and an id absent from index.jsonl | r12 Task C harness accident (Q8B8G): orphaned worker overlapped the next export and was OOM-killed (dmesg, 6.2 GB anon). **fixed (pending QA)** `5be865e` (workers exit within ~2 s of their launcher; Export staged in `.partial-*`, published when complete, print-id recorded after). **VERIFIED r14 A3** (worker gone 0.75 s, `.partial-*` only, index unchanged) when the launcher is reaped; zombie case → QA-41. |
| QA-38 | LOW | UI/24.2 | At 1366×768 Simple Results, the scatter's plot body is below the fold (top at y=652, only the title visible) | r13 Task A S4 (report-only). |
| QA-39 | LOW | CFD post/maths | `_pp_file` (and the same pattern in `sanity.py`, `timing.py`, the objectives copy) picks the "latest" postProcessing time dir by string sort, so `"1000" < "999"`. Latent today (runs write one time dir) | r14 B1(d). Sort by `float(name)`. `docs/qa/notes/maths-check-r14.md` |
| QA-40 | LOW | UI/27.3b | Simple-mode flow card shows "No Stock comparison for noise." when the run has SWL but no Stock reference (case s3); noise was meant to be Expert-only | r14 A4. `docs/qa/notes/reverify-r14.md` r22 (b3d5543): **still open** (r14 harness, s3 still shows the line in Simple). r24 (23831da): **still open** (s3 still shows the noise row in Simple). r25: still open on master and branch. r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
| QA-41 | LOW | Export/QA-37 | `watch_parent` uses `os.kill(pid, 0)`, which succeeds on a zombie: if the killed cockpit isn't reaped, the export worker keeps running (≥ 30 s seen). Files stay safe (`.partial-*`) | r14 A3 run 1 + `from-qa-14/data/a3_zombie_probe.txt`. Also exit on `os.getppid()` change or `/proc/<pid>/stat` state Z. r22 (b3d5543): re-observed by the repo's own `tests/test_worker_parent_watch.py` (2 tests fail on Linux: zombie parent reads alive). Not a formal re-test. |
| QA-42 | LOW | UI/material | Preview line "✓ fits … (… 11 g)" doesn't say which material (or infill) it weighed; PLA+ 10.87 g and PETG 11.13 g both show "11 g", so the user can't see the picker took effect | r14 A2b1/b2. Name the material (and "20 % infill") in the line. r22 (b3d5543): **still open**: rendered Preview reads '… 11 g' for both PLA+ and PETG, no material. r24 (23831da): **still open** ('… 11 g' for PLA+ and PETG, no material). r25: still open on master and branch ('… 11 g'). r25b: still open on master 0635a18 (code identical to 237a094; harness output identical to r25 branch). |
## Details
(Numbered bugs below map to QA-n.)

## Environment and what I tested

- **Box:** Linux x86_64, 8 cores, 16 GB RAM, no swap. Source is `/workspace/fansim/src`, a copy of `T:\Projects\Fan Simulator` with the working tree as of 2026-10-08. The copy has **no `.git`**, so I could not diff the uncommitted edits in `fansim/centrifugal/isolated.py` and `fansim/cfd/*`.
- **Setup:** `uv sync --extra dev` worked with no errors: uv 0.12.23 downloaded CPython 3.12.15 and installed 109 packages, including cadquery 2.8.0, trimesh 5.1.0, pyvista 0.48.4, trame 3.13.2 and vtk 9.6.2. The whole package imports on Linux, `fansim.cockpit.app` included.
- **Scope (per Kimball):** no Docker, no OpenFOAM and no CFD (Assess, Sweep, solver). Tests marked `docker` or `slow` were deselected (22 tests). For geometry, preview, export, STL checks, unit tests and the cockpit UI, see below.
- **Fans generated:** I built 21 valid configs through the project's APIs (`blade_from_flat`, `load_blade_params`, `build_impeller`, `build_impeller_with_mount`, `export_mixed_flow_stl`, `build_cror`, `build_prop`, `export_wind_turbine_stl`):
  - **Axial:** default, Stock YAML, design_space YAML, 1/2/3/5/9/11/13 blades, 40 / 250 / 600 mm diameter, hub ratio 0.7, full shroud, notch + sickle + winglet + tip-round, and motor cup.
  - **Other types:** mixed-flow with cup, CROR, FPV 5" prop, and a 200 mm wind turbine.

  Other runs:
  - `scripts/export_a12x25_print_ready.py` (Fit on).
  - One "Stock via cockpit flat" build, used for bug #1.
  - Six invalid-input probes. Four errored; two built anyway (bug #2).

  The original spread had about 55 configs. I cut it to roughly this many after the scope change.
- **STL checks:** trimesh 5.1.1 in a separate venv (`/workspace/fansim/qa/.venv`; `check_stl.py`). The report is `/workspace/fansim/qa_exports/stl_report.csv` and `.json`.
- **Math checks:** `qa/math_checks.py` writes `qa/math_checks.json`.
- **Cockpit:** `runs/qa_synthetic_bem` holds an Optuna study I generated. It has 16 trials sampled with the project's `suggest_params(space="guided")` and **scored by BEM, not CFD**. Each trial carries the user attribute `qa_synthetic=True` and the reason "QA SYNTHETIC: BEM-scored, NOT CFD". The cockpit runs at http://127.0.0.1:8080 and logs to `/workspace/fansim/cockpit.log`.

### Test results (pytest, `-m "not docker and not slow"`, 1533 selected out of 1555)
- **Totals:** 1513 passed, **3 failed**, 18 skipped, 1 xfailed, 22 deselected.
- **Failures:**
  - `tests/audit/test_direction_geometry.py::test_motor_side_with_centre_bore[1]` and `[-1]` (bug #5).
  - `tests/test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case` (bug #7).
- **How it ran:** The single full-suite run was OOM-killed (see Platform #1). I then ran it in 6 sequential chunks, and re-ran the chunk that was killed again one file per process. Logs are in `/workspace/fansim/qa/pytest_tchunk_0*.log` and `pytest_chunk01_perfile.log`.

### STL results
- **25 STLs checked:** All 25 are watertight, winding-consistent and `is_volume`, with positive volume and normals pointing outward. Each is a single body, with 0 degenerate faces, 0 duplicate faces, 0 non-manifold edges and 0 boundary edges.
- **Units and symmetry:** Everything is in mm. Rotating each part by 360°/N maps it onto itself (95th-percentile deviation ≤ 0.03 mm). The one exception is mixed-flow at 0.2 mm, because its 20 grip pads don't divide by 9 blades. Rotating by 360°/(N+1) does not match, so the blade count is confirmed.
- **Euler number / genus:** 2 for plain rotors, 0 where there is a through-bore (motor cup, mixed-flow, prop, print-ready), and −12 for the full shroud (7 handles, as expected).
- **Diameter flags:** 3 flags, none of them a mesh defect:
  - `INVALID_axial_hub_gt_tip`: +20 mm, the disc from bug #2.
  - Full shroud: +3.2 mm, because the ring is by design outside `tip_radius` (2 × (54 + 1.6) = 111.2 mm).
  - Mixed-flow: −0.64 mm, from the frame-clearance clamp by design.
- **Every other STL** has diameter exactly 2 × `tip_radius`, and height within the 25 mm A12x25 depth where that applies.

---

## Bugs

### 1. [HIGH] Geometry/Stock: the Stock A12x25 recipe is cut from 7 stations to 3 when it goes through the flat dict (cockpit Reference, print-ready export, Fit)
- **Area:** `fansim/optimize/search_space.py` `blade_to_flat()` (lines ~314-383), reached through `stock_blade_flat()` (~391).
- **Repro:**
  ```
  uv run python -c "from fansim.optimize.search_space import stock_blade_flat, blade_from_flat; from fansim.geometry.config import load_blade_params; y=load_blade_params('config/problems/a12x25_reference.yaml'); f=blade_from_flat(stock_blade_flat()); print(len(y.stations), len(f.stations))"
  ```
  This prints `7 3`.
- **Expected:** The "◆ Reference · Noctua A12x25" design in the cockpit and `scripts/export_a12x25_print_ready.py` should build the signed-off 7-station refit recipe (`a12x25_reference.yaml`, promoted 2026-09-29, golden test frozen).
- **Actual:** `blade_to_flat` keeps only the stations nearest r_frac 0, 0.5 and 1. It drops r_frac 0.22, 0.38, 0.69 and 0.84, and it re-labels the 0.533 station as 0.5. Measured sections from my two builds (`measure_sections`):

  | r/R | stagger, YAML build | stagger, cockpit/print-ready flat build |
  |---|---|---|
  | 0.45 | 35.3° | 26.6° |
  | 0.55 | 38.4° | 29.1° |
  | 0.85 | 24.7° | 30.0° |
  | 0.95 | 22.2° | 26.7° |

  Single-blade volume barely changes (2074 vs 2083 mm³), so the volume and weight checks don't catch it. STLs: `qa_exports/axial_stock_reference_yaml_9b.stl` and `qa_exports/axial_stock_via_cockpit_flat_9b.stl`.
- **Suspected cause:** The flat dict format only has root/mid/tip slots, and its docstring says "Flatten a 3-station BladeParams". `stock_blade_flat` passes it a 7-station recipe anyway. Nothing warns or raises when stations are dropped. The "⚠ Edited since assessment" banner on a freshly loaded Reference in the UI may be the same issue; that link is unconfirmed.

### 2. [MEDIUM] Geometry: no input validation on axial `BladeParams` / `blade_from_flat` (and mixed-flow `n_blades` / `z_span`)
- **Area:** `fansim/geometry/blade.py` `BladeParams` (no `__post_init__`), `fansim/optimize/search_space.py:213` `blade_from_flat`, and `fansim/centrifugal/geometry.py` `MixedFlowParams.__post_init__`.
- **Repro:** Run `/workspace/fansim/qa/gen_all.py INVALID_axial_hub_gt_tip INVALID_axial_neg_chord INVALID_axial_0_blades INVALID_axial_nan_tip INVALID_mixed_0_blades INVALID_mixed_neg_zspan`. These use the default flat dict with one field overridden.
- **Expected:** A clear `ValueError` for impossible inputs. `VoluteParams` and `WindTurbineParams` already do this.
- **Actual:**
  - `hub_radius=60, tip_radius=50` builds and exports a "valid" watertight single-body STL that is just a 120 mm disc (`qa_exports/INVALID_axial_hub_gt_tip.stl`).
  - `chord_mid=-5` builds without complaint.
  - `n_blades=0` raises `ZeroDivisionError` at `blade.py:280` (`blade_solidity`); `build_impeller` would hit the same thing at `blade.py:784`.
  - `tip_radius=NaN` fails deep in OCCT with `Standard_Failure: Courbes non jointives`.
  - `n_blades=1` builds silently, giving an unbalanced single blade.
  - Mixed-flow with `n_blades=0` or `z_span_mm=-5` passes `__post_init__`, then dies with `ValueError: Null TopoDS_Shape object`.
- **Suspected cause:** Validation exists only for the volute, wind and the mixed eye/back radii. The axial path relies on optimizer bounds, but the cockpit editor and YAML loader can go outside them.

### 3. [MEDIUM] BEM: free-delivery falls back to the sweep's maximum flow when static pressure never crosses zero
- **Area:** `fansim/fan_bem.py:198-203` (`pq_curve`).
- **Repro:**
  ```
  uv run python -c "from fansim.geometry.blade import BladeParams; from fansim.fan_bem import pq_curve; print(pq_curve(BladeParams(n_blades=0),2000).free_delivery_cfm)"
  ```
  This prints **129.0** CFM for a fan with no blades.
- **Expected:** `None`, NaN or 0, plus a flag when there is no zero crossing.
- **Actual:** `free_cfm = pts[-1].flow_cfm` (q_max = 0.6·U_tip·A). Any design whose static rise is already ≤ 0 at the first sweep point is reported at the maximum flow and would rank best in a BEM prescreen. In the same check, `hub_radius > tip_radius` returns 0/0 silently.
- **Suspected cause:** The fallback initialiser was meant for "free delivery is past the end of the sweep" but also catches "never positive".

### 4. [MEDIUM] BEM/polars: angle of attack is clamped to the table edges (no post-stall model), so paddles and reversed blades score as good fans
- **Area:** `fansim/propeller/polars.py:76-86` (`_interp_alpha` clamps cl/cd to the table edge), used by `fansim/fan_bem.py:142`.
- **Repro:** Set every station's stagger and run `pq_curve(...)` at 2000 rpm (`qa/math_checks.py`, `/tmp/bem2.py`).
  - Reference stock: free 58.2 CFM, shut-off 38.9 Pa, peak efficiency 0.536.
  - stagger 89° (axial paddle): **74.8 CFM**, 41 Pa, efficiency 0.558.
  - camber −0.06 at 45°: 79.0 CFM.
  - stagger −45° or −60° (wrong hand): shut-off **+36.8 Pa**, efficiency 0.554.
  - stagger 0°: 20.5 CFM, efficiency 0.585.
- **Expected:** Post-stall, cl should drop and cd should rise toward ~1.2-2 near 90°. A reversed blade should not produce positive pressure at 55 % efficiency.
- **Actual:** For α ≥ ~30°, cl is pinned at 0.769 and cd at 0.10. For α ≤ ~−10°, cl is pinned at −0.276. With negative lift, swirl is driven entirely by the drag term `cd·cosφ` (`fan_bem.py:144`), which still produces a positive Euler Δp.
- **Notes:** BEM is documented as ranking-only. Even so, these cases invert the ranking: the paddle beats stock. The search bounds (stagger ≤ 48°) limit how often the optimizer hits this, but the cockpit editor allows any value.

### 5. [MEDIUM] Test failure: `motor_side()` returns None for a fan with a 5 mm centre bore
- **Area:** `fansim/audit/direction.py:272-283`. Tests: `tests/audit/test_direction_geometry.py::test_motor_side_with_centre_bore[1]` and `[-1]`.
- **Repro:** `uv run --extra dev python -m pytest tests/audit/test_direction_geometry.py -k centre_bore`
- **Expected:** +1 or −1 (the cup side).
- **Actual:** None. `_tip_radius` = 50.00000000000001, so the first probe radius is 0.1·tip = 5.000000000000001. That lies on the bore wall (bore_r = 5.0), where the cut already returns 5 loops. So `r_root` = 5.0, `r_cap` = 4.5, and every probe band falls inside the empty bore: 0 of 64 rays hit. All bands return None.
- **Suspected cause:** `r_root` detection takes the first radius with ≥ 3 loops. It doesn't skip the bore wall or check that the loop count matches the blade count. This may be numerically platform-sensitive (the radius lands exactly on the bore wall, and Linux has no embree), but the logic flaw is real. The sibling `..._with_realistic_centre_bore` passes.

### 6. [LOW] CI: the "Ruff critical" gate fails (F811)
- **Repro:** `uv run --extra dev ruff check fansim tests scripts --select F811,F821`
- **Actual:** `fansim/cockpit/fan_viz.py:46:25 F811 Redefinition of unused Path from line 13`. The `ci.yml` step "Ruff critical" will go red on push. Ruff also warns about an invalid `# noqa` at `tests/test_cockpit_errors.py:48`. `mypy` passes.

### 7. [LOW/MEDIUM] Test failure: new CFD script not registered with the rotor-orientation guard
- **Area:** `tests/test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case` and `scripts/audit_archetype_direction_cfd.py` (mtime 2026-10-02; it calls `build_case` at lines ~105 and ~159).
- **Repro:** `uv run --extra dev python -m pytest tests/test_axial_scripts_oriented.py`
- **Actual:** `AssertionError: audit_archetype_direction_cfd.py: add to AXIAL_SCRIPTS or EXEMPT`.
- **Impact:** The Audit #1 guard (every CFD case is built in the designed rotation) is red, so it is unverified whether this script orients the rotor. Either register the script or exempt it with a reason.

### 8. [LOW] Math: `meanline.camber_from_turning_rad` overestimates camber by about 2×
- **Area:** `fansim/optimize/meanline.py` `camber_from_turning_rad` (m = |ε|/4).
- **Expected:** For a circular-arc camber line, the maximum camber height is (c/2)·tan(θ/4) ≈ θ/8. A NACA 4-digit line gives θ ≈ 2m/(p(1−p)) → m ≈ θ/8.3 at p = 0.4.
- **Actual:** At 10°, 20° and 30° turning the code gives 0.0436, 0.0873 and 0.131; the circular arc gives 0.0218, 0.0437 and 0.0658. The cockpit meanline seed suggests about twice the camber.
- **Everything else in meanline matched hand calculation exactly:** U, Cz, Cu2 (free vortex), W1, W2, Lieblein DF, de Haller, stagger from the disk, and Cordier σ. See `qa/math_checks.json`.

### 9. [LOW] Math/naming: two different "solidity" definitions
- **Area:** `fansim/geometry/blade.py:261-282` `blade_solidity` returns c·cosβ/s, while its docstring says "chord / circumferential pitch". `fansim/optimize/meanline.py` `solidity` returns c/s.
- **Evidence:** Default 7-blade fan, hub/mid/tip: `blade_solidity` gives 1.58/1.13/0.69; c/s by hand gives 1.76/1.26/0.75.
- **Impact:** The `--loadcap` floors (`min_sol_mid`/`min_sol_tip`, `objectives.py:323`) and `printability_score.py:110` use the projected value; the meanline DF uses c/s. Either the docstring or one of the formulas is wrong.

### 10. [LOW] Docs: the README quickstart test command fails after the documented `uv sync`
- **Area:** `README.md` Quickstart, `RECOVERY_TODO.md`, and `pyproject.toml`, where pytest is only in the `[dev]` extra.
- **Repro:** Fresh clone, then `uv sync`, then `uv run python -m pytest -q -m "not docker"` → `No module named pytest`. The RECOVERY_TODO command (`--extra optim`) doesn't add pytest either. CI uses `--extra dev`, which works.

---

## Platform / setup issues (not counted as app bugs)
1. **Test-suite memory:** A single pytest process grows to about 4-6 GB. The full fast suite was **OOM-killed twice** on this 16 GB box (`dmesg`: anon-rss 5.4 GB and 6.3 GB, the second while a chunk was running `tests/test_a12x25_validation_cli.py` … `tests/test_cror.py`). I worked around it by running the suite in 6 sequential chunks and re-running the killed chunk one file per process. This looks like accumulated OCCT/VTK memory, not a single failing test.
2. **Windows-only hardcoded paths:** `scripts/evaluate_noise.py:23-25` and `scripts/evaluate_shutoff.py:27-29` hardcode `E:/Projects/programming_2/FluidX3D`, `FluidX3D.exe` and `C:\msys64\ucrt64\bin`; the README says `../FluidX3D`. `scripts/import_prop_stls.py` uses `C:/Users/Kimball/Downloads/...` as a usage example. These were not run (GPU/LBM is out of scope).
3. **No embree on Linux:** `trimesh.ray.has_embree=False`, so ray tests use the pure-Python intersector. That is slower and possibly numerically different from his PC; it may affect #5.
4. **No git metadata** in the copy, so the uncommitted edits could not be isolated. ruff F checks on `fansim/cfd` and `fansim/centrifugal` are clean.
5. **Docker/OpenFOAM** were not installed or run, per scope. 22 `docker`/`slow` tests were deselected, and the cockpit Assess/Sweep/CFD-refine buttons were not exercised.
6. **Cockpit log noise caused by my probing:** `HTTPBadRequest` from a plain `curl /ws`, `KeyError <session id>` and `ClientConnectionResetError` from headless clients I killed, and the browser console's `405 POST /paraview/` (a trame-vtk probe). These look benign.

## Suspicious but unconfirmed
1. **Shared cockpit UI state:** A fresh browser opened on the CROR tab because an earlier headless client had left it there. Trame state is shared by all clients, which is probably by design. The browser tester should click **FAN · CFD** first.
2. **"⚠ Edited since assessment — the shown CFM/efficiency are for the un-edited design"** appears on a freshly loaded, unedited Reference (see `qa/ui_fan_tab.png`). It may be caused by bug #1; check in the browser.
3. **Fan 3-D viewport:** The first render looked like an extreme zoomed-in close-up. Check that the camera resets after Preview.
4. **Stock YAML blades hang below the hub:** The raw YAML build's bbox z_min is −9.10 while the hub bottom is −8.16, so about 0.94 mm of blade sits below the hub. The print-ready path (after Fit) is fine: the cup measured 13.0 mm deep in the hub and the mount gauge reported OK.
5. **`_root_axial_span` uses `params.stations[0]` without sorting** (`blade.py:626`), while `_interp_stations` and `tip_section_points` sort or use max. Unsorted stations (YAML, `blade_angles`) would size the hub from the wrong station.
6. **[verified fixed `cd136fe`, 2026-10-09: `random_prop_flat(fpv_5inch)` seed 12345 ×8 all trim, max radius ≤ R + 0.046 mm (tol 0.1), all valid]** **`_trim_blade_to_tip_cylinder` can still return an untrimmed blade** if all 4 intersect retries come back empty (`blade.py:1080-1084`), even though the comment says that is what it avoids. This did not happen in my 23 builds.
7. **`build_impeller_preview` doesn't check that `blade_angles_deg` has `n_blades` entries** (`blade.py:841-844`); `build_impeller` does.
8. **`chord_realisation._station_measure_fracs` hard-codes `f < 0.47`** as "inside the hub". That is an A12x25 hub ratio; for hub ratio ≳ 0.47 the root station is measured inside the hub annulus.
9. **Props:** Pitch twist is evaluated at r = hub_r (6.0 mm) and 0.5(hub+R) (34.75 mm), but the loft places those stations at 4.5 and 34.0 mm because of `root_embed` (`propeller/geometry.py:64-67`). The error is small, mostly at the root.
10. **Mixed-flow:** Blades are lofted along a straight eye→tip diagonal while the hub is a cone, so only the root section attaches to the hub. The wall between the motor cup and the cone is about 1.66 mm at z = +2 mm.
11. **Wind scaffold:** `tip_speed_ratio` is not used by the geometry, and Cp saturates for n_blades ≥ 4 (5 and 10 blades give the same Cp, 0.4267). This is a scaffold, as labelled.

## Known recovery gaps (not counted; see RECOVERY_TODO.md and README_RECOVERY.md)
- `RECOVERED-FROM-CHAT` banners remain in `README.md`, `scripts/cockpit.py`, `scripts/export_finalists.py`, `scripts/validate_stl.py`, `scripts/run_baseline.py` and others. RECOVERY_TODO says the source headers were stripped from `fansim/*.py` only.
- `fansim/cockpit/app.py.INCOMPLETE_990base` is still in the tree (marked do-not-use).
- `runs/**`, `catalog/catalog.db`, `exports/**` and `docs/control_images/*.png` are regenerable and absent by design.
- BEM is ranking-only, and absolute CFM is validation-gated (documented in `fan_bem.py` and the README status). #3 and #4 are counted because they invert the ranking, not because of absolute error.
- Stock↔close-ref absolute volume is about 1.4× (RECOVERY_TODO "Provenance / trust").

## UI pass (cockpit in browser, 2026-10-08, no CFD/Assess/Optimize clicked)
Screenshots in /workspace/fansim/qa/ui/. Browser viewport was 1024x594.

- UI-1 HIGH  VOLUTE: Preview then "Export STLs" -> "Export failed: TypeError: object of type 'PosixPath' has no len()". (volute_export_failed_posixpath.png) Likely a Path passed where str/list expected; may be Linux-only, verify on Windows.
- UI-2 MED   FAN: unedited Reference shows "Edited since assessment" on first load; Reset clears it. Possibly tied to the 7->3 station Stock recipe bug. (fan_initial_load_edited_warning_and_framing.png)
- UI-3 MED   FAN: Reset clears the 3-D viewer to empty axes instead of showing the reference fan. (fan_reset_blank_viewer.png)
- UI-4 MED   FAN: "Preview (sec)" takes ~65 s per run (worker ~160% CPU, ~6 GB RAM); progress bar jumps back and forth, spinner looks stuck. CROR Preview ~70 s / Export ~40 s, stuck near 20%. (fan_preview_stuck_running.png, cror_disabled_cfd_refine_looks_enabled_slow_preview.png)
- UI-5 MED   PROP: 5" FPV prop reports 2087 g thrust / 743 W (implausible); polar starts "J=0.00 eta=-".
- UI-6 LOW   FAN: Export STL ~2 min, file only saved server-side (exports/design_100000_*.stl + .step), no browser download; "design_100000" is a confusing name for the stock reference.
- UI-7 LOW   FAN: after Randomize, previous "Saved ...design_100000...stl" message stays on screen. (fan_randomize_stale_export_msg.png)
- UI-8 LOW   FAN: slider tooltip and side label disagree (Chord root 18.0 vs 17.75 mm; 25.0 vs 25.12); tooltips overlap "Blades" label.
- UI-9 LOW   FAN: first-load 3-D view poorly framed under dense schematic arrows; U m/s colour bar reads 3.00/3.00/3.00 (zero range).
- UI-10 LOW  VOLUTE: Preview shows only an opaque casing box hiding the impeller; "RPM" and "Load Pa@50CFM" labels clipped by Outlet panel. (volute_initial_clipped_rpm_label.png)
- UI-11 LOW  MIXED/PROP/VOLUTE: sliders show no numeric values; viewer shows blurry leftover render before first Preview. (mixed_initial_no_slider_values_artifact_viewer.png, prop_initial_blurry_viewer_stop_looks_enabled.png)
- UI-12 LOW  MIXED: Preview renders flat unshaded silhouette. (mixed_preview_flat_unshaded.png)
- UI-13 LOW  PROP Stop and CROR CFD refine look enabled (solid red/orange) while disabled.
- UI-14 LOW  All tabs: tab hover tooltip covers neighbouring tab names after clicking.
- UI-15 LOW  Console 405 on POST /paraview/ at load.


## Re-test 2026-10-09 (master @ 961f953)

**Tracker:** 11 verified (QA-1,2,3,5,6,7,8,9,10, UI-1, UI-15), 0 reopened, 5 not yet fixed (QA-4; UI-4, UI-5, UI-6, UI-11 partly fixed), 9 need a browser pass (UI-2, 3, 7, 8, 9, 10, 12, 13, 14). New: QA-11, UI-16..UI-19.

**Needs a real browser click-through:** UI-2, UI-3, UI-7, UI-8, UI-9, UI-10, UI-12, UI-13, UI-14; also the remaining parts of UI-4 (progress bar), UI-6 (click Export → download link) and UI-11 (leftover render), and a Volute Export click for UI-1.

**Fast suite, Linux, one process (§23.9):** `pytest -m "not docker and not slow"` → 1555 passed, 18 skipped, 22 deselected, 1 xfailed, 0 failed, in 21 min 40 s. No OOM kill (dmesg unchanged). Peak RSS 8.2 GB (sampled every 2 s, `qa/fullsuite_rss.log`), reached about 60–65% of the way through the run (sampler t≈850–885 s); RSS drops between files (down to ~0.7 GB at times), so the `malloc_trim` fixture in `tests/conftest.py` works. Note that the peak is HIGHER than the earlier OOM points (5.4–6.3 GB anon-rss): this run finished only because nothing else was using the box. On a 16 GB box with a browser/cockpit open, a single-process run could still OOM; it is one file (or a few) that peaks, not accumulation. Windows comparison: 1565 passed / 2.47 GB.

**Reconnect stress (UI-16..18):** cockpit from the repo on 127.0.0.1:8080 with an empty run dir; client `qa/ws_stress.py` does the browser handshake (WS `/ws` → `wslink.hello` with secret → `trame.state.get` → `trame.lifecycle.update client_connected` → `viewport.image.push.observer.add`), then closes cleanly / closes without `client_exited` / aborts the TCP connection (no close frame) / sends RST, plus groups of 3–6 overlapping sessions.
- 506 cycles, 0 errors; a fresh session got the full state (422 keys, 0.02 s) after every batch of 25. Server RSS 800→895 MB then flat, threads 19→36 then flat, fds 14 flat, asyncio tasks back to 2 between batches. **Open/close churn alone does not break it.**
- **What breaks it (UI-16):** one client that completes the handshake + image observer and then stops reading (`qa/ws_stall.py`, SIGSTOP; same as a frozen/sleeping browser tab or a dropped Wi-Fi link). After ~76 image pushes the server's send to that client blocks and **no new session can complete `wslink.hello` (probe timed out at 15 s every time for 150 s; HTTP `/index.html` still 200 in 5 ms)**. The 30 s heartbeat fires (`No PONG received after 15.0 seconds` in the log) but does not release it; only killing the stalled client recovers (next probe 0.03 s). Same with 1 or 3 stalled clients. Task census during the hang: `sendWrappedMessage` tasks piling up (6) waiting.
- **Likely code:** `wslink/protocol.py` `sendWrappedMessage` (~l.425–431): every send to every client is `await ws.send_bytes(chunk)` inside one global `async with self.attachment_atomic` lock, with no timeout, so one client whose TCP buffer is full blocks all replies (including the `wslink.hello` reply to new clients). The heartbeat timeout is handled as a message (`wslink is not expecting text message: > No PONG…`) in `handleWsRequest`'s loop rather than aborting the transport, so the blocked drain never wakes. The image pushes come from `vtkmodules/web/protocols.py` `pushRender` → publish to all authenticated clients. Upstream (wslink 2.5.7 / aiohttp 3.14.3), triggered by the cockpit's remote views. Possible fixes (not done): per-client send timeout/abort, close stalled clients on heartbeat failure, or a lower `WSLINK_HEART_BEAT` plus abort.
- **UI-17:** 20 plain `curl /ws` → 20 `KeyError` tracebacks: `handleWsRequest` registers `connections[client_id]` before `prepare()`; when `prepare()` fails, `onClose` hits `del self.unchunkers[client_id]` → KeyError, so `del self.connections[client_id]` never runs (entry leaks, "No more connections" logic never sees an empty dict). Abrupt disconnects produce 46 `Cannot write to closing transport` tracebacks per ~500 cycles; `_quiet_connection_reset` in `app.py` only filters the loop exception handler, not wslink's logger.
- **UI-18:** (correction 2026-10-09: the live code is `trame_vtk/modules/vtk/protocols/publish_image_delivery.py` `add_render_observer`/`tracking_views`, same logic.) `addRenderObserver` increments `trackingViews[...]["observerCount"]`; there is no `onClose` hook, so tabs that vanish without `observer.remove` are never subtracted and the observers are never removed.


## Re-test 2026-10-09 (2): branch `qa-fixes-2026-10-09` @ d781894

**Result:** 7 verified (UI-5, UI-16, UI-17, UI-18, UI-19, QA-11, suspicious #6 / §23.32). 0 reopened. 7 need a browser pass (UI-4, 8, 9, 13, 20, 21, 22). QA-4 is still open (patch not applied). New: QA-12 (CT0 rpm creep, LOW).

**Websocket checks** (`handoff/2026-10-09_from-qa/ws/ws_suite.sh`, same launcher and run on both builds, empty run dir, Linux):

| check | 961f953 | d781894 |
|---|---|---|
| A: 20× plain GET `/ws` | +20 `KeyError`, `connections` 0→20 (leaked) | +0, `connections` 0 |
| B: 30 observer sessions aborted (no close frame) | `observerCount` 30 | `{}` (released) |
| C: 1 frozen client + 200 image pushes | pushes stuck at 76; every fresh-session probe timed out (15 s) for 65 s+; healthy only 5 s after the frozen client was killed | 200/200 pushes in ~16 s; probes 0.25–0.38 s all along; frozen client dropped after ~15 s (`not reading for 15 s` warning, once); with 1500 pushes, fds 16→15 between t=16 and t=21 s |
| D: 506 cycles (clean / no-exit / abort / RST / 3–6 concurrent) | 0 errors, probes OK, observerCount → 538 | 0 errors, probes OK, observerCount `{}`; 41 s vs 21 s (each new session re-adds its observer and triggers a first render) |
| server after D | RSS 909 MB, 36 threads, 14 fds | RSS 952 MB, 36 threads, 14 fds |
| log counts | KeyError 20, closing-transport 15, No PONG 1 | 0, 0, 0 |

Observation (not filed): server RSS rose by about 60–100 MB during the stall test (903→966, and 952→1009 with 1500 pushes) and did not drop after the client was dropped. That looks like allocator retention, not growth: it stayed flat over the next 70 cycles.


## Re-test 2026-10-09 (3): master @ e48a32d

**Non-browser items:**

| item | result |
|---|---|
| UI-16 / UI-17 / UI-18 on master (regression) | still verified. 1 frozen client + 200 pushes: probes 0.33–0.39 s, 200/200 pushes. 20× `curl /ws`: 0 KeyErrors, 0 leaked connections. Observers `{}` after aborted sessions and after 506 cycles (0 errors). Log: `handoff/2026-10-09_from-qa-2/ws_regression_e48a32d.log` |
| `9482929` `FANSIM_WS_GUARD=0` | verified: with it set, 20× `curl /ws` gives 20 KeyErrors and 20 leaked connections, i.e. the 961f953 behaviour |
| `e7d8174` QA-12 GWS test | verified: `tests/test_prop_uiuc_gws.py` passes (3 tests), and its three data files are byte-identical to the UIUC zip extract and the QA handoff copies |
| `19fcc45` §23.39 mesh floor | verified in code only (no CFD): `ASSESS_SURF_MAX_FLOOR = 4` is used by axial Assess / `objectives.py`, and `surf_max` is stamped on the trial; `test_design_names` passes (9) |
| UI-4 / UI-9 / UI-20 (`0354b3c`) | headless pre-checks pass: `preview_motor_cup` = False on load, `preview_pct` = 0; the served template has `aspect-ratio:3 / 2` and the `✎ Edited copy of` selection slot. **Browser pass still needed** (checklist B1a–c, B3a–b, B7) |
| UI-23 | open, needs one discriminating run (r4): please reload 3× on **961f953** (pre-guard) or with `FANSIM_WS_GUARD=0`. If it still fires, it's upstream trame-client; if not, it's ours. My Windows Chrome-pane runs (1 tab, guard on/off, master) never captured it. Earlier: no headless check possible; checklist B10 |

**Linux fast suite, one process (§23.9):**
- **Result:** 1573 passed, 18 skipped, 23 deselected, 1 xfailed, 0 failed, in 20 min 44 s. No OOM.
- **Peak:** 8192 MB, held by **`tests/test_mount_gauge.py::test_gauge_accepts_carved_stock_export`**. That test alone peaks at 7.7 GB in the in-process OCCT fuse of the motor-cup hub + 9 blades. `MALLOC_ARENA_MAX=2` brings it to 6.4 GB.
- **Top 5 files by peak:** test_mount_gauge 8192, audit/test_cror_mixed_setup_audit 6454, test_cror 6402, test_notched_tips 4220, test_isolated_build 3532 (MB).
- **Comparison:** round 2 was 8.2 GB / 1555 passed; Windows was 2.47 GB.
- **Data and scripts:** `handoff/2026-10-09_from-qa-2/memory/`.

**Research results from the other QA worker (round 3; details in `handoff/2026-10-09_from-qa-2/README.md`):**
- **QA-4 and QA-12:** see their tracker rows.
- **Noise leads #1 (rotor–strut tone, Tyler–Sofrin) and #2 (ECMA-418-1 tonality via MoSQITo):** worth-it/proposed, small effort. Notes: `docs/qa/notes/noise-lead-1-rotor-strut.md`, `noise-lead-2-ecma418.md`.
- **Screen r3:**
  - What it is: axial-force mode, `max_camber` up to 0.10, 30-design shortlist in `handoff/2026-10-09_from-qa-2/screen_r3/`.
  - Top 5: T06592, T05252, T04536, S03681, S01272.
  - They beat Stock only under the axial model; euler ranks them below Stock. They sit at the edges of the search space, so CFD on them mainly tests the axial model.


## Round 3 browser results (master e48a32d, 2026-10-09 14:40 MDT) and B1 diagnosis

Checklist with results: `docs/qa/browser_checklist_2026-10-09_r3.md`. Screenshots: `docs/qa/screenshots/2026-10-09-r3/` (11 png).
- **Verdicts:** UI-4 **reopened**; UI-9 **verified** (other tabs' model framing not judged); UI-20 **verified**; UI-23 **still open** (1 tab, at unload).
- **Checklist correction:** the motor-cup switch is in the Fan tab's **'Export options'** panel (`fan_tab_ui.py:1220`), not 'Assess & print'. Claude's changelog and the `fan_core.py` comment say 'Assess & print'.
- Also seen in the console (no action): the trame-vtk warning 'Set value to model directly labels'.

**B1 / UI-4 diagnosis (code reading plus 3 headless timing runs; scripts in `handoff/2026-10-09_from-qa-2/b1/`):**

1. **Stage 1 isn't written before the CAD kernel loads.**
   - `_build_worker.main()` does write stage 1 before its own imports.
   - But the worker is started as `python -m fansim.geometry._build_worker`, and that imports the package `fansim/geometry/__init__.py` first. The package imports `fansim.geometry.blade` (CadQuery/OCP) before `main()` runs.
   - Measured with a 20 ms poll of the progress file: stage 1 appears only at **2.1–2.2 s**, which is the kernel load. That matches the browser's 2.2 s of 'starting build process'.
2. **Stages 2 and 3 are written but last only milliseconds.**
   - 'reading design' and 'realising chords' (chords are disk-cached) take under 20 ms each, so a 20 ms poll never caught them.
   - Stage 4 lands at **+0.36 s** after stage 1. The UI ticker samples about once a second, so 1–3 can never be seen.
   - Stage 5 in the fast path ('writing mesh') lasts about 70 ms (4.93 s → 5.0 s), so it's missed too.
   - Net: the bar is effectively 2 % → 60 % → done.
   - Possible fixes (proposals, not done):
     - write stage 1 from a module with no package import, or have the parent write it before spawning;
     - split stage 4, the only long one;
     - or have the caption show the latest stage *reached* rather than the current one.
3. **The 'lofting blades + hub' label** is the fast-path (motor cup off) build label at `_build_worker.py:31`. The cup path says 'building + carving motor cup', and the full non-cup build says 'building + fusing solid'. It's correct, but the changelog's stage list didn't name it.
4. **Freeze during 'writing STL' (cup on):**
   - Headless, with the cockpit itself triggering the Preview (`trigger__11`, motor cup on) and a second session timing a `trame.state.get` round trip every 0.25 s:
     - the event loop stayed responsive through stages 4 and 5 (0.02 s);
     - stage 5 ran 52.2 → 55.1 s;
     - the only block was **1.6 s** at completion, when the cockpit process loads the STL, re-renders the remote view and runs `spec_status` on the loop.
   - Measured pieces: `pv.read` of the 4.7 MB cup STL 0.07 s; `trimesh.load` + volume 0.22 s; `grade_printability` 0.04 s. So the rest is the VTK render and image push.
   - The worker itself peaks at **7.6 GB RSS** during the cup build (the same fuse that sets the test-suite peak). On the 16 GB, no-swap box with Chrome open, the extra 7–10 s stall in the browser run is most likely **memory pressure** around the end of the fuse and the tessellation, not GIL or main-thread STL reading. `run_worker_module` uses `subprocess.run`, which releases the GIL. I couldn't confirm this headlessly: my run had 10 GB available.
   - **The lost numeric value** on the bar was not reproduced headlessly: `preview_pct` went 60 → 80 → 0 together with `preview_busy` → False. It may be the client-side bar while frames were delayed. Unexplained.
   - Headless Preview times on this box: fast path 5.0 s (worker); motor cup 52.6 s (worker), 56.8 s end to end.
5. Cockpit state was reset afterwards: `preview_motor_cup` = False (the default), not busy.


## Re-test 2026-10-09 (4): master @ f238f54 (clean clone `/workspace/fansim/repo-r4`)

- **Slow suite (request 4), one process, Linux:** **22 passed, 2 skipped** (pythrust not installed; `propulsion` extra), 418 s. Overall peak **8003 MB** HWM in `test_objectives_orientation.py::test_build_case_gets_flipped_rotor_and_fitted_rig` (the Stock fuse). Per-file: objectives_orientation 7998 MB / 51.8 s; blade_le_leads 7400 / 51.4; stock_handedness 7334 / 66.9; features (3) 6777 / 104.0; prop_builder_direction (3) 3210 / 87.5; prop_cfd 1791 / 17.6; tip_trim 1511 / 20.4; wind_turbine 1215 / 5.1; midplane, cockpit_viz, spanwise, volute < 800 MB, < 5 s each. Details `handoff/2026-10-09_from-qa-3/slow/README.md`.
- **Cup-fuse memory (request 5): no strategy passes; no patch** (QA-15). Pre-registered `docs/qa/notes/cup-fuse-memory-criteria.md` (sha256 `f8fcc8bb…d5fee9`). B 7657 MB / 73 s; S1 sequential 5219 / 170 s; S2 tree 8050; S3 serial booleans **4891 / 85 s**; S4 2-thread pool 6522; S5 isolated worker 7698; S6 S1+S3 4460 / 200 s; S7 arena 2 6314. All geometry byte-identical (Hausdorff 0). The whole +5.7 GB is the one `hub.fuse(*blades)` call and it stays resident afterwards. Note `docs/qa/notes/cup-fuse-memory.md`.
- **Export / STL (request 6), Stock and 9504 with mirror pair, cockpit path:** E1–E6, E9–E12 **PASS** (watertight, consistent winding, 1 body, Euler 0, tip Ø 109.00 / 108.94, depth 17.44 / 22.00, 20 grip pads at 0.70 mm, 9 / 10 blades, mirror is an exact reflection: Hausdorff ≤ 1e-10 mm, Δvol 0, handedness flips). E7 failed only because the pre-registered value was wrong (cup is 37.25 + 2×0.35 clearance = 37.94 by design). E8 → QA-16. Duplicate build and gauge noise → QA-17. Details `handoff/2026-10-09_from-qa-3/export/README.md`.
- **Docs audit (request 8):** DOC-1..5 above; `docs/qa/notes/docs-claims-audit-2026-10-09.md`.
- **Requests 1–3 (other QA worker):** QA-4 row, QA-4b, QA-13, QA-14; notes `docs/qa/notes/r4-*.md`; `handoff/2026-10-09_from-qa-3/README.md`. `results/xcheck_dump_*.jsonl.gz` are gitignored.
- **Browser prep:** `docs/qa/browser_checklist_2026-10-09_r4.md` (UI-4 B1a–c, UI-23 B10a–c, request-7 first-time-user B11 at 1366×768 / B12 at 1920×1080). Cockpits: :8080 master f238f54, :8081 961f953 (pre-guard), :8082 master with `FANSIM_WS_GUARD=0`.

### Round 4 browser results (2026-10-09 16:34 MDT; checklist `docs/qa/browser_checklist_2026-10-09_r4.md`)
- **UI-4:** B1a/b/c **reopened**; diagnosis is in the tracker row (stale box-global progress file read before the stage-1 overwrite; `max()` keeps the bar high; stage 2 ms-long with cached chords; post-build work blocks the event loop ~3.4 s).
- **UI-23:** 0/9 reloads across 961f953, guard off and master: **not reproduced**, intermittent, LOW/open.
- **Newcomer pass (B11 1366×768, B12 1920×1080):** UI-24 (HIGH), UI-25, UI-26, UI-27 (MED), UI-28, UI-29 (LOW). Export wasn't clicked, so where the STL lands wasn't checked. New from code reading: UI-30 (shared /tmp preview path).
- **Cockpits:** :8081 (961f953) and :8082 (guard off) stopped after the pass; :8080 (master f238f54, empty run dir) left running.

## Round 6 (2026-10-10): master @ 31228d0 (clean clone `/workspace/fansim/repo-r6`)

- **Task A, builder stress test: partial. Stopped early by Kimball; n = 120 of 801 planned** (S1 14, S2 14, S3 14, S4 14, S5 14, S6 14, S7 13, S8 18, CTL 5).
  - Prereg `docs/qa/stress/PREREG.md`, committed in the QA-only clone `/workspace/fansim/qa/prereg_r6`: A0 `30ea579` (sha256 `3e716d56…dfa602`); amendments `5cf4a3a` (sha256 `d3379f0e…4bbb3`).
  - Results: K1 1/120 (QA-21); K2, K3, K4 0/119; K5 7/119 FAIL + 24 INCONCLUSIVE (QA-19); K6 0/95; K7 3/29 (QA-18); K8 0/11 FAIL but 0/11 byte-identical (QA-20); K9 0/11; K10 0/3; K11 0/120.
  - **Slowness:** about 6 min per design was box freezes, not builds. Six P builds account for about 6.1 h of 7.1 h wall time while their monotonic time was 33–128 s; total build CPU was 0.65 h. No memory waits.
  - Outputs: `handoff/2026-10-09_from-qa-5/stress/` (summary.md, PILOT.md, repro/, designs.jsonl.gz, inputs.jsonl.gz [gitignored], scripts).
- **Task B, direction check attempt 2 (option a): done on partial stress data (n = 120 of 801).** Option (a) removes all 7 K5 false refusals, adds 0 new refusals, and catches 95/95 K6 mirrors. P1, P2 and P4 PASS; P3a, P3b and P5 are untested (they need a build or a patch). Also: 8 of the 24 INCONCLUSIVE have proper camber but their sections disagree, a separate proof weakness. Task A doesn't log chirality; it should (runner follow-up). Disclosure: B's criteria weren't hashed before the data existed; the hash was recorded at evaluation. Note `docs/qa/notes/direction-attempt-2.md`.
- **Task C, motor efficiency:** done. eta_motor 0.50 (0.40–0.65). 1.68 W is the start-up maximum; measured draw is 1.0–1.5 W. The 5–7 % derate is mostly an artefact.
- **Task D, published fan test-data library:** done. 8 fans, 3 with full geometry. Both BEM models are within 3 % at free air and about ±30 % mid-curve. Licence decisions are needed: Cybenetics cited only; nv150 is CC BY-NC-ND, not MIT-clear; NF-A12x25 STL provenance.
- **Task E, near-stall flag:** not started.

## Round 7 (2026-10-11): master @ 5980677 (clean clone `/workspace/fansim/repo-r7`)

- **Task A, settings changed while a job runs: done.**
  - Note: `docs/qa/notes/settings-during-run.md`.
  - Prereg: `settings-during-run-prereg.md`, committed in `/workspace/fansim/qa/prereg_r6` as `43ce868`.
  - Harness and output: `docs/qa/settings_during_run/`.
  - **4 defects and 1 display note: QA-22 to QA-26.**
  - Optimize, Export, the airflow pictures and the Fit actions pass. The airflow pictures are protected by a generation/token guard; the Fit actions are synchronous.
  - Every geometry snapshot is correct. Only the score and lineage **stamps** read live state.
  - Recommendation: snapshot at start and say so, for Assess, Sweep and Mixed Assess.
- **Task B, stress test on new master: TRUNCATED at 65/801 by user decision** (box suspended for hours at a time). Results: `docs/qa/stress/RESULTS_R7.md`. 0 errors; K1, K3, K4, K6–K11 0 FAIL; K2 1/65 (S6_0019, one 9.75e-10 mm² sliver on a watertight 1-body mesh: threshold artefact, not filed); K5 1/65 FAIL + 16 INCONCLUSIVE (S3_0014, residual QA-19); K12 62/65 FAIL (QA-27). QA-18 and QA-21 verified fixed; QA-19 fixed on all 7 r6 cases with one new residual. Runner clock issue filed as QA-28 (LOW).
  - PREREG amendments 5–12 (K5 new rule, K12, chirality logging, memory gates) were committed as `854fc85` (sha256 `170a889a…bcef2a0`) before any build.

- **Task C, lt120 as `BladeParams` (other worker): done.**
  - Stagger PASS. Chord, camber and t/c FAIL.
  - Cause: fansim's planar sections vs the paper's cylindrical sections, plus a low-biased camber measurement.
  - A CFD proposal is written. See `docs/qa/notes/lt120-conversion.md` and `docs/qa/benchmarks/lt120/`.
- **Task G, flow-report math (other worker): done.**
  - G1 PASS 16/16.
  - G2 FAIL: a silent NaN on zero flow, on zero weights and on coarse-mesh empty bands.
  - Excluding swirl is correct but incomplete.
  - The ±15 % / 2.8 dB thresholds rest on one non-repeat pair. Proposal: 3–5 repeats and a 2σ threshold.
    **Done 2026-10-14:** baked ±3 % / +0.5 dB from five Stock v3 repeats (r4 hub bar after-bake FAIL, not widened).
  - See `docs/qa/notes/flow-report-math-check.md`.
- **Task F, external-STL stacking cut (other worker): done, DO NOT ADOPT.**
  - F1, F2 (68.5 %), F3 and F6 FAIL; F4 and F5 PASS.
  - A radial-plane variant had 0 wrong reads on 67 parts. It was not pre-registered, so we propose a pre-registered confirmation.
  - Prereg `PREREG_R7.md`, sha `c163f1d7…0e6e`, commit `2073315`.
  - See `docs/qa/notes/direction-stacking-cut.md`.
- **Task D, near-stall flag:** not done.

## Round 8 (2026-10-12): master @ f86df9a (clean clone `/workspace/fansim/repo-r8`)
Prereg for B, C and D: `6b0aedf` (branch `prereg/round8`, `/workspace/fansim/qa/prereg_r6`), sha256 `b958dda3…ec67e9`; copy in `docs/qa/PREREG_R8.md`. Handoff: `handoff/2026-10-12_from-qa-8/README.md`.
- **Task A, settings changed during a run: PASS.** QA-22..25 verified fixed; QA-26 partly fixed (Assess-existing material stamp only; caption, Export message and view jump unchanged, as planned in 27.5). New **QA-29** (LOW): the Done message is overwritten by the busy caption. `docs/qa/notes/settings-during-run-r8.md`.
- **Task C, fuse memory at the call: pre-registered comparison FAIL 21/22.** Single-process Linux VmHWM = 1.02 GB + 92.5 KiB/face; increment after the call = 0.28 GB + 72 KiB/face. The guard as implemented covered the remaining growth on 20/22 (fails on shrouded S7_0013). QA-27 updated. `docs/qa/notes/fuse-memory-at-call.md`.
- **Task B, radial-plane direction confirmation:** R1–R4 PASS (0 wrong, 54/54 cambered); R5 FAIL (79.6 % read); R6 FAIL (flipped parts not refused by a design-sign rule; 5 unreadable flat mirrors). The brief's −0.03 camber builds flat blades (deviation, v2 rebuilt). `docs/qa/notes/direction-radial-confirmation.md`.
- **Task D, built blade vs numbers: MATERIAL.** New **QA-30** (hub-face clip shortens chord; realisation doesn't see it; explains lt120) and **QA-31** (leaned/skewed blades: cut camber far below the slider; the chord stretch makes it worse). Not a chord/r effect. `docs/qa/notes/built-vs-numbers.md`.
- **Task E:** not done.


## Round 9 (2026-10-12): branch `cylinder-sections` @ 7b02bed (clean clone `/workspace/fansim/repo-r9`)
Prereg `a0260c0` (+ A1 `9438a9b`). Summary in `handoff/2026-10-12_from-qa-9/README.md`.
- **QA-32 (MED, new):** at stations the hub-face clip reaches, the chord is now restored (QA-30 fix verified), but the
  built camber is 0.005–0.011 below the slider and the stagger is up to 1.1° off. About 15 % of stress designs have
  such a station. `docs/qa/notes/built-vs-sliders-wrapped-r9.md`.
- **QA-33 (LOW–MED, new):** on wrapped builds the cylinder direction proof is INCONCLUSIVE more often (30/65 vs 24/66
  planar; Task A final, truncated at 66/150 by user decision), all "no cambered sections". `docs/qa/notes/wrapped-builder-robustness-r9.md`.
- **27.1 (QA-27) refined:** shrouded fuse peaks exceed the guard on 9/11-blade rings. The extra cost scales with the
  blade face count, not with ring faces or ring height. `docs/qa/notes/shroud-fuse-memory-r9.md`.
  **Closed 2026-10-13** (remaining-growth guard + per-platform shroud term).
- C surface fit: T1/T2 PASS, T3 FAIL. D radial-led rule: unconfirmed, because the truth method proved unreliable.
- Task A (final, 66/150 by user decision): W2, W4 and W5 PASS. W1 FAIL ×1 (OOM-like kill, 7.7 GB) and W3 FAIL ×1 (shrouded, 1.6× CPU).


## Rounds 10 + 10b (2026-10-13): master a09905a (wrap merge ae3f1c4), clean clone `/workspace/fansim/repo-r10`
Prereg `26aa359` (A, B and C in one commit). Summary in `handoff/2026-10-13_from-qa-10/README.md`.
- **Task A (print-ID mark-spec): M1–M3 PASS.** The +Z hub ring (r 10–21.45 mm) is flat over 360°. The dummy 8×3.2×0.5 recess
  stays one solid and watertight, the cup stays at K7, and the roof is 3.0 mm. Aero ratio 1.76 % (> 0.5 %).
  `docs/qa/notes/print-id-mark-spec-r10.md`.
- **Task B (wrap confirmation, 40): W2–W5 PASS. W1 and W6 FAIL ×1 (S5_0184).** 2 designs refused (hang), fuse fallback 0/38.
  `docs/qa/notes/wrap-confirmation-merged-r10b.md`.
- **QA-34 (MED, new):** featured wrapped S5_0184 (tubercles + serrations + dimples). The B-rep fuse gives 1 solid, but the STL
  is not watertight (8 bodies, 7 degenerate faces). Planar is clean. `fuse_impeller`'s one-solid check passes, so nothing
  flags it. Mesh: `handoff/2026-10-13_from-qa-10/data/S5_0184_Pc.stl.gz`.
  **Closed 2026-10-14:** those 8 bodies are 1 watertight impeller + 7 zero-area needles. `sanitize_stl` after tessellation.
- **QA-32 verified closed (Task C):** 49 allowed hanging designs, 105 stations, 0 outside chord 3 % / camber 0.005 / stagger 1.5°
  (max 2.9 % / 0.0048 / 1.46°, thin margins). The hang limit refuses exactly the designed > 2 mm (19/400). evaluate_candidate
  returns infeasible with a plain message. `docs/qa/notes/hang-limit-correction-r10b.md`.
- QA-33 still stands (B: 18/38 wrapped INCONCLUSIVE). D not run (no 27.1 patch). E not done.

## Round 12 (2026-10-14): master 143d5a8, run clone `/workspace/fansim/qa/run_r12`
Prereg `42004b3` (A–E). Summary in `handoff/2026-10-14_from-qa-12/README.md`.
- **Task A (QA-34 strip): F0 + F1 PASS.** S5_0184 and 2 new featured wraps (seed 11013) are each 1 watertight body, 0 degenerate faces, B-rep 1 solid.
- **Task B (27.1 remaining): FAIL 1/26.** S7_0172_twin at 1.032× the ask (3/3 repeats). Shroud term fine. → **QA-35 (MED, new)**.
- **Task C (28.2 print-id): P0–P4 PASS** on a real cockpit Export of Stock (SB862). → **QA-37 (LOW, new)**.
- **Task D (PLA+):** Preview grams and Export README/temps/sidecar/registry stay PETG via `active_spec().material`. → **QA-36 (MED, new)**.
- **Task E:** 4 headless proposal tests; the 2 material tests fail on HEAD (intended).

## Round 13 (2026-10-14): master 143d5a8, run clone `/workspace/fansim/qa/run_r13`
Prereg `02584e6`. Summary in `handoff/2026-10-14_from-qa-13/README.md`.
- **Task A (24.2): S0–S3 PASS** headless in the browser. S4: scatter mostly below the fold at 768 px → **QA-38 (LOW, new)**.
- **Task B:** duplicate-after-Preview table (report only). No cached Assess on disk.
- **Task C (23.9): M0 PASS, M1 PASS.** 1777 passed, 0 failed; no OOM in the run window. Peak RSS per chunk 5.1 / 2.9 / 6.9 GB (was 8.2 GB in one process); 45 min active time. `docs/qa/notes/pytest-chunks-r13.md`
- **Task D:** the other tabs ignore ui_mode; Expert-only candidates listed.

## Round 14 (2026-10-16/17): master 9562574, run clone `/workspace/fansim/qa/run_r14`
Prereg `586bbe9` (`prereg/round14`; A, B, C, F). Summary in `handoff/2026-10-16_from-qa-14/README.md`.
- **A1 (QA-35): PASS.** 26 OK pairs, 0 over the ask; worst open 0.85, S7_0172_twin 0.826 (was 1.03). → QA-35 verified.
- **A2 (QA-36 / 24.4):** tests 6/6 PASS. Browser PLA+ Export is PLA+ everywhere (README 215/60 °C, print_fit, index).
  The Preview line names no material, and PLA+ and PETG both round to 11 g (20 % infill) → **QA-42 (LOW, new)**.
  The switch-during-Preview check is INCONCLUSIVE.
- **A3 (QA-37): PASS** when the killed launcher is reaped (worker gone in 0.75 s, `.partial-*` only). If the launcher
  is left a zombie, the worker lives on → **QA-41 (LOW, new)**.
- **A4 (27.3b): FAIL**, "No Stock comparison for noise." in Simple mode → **QA-40 (LOW, new)**.
- **B maths:** `_pp_file` string-sorts time dirs → **QA-39 (LOW, new)**. B5: the hang-refusal ratio (median 1.85×)
  is explained by the loft stretching mid chord and stagger (the 2 mm limit is checked on designed chords; doc
  note / Kimball). `docs/qa/notes/maths-check-r14.md`
- **C (27.7):** guided bounds exclude Stock's root and mid stagger. C3 FAILS 3/80 as registered (tip stagger
  measured at 0.99 R against the r=1.0 value; 0/80 over 1.5° on a matched radius). Proposed bounds give 4.3 %
  refused. `docs/qa/notes/optimizer-space-wrap-r14.md`
- **D (QA-12 data):** vendored e387 tables are shaped, not measured. NASA TM-4062 is the best source.
  `docs/qa/notes/prop-ct0-data-sources.md`
- **F (27.3d):** margins proposal (v3 numbers, superseded by v4). `docs/qa/notes/flow-margins-two-run-r14.md`

## Round 15 (2026-10-17): master 9562574
Prereg `336211b` (`prereg/round15`). Summary in `handoff/2026-10-17_from-qa-15/README.md`.
- **A–C (R2.3–R2.5 data hunts):** CROR best is Shigemitsu 2018 (CC BY 4.0, 40 mm). Mixed-flow: no small CC data
  found (85 mm Treder rig, cite-only). Centrifugal best is EPJ WoC 180:02023 (60 mm, CC BY 4.0, to confirm).
  `docs/qa/notes/r15-data-hunt-cror-mixed-centrifugal.md`
- **D (R0.1 / 27.3e re-check):** slab positions, mm→m and hub exclusion agree with the hand derivation (D1, D2, D4
  PASS). The synthetic swirl field shows the push is swirl-independent outside the row (D3a FAILS as registered on
  a grid tie and passes on a 59-cell grid). With the legacy in-row inlet slab, push falls steadily with swirl, 13.40 → 1.36 Pa at S 0 → 1.5 (D3b FAILS as
  registered on direction: I predicted a rise). That matches the audit's symptom and supports the fix. Doc notes: stale `flow_report.py`
  docstring, audit says 25 vs 20 cases. `docs/qa/notes/r15-push-planes-recheck.md`
- **R3.3 install guide: NOT RUN.** The guide is not written yet. The Quickstart dry run in a fresh clone is OK.
  `docs/qa/notes/r15-install-dry-run.md`

## Round 16 hang (2026-10-17): master 9562574, run clone `/workspace/fansim/qa/run_r16`
Prereg `52eca5f` (`prereg/round16-hang`). Note `docs/qa/notes/hang-investigation-r16.md`; data
`handoff/2026-10-17_from-qa-16-hang/`.
- **QA-43 (MED, new) Geometry/validator:** the 2 mm hang limit is checked on designed geometry. The chord fixed point
  measures the clipped blade and refills the clipped chord, which drops the TE by half the clip again: built hang =
  1.75 × designed in 2 iterations (measured median 1.77, n = 140). On 300 CAD designs, 50 of the 123 cut deeper than
  2 mm pass the validator. Proposal: validate on 1.75 × designed (no-CAD, 100 % sensitivity and 1–2 % false refusals on
  feature-free designs), or on the cached realised loft. Alternatively, stop compensating for chord the clip removes on
  purpose (weigh this against QA-30).
- **QA-44 (MED, new) Optimizer vs Export hub:** the optimizer and CFD validate and score with the auto hub (often
  < 15 mm), while a12x25 Export and cup Preview grow it to 15 mm symmetrically. The clip plane moves by up to 3.3 mm.
  54/141 designs refused at the auto hub pass at the export hub, and 171/291 allowed hanging designs print with a TE
  different from the one scored (118 are not cut at all). Proposal: apply min_hub_height in the search, with the growth
  placed below the blades (blade_hub_z = +Δh/2).
- **QA-45 (LOW, new) Cup carve message:** with hub r 19.4 < 20.7 (S8_0056), `build_impeller_with_mount` raises "did
  not join into one solid (3 separate pieces)" both with and without the hang fix, instead of the plain "hub radius too
  small" message other undersized hubs get.

## Round 17 (2026-10-19): master 46a3408, run clone `/workspace/fansim/qa/run_r17`
Prereg `a212b29` (`prereg_r6` branch `prereg/round17`, `qa_r17/PREREG_R17.md`, committed 12:34 MDT before any data).
Summary in `handoff/2026-10-19_from-qa-17/README.md`. Box only. No CFD, Docker or OpenFOAM, and no fansim edits.
- **A (R2.2a) reference polars:** the section is fansim's `naca4(0.04, 0.4, 0.06)` = NACA 4406 (closed TE). At
  Re 8×10⁴, α 4° the reference is **CERTAIN**: C_l 0.855 [0.847, 0.863], C_d 0.0201 [0.0199, 0.0204] (NeuralFoil and
  XFOIL at Ncrit 9, spread 1.9 % / 2.5 %).
  - The measured anchor (NASA TM-4062 E387, public domain) has the Ncrit-9 tools **about 8 % high on C_l** at 1×10⁵,
    and all tools 13–20 % off at 6×10⁴. So **6×10⁴ is UNUSABLE** as a reference, and Ncrit 5 fails the C_d anchor
    (−30 %).
  - `docs/qa/notes/r17-A-reference-polars.md`, `docs/qa/r17/r17-A-*.csv`.
- **B (R2.3, R2.5) digitising:** both papers are CC BY 4.0, confirmed from the PDFs. Every check passed: B-cal 5/5,
  B-rep 63/63 re-reads within 2u, B-text 5/5.
  - Shigemitsu: only the total P–Q is measured (21 points, peak 510 Pa at 0.55 m³/min, 0 Pa at 1.08). The per-rotor
    curves and the efficiency are the authors' CFD → **QA-47**.
  - EPJ: the plastic wheel at 6000 / 9000 / 11 000 rpm (vector exact). No curve reaches 0 Pa → **QA-48**.
  - `docs/qa/notes/r17-B-digitised-cror-centrifugal.md`, `docs/qa/r17/r17-B-*.csv`.
- **C (R1.3/1.7/1.8):** the r14 P0 bounds with both fixes give **2.0 % refused** (Wilson 0.9–4.3 %): **PASS**, no
  bounds change needed. R1.8 alone gives 7.7 % and R1.7 alone 0.3 %.
  - On the 300 r16 designs: today 24.3 %, (i) 42.3 %, (ii) 10.7 %, both 19.3 %.
  - Built check at the export hub: 57/58 caught (the miss is a feature design), 0.4 % false refusals.
  - The 1.75× rule on the r16 built data misses one feature-free design, S2_0269 (1.997 predicted, 2.25 built) →
    **QA-46**. `docs/qa/notes/r17-C-hang-refusals.md`.
- **D (R3.1 export leak check): WAITING.** R3.1 hasn't landed, so nothing was run.
- **QA-46 (MED, new) Geometry/R1.8 acceptance:**
  - With `HANG_BUILT_FACTOR = 1.75`, S2_0269 (feature-free) is allowed at 1.997 mm predicted but builds 2.252 mm. So
    R1.8's own rule "every design with built hang > 2 mm is refused" fails 1/123 on the r16 data.
  - No constant factor meets both R1.8 rules: 1.78× catches it but refuses 4.5 % (> 3 %).
  - Options for Claude: record the FAIL, validate on the realised loft, or re-register before the run.
- **QA-47 (LOW, new) Prereg/R2.3:**
  - In Shigemitsu 2018, the per-rotor ΔPs, the 77 % rear share and η_s are the authors' URANS, not measurements. The
    2026-10-18 prereg's S1 (rear share) would therefore compare CFD with CFD.
  - Table 1 also gives stagger without saying which convention it uses (the values rise hub → tip, which suggests
    the angle is from the axis), and gives no camber or blade angles, which step 0's section rule needs.
- **QA-48 (LOW, new) Prereg/R2.5:**
  - EPJ 180:02023 never reaches free delivery: the last points are about 208 Pa at 278 L/min at 9000 rpm, because of
    the stand's own resistance. So the A1 points "0.4/0.7/0.9 × measured free delivery" are undefined.
  - Its pressure is the outflow-tube "working pressure p_b", and the volute has no scaled drawing (Fig 2 is a
    render), so the log-spiral fallback applies.

## Round 18 (2026-10-20): master 1c86f65 (fansim code identical to 46a3408), run clone `/workspace/fansim/qa/run_r17`
Prereg `5df5059` (`prereg_r6` branch `prereg/round18`, `qa_r18/PREREG_R18.md`, 08:17 MDT, before any data).
Handoff: `handoff/2026-10-20_from-qa-18/`. Box only. No CFD and no fansim edits.
- **A (R1.8 stage 2) built-hang reference values:** 10 designs: S2_0269, 4 feature designs and 5 feature-free.
  - Measured on `build_blade_solid` at the R1.7 export hub (growth below the blades) with an exact OCCT bounding box.
  - All gates PASS:
    - vertex and mesh cross-checks within 1e-7 mm;
    - fresh-process rebuild identical;
    - S2_0269 at the auto hub reproduces 2.252 mm.
  - Values (mm): S2_0269 **0.000** (−1.050 signed), S5_0207 2.829, S5_0073 2.303, S5_0112 2.626, S5_0023 7.322,
    G_0502 1.936, S1_0461 2.090, S1_0534 0.991, S3_0173 1.169, S4_0242 5.359.
  - Stage 2 refuses 6/10. `docs/qa/r18/r18-A-built-hang-reference.csv`, `docs/qa/notes/r18-A-built-hang-reference.md`.
- **B (R2.3a) Shigemitsu velocity triangles:**
  - "From the rotation plane" is **MID-ONLY**: 4/6 stations within ±15° (front hub −19.9°, rear tip +16.0°; mids
    −1.0° / +6.7°), and 4–5/6 under every sensitivity setting.
  - "From the axis" gets 0/6 (up to 3/6 with no swirl).
  - Not clearly inconsistent, so **the ruling stands**. `docs/qa/notes/r18-B-shigemitsu-velocity-triangles.md` → QA-50.
- **C (R3.1 leak check): WAITING.** R3.1 is still `ready`, not landed. Nothing was run.
- **QA-49 (MED, new) R1.8 stage-2 measurement must use the built, trimmed solid:**
  - Section points at the params' `n_span`/`n_chord` (the `blade_hang_below_hub_mm` / r16 P2 shortcut) read **0.14–0.37 mm
    low on feature designs**. Features raise the loft to 31–43 span sections, and the lowest point at r/R = 0.5 falls
    between the 18 sampled sections.
  - They read **0.05 mm high** when the lowest point is at the tip (G_0502: the untrimmed over-radius wire).
  - Measuring the `build_blade_solid` output, as the amendment says, avoids both. A section-point shortcut must copy
    `required_span_sections`, n_span ≥ 30 for > 3 stations, and the tip trim.
  - The acceptance values hold only once R1.7 is in. Today's `mount_hub_params` grows the hub symmetrically (the top
    rises 0.14–1.74 mm too), which gives hangs up to 3.2 mm larger (S5_0073: 5.345 vs 2.303).
  - Stage 1 also reads the designed hang at `n_span`. That's fine as a prefilter, but it's why the feature designs
    need stage 2.
- **QA-50 (LOW, new) R2.3a stagger and camber:** the ruling passes its own consistency test only at mid-span.
  - Under "from the plane", the front rotor's chord angle falls 17.8° hub → tip while the flow angle rises 10.3°
    (reversed twist).
  - With the ruled 4 % camber, the ideal lossless Euler rise at mid-span is 67 + 212 = **279 Pa against 510 Pa
    measured**, so A1 must miss low.
  - "From the axis" with about 10 % camber is the coherent alternative: right twist sign everywhere, and 1240 Pa ideal.
  - Report only: the pre-registered rule keeps the ruling. Claude may want to state now whether S1′ stays meaningful
    for a model that can't reach the measured pressure.

## Round 19 (2026-10-20): master 1c86f65, run clone `/workspace/fansim/qa/run_r17` (fansim code identical)
Prereg `cab2825` (`prereg_r6` branch `prereg/round19`, `qa_r19/PREREG_R19.md`, 08:32 MDT, before any BEMT run or
digitising). Handoff: `handoff/2026-10-20_from-qa-19/`.
- **A (R2.2) known-section prop: the TU Delft low-Re benchmark** (Casalino et al. 2021, AST 113:106707, **CC BY 4.0**).
  - D 0.30 m, 2 blades, **NACA 4412 full span**. Chord and twist come from Fig 4.
  - Measured C_T and C_Q at 5000 rpm, J 0–0.8. Re(0.75R) ≈ 9×10⁴.
  - The runner-up is UIUC DA4002 9×6.75 (SDA1075; licence citation-only). 8 candidates in all, in
    `docs/qa/r19/r19-A-prop-candidates.csv`. TUD-XPROP is excluded (NC-ND).
  - Note: `docs/qa/notes/r19-A-known-section-prop-hunt.md`, with a proposed CFD prereg for the TUD blade.
- **B (R2.1/R2.2) fansim BEMT on the known-section prop:**
  - The shipped `table` backend **AGREES**: C_T −4.9 % static and −7.1 % at J 0.4; C_P +0.5 % / +0.3 %. It holds
    under twist ±0.5°, chord ±2 %, ρ and n_elem.
  - Toward zero thrust C_T reads about 0.01 low: −14 % at J 0.48, −24 % at 0.60.
  - The `neuralfoil` backend DISAGREES: C_T +16.8 % static, and non-converged at every point (QA-51).
  - Section test G (J 0 → 0.4): known −2.2 pp, generic −4.4 pp → MIXED (table). The generic section isn't wrong on
    this prop.
  - APC SF's growth with J is partly a BEMT near-zero-thrust offset (about 0.01 in C_T) that known sections don't
    remove.
  - DA4002, report only: table −12 to −18 % C_T and −27 to −41 % static C_P, i.e. the static C_P deficit remains on
    thick low-camber sections at Re 2.5–6×10⁴.
  - **Deviation recorded:** the paper normalises by ρΩ²πR⁴ / ρΩ²πR⁵ (axes ×10² / ×10³). My first reading broke the
    0.18 N·m torque-cell range and was corrected before any verdict was written; no rule or tolerance was changed.
  - Note: `docs/qa/notes/r19-B-bemt-known-section-prop.md`.
- **QA-51 (MED, new) NeuralFoil BEMT backend doesn't converge:**
  - With `set_polar_backend("neuralfoil")`, **every** TUD point and every DA4002 point returns `PropPerf.converged =
    False` (at least one element hits the 60-step inflow cap).
  - The table backend converges everywhere except DA4002 design static.
  - The NeuralFoil numbers also differ from the table by +22 pp of C_T at static on the same NACA 4412.
  - Until fixed, label NeuralFoil-backend prop results unreliable whenever `converged` is False. Check any claim that
    was validated with NeuralFoil for the flag.
  - Proposal only: under-relaxation or a bisection fallback on the element that oscillates.
- **QA-52 (LOW, new) PropPerf rounding:**
  - `analyze` rounds `power_w` to 0.1 W, `thrust_n` to 1 mN and `torque_nm` to 1e-4 N·m. For small or slow props
    (DA4002 at 3030 rpm, about 5–6 W) that is up to about 1 % of C_P in validation numbers.
  - Proposal: keep unrounded fields for validation and round only for display.

## Round 20 (2026-10-21): master 027ebcb (merges `r33-install-guide` fe899cd), run clone `/workspace/fansim/qa/run_r20`
Prereg **`2c4380d`** (`prereg_r6` branch `prereg/round20`, `qa_r20/PREREG_R20.md`, committed 08:38 MDT before any data).
Handoff: `handoff/2026-10-21_from-qa-20/`.

**Discrepancy:** the brief says `r33-install-guide` is unmerged, but master 027ebcb already merges it. Code, tests and
README are identical on both, so master was tested. Kimball's PC working tree is on `r33-install-guide`; that is
noted only.

- **A (R1.8; QA-43/44/49): all PASS.**
  - `docs/qa/r20/r20-A-feature-designs.json` holds the 4 feature designs in the `hub_hang_designs.json` layout, and
    Cursor's `_design` + `mount_hub_params` recipe reproduces my r18 values bit-for-bit.
  - `blade_hang_built_mm` at the mount hub on all 10 designs: max |Δ| vs r18 is **0.0 mm**. Stage 1 refuses 5/10 and
    stage 2 refuses 6/10, both exactly as predicted.
  - `build_impeller_parts` refuses every design with built hang > 2 mm (6/10) and builds the rest.
  - The Export flat hub equals the evaluate hub to < 1e-6 mm.
  - **Status:** QA-43, QA-44 and QA-49 are **verified fixed** on master. R1.8 acceptance becomes 10/10 once Cursor
    adds the JSON.
  - Note: `docs/qa/notes/r20-A-built-hang-recheck.md`.
- **B (R2.2 rung A0 reference):** Ladson NASA TM-4074 (public domain), NACA 0012 at Re 6×10⁶, M 0.15, tripped, mean
  of 80/120/180 grit.
  - **C_d(0°) = 0.00808 ± 0.0002**, **C_l(5°) = 0.537** and **C_l(10°) = 1.063**.
  - The A0 windows: C_d 0.00646–0.00969, C_l 0.510–0.564 at 5° and 1.010–1.116 at 10°.
  - The lift slope is 0.1072/deg, within 0.3 % of McCroskey.
  - My pre-registered band flags C_l at 5° (±19 %) because of a flawed nearest-row term. A post-hoc quadratic term
    gives ±0.8 %, and either way the band sits inside the pass windows.
  - The TMR data file has a typo at 180 grit, α 2.00° (0.2213 vs the table's 0.2113).
  - Note: `docs/qa/notes/r20-B-ladson-naca0012-reference.md`.
- **C (R2.2 TUD build details):**
  - hub radius 12.5 mm, a flat boss with **no spinner**;
  - an elliptical root "from r = 10 mm", which is inside the hub radius, so inconsistent. NACA 4412 is defined from
    r/R ≈ 0.19 (Fig 4);
  - a square-cut tip with c/R 0.067;
  - an **open, upward vertical jet**, 0.60 m nozzle, and a tractor rotor on a 50 mm nacelle of unstated length;
  - the rotor-to-nozzle distance is stated two ways that disagree (0.5 m vs 1.2 D_nozzle = 0.72 m);
  - the trip status of the force data is not stated.
  - `docs/qa/r20/r20-C-tud-build-details.csv` and `docs/qa/notes/r20-C-tud-build-details.md`.
- **D (R3.3 install dry run):** on clean Linux (throwaway user, empty HOME, fresh clone and venv, no Docker), uv,
  Python 3.12, the full install, the cockpit (HTTP 200 in 12 s) and the UI test (6/6) all work.
  - **Stop point:** step 2, where `git clone <this-repo>` has no URL.
  - **Doc errors:** the cockpit prints port **8080**, not the README's 9001. Assess is "30–40 min" in code against
    "several minutes" in the README.
  - The "Docker not running" troubleshooting text doesn't exist yet (R3.4). With no Docker, the error is
    `FileNotFoundError: 'docker'`.
  - Note: `docs/qa/notes/r20-D-install-guide-dry-run.md`.
- **E (R3.1 leak check):** waiting, because R3.1 hasn't landed. Not run.
- **QA-53 (MED, new) R3.3 README install section:** two factual errors and three gaps.
  - **Errors:** the cockpit URL is `127.0.0.1:8080`, not `localhost:9001`. The first Assess takes about 30–40 min,
    not "several minutes".
  - **Gaps:**
    - `<this-repo>` and `cd Fan-simulator` give no real URL or folder;
    - there is no Linux Docker install link or `usermod` line;
    - no troubleshooting row covers "Docker not installed" (`FileNotFoundError: … 'docker'`). The "Docker not
      running" row refers to text that only R3.4 will add.
  - Proposal: the six edits in the D note.
- **QA-54 (LOW, new) Export `fit_hub` widens `hub_radius`; scoring does not:**
  - S5_0073 goes 20.49 → 20.775 mm and S5_0023 19.38 → 20.775 mm.
  - In a run without `--mountable`, `evaluate_candidate` scores the narrower hub, and Export (with "fit hub" on)
    prints the wider one. The hang is unaffected (≤ 4e-5 mm), but the root and hub are not "one hub".
  - The change is shown to the user.
  - Proposal: apply the radius growth in `evaluate_candidate` as `mount_hub_params` does for height, or label the
    difference in Export.

## Round 21 (2026-10-25): master 5063a65, run clone `/workspace/fansim/repo-r21`
Prereg **`956b8ff`** (`prereg_r6` branch `prereg/round21`, `qa_r21/PREREG_R21.md`, committed 15:41 MDT before any data).
Handoff: `handoff/2026-10-25_from-qa-21/`.

- **A (release claims audit): FAIL** (gate: 0 overstated, 0 unsupported). 60 claims: 20 supported, 20 need a label,
  15 overstated, 5 unsupported.
  - Worst:
    - the Assess message "vs stock free 60 CFM" compares a scored screening result with the datasheet (QA-56);
    - the noise ranking is presented as usable (QA-55);
    - Volute/Mixed "honest MRF CFD" (QA-57);
    - `a12x25-reference.md` "validated on Stock: 59.8" (it is the close-ref STL), and "~3–5 % discretization" against
      GCI ≈ 21 % (QA-58).
  - The missing labels are the board's R1.4 / R1.5 / R1.6 / R2.1 / R2.4 items (QA-59).
  - Note: `docs/qa/notes/r21-A-release-claims-audit.md`; table `handoff/2026-10-25_from-qa-21/data/r21-A-claims.csv`.
- **B (draft `docs/VALIDATION.md`, R3.8):** 13 surfaces plus a Known-limits list, with R1.4 wording verbatim.
  - 9 mismatches are listed, including: README Stock v2 −5.5 % vs v3 −4.5 %; 59.8 (v5 rig) vs 58.3 (cylinder rig) for the
    same STL; the board's "`wrapped-sections` audit" link has no file; prop "35–45 % low" holds only near static.
  - The rest recompute within rounding.
  - Note: `docs/qa/notes/r21-B-validation-draft.md`.
- **C (lt120 reference build pre-check, R1.1a, no CFD):**
  - The cut check **PASSES on P**: `replace(load_blade_params(fansim_params.json), section_wrap="cylinder",
    clip_below_hub=False)` → `build_impeller`.
    - 9/9 cuttable radii PASS: worst 0.11 % chord, 0.06° stagger, 0.0006 camber.
    - One watertight solid, 7 blades, direction CONCLUSIVE.
  - C as pre-registered: **NOT PASS** on freeze blockers:
    - r 23.0 mm is N/M (inside the hub);
    - there is no `reference_build` path;
    - `validation/reference/lt120/` is absent.
  - Hang: 4.76 mm designed, 4.82 mm built; with the clip on the build is refused at 8.3 mm.
  - S (clip on, hang checks bypassed) also passes, but is up to 2.2 % shorter in chord outboard. → QA-60.
  - Note: `docs/qa/notes/r21-C-lt120-reference-precheck.md`; data `handoff/2026-10-25_from-qa-21/data/r21-C-lt120-cut-check.csv`.
- **D (R3.1 export leak check):** waiting, because R3.1 has not landed. Not run.
- **QA-53:** still **open** at 5063a65. The README still has `localhost:9001`, "several minutes" and `<this-repo>`.

- **QA-55 (MED, new) Noise ranking presented as usable.** Tested 5063a65. Status: open.
  - **Repro:**
    - README:59 "tone + relative ranking are usable";
    - `fansim/cfd/flow_verdicts.py:156-162`: the hint row is ✓/⚠/better "About x dB quieter than Stock";
    - `fan_flow_report.py:30` "ranking";
    - `fan_tab_ui.py:1108`;
    - `a12x25-reference.md:57`;
    - `data.py:205` shows the column "dBA";
    - the finalist print sheet shows a bare `noise_swl`.
  - Audit-06: validation INCONCLUSIVE. R0.4 ruling: the hint only restates CFM.
  - Proposal: land R0.4 and R1.6. Say "relative, unvalidated", never "ranking is usable".
- **QA-56 (MED, new) Assess "vs stock free 60 CFM" is not vs Stock.** Tested 5063a65. Status: open.
  - **Repro:** `fansim/cockpit/fan_assess.py:405-411` compares `cfm_free` with `spec.ref_cfm` (the Noctua datasheet,
    60.1). `cfm_free` is the scored screening Assess, after derate and the ×0.95 knockdown, with GCI ≈ 21 %.
  - Assessing Stock itself prints about "−17 % (lower free-air)": 49.6 vs 60 (how-scores).
  - Proposal: compare with Stock's own Assess score in the same mesh, or label the line "vs the Noctua datasheet; not
    like for like".
- **QA-57 (MED, new) Mixed/Volute "honest CFD" wording; Mixed not labelled experimental.** Tested 5063a65. Status: open.
  - **Repro:**
    - `mixed_tab.py:765` "honest MRF duct";
    - `volute_tab.py:164, 691` "honest (radial MRF) CFD";
    - `app.py:187-191` "Mixed · estimate";
    - `fan_tab_ui.py:495`.
  - The volute oscillates 17–23 % (audit-07:112), and Mixed has no published comparison (R2.4).
  - Proposal: R2.4's "Experimental: not validated against published data", and "unconverged proxy (±20 %)" for Volute.
- **QA-58 (LOW, new) Stale or incorrect validation numbers in user docs and cockpit copy.** Tested 5063a65. Status: open.
  - **Repro:**
    - `a12x25-reference.md:24` (59.8 attributed to Stock) and `:30` ("every gap closed");
    - `design-rules.md:43` "~3–5 %", and `:39` "more blades raise airflow" against its own table (ρ −0.35);
    - `adversarial-review.md:23-25, 237-239`, which README:12 links as "what is validated";
    - README:66 "the one real gap";
    - `fan_copy.py:129` "~0.6×" (audit-04:80 says stale);
    - `fan_tab_ui.py:493` "one CFD solve (~15–30 min)";
    - `figures.py:399` "under-predicts static ~2×".
  - Proposal: correct these from r21 B, add historical banners, and point README:12 at `docs/VALIDATION.md`.
- **QA-59 (LOW, new) Board-decided release labels not landed.** Tested 5063a65. Status: open (tracks R1.4/R1.5/R1.6/R2.1/R2.4).
  - **Repro:**
    - R1.4: no "about 5 % less airflow" phrase in the README or the Stock text (`fan_trials.py:354`), and no
      "Known limits" list;
    - R1.5: no "estimate, not validated" on structural/vibration (README:27, 62; `fan_tab_ui.py:889, 911`;
      `figures.py:394` "safety gate");
    - R2.1: the prop "rank and print from the BEMT numbers" lacks "±15 % at static; worse toward zero-thrust J";
    - the export print sheet has a bare "Predicted performance (sim)" (`print_export.py:373`).
  - Proposal: the wording in r21 B "Known limits".
- **QA-60 (MED, new) lt120 reference build: freeze items.** Tested 5063a65. Status: open (R1.1a).
  - **Repro:** `docs/qa/notes/r21-C-lt120-reference-precheck.md`.
    - There is no `reference_build`. `clip_below_hub=False` also drops the clip and its correction.
    - The table's r 23.0 station is inside the 25 mm hub (r0 = 23), so it is N/M.
    - `validation/reference/lt120/` is absent.
    - Tip 56.5→60 mm is extrapolated.
    - Clip-on and clip-off builds differ by up to 2.2 % chord.
  - Proposal: freeze P (clip off; it matches the table), record r 23 as an embedded root, add a cut test.

## Round 22 (2026-10-29): master b3d5543, run clone `/workspace/fansim/repo-r22`
Prereg **`715891f`** (`prereg_r6` branch `prereg/round22`, `qa_r22/PREREG_R22.md`, committed 20:24 MDT before any data).
Handoff: `handoff/2026-10-29_from-qa-22/`. Bundle: `master_b3d5543.bundle` (the brief's `fansim.bundle` is not on the box).

- **A (UI and bug pass; cockpit headless on :8080, Playwright with system Chrome; fast pytest):**
  - **QA-53 verified.**
    - The cockpit prints `http://127.0.0.1:8080/`, which is README:137.
    - README:138 says "30–40 min", which matches `fan_assess.py:332`.
    - README:107 "the GitHub URL" (interim).
    - The Docker-not-installed row is still absent (R3.4).
  - **R1.4 phrase verified:** it is in README:204 and renders in the Stock Expert caption. Simple shows nothing extra.
  - **UI-26 still open:** 'Gold = parametric Stock…' renders on the first view in both modes, the hose line in Expert,
    and camber/Difficulty after Preview.
  - **UI-27 still open:** the viewer bottom is at 957 px of 768. The picker and Preview are now above the fold.
  - **UI-29 still open:** only 'Start here' fails (12 px grey caption). The column is 41 % and the body is 16 px.
  - **QA-40 still open:** in the r14 harness, s3 still shows "No Stock comparison for noise." in Simple.
  - **QA-42 still open:** a rendered Preview reads "… 11 g" for both PLA+ and PETG, with no material.
  - **Pytest** (`-m "not docker and not slow"`, one process, 40 min): **1880 passed, 4 failed**, 21 skipped, 23 deselected,
    1 xfailed. All 4 failures repeat when run alone.
    - QA-62: `test_axial_scripts_oriented`.
    - QA-63: `test_fuse_memory`.
    - QA-41: 2 × `test_worker_parent_watch`.
  - Note: `docs/qa/notes/r22-A-ui-bug-pass.md`.
- **B (lt120 freeze re-cut, R1.1a; committed `lt120.stl`, not rebuilt): PASS.**
  - r = 23 is N/M, and **9/9** radii 26.7–56.5 PASS. Worst: chord −2.26 % (gate 3 %), stagger 0.063°, camber 0.0002.
  - Identical to r21 S (Δ 0 at every radius). Against r21 P, 0.8–2.2 % shorter in chord outboard (clip on).
  - The STL is watertight, 1 body, 7 blades; direction CONCLUSIVE.
  - All 5 QA-60 sub-items are closed. → **QA-60 closed** (B passes, and the freeze/board text matches the code).
  - Note: `docs/qa/notes/r22-B-lt120-freeze-recut.md`.
- **C (A0b bookkeeping, `scripts/prop_section_2d.py`, code reading only): consistent, no setup bug, so it does not explain the A0 FAIL.**
  - U = (cos α, sin α), liftDir = (−sin α, cos α), dragDir = (cos α, sin α), all from the same `a`. The geometry is not rotated, so α is applied once.
  - The `coefficient.dat` Cd/Cl columns are read correctly.
  - Code-visible candidates (report-only): convergence (`residualControl {}`, last-20 % mean), 48 uniform cells per
    surface at the LE, 8c far field, fixed +x wake blocks.
  - Note: `docs/qa/notes/r22-C-a0b-alpha-bookkeeping.md`.
- **D (R3.1 export leak check):** waiting, because R3.1 has not landed. Not run.

- **QA-61 (LOW, new) Assess time: the cockpit's static copy says "~15–30 min", while the README and the running note say "30–40 min".** Tested b3d5543. Status: open.
  - **Repro:**
    - the Actions button "ASSESS (~15–30 MIN)" (`fan_tab_ui.py:594`, rendered);
    - `fan_tab_ui.py:494` (also in QA-58) and `:896`;
    - `fan_core.py:84`;
    - the sweep step `fan_assess.py:482`.
  - These disagree with README:138, `fan_assess.py:332` and `run_settings.py:3`.
  - Proposal: one constant, used everywhere.
- **QA-62 (MED, new) `scripts/validate_lt120.py` calls `build_case` but is not in `AXIAL_SCRIPTS` or `EXEMPT`.** Tested b3d5543. Status: open.
  - **Repro:** `pytest tests/test_axial_scripts_oriented.py` fails: "validate_lt120.py: add to AXIAL_SCRIPTS or EXEMPT".
  - It came in with R1.1a `6f25583`, so the lt120 validation run is outside the orientation guard (same class as bug #7).
  - Proposal: list it and orient it before the R1.1b night result is used.
- **QA-63 (LOW, new) Fuse RAM guard: "remaining" estimate above "whole peak" at 18 084 faces.** Tested b3d5543. Status: open.
  - **Repro:** `pytest tests/test_fuse_memory.py`: `fuse_remaining_estimate_gb(18084)` = 1.934 is not less than
    `fuse_peak_estimate_gb(18084)` = 1.925. Both are pure functions, so this fails on every OS.
  - Proposal: refit one of the two estimates, or fix the invariant.


## Round 23 (2026-10-31): master 3b92eea, run clone `/workspace/fansim/repo-r23`
Prereg **`0006f9b`** (`prereg_r6` branch `prereg/round23`, `qa_r23/PREREG_R23.md`, committed 12:19 MDT before any data).
Handoff: `handoff/2026-10-31_from-qa-23/`. Bundle: `master_3b92eea.bundle` (the brief's `fansim.bundle` is not on the box).

- **A (lt120 knee, no CFD): 13.71 Pa / 60 CFM is AT THE KNEE, robust (100 % of 5000 MC draws, Q ±3 %, ΔP ±0.5 Pa).**
  - Measured slopes, 8→32→40→60→84 CFM: −0.703 / −0.307 / **−0.049** / −0.286 Pa/CFM (steep, flat, flat, flat).
    60 CFM ends a 40–60 CFM plateau; PCHIP slope −0.08 vs −0.42 Pa/CFM at 84 CFM, so 1 Pa ≈ 12 CFM there.
    The 5 points do not resolve a stall dip.
  - **CFD shape does not agree:** steep through 17.14 Pa with no plateau. The 6.85–13.71 Pa slope is 1.5–1.6× the measured
    one (1.5 mm gap 0.68, INCONCLUSIVE).
  - **Tutar & Cam 2025** (CC BY 4.0, Figs. 8/9, prescribed-flow CFD): they show the plateau and call 40–60 cfm the
    "stall range". 6.85 Pa is matched (≈ −3.5 %). 13.71 Pa is not matched in flow (≈ 41 cfm, 38–50), even though they
    are only ≈ 1 Pa low.
  - Note: `docs/qa/notes/r23-A-lt120-knee.md`.
- **B ("near the knee" warning, proposal only): NEEDS MORE DATA.**
  - R23-KNEE = K1 unconverged OR K2 φ ≤ 0.6 OR K3 P ≥ 0.6 × BEM shut-off.
  - On A12x25 Stock 5/10/15/20, lt120 6.85/13.71 and FAN-01 7–253 Pa: **6 hits, 1 miss (lt120 13.71, converged +24.5 %),
    0 false flags.** Only K1 fires; K2 is n/a without a free-air CFD, and K3 never fires.
  - Draft: land K1 as the warning, show φ and P/shutoff as report-only, and add a converged-near-knee caveat. A BEM-
    flattening K4 is exploratory (lt120 0.51, A12x25 15 Pa 0.47).
  - Note: `docs/qa/notes/r23-B-near-knee-warning-spec.md`.
- **C:** waiting (R3.1 export leak check; r21 A re-run after R1.10). Not run.

- **QA-64 (LOW, new) The release wording "Fan CFD: validated near free air on three published fans, within 8 %" overstates lt120.** Tested 3b92eea. Status: open.
  - **Repro:** `docs/validation/audits/2026-10-30-lt120-tip-gap-prereg.md:69` and `2026-10-18-lt120-validation-prereg.md:79/89`.
    - lt120's point is 6.85 Pa, about 20 % of the 34 Pa near-shut-off point. It is on the stable branch, and the dataset
      has no free-air point.
    - The error is +8.1 % as a two-mesh mean, and +9.5 % on the 6.2 mm mesh.
  - Proposal: "within 10 %", and for lt120 "at its lowest measured load (6.85 Pa)" instead of "near free air".

## Tooltip audit (2026-10-31): master 3b92eea, clean clone `/workspace/fansim/repo-tt`
Asked by Kimball 12:58 MDT. Note: `docs/qa/notes/tooltip-audit-2026-10-31.md`. Handoff: `handoff/2026-10-31_from-qa-tooltips/`. No source edits, no CFD/Docker/Assess/Sweep/Optimize run.

- **Inventory:** 229 setting-bound controls: 53 image+text (all Fan › Geometry), 19 text-only, 157 none. Optimize: 16/16 text-only, 0 images.
- **Generator found:** `scripts/generate_control_images.py` (pyvista, 460×250). Driven unmodified via a wrapper to make the missing rotor images. Stator/casing and SEARCH/EVAL settings use fallback renders/schematics.
- **New:** UI-31 (HIGH), UI-32 … UI-36 (MED), UI-37, UI-38 (LOW).

## Round 24 (2026-11-01): master 23831da, run clone `/workspace/fansim/repo-r24`

- Prereg: **`88c4e79`** (`prereg_r6`, branch `prereg/round24`, `qa_r24/PREREG_R24.md`), committed at 12:21 MST, before any data.
- Handoff: `handoff/2026-11-01_from-qa-24/`.
- Bundle: `master_23831da.bundle`. The brief's `fansim.bundle` is not on the box.
- No source changes since 3b92eea in `fansim/`, `scripts/`, `docs/control_images` or the README.

- **A (UI and bugs): all 16 items are still open; 0 verified.** Note: `docs/qa/notes/r24-A-ui-bug-pass.md`.
  - **UI items:**
    - UI-26: 'Gold = parametric Stock' is still on the first view.
    - UI-27: the viewer bottom is at 957 px of 768.
    - UI-29: 'Start here' is still 12 px grey.
    - UI-31 (HIGH), on this bundle: the switch renders, and there is no `--verify-cfd`.
    - UI-32: 0 `opt_*` images load.
    - UI-33: no "sliders unused" text.
    - UI-34: Boost/NN stay enabled and do nothing.
    - UI-35: 13/13 ranges still differ.
    - UI-36: 0/8 controls show a tooltip.
    - UI-37: 1/100 proxy-tab controls have one.
    - UI-38: design pick still resets silently. Correction: the Print-material caption already mentions Optimize.
  - **QA items:**
    - QA-40: s3 noise row still in Simple.
    - QA-42: "11 g" with no material.
    - QA-61: "~15–30" vs "30–40 min".
    - QA-62 and QA-63: their tests still fail.
  - **Pytest** (`-m "not docker and not slow"`, one process, 25 min 35 s): **1883 passed, 4 failed**, 21 skipped, 23 deselected, 1 xfailed.
    - The failures are the same 4 as r22: QA-62, QA-63, and QA-41 × 2 (`test_worker_parent_watch`).
- **B (QA-64 wording, no CFD): needs grok's proposed wording.** Note: `docs/qa/notes/r24-B-qa64-wording.md`.
  - A12x25: −0.5 % at 0 Pa (`a12x25_pq_report.md:27`).
  - FAN-01: +2.6 % at 7 Pa, P/Pmax 0.028 (`fan01/fan01_report.md:23`).
  - lt120: +8.1 % two-mesh mean, +9.5 % on the 6.2 mm mesh, at 6.85 Pa, P/Pmax 0.20 (`2026-10-18-lt120-validation-prereg.md:69`).
  - As worded, the claim fails twice on lt120: it is not near free air, and 8.1 > 8.0.
  - "Within 10 %", with lt120 "at its lowest measured load (6.85 Pa)", holds for every number.
  - Caveat: the 1.0 mm tip-gap variant gave +13.0 % at 6.85 Pa, so the claim is for the frozen 0.5 mm gap.
- **C (is K1 visible?): PARTIAL.** Note: `docs/qa/notes/r24-C-k1-visibility.md`.
  - "UNCONVERGED" reaches the user only in the reject message, when the probe reverses (`objectives.py:140`, `fan_assess.py:210`).
  - A design that scores but did not converge shows nothing:
    - `_assess` doesn't keep `result.reason`, and `_assess_existing` blanks it (`fan_assess.py:223-232,284`);
    - `stamp_score_extra` doesn't copy `converged`;
    - the flow card never reads it.
  - Proposal: `docs/qa/patches/r24-C-k1-visible.patch`. It adds 5 lines across 2 files and passes `git apply --check`.
- **D:** still waiting. Not run.
  - R3.1 export leak check: R3.1 is `ready`, not landed.
  - r21 A claims-audit re-run: waiting for R1.10 (`ready`).

- **QA-65 (MED, new) Assess drops the "UNCONVERGED" note for a feasible score.** Tested on 23831da. Status: open.
  - `objectives.py:602-606` puts "UNCONVERGED (…)" into `ObjectiveResult.reason`, and `raw["converged"]` = False. Its docstring (`:11-12`) says "unconverged results are flagged".
  - But the cockpit:
    - never stores `result.reason` on the Design (`fan_assess.py:223-232`, and `:284` sets it to `""`);
    - never stamps `converged` (`score_caption.py:74-77`).
  - So the Done message, the info lines and `design.json` all look the same as for a converged score.
  - Pure-call repro: `score_caption(stamp_score_extra({}, {"converged": False}, load_pa=8, preset="case"))` gives the same string as for True.
  - This is the K1 case from r23 B: 6/6 of the known bad points were unconverged.
  - Proposal: `docs/qa/patches/r24-C-k1-visible.patch`.

## Round 25 (2026-11-02): master 9d0118f plus unmerged `r111-hide-surrogate` @237a094, run clones `/workspace/fansim/repo-r25` (master) and `/workspace/fansim/repo-r25-r111` (branch)

**Brief:** Cursor's **uncommitted draft** `CLAUDE_TO_QA_r25_DRAFT.md`. It was left untracked and is not in any commit; a copy is in `handoff/2026-11-02_from-qa-25/` for the record. Its `fansim.bundle` does not exist; I used `master_9d0118f_plus_r111.bundle`, verified as master 9d0118f and branch 237a094 (7 commits ahead of b0228fe).

**Prereg:** `prereg/round25` b7e7574e (`qa_r25/PREREG_R25.md`), committed 2026-11-02 08:22 MST before any data.

No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run, and no source was edited.

- **A (UI-31 / QA-62 + remaining UI): run on the branch.** Every branch result is *verified on unmerged branch r111-hide-surrogate @237a094, not on master*. Note: `docs/qa/notes/r25-A-r111-branch-check.md`.
  - **UI-31: fixed on branch (pending merge).**
    - 0 Surrogate-guided labels render in Expert; master renders 1.
    - `cockpit_optimization_argv` gives no `--surrogate-guided` even with the state forced on. On master, `fan_optimize.py:141` wires the state.
    - The CLI refuses `--surrogate-guided` unless `--verify-cfd` or `--stub-labels` is given (`run_optimization.py:164-170`).
    - **Master: still open.**
  - **R1.11 closing items (9e36cea), on the branch:**
    - done: the cockpit behaviour test, the CLI stub flag, and the dead-tooltip removal;
    - partial: the CLI behaviour test only unit-tests the guard function (patch `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch`: 7/7 pass on a 237a094 scratch copy);
    - partial: the "synthetic labels, not CFD" stamp goes to stdout only.
    - **Not closable yet** (QA-66).
  - **QA-62: fixed on branch (pending merge).** `validate_lt120.py` is in `AXIAL_SCRIPTS` and `test_axial_scripts_oriented` passes. **Master: still open** (the test fails).
  - **Everything else is still open on both heads:**
    - UI-26, 27, 29, 32–38;
    - QA-40, 42, 61, 63.
    - The harness output is identical to r24, except:
      - the removed Surrogate-guided row (inventory 292 vs 293);
      - UI-26's 1366 Simple "Gold" miss, which happened on both heads and is treated as render timing, since there is no code change.
  - The branch merges cleanly in code, but **conflicts in `docs/release/RELEASE_PLAN.md`**.
- **QA-66 (MED, new) The R1.11 CLI gate still lets synthetic labels through.** Found on the branch, by code reading only.
  1. `--verify-cfd` still labels the DoE (24 by default) with `synthetic_label` (`surrogate_search.py:458,484`; no `label_fn` from the CLI), and prints no notice.
  2. `scripts/run_surrogate_search.py:26-27` adds `--stub-labels` silently.
  3. The stub output on disk is not stamped "synthetic labels, not CFD"; only stdout says it.
  - The cockpit is not exposed on the branch. Status: open.
- **B (the QA-65 patch as adopted on master): holes.** Note: `docs/qa/notes/r25-B-qa65-adopted-review.md`.
  - 9d0118f is **board-only**, and the patch is **not applied**: `git apply --check` still passes, and unpatched master shows no warning.
  - On a scratch copy of master + patch:
    - `converged=False` shows "⚠ loaded point did not settle…";
    - True, None, missing, a string "False" and a re-assess to True all stay silent;
    - the reject text is identical to r24.
  - **Holes:**
    - Optimize-trial designs never carry `converged` (`study.py`/`data.py`);
    - there is no test.
  - Add-on patch `docs/qa/patches/r25-B-qa65-test-and-trials.patch`:
    - `git apply --check` OK on 9d0118f;
    - 142 passed in the 15 related files (master alone gives 131 without the 2 new tests).
  - **QA-65 stays open (MED) on master.**
- **C (QA-64 strings): still live.** Note: `docs/qa/notes/r25-C-qa64-strings.md`.
  - `2026-10-18-lt120-validation-prereg.md:89` "Fan CFD: validated near free air on three published fans (within 8 %)."
  - `2026-10-30-lt120-tip-gap-prereg.md:69` "… , within 8 %."
  - There are no hits in `fansim/` or the README; the other 17 hits are QA records or board quotes.
  - R1.10 is still `ready`. **QA-64 stays open (LOW).**
- **D: waiting.** The R3.1 export leak check is waiting for R3.1; the r21 A claims audit is waiting for R1.10.
- **Fast suite** (`-m "not docker and not slow"`):
  - **master 9d0118f:** 4 failed, 1883 passed, 21 skipped, 23 deselected, 1 xfailed, 42 min 48 s (run in parallel with the branch run). The failures:
    - QA-62 `test_no_unlisted_script_calls_build_case`;
    - QA-63 `test_remaining_growth_is_less_than_whole_peak_and_shroud_adds_blade_faces`;
    - QA-41 ×2 `test_worker_parent_watch`.
  - **branch 237a094:** 3 failed, 1889 passed, 21 skipped, 23 deselected, 1 xfailed, 66 min 18 s. The failures are QA-63 and QA-41 ×2; QA-62 now passes, and the +6 passes are QA-62 plus the 5 R1.11 tests. Verified on unmerged branch r111-hide-surrogate @237a094, not on master.
- **QA-67 (LOW, new) A fast-suite smoke test runs on unseeded random geometry and can take ~25 min.**
  - `tests/test_fan_tab_setup_smoke.py::test_readonly_handlers_run` calls `fan_randomize_geometry()` (global `random`, `fan_editor.py:518`) and then `fan_on_fit_envelope()`.
  - In the branch run, py-spy at 09:12 MST showed it in `makeSolid` ← `_capped_loft` ← `build_blade_solid` ← `impeller_z_extent`. The output had sat at 37 % since about 08:48, and the test then passed.
  - Master's run (same test file) finished in 42 min overall, so the slowness is non-deterministic, not branch code.
  - Fix: seed the RNG in the test (or the fixture), or monkeypatch `random`. Status: open.

## Round 25b (grok, 2026-11-02): light re-check of master 0635a18

**Build:** master `0635a18` (2026-11-02 12:29 MST): merge `94f71d9` (`r111-onto-master`), fix `23704f5`, and board `0635a18` (R1.11 `done 23704f5`). Its `fansim/`, `scripts/` and `tests/` are byte-identical to `237a094`, the r25 branch.

**Prereg:** `prereg/round25b` d207af8 (`qa_r25b/PREREG_R25B.md`), committed 2026-11-02 16:22 MST, before any data.

No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run, and no full fast suite. Only targeted pytest files ran, and `test_fan_tab_setup_smoke.py` (QA-67) was skipped. No source was edited.

Note: `docs/qa/notes/r25b-master-0635a18-recheck.md`.

- **UI-31: verified on master 0635a18.**
  - 0 Surrogate-guided labels render in Expert (9d0118f rendered 1).
  - `cockpit_optimization_argv` with the state forced on gives no `--surrogate-guided`.
  - The CLI guard refuses with neither `--verify-cfd` nor `--stub-labels` (`run_optimization.py:164-170`).
- **QA-62: verified on master 0635a18.** `test_axial_scripts_oriented` passes, and `validate_lt120.py` is listed.
- **R1.11 CLI behaviour test: patch still needed.** Master's test only unit-tests `surrogate_guided_cli_error`. `docs/qa/patches/r25-A-r111-cli-behaviour-test.patch` applies, and gives 7 passed on a 0635a18 scratch copy (master alone: 5).
- **QA-66 (MED): still open on master, 0/3 rules.**
  1. `--verify-cfd` still trains the DoE on `synthetic_label` (`surrogate_search.py:458,484`), with no notice.
  2. `run_surrogate_search.py:26-27` adds `--stub-labels` silently.
  3. No "synthetic / not CFD" stamp on disk: `stub_result.json` has none; `surrogate_guided.json` has only `notes` "verify=stub" and `reason` "stub-verify".
  - The board's "stamps stub output" is **stdout only** (`run_optimization.py:179-180`).
- **R1.11: not closable.** The CLI test is not covered, and QA-66 is open. UI-31 and QA-62 are verified.
- **QA-65 (MED): still open on master.** The code is **not** on 0635a18: `r24-C-k1-visible.patch` still applies, and unpatched master shows no warning for `converged=False`.
  - The committed brief and the Next-round header say "QA-65 landed in 9d0118f"; that is incorrect.
  - On scratch 0635a18 with r24-C and r25-B, the behaviour is the same as r25: only `converged is False` warns.
  - `r25-B-qa65-test-and-trials.patch` still applies. `test_score_caption.py` gives 11 passed on scratch and 9 on master.
- **"Drop dead tooltip" (23704f5): no UI-3x status change.**
  - It removes only `opt_surrogate_guided` from `OPT_SEARCH_HELP`.
  - a_tooltips, scan (4221 leaves), inventory (292 rows), range_check (58 rows, 20 mismatches), a_probe and a_flowcard are all identical to the r25 branch data.
  - a_ui differs in 1 timing field only.
- **Carried, still open on 0635a18:**
  - UI-26 (1366 Simple miss again, render timing), UI-27, UI-29, UI-32 … UI-38;
  - QA-40, QA-42, QA-61 (8 hits, identical);
  - QA-63 (`test_fuse_memory`: 1 failed, `1.934 < 1.925` false).
  - QA-64 and QA-67 are unchanged and were not re-tested.
- **Targeted tests:**
  - 4 files: 1 failed (QA-63), 33 passed, 1 skipped;
  - `test_score_caption` + R1.11 + argv: 30 passed.
- **ID changes:** UI-31 and QA-62 → **verified**. There are no new IDs.

## Round 26 (grok, 2026-11-04): re-check of QA-66 / R1.11 and QA-65 on master bd6abdd

**Build:** master `bd6abdd` (2026-11-04 12:23 MST), which includes `5611332` (QA-66) and `c10c06b` (QA-65). Run clone: `/workspace/fansim/repo-r26`.

**Prereg:** `prereg/round26` 00ed802 (`qa_r26/PREREG_R26.md`), committed 2026-11-04 12:25 MST, before any data.

No CFD, Docker, OpenFOAM, Assess, Sweep or Optimize was run, and no full fast suite. The probes are library and CLI calls with Docker monkeypatched and CFD verify faked. No source was edited.

Note: `docs/qa/notes/r26-qa66-qa65-recheck.md`.

- **Targeted tests:** surrogate_guided, r111, score_caption and argv give **46 passed**.
- **QA-66 (MED): verified, 5/5.**
  1. `--verify-cfd` makes 0 `synthetic_label` calls; labels are "catalog + CFD verify".
  2. `run_surrogate_search.py` refuses with neither flag.
  3. "synthetic labels, not CFD" is written to `surrogate_guided.json` and 2/2 `stub_result.json`.
  4. With fewer than 8 catalog rows or no catalog, the run refuses before any search (0 synthetic calls, no JSON).
  5. `priors` are stamped "prior, not CFD".
  - The r25-A CLI behaviour test is **covered** (both tests are on master verbatim).
- **R1.11: closable.**
- **QA-68 (LOW, new): the CLI catalog refusal is an uncaught traceback.**
  - `run_optimization.py` main does not catch the `RuntimeError` from `run_surrogate_guided`, so a user with Docker and no catalog gets a traceback (exit 1), not a clean exit 2. The out dir is created first.
  - Patch: `docs/qa/patches/r26-A-qa68-catch-refusal.patch`, with a test that fails on master and passes when patched; 36 passed on scratch.
  - Not a blocker.
- **QA-65 (MED): verified, 3/3. Closable.**
  - `r24-C-k1-visible.patch` and `r25-B-qa65-test-and-trials.patch` both reverse-apply cleanly, so their content is present (r25-B is now redundant).
  - Only `converged is False` warns; this was checked for 7 cases.
  - Optimize trials carry `converged` through `load_designs` to the caption (probe).
  - `test_score_caption`: 11 passed.
  - Optional: `docs/qa/patches/r26-B-qa65-trial-test.patch` adds a repo test for the trial path.
- **UI-26: still open.** "Gold = parametric Stock" is on the first view in 3/4 views (1366 Expert, 1920 Simple, 1920 Expert). The 1366 Simple miss is render timing (the Stock cache was still building), the same as r25/r25b.
- **Not re-tested; carried still open:** UI-27, UI-29, UI-32…38, QA-40, QA-42, QA-61, QA-63, QA-64, QA-67.
- **Still waiting:** R3.1 (export leak check) and R1.10 (claims audit, QA-64 strings).
- **ID changes:** QA-66 and QA-65 → **verified**. New: **QA-68** (LOW).



## Round 26 follow-up (grok, 2026-11-08): QA-68 re-check on master 419df2e

**Build:** master `419df2e`, from bundle sha256 `24bcef9c…2e25c` (verified). Clone: `/workspace/fansim/repo-r26-qa68`. **Prereg:** `prereg/round26-qa68-recheck` 491f0d2, committed 2026-11-08 13:30 MST, before data. No Docker, CFD, OpenFOAM, Assess, Sweep or Optimize compute: Docker presence is mocked and CFD verify is guarded. No source edits. Note: `docs/qa/notes/r26-qa68-recheck.md`.

- **QA-68 (LOW): verified, closable.**
  - **Behavioural:** `run_optimization.py --surrogate-guided --verify-cfd` returns 2 with the refusal message and no exception in all 4 refusal cases (no catalog; 7-row catalog; Docker absent at the CLI guard; Docker absent at the library refusal). A real subprocess exits 2 with empty stderr. There were 0 CFD verify calls and no JSON written. An 8-row control reaches the guarded verify, which shows the mock is live.
  - **Tests:** r111 (9), surrogate_guided (11) and argv (16) give 36 passed. With the fix reverted in a scratch clone, the QA-68 test fails (1 failed, 8 passed).
  - **Static:** d08e48c (merged d365bea) is our script hunk exactly, and nothing later touches it.
  - **Info only, no ID:** the `except RuntimeError` covers the whole run, so a later runtime error would also exit 2 without a traceback.
- **Not re-tested:** R1.10 G2 (queued, not merged), R3.1 (not landed), R3.3 and the r26 carried items.
- **ID changes:** QA-68 → **verified**.



## Round 26 follow-up (grok, 2026-11-08): R1.10 G2 / QA-55 noise claims on master 83681c2

**Build:** master `83681c2`, from bundle sha256 `fdea337f…8736` (verified). Clone: `/workspace/fansim/repo-r26-g2`. G2 = `8d06672` (merged `3fca917`). **Prereg:** `prereg/round26-g2-noise-claims` 414177a, committed 2026-11-08 13:38 MST, before data. No Docker, CFD, Assess, Sweep or Optimize; no browser. No source edits. Note: `docs/qa/notes/r26-g2-noise-claims-recheck.md`.

- **G2 / QA-55 noise claims (A01, A04, A10, C10, C14, C16, C17, D03, E01): verified, closable.**
  - **Behavioural:**
    - The noise row is `na`, never better, in 7/7 cases (hint ±5/±30 dB, equal, no Stock, SWL ±10 dB), with no noise in the overall line.
    - The Expert hint text is exact and carries the `expert_only` flag.
    - The design list shows "SWL est. 44.2".
    - The print sheet shows "noise estimate 44.2 (not dB(A); not validated)".
  - **Tests:** g2_noise_copy (4), flow_verdicts (16) and design_dropdown (4) give 24 passed. Red checks on a scratch clone: a "dBA" label gives 2 failed; the pre-G2 `flow_verdicts` gives 1 failed.
  - **Static only:** README wording (ruled sentence present; old phrases appear 0 times); the Optimize text at `fan_tab_ui.py:1110`; `fan_flow_report` and `a12x25-reference` wording; 7 cockpit dB(A) hits, all published, measured or qualified.
  - **Visual not done:** the noise row's Expert/Simple visibility (`v_show` at `fan_tab_ui.py:1392`).
- **QA-69 (LOW, new): `docs/design-rules.md:10` (from `scripts/extract_design_rules.py:106`) says "Noise dB(A) (min)" for the LBM model output.** Suggest relabelling it in G4, which owns `design-rules.md`. Not a G2 blocker.
- **R1.10 stays open** (G3 not merged, G4/G5 pending, release re-audit). R3.1 is not landed; R3.5b is queued, not passed. Night-gate counts were not re-checked.
- **ID changes:** QA-55 (noise claims) → **verified**. New: **QA-69** (LOW).



## ui-hunt-1 (grok, 2026-11-09): exploratory UI bug hunt on master 83681c2

**Build:** master `83681c2`, clone `/workspace/fansim/repo-r26-g2`. **Prereg:** `prereg/ui-hunt-1` cf2c813, committed 2026-11-09 08:46 MST, before data. Headless cockpit, empty run. Assess, Sweep, Optimize, Export and Randomize were never clicked. No CFD, Docker or OpenFOAM. No source edits. Note: `docs/qa/notes/ui-hunt-1-2026-11-09.md`.

- **UI-39 (MED, new): Sweep "steps" has no validation and no cap.**
  - Empty or "1e9" make Run fail silently (`int()` ValueError, `fan_assess.py:448`).
  - Any large count queues that many full CFD Assess runs.
  - Patch: `docs/qa/patches/ui-hunt-1-UI39-UI40-steps-trials.patch` (2–12 with a visible refusal).
- **UI-40 (MED, new): Optimize "Trials" accepts −5, 100 or 1e9 silently, then runs 2–40 (`fan_optimize.py:130-133`).** Same patch: the label reads "Trials (2–40)", with min/max on the field.
- **UI-41 (LOW, new): Fan number boxes (Seed CFM, ΔP and RPM; arrow Scale) show no validation state and store typed text.** Errors surface only on click (Seed) or as a silent clamp (Scale 0.2–20).
- **UI-42 (LOW, new): slider readouts are unrounded with cryptic units** ("18.7018 mm", "0 0–1", "0 c", "0 t"; `fan_widgets.py:35`).
- **QA-70 (LOW, new): the G2 Expert noise-hint row is dropped when a run has no turbulence SWL** (`fan_flow_report.py:146`), though the hint needs only tip speed + CFM. Patch: `docs/qa/patches/ui-hunt-1-QA70-noise-hint-row.patch`, with a test that fails without the fix (21 passed on scratch).
- **G2 noise row visual: verified** (template render with injected rows: shown in Expert, hidden in Simple).
- **No bug found in:**
  - page errors (0);
  - HTTP errors (UI-15's 405 only);
  - overflow or clipping at 1366/1920 (0);
  - tooltip images (3/3 load);
  - links;
  - state across a tab switch or reload;
  - Simple/Expert toggling;
  - the Expert-only-tab → Simple fallback.
- **Re-checked, still open:**
  - UI-26: shown 2.2 s after load on a warm cache. After an edit, the caption stays "Stock reference loaded" until Preview.
  - UI-27: 957/768 and 1172/1080.
  - UI-29: 12 px.
  - UI-32, UI-33, UI-34, UI-36 (0/8).
  - UI-35 (20/58, unchanged).
  - UI-37: inventory identical to r25b.
  - UI-38: picking a design still silently resets settings.
- **ID changes:** new UI-39, UI-40 (MED), UI-41, UI-42 and QA-70 (LOW).


## Research leads #23–29 (2026-11-09) — Fan Sim QA

Prereg `1bfb38c` on `prereg/research-leads23-29` before prototypes. Clone master `83681c2`. No CFD/Assess/Sweep/Optimize; no PyTorch; patches not applied.

| Lead | Status | Note |
|---|---|---|
| #23 UIUC flat-plate Cl@40k | worth-it/proposed | Cl/Cm check table + test patch; no Cd online; flat≠Stock cambered |
| #24 Pelz tip η (C·s·ψ) | worth-it/proposed | `pelz-tip-eta.patch`; calibrate C; patents expired |
| #25 Kim 2021 OGV rules | worth-it/proposed | `stator-linear-exit-frac.patch`; CC BY 4.0; avoid US8333559B2 tip lean |
| #26 fluids ISO 5167 | blocked (hardware) | MIT maths OK; same gate as #18 |
| #27 BPF / acoustic tach | worth-it/proposed | MIT; BPF sketch recovers 2000 rpm synthetic |
| #28 Ax/BoTorch qNEHVI | worth-it/proposed (optional) | MIT; ~800 MB torch; park until CFD-finalist path |
| #29 PartForge UX pattern | worth-it/proposed | 51 controls → Preset/Primary/Advanced/Hidden; tie ui-hunt-1 |

Zip: `research_leads23-29_out.zip` (placement needs Kimball approval).



## G3 re-check (grok, 2026-11-09): R1.10 G3 / QA-57 on master 41e2dc9

**Build:** master `41e2dc9`, from bundle sha256 `f999d7de…5939` (verified). Clone: `/workspace/fansim/repo-r26-g3`. **Prereg:** `prereg/g3-41e2dc9` 7e3e214, committed 2026-11-09 09:33 MST, before data (from a separate worktree). No CFD, Docker or OpenFOAM, and no Assess, Sweep, Optimize, Export or Randomize. No source edits. Note: `docs/qa/notes/g3-recheck-2026-11-09.md`.

- **G3 claims C22, C24 and C25: verified.**
  - **Rendered (headless, empty run):** the Expert tab reads "MIXED · EXPERIMENTAL", with tooltip "Experimental: not validated against published data". Mixed Design and Results show "Assess runs MRF CFD (not validated against published data)". The Volute tooltip and Optimize lines say "ranking only, unvalidated (CFD not yet converged)". There are 0 "honest" lines in Mixed or Volute.
  - **Probe:** the mixed export sidecar text carries both sentences.
  - **Tests:** G3 copy (4) + simple-mode copy (28) give 32 passed. A red check fails 2 tests.
- **QA-57 (MED): partly fixed.**
  - The Mixed side is done.
  - The **Volute Assess** copy and result readout still have no unvalidated/unconverged label (`volute_tab.py:159,163,410-419`); the label sits only on the Optimize lines.
  - Patch: `docs/qa/patches/g3-QA57-volute-assess-label.patch`, with a test that fails without the fix (33 passed on scratch).
- **Info only:** the Mixed Optimize done-message has no label (the readout keeps it), and the Export message doesn't mention the sidecar `.md`.
- **ui-hunt-1 regression:** UI-39, UI-40, UI-41, UI-42 and QA-70 are **still open** on 41e2dc9. The cited files are unchanged since 83681c2, both patches still apply, and the probes repeat.
- **R1.10 stays open** (G4/G5, release re-audit). R3.1 is not landed; R3.5b is still "rerun". The night-gate counts 668/568/683 were not re-checked.
- **ID changes:** none new. QA-57 → **partly fixed**.


## Research lead #30 (2026-11-09) — Fan Sim QA

Prereg `067eb89` on `prereg/research-lead30` before prototypes. Clone master `83681c2`. No CFD/Assess/Sweep/Optimize. Patch not applied.

| Lead | Status | Note |
|---|---|---|
| #30 Amiet/Sears via amiet_tools (BSD-3) | worth-it/proposed | Thin `strut_gust.py` relative strut-tone vs gap/skew; ranking stable under ±2× gust; absolute levels need wake model. Patch: amiet-strut-tone.patch (4 tests). LE broadband parked (needs turbulence input; pairs with BPM #3). |

Zip: `research_lead30_out.zip` (placement needs Kimball approval). Does not modify the #23–29 zip.


