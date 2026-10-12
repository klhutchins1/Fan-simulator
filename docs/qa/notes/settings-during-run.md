# Settings changed while a job runs (QA round 7, Task A)

- **Code:** master `5980677`.
- **Pre-registration:** `settings-during-run-prereg.md`, committed in the QA-only clone `/workspace/fansim/qa/prereg_r6` (branch `prereg/round7`) as `43ce868` (sha256 `465f9fb3…1057ff`) before any testing.
- **Verdict key:**
  - (a) the change alters the running job;
  - (b) the run ignores the change but saves or stamps the changed value;
  - (c) the result is attached to the wrong design;
  - (d) no harm;
  - (e) locked (the job is synchronous).
- **Defects:** (a) without a UI notice, (b) and (c).

## Method
1. **Code reading.** For each job I found where it takes its inputs, then listed every `state.*` / `session.*` read after that point.
2. **Headless reproduction.** The harness is `docs/qa/settings_during_run/harness.py`; its output is `harness_output.json` in the same folder.
   - It is a test harness, not a patch.
   - It builds a real cockpit context, the same way `tests/test_fan_tab_setup_smoke.py` does, on a **real asyncio loop with a real thread executor**.
   - It monkeypatches three runners. Each patched runner records what it was given, sleeps, and then returns a canned result:
     - `fan_assess.evaluate_candidate_isolated`, the runner that `_blocking_eval` calls; the canned result is built from the `flat` the run was given;
     - `fansim.geometry.isolated.build_stl_isolated`, for Preview;
     - `fansim.isolated_job.run_worker_module`, for Export.
   - While the job "runs", the harness changes settings exactly as the UI handlers do (`state.x = …`, `ctx.fan_select(id)`), then compares what the run used with what was saved.
   - The brief asked for a 60 s sleep. I used 3 s, because only the order of events matters. `python harness.py 60` reproduces the same result.
3. **No browser pass.** UI re-testing has been dropped since round 6. Cells marked "code" are from code reading only.

## Snapshot points (where each job takes its inputs)
- **Assess (fan):** `on_assess` takes `params, flat` at the click (`fan_assess.py:331`).
  - The sliders are therefore safe.
  - The **score settings** are not taken at the click. `_blocking_eval` reads preset, wall-ks, spec, refine-op and material when the worker thread starts, effectively at the start (`fan_assess.py:132-145`).
  - At save time, 30–40 min later, the job **reads the live state again**:
    - `state.fan_model` (`:220`, `:297`);
    - `state.assess_material` (`:222`);
    - `state.assess_preset` → `load_pa` / `preset`, and `state.assess_refine_op`, in `_stamp_assess_extra` (`:171-177`);
    - `state.library_parent_id` / `library_place_op` → `parent_id`, `place_op`, `placed_on` (`:225-228`).
  - **Nothing in the UI locks these controls.** The only control bound to `disabled=("assess_busy",)` is the Sweep Run button (`fan_tab_ui.py:959`).
- **Selecting a design changes the score settings.** `fan_trials.select` sets `assess_preset`, `assess_refine_op` and `assess_wall_ks` from the selected design (`fan_trials.py:95-97`) and clears `library_parent_id` (`:47-48`). So **clicking a different design during Assess** rewrites three of the values that get stamped onto the running job's result.
- **Assess-existing (re-score of a `cfd_stale` design):** the target design `cur` is chosen at the start (`:368-374`), so the result goes to the right design. The stamps are read live (`:297`, `:302`), as for Assess.
- **Sweep:** `base_flat` is taken at the click (`:434`). Each step calls `_assess`, so every step's `_blocking_eval` reads the **current** material, preset, spec, refine-op and wall-ks (`:476` → `:132-145`).
- **Optimize (fan):** the whole argv is built at the click (`fan_optimize.py:130-152`), and `fan_model`, preset, refine, wall-ks and material are passed to the subprocess. Merged designs take their stamps from the subprocess's own records (`optimize/cli_argv.py:` `merge_opt_designs`).
- **Preview:**
  - `params, flat, feat` are taken at the click (`fan_viz.py:332-335`).
  - The motor-cup switch and the spec are read when the build thread starts (`:304-305`).
  - After the build, the caption reads the **live** camber sliders (`:420`), and `spec_status` reads the **live** `session.active_spec()` (`:389` → `fan_assess.py:95`).
  - The preview is not saved.
