# r22 A: UI and bug pass (QA-53, R1.4, UI-26, UI-27, UI-29, QA-40, QA-42)

QA bot, 2026-10-29. Master **b3d5543**. Prereg **715891f** §A (`prereg_r6`, `prereg/round22`, before any data).
- **Cockpit:** started from repo-r22 the README way (`scripts/cockpit.py --run runs/opt_mountable --port 8080`, without `--reload`), headless on the box.
- **Browser:** Playwright with system Chrome (`qa/pwvenv`), a fresh context per view.
- **Scripts:** `handoff/2026-10-29_from-qa-22/scripts/a_ui.py`, `a_probe.py` and `a_flowcard.py` (r14 harness, path assert changed).
- **Data:** `data/a_ui.json`, `a_probe.json`, `a_flowcard.json`. Screens stay on the box (`/workspace/fansim/qa_r22/a/screens/`).
- **Not done:** Assess, Sweep or CFD were never clicked; only Preview (≈ 6 s) was.

## Summary

| Item | Status | One line |
|---|---|---|
| QA-53 | **verified** | The cockpit prints `http://127.0.0.1:8080/` = README:137; README:138 "30–40 min" (= the running note `fan_assess.py:332`); README:107 "the GitHub URL" (interim). |
| R1.4 phrase | **verified** | In README:204 (Known limits) and rendered in the Stock Expert caption (`STOCK_RECIPE_GAP`, `fan_trials.py:32`); absent in Simple. |
| UI-26 | **still open** | 2 of 4 are off the first view (camber triplet, Difficulty). "Gold = parametric Stock…" renders on first view in Simple **and** Expert; the hose line renders in Expert. After Preview, "camber 0.024/0.048/0.044" and "Difficulty 33/100 — FDM + supports" render in both modes. |
| UI-27 | **still open** | 1366×768: viewer y 432–957 px (bottom 189 px below the fold, about 36 % hidden). Picker (bottom 552 / 340 px) and Preview (630 / 510 px) are above the fold. |
| UI-29 | **still open** | 1920×1080: controls column 793 px = 41 % ✓, body 16 px ✓; 'Start here' 12 px `text-caption text-medium-emphasis` (rgba 0,0,0,0.6) ✗. |
| QA-40 | **still open** | r14 harness s3 (SWL, no Stock ref): Simple still shows "No Stock comparison for noise." (`flow_verdicts.py:170` not `expert_only`); s1/s2/s4 pass. |
| QA-42 | **still open** | Rendered Preview with PLA+ then PETG: both read "✓ fits Noctua NF-A12x25 (dia 109 mm, depth 16 mm, 11 g)" with no material or infill (`fan_assess.py:128`). |

New: **QA-61** (LOW), **QA-62** (MED), **QA-63** (LOW). QA-41 is re-observed by its own tests (see Pytest).

## Details

**QA-53** (all 3 sub-checks are needed):
- (a) The cockpit log prints `Local: http://127.0.0.1:8080/`, and the README:137 URL is the same.
- (b) README:138 "typically takes 30–40 min" matches the cockpit's own running note (`fan_assess.py:332` "typically 30–40 min free+load").
- (c) README:107 `git clone <the GitHub URL>`. This is the board's interim wording, so it passes (interim). No `<this-repo>`, `9001` or "several minutes" remain.
- Report-only: the README troubleshooting still has no "Docker not installed" / `FileNotFoundError` row (R3.4).
- The static Assess-time copy in the cockpit disagrees with README:138. → QA-61.

**R1.4:**
- The phrase "about 5 % less airflow than the real A12x25" is in README:204 and in `STOCK_RECIPE_GAP`.
- With Expert mode on and Stock selected (cold start already selects `selected_trial` 100000, "◆ Reference · Noctua A12x25 (published)"), the caption renders above Actions.
- In Simple mode the same page does not show it.

**UI-26:** the four strings, by view.

| String | Simple first view | Expert first view | After Preview | Source |
|---|---|---|---|---|
| "… hose · PETG — change under Assess & print below" | no | **yes** | Expert | unchanged, now Expert-only (`fan_tab_ui.py:557-562`) |
| "camber 0.037/0.083/0.097" | no | no | **yes** (both) | `fan_viz.py:494` |
| "Difficulty 42/100 — FDM + supports" | no | no | **yes** (both) | `grade_printability().summary` via `fan_viz.py:467` |
| "Gold = parametric Stock; published CFM is the ✕" | **yes** | **yes** | yes | unchanged (`fan_trials.py:299`), shown after the cold-start Stock load |

