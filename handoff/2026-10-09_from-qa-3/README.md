# QA → Claude, round 4 (2026-10-09). Requests 1, 2, 3

- **Where it ran:** worktree `research/r4_axial` at `5396796` (made from repo-r4 with `git worktree add`; no branch was checked out in repo-r4) and the
  round-3 QA clone. Single core, nice 19. No CFD. Nothing committed to repo-r4. :8080 not touched.
- **Pre-registration:** `docs/qa/notes/r4-prereg-axial-crosscheck-eff-audit.md`, sha256
  `1252f73ff4655137290a7eab8d30a181034cb1fe5ef7dadd46e5e09dccc4acaf`, committed in the QA clone at `e4db298b882c643b3ae3563c7708caf7d1c26ff7` (branch
  `prereg/round4`, 15:32 MDT), before any run.

## Results
1. **Cross-check: EQUIVALENT.** Claude's `axial_force` and the QA model give **identical** results on all 6,596 screen-r3 designs plus Stock, paddle and reversed blades:
   - max diff 0 in free CFM, shut-off, peak η and score;
   - ρ = 1.000;
   - 0 guard or feasibility disagreements.

   Guard break test (1,822 designs):
   - 0 false refusals; the editor's closest call has peak η 7.3 %.
   - Editor sliders can't build an exploit.
   - Hand-edited files can: a full 80° paddle (8.9 %), 4 outer stations at 89° (7.3 %) and a wrong-hand inner half (10.9 %) all pass.
   - Suggested extra check: Euler free > 1.3 × axial free. The editor max is 1.26; these slips are 1.40–1.68.
   - **Separate issue:** the axial model gives peak η up to **115 %** for 11-blade, high-solidity editor designs (6 of 1,752 > 100 %). Don't rank on it until
     static rise ≤ Euler work is enforced.
   - My pre-registered junk criterion J1 turned out unusable because it flags Stock; disclosed in the note.

   Note: `docs/qa/notes/r4-axial-crosscheck-and-guard.md`.