- **Export STL:**
  - The spec, the fitted `flat_x, feat_x` and the basename (from `selected_trial`) are taken at the click (`fan_export.py:151-176`).
  - `also_mirror` is read at task start (`:199`).
  - The file contents are all from the snapshot.
  - The completion message reads the live `state.e_hub_radius` / `e_hub_height` (`:236`, `:241`).
- **Airflow pictures:** guarded by a generation counter and a `selected_trial == token` check (`fan_viz.py:612-647`, `:729-752`). A result for a deselected design is dropped.
- **Fit envelope / Scale to hub:** synchronous handlers (`fan_editor.py:339`, `:388`), so they are locked by construction. Fit hub and Fit frame on export are checkboxes read at the click.
- **Mixed Assess:** the flat and `load_pa` are taken at the click (`mixed_tab.py:348`, `:356`). The saved `extra` reads the live `state.mf_assess_preset` (`:393`) and `state.mf_refine_op` (`:394`); refine-op is used in the run at thread start (`:383`).
- **Prop:**
  - Analyze snapshots `spec, params` at the click (`prop_tab.py:497`).
  - Export snapshots the spec at the click (`:813`), but reads `prop_editor_params()` inside the worker lambda (`:834`), which is a few ms later.
  - Refine snapshots the base, mesh preset and pareto at the click; `spec_key` is read at thread start (`:743`).
- **Volute Assess:** flat, `load_pa` and rpm are taken at the click (`volute_tab.py:372-381`). Nothing is stamped from state afterwards, and the result is not added to a catalog.
- **CROR preview / thin:** the params are built in the worker at thread start (`cror_tab.py:246`, `:321`). Nothing is saved from live state.

## Reproduced (headless harness, `harness_output.json`)
In every scenario the run itself used the starting values (PETG, `case` hose = 8 Pa, refine off, a12x25, camber_mid 0.0834). Only Sweep differs; see A7.

| # | changed during the run | saved on the new result | class |
|---|---|---|---|
| A0 | nothing | PETG, case, 8 Pa, refine off, a12x25 | d (control) |
| A1 | camber slider +0.03 | params camber_mid 0.0834, the start value | d |
| A2 | material → PLA, hose → legacy, refine → on | **material PLA, preset legacy, load_pa 1.0, refine_op True** | **b** |
| A3 | fan model → delta_afc1212de | **fan_model delta_afc1212de**; the Done message says "motor-limited: 2000 RPM (51%)", computed against the wrong spec | **b** |
| A4 | clicked another design (one saved with legacy hose and refine on) | **preset legacy, load_pa 1.0, refine_op True** | **b** (caused by selecting a design) |
| A5 | applied a different library recipe (`library_parent_id` X → Y, as `fan_library.py:83-84` does) | **parent_id LIB_Y**, placed_on = the current model | **c** (lineage attached to the wrong parent) |
| A6 | Assess-existing on #4300, clicked #4301 mid-run | result written to #4300 with #4300's params; #4301 still stale | d; at the end the view jumps back to #4300 (`fan_assess.py:410`) |
| A7 | Sweep (3 steps), material → PLA during step 1 | steps 2–3 **ran with PLA**; step 1 ran with PETG but was **saved as PLA** | **a** (no notice) + **b** |
| P1 | Preview: camber +0.03 and motor cup toggled on | built with camber 0.0834 and no cup; the caption says "camber 0.037/**0.113**/0.097" | d for the build; caption mismatch (display only) |
| E1 | Export: hub radius +3 mm, mirror on, another design selected | file built with hub 21.5 mm, mirror off, named after the design selected at the click | d |

## Job × setting table
- **Cell codes:**
  - **b\*** means the value shown on screen is wrong but nothing is saved. This is outside (a)–(d), so I grade it pass with a LOW note.
  - **r** means the value is read in the worker a few ms after the click. That is a race, not a practical defect.
  - "code" means the cell comes from code reading only. All other entries were reproduced by the harness.
- **Column "slider":** every blade slider. **Column "mesh/refine, wall-ks":** the refine-op and wall-roughness switches.