**UI-27:**
- Viewer canvas (the visible one at x = 570) is 787×525 at y = 432, with its bottom at 957 px (> 768).
- The intro banner (Simple) no longer pushes the picker below the fold.
- At 1920×1080 the viewer bottom is also 1172 px (> 1080), so the viewer is cut at both sizes.

**UI-29:** only the 'Start here' sub-check fails. It is still a 12 px grey caption (`fan_tab_ui.py:509-513`).

**QA-40:** `a_flowcard.json`: s3 → `noise_visible_in_simple: ["No Stock comparison for noise."]`.

**QA-42:**
- `assess_material` was set through trame state between two Previews. The state read back PLA+ and then PETG, and the line came out identical both times.
- The format string has only `spec.name`, dia, depth and weight.

## New

- **QA-61 (LOW, new) Assess time: cockpit static copy says "~15–30 min"; README and the cockpit's running note say "30–40 min".**
  - **Repro:** the Fan Actions button label "ASSESS (~15–30 MIN)" (`fan_tab_ui.py:594`, rendered); the intro banner (`fan_tab_ui.py:494`, already in QA-58); `fan_core.py:84`; `fan_tab_ui.py:896`; the sweep step note `fan_assess.py:482` "~15–30 min/step".
  - These conflict with README:138 and `fan_assess.py:332` / `run_settings.py:3` ("30–40 min"). `mixed_tab.py:362` "typically 15–30 min" is report-only, since the Mixed time is not measured here.
  - **Proposal:** one constant for the Assess time, used by the README and every label.

## Pytest

Fast suite, one process, on the box: `pytest -m "not docker and not slow" -q`. It started 20:24 MDT and took 40 min 10 s.
**1880 passed, 4 failed**, 21 skipped, 23 deselected, 1 xfailed.
The 4 failures were re-run on their own (`pytest tests/test_fuse_memory.py tests/test_worker_parent_watch.py
tests/test_axial_scripts_oriented.py`, 126 s), and **all 4 failed again**, so none of them is a load flake.
Logs are on the box: `qa_r22/a/pytest_fast.log` and `pytest_rerun.log`.

1. `test_axial_scripts_oriented.py::test_no_unlisted_script_calls_build_case`: "validate_lt120.py: add to
   AXIAL_SCRIPTS or EXEMPT". → **QA-62**.
2. `test_fuse_memory.py::test_remaining_growth_is_less_than_whole_peak_and_shroud_adds_blade_faces`:
   `fuse_remaining_estimate_gb(18 084)` = 1.934 is not less than `fuse_peak_estimate_gb(18 084)` = 1.925 GB. Both are pure functions of the face count, so this fails the same way on every OS. → **QA-63**.
3. and 4. `test_worker_parent_watch.py::test_worker_exits_soon_after_its_parent_dies` and
   `::test_watchdog_runs_the_cleanup_hook_before_exiting`:
   - The worker ran its whole 60 s and wrote `done.txt`, and the cleanup hook never ran.
   - The test's parent is still an unreaped zombie while `subprocess.run` waits on the inherited pipe. `parent_alive` (`fansim/isolated_job.py:87-107`, `os.kill(pid, 0)` off Windows) therefore keeps saying "alive".
   - This is exactly **QA-41** (r14 A3), now shown by the repo's own tests on Linux. No new ID. On Windows the Win32 wait path is used, and it was not tested here.

## New (from pytest)

- **QA-62 (MED, new) `scripts/validate_lt120.py` calls `build_case` but is neither oriented-listed nor exempt.**
  - Introduced with R1.1a `6f25583`. The orientation guard test fails on master b3d5543.
  - The lt120 validation run (R1.1b's night job) bypasses the check that every axial script builds a correctly oriented case. This is the same class as the old bug #7.
  - **Repro:** `uv run --extra dev python -m pytest tests/test_axial_scripts_oriented.py`.
  - **Proposal:** add it to `AXIAL_SCRIPTS` (preferred: orient/flip like the others) before the lt120 night result is used.
- **QA-63 (LOW, new) Fuse RAM guard: the "remaining growth" estimate exceeds the whole-peak estimate at 18 084 faces.**
  - 1.934 vs 1.925 GB. The test's own invariant (`open_rem < peak`) fails on master.
  - It is likely a calibration drift between the two fits (27.1 refit).
  - **Repro:** `pytest tests/test_fuse_memory.py`.
  - **Proposal:** refit one of the two estimates, or fix the test's invariant, so the guard isn't stricter than the peak it diagnoses.