2. **Efficiency audit: same quantity.**
   - Both are static-pressure × flow / shaft power at the hose op, × the same print k_eta. The definition part is −0.66 pp.
   - Stock gap, 29.4 → 17.9 (scored):
     - ≈ 4 pp is the CFD-side linear η interpolation (Stock's op sits at t = 0.755);
     - ≈ 6.8 pp is real BEM error, mainly pressure: BEM 14.7 Pa vs CFD 8.0 Pa at 41.75 CFM.

   Note: `docs/qa/notes/r4-efficiency-definition-audit.md`.
3. **Scored vs raw:** consistent with the code, but **not reproducible from the CSV**.
   - Implied derate λ is 0.954 / 0.939 / 0.934 for stock / t9005 / bem_9504. The CFD Stock is motor-limited to 1,907 rpm under the assumed 0.40 motor efficiency.
   - Implied p_free is 1.7–3.2 Pa.
   - Undocumented for users: the print knockdown, the derate's motor-efficiency assumption, the p_free stamping, **fan-line extrapolation past the probe** (t9005, 9504) and
     **linear η interpolation**.

   Note: `docs/qa/notes/r4-scored-vs-raw.md`.

## Status lines for docs/QA_REVIEW.md
- QA-4 (axial-force, branch `axial-force-bem` 5396796): the re-implementation is verified identical to the QA model on 6,601 cases (0 diffs, ρ 1.000, 0 guard/feasibility disagreements).
  - Guard: 0 false refusals; refuses all fully paddle-like or wrong-hand blades.
  - Hand-edited partial paddles or wrong-hand spans get through (closest: 80° paddle at peak η 8.9 %).
  - **New:** the axial model's efficiency is unbounded (peak η up to 115 % on 11-blade, high-solidity designs), so it must not rank until an energy bound is added.
- QA-4b (η gap, Stock BEM 29.4 % vs CFD 17.9 %): same quantity (definition part −0.66 pp). Of the rest:
  - ≈ 4 pp is the CFD scorer's linear η interpolation (penalises op between free and probe);
  - ≈ 6.8 pp is real BEM over-prediction of pressure under load (14.7 vs 8.0 Pa at 41.75 CFM).
- NEW (release trust, scored vs raw): scored CFM/η can't be reproduced from `cfd_designs.csv`; it needs derate, p_free and η_free/η_probe columns.
  - Undocumented for users: print knockdown, motor-efficiency 0.40 behind the derate (Stock derated to 1,907 rpm), p_free stamping, fan-line extrapolation past the probe, linear η interpolation.

## Files
- `scripts/`:
  - xcheck_dump.py (run in each clone);
  - xcheck_compare.py;
  - guard_break.py;
  - eff_audit.py;
  - scored_vs_raw.py.
- `results/`:
  - xcheck_result.json;
  - xcheck_dump_qa.jsonl.gz, xcheck_dump_claude.jsonl.gz;
  - guard_break.json (1,822 designs, all flags);
  - eff_audit.json;
  - scored_vs_raw.json.

---

# QA → Claude, round 4: requests 4, 5, 6, 8 and browser prep (second QA worker)

- **Where it ran:** clean clone `/workspace/fansim/repo-r4` @ master `f238f54`, `uv sync --extra dev`, Linux, 16 GB box with no swap. Memory-heavy jobs ran one at a time. No CFD, nothing committed.
- **Pre-registration:** both files hashed at 15:32:58 MDT, before any run. Read-only copies are in `/workspace/fansim/qa/prereg_r4/`.
  - `docs/qa/notes/cup-fuse-memory-criteria.md`: sha256 `f8fcc8bbbacb72aa4abe5f48497952986289f92397f33b142031d5a3a3d5fee9`.
  - `docs/qa/notes/export-correctness-criteria.md`: sha256 `91171a080fa86a297604613e97df3e7a92439383fe42a4edcfeab66d041bcc7f`.

## Results
4. **Slow suite:** **22 passed, 2 skipped** (`pythrust` missing), 418 s. Peak **8003 MB** (`test_objectives_orientation`, the Stock fuse). Per-file table: `slow/README.md`.
5. **Cup-fuse memory:** **no strategy meets ≤ 4.0 GB**, so there's no patch. The best is serial OCCT booleans (S3): 7657 → 4891 MB, +15 % time, identical solid. S1+S3 gets to 4460 MB but takes 2.7× the time. Note: `docs/qa/notes/cup-fuse-memory.md`. Data: `cupfuse/`.
6. **Export / STL:** Stock and 9504 pass E1–E6 and E9–E12. The mirror is an exact reflection (Hausdorff ≤ 1e-10 mm).
   - E7 "failed" only because my pre-registered Ø was wrong (37.94 = 37.25 + 2×0.35 by design).
   - **E8 finding (QA-16):** the 13 mm cup is measured from the lowest blade point, so the hub only holds 12.06 mm (Stock) / 10.58 mm (9504).
   - Duplicate as-designed build and gauge Ø noise → QA-17.
   - Details: `export/README.md`.
8. **Docs audit:** 21 claims checked. False or stale: the personal plan path; the tip band 55–57 mm (it excludes Stock's 54.5 and contradicts the 110 mm frame); the "reality check", Task 3.1 and FW-H text; `config/design_space.yaml` (7 blades / 120 mm frame). Clean-clone gaps: runs/, catalog.db, config/fan_models, build/, the propulsion extra. Note: `docs/qa/notes/docs-claims-audit-2026-10-09.md`.

**Browser prep:** `docs/qa/browser_checklist_2026-10-09_r4.md`. Three cockpits are running, each with an empty run dir under `/workspace/fansim/qa/runs/`:
- :8080 — master f238f54;
- :8081 — 961f953, from a `git archive` export in `/workspace/fansim/qa/r4_961f953`, using repo-r4's venv (lockfile unchanged);
- :8082 — master with `FANSIM_WS_GUARD=0`.

## Files (this section)
- `slow/`: README.md, rss_nodeid_plugin.py, rss_sampler.py, per_file_peaks.py, pertest_rss.tsv, rss_samples.tsv, pytest_slow.log.
- `cupfuse/`: cupfuse_job.py, cupfuse_driver.py, run_all.sh, compare.py, verdicts.json, stages_{B,S1..S7,X1}.json, driver_{B,S1..S7,X1}.json.
  - X1 = S3 + MALLOC_ARENA_MAX=2. It is exploratory and was not pre-registered.
- `export/`: README.md, export_run.py, export_check.py, cup_measure.py, checks_{stock,9504}.json, cup_measure.jsonl, run_{stock,9504}.json, {stock,9504}_print_fit.json.

## Browser pass, round 4 (reported 16:34 MDT; checklist `docs/qa/browser_checklist_2026-10-09_r4.md`, 12 screenshots in `docs/qa/screenshots/2026-10-09-r4/`)
- **UI-4: B1a/b/c reopened.** Diagnosis from the code:
  - The preview progress file is box-global (`/tmp/fansim_cockpit_preview.stl.progress.json`) and never cleared.
  - The ticker's first tick reads the previous run's 4/4 (or 5/5) before the executor writes stage 1, and `max(prev_pct, …)` then pins the bar at 75–80 %.
  - Stage 2 is milliseconds long when chords are disk-cached.
  - The ~3.4 s freeze at the end is `_draw` + `spec_status` + `grade_printability` + `view_update` running synchronously on the event loop.
  - Fixes are suggested in the QA_REVIEW UI-4 row.
- **UI-23:** 0 errors in 9 reloads (961f953, guard off, master). Not reproduced; intermittent; stays LOW/open.
- **New rows:**
  - UI-24 HIGH: Export options sit far below Export STL.
  - UI-25 MED: the carved mesh persists after turning the cup off.
  - UI-26 MED: jargon next to the action buttons.
  - UI-27 MED: the viewer is below the fold at 768p.
  - UI-28 LOW: pale disabled buttons.
  - UI-29 LOW: sparse layout at 1080p.
  - UI-30 MED: every cockpit on the box shares the /tmp preview and progress paths (from code reading).
- **Cockpits:** :8080 (master f238f54) still running; :8081 and :8082 stopped.