| job | slider | hose / preset | material | fan model | mesh/refine, wall-ks | motor cup | memory tier | select other design |
|---|---|---|---|---|---|---|---|---|
| Assess | d | **b** | **b** | **b** | refine **b**; wall-ks d (stamped from the run's raw) | n/a | n/a | **b** (rewrites preset/refine/wall-ks); **c** via library parent |
| Assess-existing | d | **b** (code: same `_stamp_assess_extra`) | material not stamped at all (gap) | **b** (code, `:297`) | refine **b** (code) | n/a | n/a | d (target fixed at start); view jumps back |
| Sweep | d (base snapshot) | **a+b** (code: same path as material) | **a+b** | **a+b** (code: spec read per step) | **a+b** (code) | n/a | n/a | **b** (as Assess) |
| Optimize | d | d | d | d | d | n/a | n/a | d |
| Preview | d | n/a | n/a | b\* (verdict uses the live spec) | n/a | d (r) | d (r) | b\* (the preview is drawn over the new selection) |
| Preview with cup | d | n/a | n/a | d (r); verdict b\* | n/a | d (r) | d (r; tier read in the build subprocess) | b\* |
| Export STL | d | n/a | d (spec at click) | d | n/a | d | d (worker subprocess) | d (name from the click) |
| Airflow pictures | n/a | n/a | n/a | n/a | n/a | n/a | n/a | d (token guard) |
| Fit envelope / Scale to hub | e | e | e | e | e | e | e | e |
| Mixed Assess | d | **b** (code `:393`) | n/a | n/a (fixed A12X25) | refine **b** (code `:394`) | n/a | n/a | d (code) |
| Prop Analyze / Export / Refine | d / d (r) / d | n/a | n/a | d (r) | mesh preset d | n/a | n/a | d |
| Volute Assess | d | d (`load_pa` snapshot) | n/a | n/a | n/a | n/a | n/a | d |
| CROR preview / thin | d (r) | n/a | n/a | n/a | n/a | n/a | n/a | d |

Display-only notes: the Preview caption camber (`fan_viz.py:420`) and the Export hub message (`fan_export.py:236/241`) show live values, not the built ones.

## New QA rows
- **QA-22 (MED, b):** Assess, Assess-existing, Sweep and Mixed Assess stamp material, hose / `load_pa`, refine-op and fan model from the **live** state at save time, not from the values the run used. Repro: harness A2, A3.
- **QA-23 (MED, b, the most likely case):** clicking a different design while Assess runs restamps the running job's result with that design's hose and refine-op, because `fan_trials.select` writes `assess_preset` / `assess_refine_op` / `assess_wall_ks` (`fan_trials.py:95-97`). Repro: harness A4.
- **QA-24 (MED, c):** the library lineage (`parent_id` / `place_op` / `placed_on`) is read at save time. Applying a different recipe during Assess saves the result under the wrong parent; selecting a trial or randomizing clears it. Repro: harness A5.
- **QA-25 (LOW–MED, a+b):** a Sweep picks up material, hose, spec, refine and wall-ks changes **between steps** without saying so, and stamps step 1 with the changed value. Repro: harness A7.
- **QA-26 (LOW, display):**
  - The Preview caption shows the live camber sliders, and the Preview verdict uses the live fan model.
  - The Export message shows the live hub radius and height.
  - Assess-existing never stamps `material`.
  - After Assess, the view jumps back to the assessed design.
  - Repro: harness P1 for the caption; the rest from code.

## Recommendation per job (Kimball decides)
| job | recommendation | reason |
|---|---|---|
| Assess / Assess-existing | **snapshot at start and say so**: capture preset, `load_pa`, refine, wall-ks, material, fan model and library parent in `on_assess` next to `flat`, pass them to `_blocking_eval` and `_stamp_assess_extra`, and show "this run uses the settings from when you pressed Assess" | 30–40 min is too long to lock the cockpit, and the run already snapshots geometry, so only the stamps are wrong |
| Sweep | **snapshot at start and say so** (the same capture, once per sweep) | a sweep is hours long, so silently mixing materials across steps makes its points incomparable |
| Design selection during Assess | **snapshot** (fixes QA-23 without a lock); optionally drop the end-of-run `session.select` jump when the user has navigated away | browsing results while CFD runs is the normal workflow |
| Mixed Assess | **snapshot at start** (`hose`, `refine_op` with `load_pa`) | the same bug class as fan Assess |
| Optimize | **no change** (already snapshotted) | the argv captures everything |
| Preview / Preview with cup | **snapshot the caption values and the spec at the click** | builds are already correct; only the caption and verdict drift |
| Export STL | **no change** to the build; build the message from the fitted `flat_x` | the files are correct; only the message reads live sliders |
| Airflow pictures | **no change** | the token guard already drops stale results |
| Fit envelope / Scale to hub | **no change** | synchronous |
| Prop / Volute / CROR | **snapshot in the handler** rather than in the worker lambda (prop export, cror) | it closes a ms-scale race at no cost |
